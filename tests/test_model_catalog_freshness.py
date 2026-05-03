"""Phase 19.8 (audit remediation 2026-05-02) — tests for the
stale-catalog watchdog.

Covers:

- ``evaluate_catalog_freshness`` pure-function behaviour against
  injected ``today`` dates: fresh, exactly-at-threshold, just-over-
  threshold, malformed input.
- The ``cmd_doctor`` integration adds a ``model_catalog`` block to
  ``--json`` output without changing existing exit codes.
- The text-output path renders the freshness line in fresh / stale
  / parse-error cases.

Pure-stdlib tests; no network, no real provider calls.
"""

from __future__ import annotations

import io
import unittest
from datetime import date, timedelta
from unittest import mock

from mythic_vibe_cli.ai.providers.model_catalog import (
    DEFAULT_CATALOG_STALENESS_DAYS,
    STATIC_LAST_UPDATED,
    CatalogFreshness,
    evaluate_catalog_freshness,
)


class EvaluateCatalogFreshnessTests(unittest.TestCase):
    """Pure-function behaviour with injected ``today``."""

    def test_fresh_catalog_when_within_threshold(self) -> None:
        result = evaluate_catalog_freshness(
            threshold_days=90,
            today=date(2026, 5, 10),
            last_updated="2026-05-02",
        )
        self.assertIsInstance(result, CatalogFreshness)
        self.assertFalse(result.is_stale)
        self.assertEqual(result.days_since_update, 8)
        self.assertEqual(result.threshold_days, 90)
        self.assertIsNone(result.parse_error)

    def test_exactly_at_threshold_is_still_fresh(self) -> None:
        """The boundary is ``> threshold``, not ``>=``. Day 90
        exactly should not warn."""
        result = evaluate_catalog_freshness(
            threshold_days=90,
            today=date(2026, 5, 2) + timedelta(days=90),
            last_updated="2026-05-02",
        )
        self.assertEqual(result.days_since_update, 90)
        self.assertFalse(result.is_stale)

    def test_one_day_past_threshold_is_stale(self) -> None:
        result = evaluate_catalog_freshness(
            threshold_days=90,
            today=date(2026, 5, 2) + timedelta(days=91),
            last_updated="2026-05-02",
        )
        self.assertEqual(result.days_since_update, 91)
        self.assertTrue(result.is_stale)

    def test_malformed_last_updated_treated_as_stale(self) -> None:
        """Defensive: a hand-edited fork could break the date
        format. Surface the parse error and treat as stale."""
        result = evaluate_catalog_freshness(
            threshold_days=90,
            today=date(2026, 5, 10),
            last_updated="not a date",
        )
        self.assertTrue(result.is_stale)
        self.assertIsNotNone(result.parse_error)
        self.assertEqual(result.days_since_update, -1)

    def test_default_threshold_matches_documented_value(self) -> None:
        """The 90-day default is part of the operator contract —
        if it changes, the threat-model + compatibility-policy
        docs need to follow."""
        self.assertEqual(DEFAULT_CATALOG_STALENESS_DAYS, 90)

    def test_default_uses_static_last_updated_constant(self) -> None:
        """When no last_updated is passed, the helper reads the
        module-level constant — the same one curators bump when
        refreshing the catalog."""
        result = evaluate_catalog_freshness(
            threshold_days=10_000,
            today=date(2030, 1, 1),
        )
        self.assertEqual(result.last_updated, STATIC_LAST_UPDATED)


class DoctorJsonIntegrationTests(unittest.TestCase):
    """The doctor handler emits a ``model_catalog`` JSON block and
    a text-output freshness line. Test both surfaces without
    actually shelling out."""

    def _run_doctor(self, *, json_mode: bool, tmp_path) -> str:
        import argparse
        import sys

        from mythic_vibe_cli.commands import cmd_doctor

        # Argparse Namespace mirrors what app.py builds in real
        # invocations.
        ns = argparse.Namespace(
            path=str(tmp_path),
            json=json_mode,
            repo_boundary=False,
        )
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured
        try:
            cmd_doctor(ns)
        finally:
            sys.stdout = original_stdout
        return captured.getvalue()

    def test_json_payload_includes_model_catalog_block(self) -> None:
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            output = self._run_doctor(json_mode=True, tmp_path=tmp)
        payload = json.loads(output)
        self.assertIn("model_catalog", payload)
        catalog = payload["model_catalog"]
        for key in (
            "last_updated", "threshold_days",
            "days_since_update", "is_stale", "parse_error",
        ):
            self.assertIn(key, catalog)

    def test_text_output_includes_catalog_line(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            output = self._run_doctor(json_mode=False, tmp_path=tmp)
        self.assertIn("Model catalog", output)


class DoctorTextOutputBranchesTests(unittest.TestCase):
    """Cover the three text-output branches by patching
    ``evaluate_catalog_freshness`` to return controlled fixtures —
    avoids depending on the wall-clock date for branch coverage."""

    def _capture(self, fixture: CatalogFreshness) -> str:
        import argparse
        import io
        import sys
        import tempfile

        from mythic_vibe_cli import commands as commands_module

        ns = argparse.Namespace(
            path=tempfile.mkdtemp(),
            json=False,
            repo_boundary=False,
        )
        captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured
        try:
            with mock.patch.object(
                commands_module,
                # Imported INSIDE cmd_doctor so we patch where the
                # name is resolved (the module of the providers
                # subpackage), not the import site.
                # But cmd_doctor uses `from .ai.providers.model_catalog
                # import evaluate_catalog_freshness` at function scope.
                # Simplest patch is at the SOURCE module — that's
                # what the function-level import resolves to.
                "evaluate_catalog_freshness",
                create=True,
                new=lambda **kwargs: fixture,
            ):
                # The patch above won't take effect because cmd_doctor
                # imports the symbol fresh inside the function. Patch
                # the source module instead.
                with mock.patch(
                    "mythic_vibe_cli.ai.providers.model_catalog."
                    "evaluate_catalog_freshness",
                    return_value=fixture,
                ):
                    commands_module.cmd_doctor(ns)
        finally:
            sys.stdout = original_stdout
        return captured.getvalue()

    def test_fresh_branch(self) -> None:
        out = self._capture(CatalogFreshness(
            last_updated="2026-05-02",
            threshold_days=90,
            days_since_update=10,
            is_stale=False,
        ))
        self.assertIn("fresh", out)
        self.assertIn("2026-05-02", out)

    def test_stale_branch(self) -> None:
        out = self._capture(CatalogFreshness(
            last_updated="2025-01-01",
            threshold_days=90,
            days_since_update=487,
            is_stale=True,
        ))
        self.assertIn("STALE", out)
        self.assertIn("487", out)

    def test_parse_error_branch(self) -> None:
        out = self._capture(CatalogFreshness(
            last_updated="garbage",
            threshold_days=90,
            days_since_update=-1,
            is_stale=True,
            parse_error="invalid format",
        ))
        self.assertIn("malformed", out)
        self.assertIn("invalid format", out)


if __name__ == "__main__":
    unittest.main()
