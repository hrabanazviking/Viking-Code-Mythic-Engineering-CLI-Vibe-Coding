"""Tests for PH-03 slice 3.4 — forge approval gates.

Two surfaces:

1. ``cmd_forge_plan`` with ``--interactive`` and an injected
   ``gate_handler`` callable. Tests record every gate context the
   handler sees and verify the orchestrator reacts correctly to
   each :data:`GateDecision`.
2. :func:`default_gate_handler` itself, exercised through mocked
   ``input()`` so we lock in the y/n/?/s parsing and the
   default-empty-input behaviour.

No provider call. No real stdin. The non-interactive default path
is already covered by ``tests/test_forge_command.py``; this file
adds coverage for the interactive surface.
"""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from mythic_vibe_cli.exit_codes import SUCCESS
from mythic_vibe_cli.forge import (
    ForgeGateContext,
    cmd_forge_plan,
    default_gate_handler,
)
from mythic_vibe_cli.forge_ledger import ForgeLedger
from mythic_vibe_cli.workflow_engine import DEFAULT_ROLE_SEQUENCE


def _ns(tmp: str, *, interactive: bool = True, skip_ledger: bool = False) -> argparse.Namespace:
    return argparse.Namespace(
        path=tmp,
        task="Slice 3.4 gate test",
        dry_run=True,
        skip_ledger=skip_ledger,
        interactive=interactive,
        json=True,
        quiet=False,
        verbose=False,
    )


# ---- Injected gate handler — round-trip behaviour -----------------------


class GateHandlerInvocationTests(unittest.TestCase):
    def test_handler_called_once_per_pair_when_advancing(self) -> None:
        recorded: list[ForgeGateContext] = []

        def handler(context: ForgeGateContext) -> str:
            recorded.append(context)
            return "advance"

        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                code = cmd_forge_plan(_ns(tmp, skip_ledger=True), gate_handler=handler)
            self.assertEqual(code, SUCCESS)

        # Six steps -> five gates between them.
        self.assertEqual(len(recorded), len(DEFAULT_ROLE_SEQUENCE) - 1)
        # Each gate sees the *completed* role and the *next* role.
        for i, ctx in enumerate(recorded):
            self.assertEqual(ctx.completed_role, DEFAULT_ROLE_SEQUENCE[i])
            self.assertEqual(ctx.next_role, DEFAULT_ROLE_SEQUENCE[i + 1])
            self.assertEqual(ctx.completed_step_index, i)
            self.assertEqual(ctx.total_steps, len(DEFAULT_ROLE_SEQUENCE))

    def test_no_gate_called_when_interactive_is_off(self) -> None:
        recorded: list[ForgeGateContext] = []

        def handler(context: ForgeGateContext) -> str:
            recorded.append(context)
            return "advance"

        with tempfile.TemporaryDirectory() as tmp:
            ns = _ns(tmp, interactive=False, skip_ledger=True)
            with redirect_stdout(io.StringIO()):
                code = cmd_forge_plan(ns, gate_handler=handler)
            self.assertEqual(code, SUCCESS)

        self.assertEqual(recorded, [])

    def test_no_gate_after_final_step(self) -> None:
        """The Scribe step has no following gate (no next role)."""
        seen_completed_roles: list[str] = []

        def handler(context: ForgeGateContext) -> str:
            seen_completed_roles.append(context.completed_role)
            return "advance"

        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                cmd_forge_plan(_ns(tmp, skip_ledger=True), gate_handler=handler)

        # Scribe is the last in DEFAULT_ROLE_SEQUENCE; it should never
        # appear in the completed_role list of a gate context.
        self.assertNotIn("Scribe", seen_completed_roles)


# ---- Decision behaviour --------------------------------------------------


class AbortDecisionTests(unittest.TestCase):
    def test_abort_at_third_gate_marks_remaining_steps_blocked(self) -> None:
        call_count = {"n": 0}

        def handler(context: ForgeGateContext) -> str:
            call_count["n"] += 1
            # Abort right after the second step (between Architect and
            # Cartographer in DEFAULT_ROLE_SEQUENCE: Skald, Architect,
            # Cartographer, Forge Worker, Auditor, Scribe).
            if context.completed_role == "Architect":
                return "abort"
            return "advance"

        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_plan(_ns(tmp), gate_handler=handler)
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())

            # Handler called twice: after Skald (advance) and after
            # Architect (abort). No further calls.
            self.assertEqual(call_count["n"], 2)
            self.assertTrue(payload["aborted"])

            # All six steps appear in the payload — but everything from
            # Cartographer onwards is blocked with the abort note.
            statuses_by_role = {step["role"]: step["status"] for step in payload["steps"]}
            self.assertEqual(statuses_by_role["Skald"], "pending")
            self.assertEqual(statuses_by_role["Architect"], "blocked")  # blocked on prior_outputs
            for blocked_role in ("Cartographer", "Forge Worker", "Auditor", "Scribe"):
                self.assertEqual(
                    statuses_by_role[blocked_role],
                    "blocked",
                    msg=f"{blocked_role} should be blocked after abort",
                )

            # Ledger reflects the abort: the four trailing entries carry
            # "operator aborted at gate" notes.
            ledger = ForgeLedger(root=Path(tmp))
            entries = {e.role: e for e in ledger.load()}
            for blocked_role in ("Cartographer", "Forge Worker", "Auditor", "Scribe"):
                entry = entries[blocked_role]
                self.assertEqual(entry.status, "blocked")
                self.assertIn("operator aborted at gate", entry.notes)


