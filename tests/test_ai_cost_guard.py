"""Tests for the daily cost guard (PH-08 slice 8.2)."""

from __future__ import annotations

import argparse
import io
import json
import os
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from mythic_vibe_cli.ai.cost_guard import (
    COST_CAP_ENV,
    BudgetCheck,
    check_budget,
    compute_today_spend_usd,
)
from mythic_vibe_cli.exit_codes import OPERATIONAL_FAILURE


@contextmanager
def _scrub_env(name: str):
    saved = os.environ.pop(name, None)
    try:
        yield
    finally:
        if saved is not None:
            os.environ[name] = saved


def _today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _seed_ledger(root: Path, entries: list[dict[str, object]]) -> Path:
    """Write JSONL entries to the canonical ledger path."""
    log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")
    return log_path


# ---- compute_today_spend_usd -----------------------------------------


class ComputeTodaySpendTests(unittest.TestCase):
    def test_no_ledger_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(compute_today_spend_usd(Path(tmp)), 0.0)

    def test_sums_today_observed_costs_under_response_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            today = _today_iso()
            _seed_ledger(
                root,
                [
                    {
                        "timestamp": today,
                        "provider": "anthropic",
                        "response": {"metadata": {"observed_cost_usd": 0.12}},
                    },
                    {
                        "timestamp": today,
                        "provider": "openai",
                        "response": {"metadata": {"observed_cost_usd": 0.34}},
                    },
                ],
            )
            self.assertAlmostEqual(
                compute_today_spend_usd(root), 0.46, places=4
            )

    def test_skips_yesterday_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            today = _today_iso()
            _seed_ledger(
                root,
                [
                    {
                        "timestamp": "2026-01-01T00:00:00Z",  # ancient
                        "response": {"metadata": {"observed_cost_usd": 9.99}},
                    },
                    {
                        "timestamp": today,
                        "response": {"metadata": {"observed_cost_usd": 0.10}},
                    },
                ],
            )
            self.assertAlmostEqual(
                compute_today_spend_usd(root), 0.10, places=4
            )

    def test_falls_back_to_top_level_metadata(self) -> None:
        """Some older entries (or future provider variants) record
        observed_cost_usd at the entry's top-level metadata rather
        than nested under response.metadata. The reader handles both."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            today = _today_iso()
            _seed_ledger(
                root,
                [
                    {
                        "timestamp": today,
                        "metadata": {"observed_cost_usd": 0.20},
                    }
                ],
            )
            self.assertAlmostEqual(
                compute_today_spend_usd(root), 0.20, places=4
            )

    def test_corrupt_lines_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            today = _today_iso()
            log_path.write_text(
                json.dumps(
                    {
                        "timestamp": today,
                        "response": {"metadata": {"observed_cost_usd": 0.05}},
                    }
                )
                + "\n"
                + "{not-json\n"
                + json.dumps([1, 2, 3])  # non-dict
                + "\n",
                encoding="utf-8",
            )
            self.assertAlmostEqual(
                compute_today_spend_usd(root), 0.05, places=4
            )

    def test_missing_or_zero_cost_contributes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            today = _today_iso()
            _seed_ledger(
                root,
                [
                    {
                        "timestamp": today,
                        "response": {"metadata": {"observed_cost_usd": 0.0}},
                    },
                    {"timestamp": today, "response": {}},  # no metadata
                    {"timestamp": today},  # no response at all
                ],
            )
            self.assertEqual(compute_today_spend_usd(root), 0.0)


# ---- check_budget -----------------------------------------------------


class CheckBudgetTests(unittest.TestCase):
    def test_disabled_when_no_env_and_no_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with _scrub_env(COST_CAP_ENV):
                check = check_budget(Path(tmp), 5.0)
        self.assertTrue(check.allowed)
        self.assertEqual(check.cap_usd, 0.0)
        self.assertIn("no daily cap", check.reason)

    def test_within_cap_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_ledger(
                root,
                [
                    {
                        "timestamp": _today_iso(),
                        "response": {"metadata": {"observed_cost_usd": 0.50}},
                    }
                ],
            )
            check = check_budget(root, 0.10, cap_usd_override=1.0)
        self.assertTrue(check.allowed)
        self.assertEqual(check.cap_usd, 1.0)
        self.assertAlmostEqual(check.today_spent_usd, 0.50, places=4)
        self.assertIn("within cap", check.reason)

    def test_exceeds_cap_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_ledger(
                root,
                [
                    {
                        "timestamp": _today_iso(),
                        "response": {"metadata": {"observed_cost_usd": 0.95}},
                    }
                ],
            )
            check = check_budget(root, 0.20, cap_usd_override=1.0)
        self.assertFalse(check.allowed)
        self.assertIn("daily cap exceeded", check.reason)

    def test_negative_or_zero_override_disables(self) -> None:
        """An override of 0 or below disables the cap even when the
        env var is set — useful for tests + emergency bypass."""
        try:
            os.environ[COST_CAP_ENV] = "1.0"
            with tempfile.TemporaryDirectory() as tmp:
                check = check_budget(Path(tmp), 5.0, cap_usd_override=0.0)
            self.assertTrue(check.allowed)
            self.assertEqual(check.cap_usd, 0.0)
        finally:
            os.environ.pop(COST_CAP_ENV, None)

    def test_env_var_parsed_when_no_override(self) -> None:
        try:
            os.environ[COST_CAP_ENV] = "0.50"
            with tempfile.TemporaryDirectory() as tmp:
                check = check_budget(Path(tmp), 0.40)
            self.assertTrue(check.allowed)
            self.assertEqual(check.cap_usd, 0.50)
        finally:
            os.environ.pop(COST_CAP_ENV, None)

    def test_garbage_env_treated_as_disabled(self) -> None:
        try:
            os.environ[COST_CAP_ENV] = "not-a-number"
            with tempfile.TemporaryDirectory() as tmp:
                check = check_budget(Path(tmp), 5.0)
            self.assertTrue(check.allowed)
            self.assertEqual(check.cap_usd, 0.0)
        finally:
            os.environ.pop(COST_CAP_ENV, None)

    def test_to_dict_round_trip(self) -> None:
        check = BudgetCheck(
            allowed=True,
            today_spent_usd=0.5,
            cap_usd=1.0,
            projected_cost_usd=0.1,
            reason="ok",
        )
        payload = check.to_dict()
        for key in {
            "allowed",
            "today_spent_usd",
            "cap_usd",
            "projected_cost_usd",
            "reason",
        }:
            self.assertIn(key, payload)


# ---- cmd_ai_run integration ------------------------------------------


class CmdAiRunBudgetGateTests(unittest.TestCase):
    """The gate fires only on live calls; dry-runs always pass through."""

    def _run_namespace(self, **overrides: object) -> argparse.Namespace:
        base = dict(
            path=".",
            provider="copy-paste",
            packet="hello",
            json=True,
            dry_run=False,
            conversation_id="",
            no_record=True,
        )
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_dry_run_skips_budget_check(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_run

        with tempfile.TemporaryDirectory() as tmp:
            ns = self._run_namespace(path=str(tmp), dry_run=True)
            with mock.patch(
                "mythic_vibe_cli.ai.cost_guard.check_budget"
            ) as guard:
                buf = io.StringIO()
                with redirect_stdout(buf):
                    cmd_ai_run(ns)
                guard.assert_not_called()

    def test_blocked_call_returns_operational_failure(self) -> None:
        from mythic_vibe_cli.ai.providers.copy_paste import CopyPasteProvider
        from mythic_vibe_cli.commands import cmd_ai_run

        with tempfile.TemporaryDirectory() as tmp:
            ns = self._run_namespace(path=str(tmp))
            with mock.patch(
                "mythic_vibe_cli.ai.cost_guard.check_budget",
                return_value=BudgetCheck(
                    allowed=False,
                    today_spent_usd=10.0,
                    cap_usd=1.0,
                    projected_cost_usd=0.5,
                    reason="daily cap exceeded",
                ),
            ):
                # Even a "real" CopyPaste call is a no-op (no
                # network), but mocking the provider to a non-dry
                # response makes the assertion meaningful — we never
                # reach provider.run() when blocked.
                with mock.patch.object(
                    CopyPasteProvider, "run"
                ) as run_mock:
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        exit_code = cmd_ai_run(ns)
                    run_mock.assert_not_called()
        self.assertEqual(exit_code, OPERATIONAL_FAILURE)

    def test_within_cap_allows_call(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_run

        with tempfile.TemporaryDirectory() as tmp:
            ns = self._run_namespace(path=str(tmp))
            # No env var, no override → guard returns allowed=True
            # naturally; no mocking needed. Confirm SUCCESS path runs.
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_ai_run(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["command"], "ai run")


if __name__ == "__main__":
    unittest.main()
