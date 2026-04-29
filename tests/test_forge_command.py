"""Tests for PH-03 slice 3.3 — forge command (dry-run + ledger inspection).

End-to-end tests through ``app.main`` for the user-facing surface,
plus targeted tests of the helpers ``materialize_agent_input`` and
``render_forge_packet`` that build the per-agent packets.
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from mythic_vibe_cli import app
from mythic_vibe_cli.exit_codes import (
    SUCCESS,
    UNSAFE_OPERATION_BLOCKED,
    USER_INPUT_ERROR,
)
from mythic_vibe_cli.forge import materialize_agent_input, render_forge_packet
from mythic_vibe_cli.forge_ledger import ForgeLedger
from mythic_vibe_cli.workflow_engine import DEFAULT_ROLE_SEQUENCE, WorkflowEngine


# ---- forge plan ----------------------------------------------------------


class ForgePlanDryRunTests(unittest.TestCase):
    def test_dry_run_produces_six_role_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    [
                        "forge",
                        "plan",
                        "--dry-run",
                        "--task",
                        "Refactor router",
                        "--path",
                        tmp,
                        "--json",
                    ]
                )
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["command"], "forge plan")
            self.assertTrue(payload["dry_run"])
            self.assertEqual(payload["task"], "Refactor router")
            self.assertEqual(len(payload["steps"]), len(DEFAULT_ROLE_SEQUENCE))
            self.assertEqual(
                [s["role"] for s in payload["steps"]],
                list(DEFAULT_ROLE_SEQUENCE),
            )

    def test_dry_run_writes_ledger_entries_by_default(self) -> None:
        """Each role gets one ledger row. Skald passes contract
        validation (only needs task+phase) and lands as `pending`;
        every other role fails contract validation in dry-run because
        their contracts require `prior_outputs` (which slice 3.5 will
        populate from the ledger when previous agents have completed).
        Today they correctly land as `blocked` with the validation
        error in `notes`. The test pins this designed-failure-mode so
        slice 3.5 can observe the transition to `pending`.
        """
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "forge",
                        "plan",
                        "--dry-run",
                        "--task",
                        "Smoke",
                        "--path",
                        tmp,
                    ]
                )
            ledger = ForgeLedger(root=Path(tmp))
            entries = ledger.load()
            self.assertEqual(len(entries), len(DEFAULT_ROLE_SEQUENCE))
            for entry, expected_role in zip(entries, DEFAULT_ROLE_SEQUENCE):
                self.assertEqual(entry.role, expected_role)
                self.assertTrue(entry.workflow_id.startswith("WF-"))
                self.assertTrue(entry.step_id.startswith("step-"))
                self.assertEqual(entry.agent_input.role, expected_role)
            # Skald passes; rest are blocked on missing prior_outputs.
            by_role = {e.role: e for e in entries}
            self.assertEqual(by_role["Skald"].status, "pending")
            self.assertEqual(by_role["Skald"].notes, ())
            for blocked_role in ("Architect", "Cartographer", "Forge Worker", "Auditor", "Scribe"):
                entry = by_role[blocked_role]
                self.assertEqual(entry.status, "blocked", msg=f"{blocked_role} should be blocked")
                self.assertTrue(
                    any("prior_outputs" in note for note in entry.notes),
                    msg=f"{blocked_role} notes should explain the prior_outputs gap",
                )

    def test_skip_ledger_flag_writes_no_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "forge",
                        "plan",
                        "--dry-run",
                        "--task",
                        "Smoke",
                        "--skip-ledger",
                        "--path",
                        tmp,
                    ]
                )
            ledger = ForgeLedger(root=Path(tmp))
            self.assertEqual(ledger.load(), [])
            self.assertFalse(ledger.path.exists())

    def test_dry_run_text_output_renders_per_agent_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    [
                        "forge",
                        "plan",
                        "--dry-run",
                        "--task",
                        "Refactor router",
                        "--path",
                        tmp,
                    ]
                )
            self.assertEqual(code, SUCCESS)
            output = stdout.getvalue()
            self.assertIn("Mythic forge plan", output)
            self.assertIn("Per-agent packets", output)
            self.assertIn("Mythic Forge Packet", output)
            for role in DEFAULT_ROLE_SEQUENCE:
                self.assertIn(role, output)

    def test_dry_run_json_packet_contains_role_and_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                app.main(
                    [
                        "forge",
                        "plan",
                        "--dry-run",
                        "--task",
                        "X",
                        "--path",
                        tmp,
                        "--json",
                    ]
                )
            payload = json.loads(stdout.getvalue())
            architect = next(s for s in payload["steps"] if s["role"] == "Architect")
            packet = architect["packet"]
            self.assertIn("Architect", packet)
            self.assertIn("Identity:", packet)
            self.assertIn("System prompt", packet)
            self.assertIn("AgentInput payload", packet)
            self.assertIn("GATE:", packet)


class ForgePlanGuardsTests(unittest.TestCase):
    def test_missing_task_is_blocked_by_argparse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as cm, redirect_stderr(io.StringIO()):
                app.main(["forge", "plan", "--dry-run", "--path", tmp])
            self.assertEqual(cm.exception.code, 2)

    def test_blank_task_after_strip_returns_user_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = app.main(
                    [
                        "forge",
                        "plan",
                        "--dry-run",
                        "--task",
                        "   ",
                        "--path",
                        tmp,
                    ]
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("requires --task", stderr.getvalue())

    def test_non_dry_run_blocked_until_slice_3_5(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = app.main(
                    [
                        "forge",
                        "plan",
                        "--task",
                        "Real run",
                        "--path",
                        tmp,
                    ]
                )
            self.assertEqual(code, UNSAFE_OPERATION_BLOCKED)
            self.assertIn("Provider-backed forge is not enabled", stderr.getvalue())


# ---- materialize_agent_input + render_forge_packet ----------------------


class MaterializeAgentInputTests(unittest.TestCase):
    def test_input_carries_workflow_identity_and_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("Refactor router")
            architect_step = next(s for s in plan.steps if s.role == "Architect")
            agent_input = materialize_agent_input(plan, architect_step)
            self.assertEqual(agent_input.role, "Architect")
            self.assertEqual(agent_input.task, "Refactor router")
            self.assertEqual(agent_input.phase, "architecture")
            self.assertEqual(agent_input.workflow_id, plan.workflow_id)
            self.assertEqual(agent_input.workflow_step_id, architect_step.step_id)
            self.assertTrue(any("GATE:" in inv for inv in agent_input.invariants))

    def test_input_passes_contract_validation(self) -> None:
        from mythic_vibe_cli.workflow_agents import contract_for, validate_input

        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("Smoke")
            for step in plan.steps:
                agent_input = materialize_agent_input(plan, step)
                contract = contract_for(step.role)
                errors = validate_input(agent_input, contract)
                if step.role == "Skald":
                    # Skald requires only task + phase — should pass.
                    self.assertEqual(errors, [], msg=f"{step.role} validation: {errors}")
                else:
                    # Other roles require prior_outputs in slice 3.1; in
                    # dry-run we know they'll fail validation. The forge
                    # command surfaces this as status="blocked" but
                    # continues — slice 3.5 will fix this by populating
                    # prior_outputs from the ledger.
                    self.assertTrue(
                        any("prior_outputs" in err for err in errors),
                        msg=f"{step.role} should flag missing prior_outputs",
                    )


class RenderForgePacketTests(unittest.TestCase):
    def test_packet_contains_canonical_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("Refactor router")
            scribe_step = next(s for s in plan.steps if s.role == "Scribe")
            agent_input = materialize_agent_input(plan, scribe_step)
            packet = render_forge_packet(plan, scribe_step, agent_input)
            for section in [
                "Mythic Forge Packet",
                "## 1. Role",
                "## 2. System prompt",
                "## 3. Step objective",
                "## 4. Invariants",
                "## 5. Verification (gates that must pass to advance)",
                "## 6. Expected output artefacts",
                "## 7. AgentInput payload",
            ]:
                self.assertIn(section, packet)

    def test_packet_lists_contract_artefact_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            architect_step = next(s for s in plan.steps if s.role == "Architect")
            agent_input = materialize_agent_input(plan, architect_step)
            packet = render_forge_packet(plan, architect_step, agent_input)
            self.assertIn("ARCHITECTURE.md", packet)
            self.assertIn("DOMAIN_MAP.md", packet)


# ---- forge ledger list / latest / show ----------------------------------


class ForgeLedgerListTests(unittest.TestCase):
    def _seed(self, tmp: str) -> None:
        with redirect_stdout(io.StringIO()):
            app.main(
                ["forge", "plan", "--dry-run", "--task", "seed", "--path", tmp]
            )

    def test_list_text_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._seed(tmp)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["forge", "ledger", "list", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            output = stdout.getvalue()
            self.assertIn(f"Forge ledger ({len(DEFAULT_ROLE_SEQUENCE)} entries)", output)
            for role in DEFAULT_ROLE_SEQUENCE:
                self.assertIn(role, output)

    def test_list_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._seed(tmp)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["forge", "ledger", "list", "--json", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["count"], len(DEFAULT_ROLE_SEQUENCE))
            self.assertEqual(len(payload["entries"]), len(DEFAULT_ROLE_SEQUENCE))

    def test_list_on_empty_project_reports_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["forge", "ledger", "list", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            self.assertIn("Forge ledger is empty", stdout.getvalue())


class ForgeLedgerLatestTests(unittest.TestCase):
    def test_latest_window_respects_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                app.main(["forge", "plan", "--dry-run", "--task", "seed", "--path", tmp])
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    ["forge", "ledger", "latest", "--limit", "2", "--json", "--path", tmp]
                )
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["limit"], 2)
            self.assertEqual(payload["count"], 2)


class ForgeLedgerShowTests(unittest.TestCase):
    def test_show_returns_entries_for_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                payload_run = io.StringIO()
                with redirect_stdout(payload_run):
                    app.main(
                        [
                            "forge",
                            "plan",
                            "--dry-run",
                            "--task",
                            "seed",
                            "--path",
                            tmp,
                            "--json",
                        ]
                    )
                workflow_id = json.loads(payload_run.getvalue())["workflow_id"]

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    [
                        "forge",
                        "ledger",
                        "show",
                        "--workflow",
                        workflow_id,
                        "--json",
                        "--path",
                        tmp,
                    ]
                )
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["workflow_id"], workflow_id)
            self.assertEqual(payload["count"], len(DEFAULT_ROLE_SEQUENCE))
            self.assertEqual(
                {e["role"] for e in payload["entries"]},
                set(DEFAULT_ROLE_SEQUENCE),
            )

    def test_show_filters_by_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                payload_run = io.StringIO()
                with redirect_stdout(payload_run):
                    app.main(
                        [
                            "forge",
                            "plan",
                            "--dry-run",
                            "--task",
                            "seed",
                            "--path",
                            tmp,
                            "--json",
                        ]
                    )
                workflow_id = json.loads(payload_run.getvalue())["workflow_id"]

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    [
                        "forge",
                        "ledger",
                        "show",
                        "--workflow",
                        workflow_id,
                        "--step",
                        "step-03",
                        "--json",
                        "--path",
                        tmp,
                    ]
                )
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["count"], 1)
            self.assertEqual(payload["entries"][0]["step_id"], "step-03")

    def test_show_unknown_workflow_returns_user_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = app.main(
                    [
                        "forge",
                        "ledger",
                        "show",
                        "--workflow",
                        "WF-DOES-NOT-EXIST",
                        "--path",
                        tmp,
                    ]
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("No ledger entries", stderr.getvalue())


# ---- forge dispatcher fall-through --------------------------------------


class ForgeDispatcherFallthroughTests(unittest.TestCase):
    """Every dispatcher in this slice should surface an error, never
    exit silently with code 2 (per the slice 1.3 F-006/F-007 fix
    pattern)."""

    def test_forge_dispatcher_unknown_subcommand(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_dispatch
        import argparse

        ns = argparse.Namespace(forge_command="bogus")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = cmd_forge_dispatch(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        self.assertIn("Unknown forge subcommand", stderr.getvalue())

    def test_forge_ledger_dispatcher_unknown_subcommand(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_ledger_dispatch
        import argparse

        ns = argparse.Namespace(ledger_command="bogus")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = cmd_forge_ledger_dispatch(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        self.assertIn("Unknown forge ledger subcommand", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