class SkipDecisionTests(unittest.TestCase):
    def test_skip_marks_only_the_next_step_blocked(self) -> None:
        def handler(context: ForgeGateContext) -> str:
            # Skip the next step right after Skald — so Architect is
            # marked blocked. Subsequent gates advance normally.
            if context.completed_role == "Skald":
                return "skip"
            return "advance"

        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                cmd_forge_plan(_ns(tmp), gate_handler=handler)
            payload = json.loads(stdout.getvalue())

            statuses_by_role = {step["role"]: step["status"] for step in payload["steps"]}
            self.assertEqual(statuses_by_role["Skald"], "pending")
            self.assertEqual(statuses_by_role["Architect"], "blocked")
            # Cartographer and onwards re-evaluate their own contracts:
            # they're blocked on prior_outputs in dry-run, but the ledger
            # entry for them does NOT carry the operator-skipped note.
            ledger = ForgeLedger(root=Path(tmp))
            cartographer = next(e for e in ledger.load() if e.role == "Cartographer")
            self.assertNotIn("operator skipped at preceding gate", cartographer.notes)

            architect = next(e for e in ledger.load() if e.role == "Architect")
            self.assertEqual(architect.status, "blocked")
            self.assertIn("operator skipped at preceding gate", architect.notes)

    def test_skip_does_not_abort_rest_of_run(self) -> None:
        recorded: list[str] = []

        def handler(context: ForgeGateContext) -> str:
            recorded.append(context.completed_role)
            if context.completed_role == "Skald":
                return "skip"
            return "advance"

        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                cmd_forge_plan(_ns(tmp), gate_handler=handler)

        # After skipping Architect, the orchestrator continues — so
        # gates fire after Cartographer, Forge Worker, Auditor.
        # (No gate fires after Architect because the step was skipped
        # rather than executed.)
        self.assertIn("Cartographer", recorded)
        self.assertIn("Forge Worker", recorded)
        self.assertIn("Auditor", recorded)


class GateContextRoundTripTests(unittest.TestCase):
    def test_to_dict_preserves_every_field(self) -> None:
        ctx = ForgeGateContext(
            workflow_id="WF-X",
            completed_step_index=2,
            completed_step_id="step-03",
            completed_role="Cartographer",
            completed_status="pending",
            completed_validation_errors=("err1", "err2"),
            next_step_id="step-04",
            next_role="Forge Worker",
            total_steps=6,
        )
        payload = ctx.to_dict()
        self.assertEqual(payload["workflow_id"], "WF-X")
        self.assertEqual(payload["completed_step_index"], 2)
        self.assertEqual(payload["completed_role"], "Cartographer")
        self.assertEqual(payload["completed_validation_errors"], ["err1", "err2"])
        self.assertEqual(payload["next_role"], "Forge Worker")


# ---- default_gate_handler — stdin parsing -------------------------------


def _ctx() -> ForgeGateContext:
    return ForgeGateContext(
        workflow_id="WF-X",
        completed_step_index=0,
        completed_step_id="step-01",
        completed_role="Skald",
        completed_status="pending",
        completed_validation_errors=(),
        next_step_id="step-02",
        next_role="Architect",
        total_steps=6,
    )


class DefaultGateHandlerStdinTests(unittest.TestCase):
    def test_y_returns_advance(self) -> None:
        with patch("builtins.input", side_effect=["y"]):
            self.assertEqual(default_gate_handler(_ctx()), "advance")

    def test_yes_returns_advance(self) -> None:
        with patch("builtins.input", side_effect=["yes"]):
            self.assertEqual(default_gate_handler(_ctx()), "advance")

    def test_empty_returns_advance(self) -> None:
        """Empty input defaults to advance — the safe choice for
        Ctrl+D-style approval flows."""
        with patch("builtins.input", side_effect=[""]):
            self.assertEqual(default_gate_handler(_ctx()), "advance")

    def test_n_returns_abort(self) -> None:
        with patch("builtins.input", side_effect=["n"]):
            self.assertEqual(default_gate_handler(_ctx()), "abort")

    def test_no_returns_abort(self) -> None:
        with patch("builtins.input", side_effect=["no"]):
            self.assertEqual(default_gate_handler(_ctx()), "abort")

    def test_s_returns_skip(self) -> None:
        with patch("builtins.input", side_effect=["s"]):
            self.assertEqual(default_gate_handler(_ctx()), "skip")

    def test_question_mark_reprompts_then_advances(self) -> None:
        """? prints detail (we just verify it doesn't crash) then loops
        back for another response."""
        with patch("builtins.input", side_effect=["?", "y"]) as mock_input:
            self.assertEqual(default_gate_handler(_ctx()), "advance")
            self.assertEqual(mock_input.call_count, 2)

    def test_unknown_response_reprompts(self) -> None:
        with patch("builtins.input", side_effect=["maybe", "y"]) as mock_input:
            self.assertEqual(default_gate_handler(_ctx()), "advance")
            self.assertEqual(mock_input.call_count, 2)

    def test_eof_returns_advance(self) -> None:
        with patch("builtins.input", side_effect=EOFError()):
            self.assertEqual(default_gate_handler(_ctx()), "advance")

    def test_case_insensitive(self) -> None:
        with patch("builtins.input", side_effect=["YES"]):
            self.assertEqual(default_gate_handler(_ctx()), "advance")
        with patch("builtins.input", side_effect=["N"]):
            self.assertEqual(default_gate_handler(_ctx()), "abort")
        with patch("builtins.input", side_effect=["S"]):
            self.assertEqual(default_gate_handler(_ctx()), "skip")


if __name__ == "__main__":
    unittest.main()
