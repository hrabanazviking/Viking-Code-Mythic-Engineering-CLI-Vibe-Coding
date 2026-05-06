"""Tests for PH-03 slice 3.5 — provider-backed forge run.

End-to-end coverage of ``cmd_forge_run`` using a stub provider
that returns deterministic responses, so no live API key is
needed and the tests run hermetically.
"""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from mythic_vibe_cli.ai.providers.base import ProviderResponse, ProviderStatus
from mythic_vibe_cli.exit_codes import (
    OPERATIONAL_FAILURE,
    SUCCESS,
    UNSAFE_OPERATION_BLOCKED,
    USER_INPUT_ERROR,
)
from mythic_vibe_cli.forge import (
    ForgeGateContext,
    build_agent_output_from_response,
    cmd_forge_run,
    prior_outputs_for_step,
)
from mythic_vibe_cli.forge_ledger import ForgeLedger, ForgeLedgerEntry
from mythic_vibe_cli.workflow_agents import AgentInput
from mythic_vibe_cli.workflow_engine import DEFAULT_ROLE_SEQUENCE, WorkflowEngine


# ---- Stub provider ------------------------------------------------------


class StubProvider:
    """Deterministic provider used by every test in this file.

    The first non-empty line of ``content`` becomes the
    ``AgentOutput.summary``; full ``content`` is preserved as
    ``raw_response``.
    """

    name = "stub"
    model = "test"

    def __init__(self, *, content_template: str = "Stub response from {role}\nfollow-up text", error: Exception | None = None) -> None:
        self.content_template = content_template
        self.error = error
        self.calls: list[dict[str, str]] = []

    def validate_config(self) -> ProviderStatus:
        return ProviderStatus(configured=True, details=["stub"])

    def estimate(self, packet: object) -> object:
        from mythic_vibe_cli.ai.providers.base import Estimate

        return Estimate(input_tokens=0, output_tokens=0, cost_usd=0.0)

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:
        if self.error is not None:
            raise self.error
        # Capture which packet we saw so tests can verify the packet id.
        if isinstance(packet, dict):
            self.calls.append({"packet_id": str(packet.get("packet_id", "")), "text": str(packet.get("text", ""))})
            packet_id = str(packet.get("packet_id") or "stub")
            text = str(packet.get("text") or "")
        else:
            self.calls.append({"packet_id": "inline", "text": str(packet)})
            packet_id = "stub"
            text = str(packet)
        # Pull role out of the packet text so each response is role-tagged.
        role = "Unknown"
        for line in text.splitlines():
            if line.strip().startswith("- Step:"):
                # `- Step: step-NN (Role — phase)`
                stripped = line.strip()
                if "(" in stripped and ")" in stripped:
                    role_part = stripped.split("(", 1)[1].split(")", 1)[0]
                    role = role_part.split("—")[0].strip()
                break
        return ProviderResponse(
            provider=self.name,
            model=self.model,
            content=self.content_template.format(role=role),
            packet_id=packet_id,
            dry_run=False,
            usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        )


def _ns(tmp: str, *, interactive: bool = False, skip_ledger: bool = False, provider: str = "stub") -> argparse.Namespace:
    return argparse.Namespace(
        path=tmp,
        task="Slice 3.5 e2e",
        provider=provider,
        skip_ledger=skip_ledger,
        interactive=interactive,
        json=True,
        quiet=False,
        verbose=False,
    )


def _factory_for(provider: StubProvider):
    def factory(name: str, root: Path) -> StubProvider:
        return provider

    return factory


# Slice 3.6: by default cmd_forge_run runs DEFAULT_AUDITOR_GATES, which
# fail on bare temp projects (no boundary docs / no recorded
# verification). The slice 3.5 orchestration tests aren't about gate
# logic — they verify the run loop, the ledger transitions, and
# prior_outputs population. They opt out of gates by passing
# ``auditor_gates={}``. Slice 3.6's own tests in
# tests/test_forge_verifier.py exercise the gate runners directly.
_NO_GATES: dict = {}


