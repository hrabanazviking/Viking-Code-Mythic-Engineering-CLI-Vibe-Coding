"""Tests for PH-14 Slices 14.2 + 14.3 + 14.4.

Covers the policy gate (evaluate / enforce_policy), the override
log, and the cmd_oath wiring + cmd_policy_report aggregator.
"""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from mythic_vibe_cli.commands import (
    cmd_oath,
    cmd_policy_dispatch,
    cmd_policy_report,
)
from mythic_vibe_cli.exit_codes import (
    SUCCESS,
    UNSAFE_OPERATION_BLOCKED,
    USER_INPUT_ERROR,
)
from mythic_vibe_cli.policy.constraint_store import (
    Constraint,
    SEVERITY_ADVISORY,
    SEVERITY_BLOCKING,
    SEVERITY_WARN,
)
from mythic_vibe_cli.policy.override_log import (
    OVERRIDE_LOG_PATH,
    OverrideRecord,
    append_override,
    read_overrides,
)
from mythic_vibe_cli.policy.policy_gate import (
    PolicyDecision,
    enforce_policy,
    evaluate,
    evaluate_for_root,
)


# ---- evaluate --------------------------------------------------------


class EvaluateTests(unittest.TestCase):
    def test_no_constraints_allows(self) -> None:
        decision = evaluate([], action="write", command="oath")
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_override)
        self.assertEqual(decision.violations, [])

    def test_only_warn_advisory_allows(self) -> None:
        constraints = [
            Constraint(
                id="r1", kind="rule", text="be nice", severity=SEVERITY_WARN
            ),
            Constraint(
                id="r2", kind="rule", text="be brave", severity=SEVERITY_ADVISORY
            ),
        ]
        decision = evaluate(constraints, action="write", command="oath")
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_override)
        # Notes describe the bypass.
        self.assertTrue(any("no blocking" in n for n in decision.notes))

    def test_blocking_constraint_blocks(self) -> None:
        constraints = [
            Constraint(
                id="b1",
                kind="rule",
                text="never break the law",
                severity=SEVERITY_BLOCKING,
            ),
            Constraint(
                id="r2", kind="rule", text="be brave", severity=SEVERITY_WARN
            ),
        ]
        decision = evaluate(constraints, action="write", command="oath")
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_override)
        self.assertEqual([c.id for c in decision.violations], ["b1"])

    def test_decision_to_dict(self) -> None:
        decision = PolicyDecision(allowed=True)
        payload = decision.to_dict()
        for key in {
            "allowed",
            "violations",
            "requires_override",
            "notes",
            "violation_count",
        }:
            self.assertIn(key, payload)

    # ---- Phase A.2 regression (2026-05-02 audit, finding #3) ----------
    #
    # ``evaluate()`` accepts ``Iterable[Constraint]``. Before the fix,
    # the function exhausted the iterable in the list-comprehension at
    # the top of the body, then called ``any(constraints)`` on the same
    # now-empty iterator a few lines later. List inputs were fine
    # (lists support multiple iteration); generator inputs silently
    # suppressed the advisory note. The fix materialises the iterable
    # once at the top of evaluate(); these tests lock the contract.

    def test_generator_input_with_warn_only_still_emits_note(self) -> None:
        """Regression for finding #3: a generator yielding warn/advisory
        constraints should still produce the "no blocking" advisory
        note. Pre-fix this returned an empty notes list because
        ``any(constraints)`` ran on an exhausted generator."""
        def constraint_stream():
            yield Constraint(
                id="r1", kind="rule", text="be nice", severity=SEVERITY_WARN
            )
            yield Constraint(
                id="r2", kind="rule", text="be brave", severity=SEVERITY_ADVISORY
            )

        decision = evaluate(constraint_stream(), action="write", command="oath")
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_override)
        self.assertTrue(
            any("no blocking" in n for n in decision.notes),
            f"expected advisory note, got notes={decision.notes!r}",
        )

    def test_generator_input_with_blocking_constraint_still_blocks(self) -> None:
        """A generator yielding a blocking constraint must still
        produce the blocking decision (not silently skipped because
        the iterator was exhausted)."""
        def constraint_stream():
            yield Constraint(
                id="b1",
                kind="rule",
                text="never break the law",
                severity=SEVERITY_BLOCKING,
            )
            yield Constraint(
                id="r2", kind="rule", text="be brave", severity=SEVERITY_WARN
            )

        decision = evaluate(constraint_stream(), action="write", command="oath")
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_override)
        self.assertEqual([c.id for c in decision.violations], ["b1"])

    def test_iterator_input_yields_same_decision_as_list(self) -> None:
        """Parity check: list vs iter() of the same constraints must
        produce the same decision (allowed, requires_override,
        violation IDs, and the presence of the advisory note when
        applicable)."""
        constraints = [
            Constraint(
                id="r1", kind="rule", text="be nice", severity=SEVERITY_WARN
            ),
        ]
        list_decision = evaluate(constraints, action="write", command="oath")
        iter_decision = evaluate(iter(constraints), action="write", command="oath")
        self.assertEqual(list_decision.allowed, iter_decision.allowed)
        self.assertEqual(
            list_decision.requires_override, iter_decision.requires_override
        )
        self.assertEqual(
            [c.id for c in list_decision.violations],
            [c.id for c in iter_decision.violations],
        )
        # Both must surface the advisory note.
        self.assertTrue(any("no blocking" in n for n in list_decision.notes))
        self.assertTrue(any("no blocking" in n for n in iter_decision.notes))


# ---- evaluate_for_root -----------------------------------------------


class EvaluateForRootTests(unittest.TestCase):
    def test_loads_and_evaluates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "constraints.md").write_text(
                "- never break the law [blocking]\n",
                encoding="utf-8",
            )
            decision = evaluate_for_root(
                root, action="write", command="oath"
            )
        self.assertFalse(decision.allowed)
        self.assertEqual(len(decision.violations), 1)


# ---- enforce_policy --------------------------------------------------


class EnforcePolicyTests(unittest.TestCase):
    def test_allows_when_no_constraints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proceed, decision = enforce_policy(
                Path(tmp), action="write", command="oath"
            )
        self.assertTrue(proceed)
        self.assertFalse(decision.requires_override)

    def test_blocks_when_blocking_constraint_no_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "constraints.md").write_text(
                "- never break the law [blocking]\n",
                encoding="utf-8",
            )
            proceed, decision = enforce_policy(
                root, action="write", command="oath"
            )
        self.assertFalse(proceed)
        self.assertTrue(decision.requires_override)

    def test_override_allows_and_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "constraints.md").write_text(
                "- never break the law [blocking]\n",
                encoding="utf-8",
            )
            proceed, decision = enforce_policy(
                root,
                action="write",
                command="oath",
                override_reason="urgent fire — operator approved",
            )
            ledger = root / OVERRIDE_LOG_PATH
            ledger_exists = ledger.is_file()
            ledger_lines = ledger.read_text(encoding="utf-8").splitlines() if ledger_exists else []
        self.assertTrue(proceed)
        self.assertTrue(ledger_exists)
        self.assertEqual(len(ledger_lines), 1)
        payload = json.loads(ledger_lines[0])
        self.assertEqual(payload["command"], "oath")
        self.assertEqual(payload["reason"], "urgent fire — operator approved")
        self.assertGreaterEqual(len(payload["violation_ids"]), 1)


# ---- override log ----------------------------------------------------


class OverrideLogTests(unittest.TestCase):
    def test_append_then_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            append_override(
                root,
                action="write",
                command="oath",
                reason="reason A",
                violation_ids=["b1", "b2"],
            )
            append_override(
                root,
                action="write",
                command="checkin",
                reason="reason B",
            )
            records = read_overrides(root)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].reason, "reason A")
        self.assertEqual(records[0].violation_ids, ("b1", "b2"))

    def test_read_missing_ledger_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(read_overrides(Path(tmp)), [])

    def test_skip_malformed_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / OVERRIDE_LOG_PATH).write_text(
                'this is not json\n{"timestamp":"x","reason":"good"}\n',
                encoding="utf-8",
            )
            records = read_overrides(root)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].reason, "good")

    def test_record_to_from_dict_round_trip(self) -> None:
        original = OverrideRecord(
            timestamp="2026-05-01T00:00:00Z",
            action="write",
            command="oath",
            reason="x",
            actor="tester",
            host="hostX",
            violation_ids=("a", "b"),
        )
        payload = original.to_dict()
        rebuilt = OverrideRecord.from_dict(payload)
        self.assertEqual(rebuilt, original)