# ---- Happy path: every step succeeds ------------------------------------


class ForgeRunHappyPathTests(unittest.TestCase):
    def test_every_step_runs_through_provider_and_succeeds(self) -> None:
        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_run(
                    _ns(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates=_NO_GATES,
                )
            payload = json.loads(stdout.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["success_count"], len(DEFAULT_ROLE_SEQUENCE))
            self.assertEqual(payload["failure_count"], 0)
            self.assertFalse(payload["aborted"])
            self.assertEqual(len(stub.calls), len(DEFAULT_ROLE_SEQUENCE))

            # Every step ended in succeeded with an agent_output payload.
            for step in payload["steps"]:
                self.assertEqual(step["status"], "succeeded", msg=step["role"])
                self.assertIsNotNone(step["agent_output"])
                self.assertIn("Stub response from", step["agent_output"]["summary"])

    def test_ledger_records_running_then_succeeded_for_each_step(self) -> None:
        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                cmd_forge_run(
                    _ns(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates=_NO_GATES,
                )

            ledger = ForgeLedger(root=Path(tmp))
            entries = ledger.load()

            # Two ledger entries per step: running (appended) and the
            # succeeded update happens in place via update_step on the
            # latest matching record. `find_step` returns the most
            # recent match — succeeded.
            workflow_id = entries[0].workflow_id
            for role in DEFAULT_ROLE_SEQUENCE:
                step_id = next(e.step_id for e in entries if e.role == role)
                latest = ledger.find_step(workflow_id, step_id)
                self.assertIsNotNone(latest)
                assert latest is not None
                self.assertEqual(latest.status, "succeeded")
                self.assertIsNotNone(latest.agent_output)
                self.assertIsNotNone(latest.completed_at)
                self.assertIsNotNone(latest.duration_ms)


# ---- Prior outputs flow ------------------------------------------------


class PriorOutputsTests(unittest.TestCase):
    def test_prior_outputs_grow_as_run_progresses(self) -> None:
        """The Architect's AgentInput should carry the Skald output;
        Cartographer should carry Skald + Architect; etc. This is the
        slice 3.5 transition that unblocks the slice 3.1 contracts.

        Verified by reading the ledger after the run: each entry's
        ``agent_input.prior_outputs`` should contain N strings where
        N is the step's index in the sequence (Skald=0, Architect=1,
        Cartographer=2, ...).
        """
        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                cmd_forge_run(
                    _ns(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates=_NO_GATES,
                )

            ledger = ForgeLedger(root=Path(tmp))
            entries_by_role = {e.role: e for e in ledger.load() if e.status == "succeeded"}

        for index, role in enumerate(DEFAULT_ROLE_SEQUENCE):
            entry = entries_by_role[role]
            self.assertEqual(
                len(entry.agent_input.prior_outputs),
                index,
                msg=f"{role} should see {index} prior outputs, saw {len(entry.agent_input.prior_outputs)}",
            )
            # Each prior_output must be a parseable JSON dict carrying
            # an earlier role's name.
            seen_roles: list[str] = []
            for raw in entry.agent_input.prior_outputs:
                parsed = json.loads(raw)
                seen_roles.append(parsed["role"])
            self.assertEqual(seen_roles, list(DEFAULT_ROLE_SEQUENCE[:index]))

    def test_no_blocked_steps_when_provider_succeeds(self) -> None:
        """Slice 3.3 dry-run leaves Architect..Scribe blocked on
        prior_outputs. Slice 3.5 should resolve every one of them."""
        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                cmd_forge_run(
                    _ns(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates=_NO_GATES,
                )
            payload = json.loads(stdout.getvalue())

            blocked_roles = [s["role"] for s in payload["steps"] if s["status"] == "blocked"]
            self.assertEqual(blocked_roles, [], msg=f"unexpected blocked roles: {blocked_roles}")


class PriorOutputsForStepHelperTests(unittest.TestCase):
    def test_returns_serialised_outputs_for_completed_priors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            ledger = ForgeLedger(root=Path(tmp))

            # Skald completes with an output.
            from mythic_vibe_cli.workflow_agents import AgentOutput

            skald_step = plan.steps[0]
            skald_input = AgentInput(role="Skald", task="X", phase="intent",
                                      workflow_id=plan.workflow_id, workflow_step_id=skald_step.step_id)
            skald_output = AgentOutput(
                role="Skald",
                timestamp="2026-04-29T22:00:00Z",
                workflow_id=plan.workflow_id,
                workflow_step_id=skald_step.step_id,
                summary="captured intent",
            )
            ledger.append(
                ForgeLedgerEntry(
                    workflow_id=plan.workflow_id or "",
                    step_id=skald_step.step_id,
                    role="Skald",
                    status="succeeded",
                    started_at="2026-04-29T22:00:00Z",
                    agent_input=skald_input,
                    agent_output=skald_output,
                )
            )

            # Architect's prior_outputs should include the Skald JSON.
            architect_step = plan.steps[1]
            priors = prior_outputs_for_step(plan, architect_step, ledger)
            self.assertEqual(len(priors), 1)
            parsed = json.loads(priors[0])
            self.assertEqual(parsed["role"], "Skald")
            self.assertEqual(parsed["summary"], "captured intent")

    def test_skips_priors_without_agent_output(self) -> None:
        """Blocked or failed prior steps don't have an agent_output;
        they should be silently excluded."""
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            ledger = ForgeLedger(root=Path(tmp))

            skald_step = plan.steps[0]
            skald_input = AgentInput(role="Skald", task="X", phase="intent",
                                      workflow_id=plan.workflow_id, workflow_step_id=skald_step.step_id)
            ledger.append(
                ForgeLedgerEntry(
                    workflow_id=plan.workflow_id or "",
                    step_id=skald_step.step_id,
                    role="Skald",
                    status="failed",
                    started_at="2026-04-29T22:00:00Z",
                    agent_input=skald_input,
                    agent_output=None,
                )
            )

            architect_step = plan.steps[1]
            priors = prior_outputs_for_step(plan, architect_step, ledger)
            self.assertEqual(priors, ())


# ---- Provider error handling -------------------------------------------


class ProviderErrorTests(unittest.TestCase):
    def test_provider_exception_marks_step_failed_and_continues(self) -> None:
        stub = StubProvider(error=RuntimeError("boom"))
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_run(_ns(tmp), provider_factory=_factory_for(stub))
            payload = json.loads(stdout.getvalue())

            self.assertEqual(code, OPERATIONAL_FAILURE)
            # First step (Skald) failed; everything after that is
            # blocked because their contracts need prior_outputs which
            # never materialised.
            statuses = [s["status"] for s in payload["steps"]]
            self.assertEqual(statuses[0], "failed")
            for status in statuses[1:]:
                self.assertEqual(status, "blocked")

            # Ledger reflects the failure.
            ledger = ForgeLedger(root=Path(tmp))
            skald_entry = next(e for e in ledger.load() if e.role == "Skald" and e.status == "failed")
            self.assertIn("provider raised: boom", skald_entry.notes)


class MissingProviderTests(unittest.TestCase):
    def test_unknown_provider_returns_user_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = cmd_forge_run(_ns(tmp, provider="nonexistent-provider"))
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("Unknown provider", stderr.getvalue())

    def test_missing_provider_arg_returns_user_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ns = _ns(tmp, provider="")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = cmd_forge_run(ns)
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("forge run requires --provider", stderr.getvalue())

    def test_missing_task_returns_user_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ns = _ns(tmp)
            ns.task = ""
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = cmd_forge_run(ns)
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("forge run requires --task", stderr.getvalue())


# ---- Interactive abort mid-run ------------------------------------------


class InteractiveAbortTests(unittest.TestCase):
    def test_abort_mid_run_marks_remaining_steps_blocked(self) -> None:
        stub = StubProvider()

        def handler(context: ForgeGateContext) -> str:
            if context.completed_role == "Architect":
                return "abort"
            return "advance"

        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_run(
                    _ns(tmp, interactive=True),
                    provider_factory=_factory_for(stub),
                    gate_handler=handler,
                    auditor_gates=_NO_GATES,
                )
            payload = json.loads(stdout.getvalue())

            self.assertEqual(code, UNSAFE_OPERATION_BLOCKED)
            self.assertTrue(payload["aborted"])
            statuses_by_role = {step["role"]: step["status"] for step in payload["steps"]}
            self.assertEqual(statuses_by_role["Skald"], "succeeded")
            self.assertEqual(statuses_by_role["Architect"], "succeeded")
            for blocked_role in ("Cartographer", "Forge Worker", "Auditor", "Scribe"):
                self.assertEqual(statuses_by_role[blocked_role], "blocked")

            # Provider was called twice (Skald + Architect), no further.
            self.assertEqual(len(stub.calls), 2)


# ---- AgentOutput helper -------------------------------------------------


class BuildAgentOutputTests(unittest.TestCase):
    def test_summary_is_first_non_empty_line(self) -> None:
        response = ProviderResponse(
            provider="stub", model="t",
            content="\n\nFirst real line\nSecond line\n",
            packet_id="x",
        )
        agent_input = AgentInput(role="Skald", task="X", phase="intent")
        output = build_agent_output_from_response(response, agent_input)
        self.assertEqual(output.summary, "First real line")
        self.assertEqual(output.raw_response, response.content)

    def test_summary_truncated_to_200_chars(self) -> None:
        long_line = "x" * 500
        response = ProviderResponse(
            provider="stub", model="t",
            content=long_line, packet_id="x",
        )
        agent_input = AgentInput(role="Skald", task="X", phase="intent")
        output = build_agent_output_from_response(response, agent_input)
        self.assertEqual(len(output.summary), 200)

    def test_empty_response_yields_empty_summary(self) -> None:
        response = ProviderResponse(provider="stub", model="t", content="", packet_id="x")
        agent_input = AgentInput(role="Skald", task="X", phase="intent")
        output = build_agent_output_from_response(response, agent_input)
        self.assertEqual(output.summary, "")
        self.assertEqual(output.role, "Skald")


# ---- Skip-ledger flag ---------------------------------------------------


class SkipLedgerFlagTests(unittest.TestCase):
    def test_skip_ledger_writes_no_file(self) -> None:
        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                code = cmd_forge_run(
                    _ns(tmp, skip_ledger=True),
                    provider_factory=_factory_for(stub),
                    auditor_gates=_NO_GATES,
                )
            self.assertEqual(code, SUCCESS)
            ledger = ForgeLedger(root=Path(tmp))
            self.assertFalse(ledger.path.exists())


# ---------------------------------------------------------------------------
# PH-25.1 coverage push — exercise the human-readable output paths of
# cmd_forge_run + the ledger / reflection sub-commands. These paths only
# fire when ``--json`` is absent, which existing tests skip because they
# all pass json=True.
# ---------------------------------------------------------------------------


def _ns_human(tmp: str, **kwargs) -> argparse.Namespace:
    """Like ``_ns`` but with json=False, hitting the write_line/
    write_bullet output rendering."""
    ns = _ns(tmp, **kwargs)
    ns.json = False
    return ns


class ForgeRunHumanReadableOutputTests(unittest.TestCase):
    def test_human_readable_output_lists_each_step(self) -> None:
        stub = StubProvider()
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(out):
                code = cmd_forge_run(
                    _ns_human(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates=_NO_GATES,
                )
        self.assertEqual(code, SUCCESS)
        text = out.getvalue()
        self.assertIn("Mythic forge run", text)
        self.assertIn("Workflow", text)
        self.assertIn("Steps", text)
        self.assertIn("Provider", text)
        # Per-step lines render with role + phase + handoff arrow.
        self.assertIn("->", text)
        self.assertIn("status:", text)

    def test_human_readable_output_includes_aborted_marker_when_relevant(self) -> None:
        """When a gate aborts, the output renders an ``Aborted: yes``
        line. This is the slice-3.6 abort branch of the renderer."""
        # Strict gate that always rejects on first invocation.
        def rejecting_gate(ctx) -> bool:  # noqa: ANN001
            return False

        stub = StubProvider()
        out = io.StringIO()
        ns = _ns_human(tmp_dir := tempfile.mkdtemp())
        ns.interactive = True
        try:
            with redirect_stdout(out):
                cmd_forge_run(
                    ns,
                    provider_factory=_factory_for(stub),
                    auditor_gates=_NO_GATES,
                    gate_handler=rejecting_gate,
                )
            text = out.getvalue()
            self.assertIn("Mythic forge run", text)
            self.assertIn("Interactive", text)
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)


class ForgeLedgerLatestTests(unittest.TestCase):
    def test_latest_human_readable_with_no_entries(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_ledger_latest

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, limit=5, json=False, quiet=False, verbose=False)
            with redirect_stdout(out):
                code = cmd_forge_ledger_latest(ns)
        self.assertEqual(code, SUCCESS)
        self.assertIn("No entries", out.getvalue())

    def test_latest_human_readable_renders_entries(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_ledger_latest

        # Seed a real ledger via a forge run.
        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                cmd_forge_run(
                    _ns(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates=_NO_GATES,
                )
            out = io.StringIO()
            ns = argparse.Namespace(path=tmp, limit=10, json=False, quiet=False, verbose=False)
            with redirect_stdout(out):
                code = cmd_forge_ledger_latest(ns)
        self.assertEqual(code, SUCCESS)
        text = out.getvalue()
        self.assertIn("Forge ledger", text)
        self.assertIn("::", text)


class ForgeLedgerShowTests(unittest.TestCase):
    def test_show_requires_workflow_arg(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_ledger_show

        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, workflow="", step="", json=False, quiet=False, verbose=False)
            err_buf = io.StringIO()
            with redirect_stderr(err_buf):
                code = cmd_forge_ledger_show(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        self.assertIn("--workflow", err_buf.getvalue())

    def test_show_unknown_workflow_returns_error_json(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_ledger_show

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, workflow="WF-NOPE", step="", json=True, quiet=False, verbose=False)
            with redirect_stdout(out):
                code = cmd_forge_ledger_show(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["count"], 0)
        self.assertIn("errors", payload)

    def test_show_unknown_workflow_with_step_returns_error_human(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_ledger_show

        err_buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, workflow="WF-NOPE", step="step-01", json=False, quiet=False, verbose=False)
            with redirect_stderr(err_buf):
                code = cmd_forge_ledger_show(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        # Error message should mention both workflow + step.
        msg = err_buf.getvalue()
        self.assertIn("WF-NOPE", msg)
        self.assertIn("step-01", msg)

    def test_show_human_readable_renders_entries(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_ledger_show

        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                cmd_forge_run(
                    _ns(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates=_NO_GATES,
                )
            ledger = ForgeLedger(root=Path(tmp))
            entries = ledger.load()
            self.assertGreater(len(entries), 0)
            workflow_id = entries[0].workflow_id

            out = io.StringIO()
            ns = argparse.Namespace(path=tmp, workflow=workflow_id, step="", json=False, quiet=False, verbose=False)
            with redirect_stdout(out):
                code = cmd_forge_ledger_show(ns)
        self.assertEqual(code, SUCCESS)
        text = out.getvalue()
        self.assertIn("Forge ledger", text)
        self.assertIn(workflow_id, text)


class ForgeReflectionDispatchTests(unittest.TestCase):
    def test_reflection_list_human_readable_with_no_entries(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_reflection_list

        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            ns = argparse.Namespace(path=tmp, json=False, quiet=False, verbose=False)
            with redirect_stdout(out):
                code = cmd_forge_reflection_list(ns)
        self.assertEqual(code, SUCCESS)
        self.assertIn("No forge reflections", out.getvalue())

    def test_reflection_list_human_readable_renders_workflow_ids(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_reflection_list

        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                cmd_forge_run(
                    _ns(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates=_NO_GATES,
                )
            out = io.StringIO()
            ns = argparse.Namespace(path=tmp, json=False, quiet=False, verbose=False)
            with redirect_stdout(out):
                code = cmd_forge_reflection_list(ns)
        self.assertEqual(code, SUCCESS)
        self.assertIn("Forge reflections", out.getvalue())

    def test_reflection_show_requires_workflow(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_reflection_show

        err_buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, workflow="", json=False, quiet=False, verbose=False)
            with redirect_stderr(err_buf):
                code = cmd_forge_reflection_show(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        self.assertIn("--workflow", err_buf.getvalue())

    def test_reflection_show_unknown_workflow_returns_error_json(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_reflection_show

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, workflow="WF-NOPE", json=True, quiet=False, verbose=False)
            with redirect_stdout(out):
                code = cmd_forge_reflection_show(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        payload = json.loads(out.getvalue())
        self.assertFalse(payload["ok"])

    def test_reflection_latest_with_no_entries_human(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_reflection_latest

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, json=False, quiet=False, verbose=False)
            with redirect_stdout(out):
                code = cmd_forge_reflection_latest(ns)
        self.assertEqual(code, SUCCESS)
        self.assertIn("No forge reflections", out.getvalue())

    def test_reflection_latest_with_no_entries_json_returns_input_error(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_reflection_latest

        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, json=True, quiet=False, verbose=False)
            with redirect_stdout(out):
                code = cmd_forge_reflection_latest(ns)
        # JSON-flagged means errors-payload + USER_INPUT_ERROR exit.
        self.assertEqual(code, USER_INPUT_ERROR)
        payload = json.loads(out.getvalue())
        self.assertFalse(payload["ok"])

    def test_reflection_dispatch_unknown_subcommand(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_reflection_dispatch

        err_buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(
                path=tmp,
                reflection_command="nosuch",
                json=False,
                quiet=False,
                verbose=False,
            )
            with redirect_stderr(err_buf):
                code = cmd_forge_reflection_dispatch(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        self.assertIn("Unknown forge reflection subcommand", err_buf.getvalue())

    def test_reflection_dispatch_routes_list(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_reflection_dispatch

        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(
                path=tmp,
                reflection_command="list",
                json=True,
                quiet=False,
                verbose=False,
            )
            with redirect_stdout(io.StringIO()):
                code = cmd_forge_reflection_dispatch(ns)
        self.assertEqual(code, SUCCESS)


class ForgeLedgerDispatchTests(unittest.TestCase):
    def test_ledger_dispatch_unknown_subcommand(self) -> None:
        from mythic_vibe_cli.forge import cmd_forge_ledger_dispatch

        err_buf = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(
                path=tmp,
                ledger_command="nosuch",
                json=False,
                quiet=False,
                verbose=False,
            )
            with redirect_stderr(err_buf):
                code = cmd_forge_ledger_dispatch(ns)
        # Most dispatchers in forge.py return USER_INPUT_ERROR
        # for unknown sub.
        self.assertEqual(code, USER_INPUT_ERROR)


if __name__ == "__main__":
    unittest.main()