# ---- cmd_oath wired ---------------------------------------------------


class CmdOathPolicyTests(unittest.TestCase):
    def _ns(self, path: str, **overrides: object) -> argparse.Namespace:
        base = dict(path=path, yes=False, override="")
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_no_constraints_runs_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_oath(self._ns(tmp))
        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("AI may generate", buf.getvalue())

    def test_blocking_constraint_blocks_without_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "constraints.md").write_text(
                "- never break the law [blocking]\n",
                encoding="utf-8",
            )
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                with redirect_stdout(io.StringIO()):
                    exit_code = cmd_oath(self._ns(str(root)))
        self.assertEqual(exit_code, UNSAFE_OPERATION_BLOCKED)
        self.assertIn("Policy gate blocks", stderr.getvalue())

    def test_blocking_constraint_with_override_proceeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "constraints.md").write_text(
                "- never break the law [blocking]\n",
                encoding="utf-8",
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_oath(
                    self._ns(str(root), override="acknowledged risk")
                )
            ledger_exists = (root / OVERRIDE_LOG_PATH).is_file()
        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("Policy override accepted", buf.getvalue())
        self.assertTrue(ledger_exists)


# ---- cmd_policy_report -----------------------------------------------


class CmdPolicyReportTests(unittest.TestCase):
    def _ns(self, path: str, *, json_mode: bool = True) -> argparse.Namespace:
        return argparse.Namespace(path=path, json=json_mode)

    def test_empty_repo_returns_zero_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_policy_report(self._ns(tmp))
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertEqual(payload["counts"]["constraints"], 0)
        self.assertEqual(payload["counts"]["overrides"], 0)

    def test_constraints_and_overrides_aggregated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "constraints.md").write_text(
                "- rule A [blocking]\n- rule B [warn]\n- rule C [advisory]\n",
                encoding="utf-8",
            )
            append_override(
                root,
                action="write",
                command="oath",
                reason="reason A",
                violation_ids=["rule:rule-a"],
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_policy_report(self._ns(str(root)))
            payload = json.loads(buf.getvalue())
        self.assertEqual(payload["counts"]["constraints"], 3)
        self.assertEqual(payload["counts"]["overrides"], 1)
        self.assertEqual(payload["counts"]["severity"][SEVERITY_BLOCKING], 1)
        self.assertEqual(payload["counts"]["severity"][SEVERITY_WARN], 1)
        self.assertEqual(payload["counts"]["severity"][SEVERITY_ADVISORY], 1)

    def test_text_mode_shows_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "constraints.md").write_text(
                "- never break the law [blocking]\n",
                encoding="utf-8",
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_policy_report(self._ns(str(root), json_mode=False))
        output = buf.getvalue()
        self.assertIn("Mythic policy report", output)
        self.assertIn("Constraints", output)
        self.assertIn("never break the law", output)


class CmdPolicyDispatchTests(unittest.TestCase):
    def test_unknown_subcommand_returns_user_input_error(self) -> None:
        ns = argparse.Namespace(policy_command="ghost")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = cmd_policy_dispatch(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)
        self.assertIn("Unknown policy subcommand", stderr.getvalue())


class PolicyArgparseTests(unittest.TestCase):
    def test_oath_accepts_override_and_path(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(
            ["oath", "--path", ".", "--override", "test reason"]
        )
        self.assertEqual(ns.command, "oath")
        self.assertEqual(ns.override, "test reason")

    def test_policy_report_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["policy", "report", "--json"])
        self.assertEqual(ns.command, "policy")
        self.assertEqual(ns.policy_command, "report")


if __name__ == "__main__":
    unittest.main()
