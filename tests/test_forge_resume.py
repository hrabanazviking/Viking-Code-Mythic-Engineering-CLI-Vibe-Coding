"""Tests for PH-03 slice 3.8 — forge resume.

End-to-end tests using stub providers and gate handlers. The pattern:

1. ``forge run`` to seed a partial workflow (succeeded prefix +
   failed/blocked tail, or a strict-abort).
2. ``forge resume`` against the same workflow.
3. Verify the resume re-executed only the unfinished steps, that
   prior_outputs flowed correctly, and that the reflection was
   rewritten.
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
    USER_INPUT_ERROR,
)
from mythic_vibe_cli.forge import (
    cmd_forge_resume,
    cmd_forge_run,
)
from mythic_vibe_cli.forge_ledger import ForgeLedger
from mythic_vibe_cli.forge_reflection import load_forge_reflection
from mythic_vibe_cli.workflow_agents import VerificationResult
from mythic_vibe_cli.workflow_engine import DEFAULT_ROLE_SEQUENCE


# ---- Stub provider ------------------------------------------------------


class StubProvider:
    """Provider with optional per-role error injection."""

    name = "stub"

    def __init__(self, *, raise_for_role: str | None = None, response_template: str = "{role} response v{run}") -> None:
        self.raise_for_role = raise_for_role
        self.response_template = response_template
        self.run_count = 0
        self.calls_by_role: dict[str, int] = {}

    def validate_config(self) -> ProviderStatus:
        return ProviderStatus(configured=True, details=["stub"])

    def estimate(self, packet: object) -> object:
        from mythic_vibe_cli.ai.providers.base import Estimate

        return Estimate(0, 0, 0.0)

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:
        text = ""
        if isinstance(packet, dict):
            text = str(packet.get("text") or "")
        role = "Unknown"
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("- Step:") and "(" in stripped and ")" in stripped:
                role = stripped.split("(", 1)[1].split(")", 1)[0].split("—")[0].strip()
                break
        self.calls_by_role[role] = self.calls_by_role.get(role, 0) + 1
        if self.raise_for_role and role == self.raise_for_role:
            raise RuntimeError(f"stub failure on {role}")
        self.run_count += 1
        return ProviderResponse(
            provider=self.name,
            model="t",
            content=self.response_template.format(role=role, run=self.run_count),
            packet_id="stub-pkt",
            dry_run=False,
        )


def _factory_for(provider: StubProvider):
    def factory(name: str, root: Path) -> StubProvider:
        return provider

    return factory


def _ns_run(tmp: str, **overrides: object) -> argparse.Namespace:
    base = {
        "path": tmp,
        "task": "Slice 3.8 resume",
        "provider": "stub",
        "skip_ledger": False,
        "interactive": False,
        "strict": False,
        "skip_reflection": False,
        "json": True,
        "quiet": False,
        "verbose": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _ns_resume(tmp: str, **overrides: object) -> argparse.Namespace:
    base = {
        "path": tmp,
        "provider": "stub",
        "workflow": "",
        "skip_ledger": False,
        "interactive": False,
        "strict": False,
        "skip_reflection": False,
        "json": True,
        "quiet": False,
        "verbose": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


# ---- Resume after provider failure -------------------------------------


class ResumeAfterProviderFailureTests(unittest.TestCase):
    def test_resume_reruns_only_failed_and_remaining_steps(self) -> None:
        """Seed a run where the Auditor fails. Resume should skip
        Skald/Architect/Cartographer/Forge Worker (all succeeded) and
        only re-execute Auditor + Scribe."""
        with tempfile.TemporaryDirectory() as tmp:
            # Seed run: Auditor raises.
            failing_provider = StubProvider(raise_for_role="Auditor")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                seed_code = cmd_forge_run(
                    _ns_run(tmp),
                    provider_factory=_factory_for(failing_provider),
                    auditor_gates={},
                )
            json.loads(stdout.getvalue())  # parsed for shape only
            self.assertEqual(seed_code, OPERATIONAL_FAILURE)
            self.assertEqual(failing_provider.calls_by_role.get("Auditor", 0), 1)

            # Resume: replace the failing provider with one that
            # succeeds for every role.
            healing_provider = StubProvider()
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                resume_code = cmd_forge_resume(
                    _ns_resume(tmp),
                    provider_factory=_factory_for(healing_provider),
                    auditor_gates={},
                )
            resume_payload = json.loads(stdout.getvalue())

            self.assertEqual(resume_code, SUCCESS)
            self.assertFalse(resume_payload["noop"])
            self.assertEqual(resume_payload["resume_step_id"], "step-05")  # Auditor

            # Skipped steps are the four prior succeeded ones.
            self.assertEqual(
                resume_payload["skipped_already_succeeded"],
                ["step-01", "step-02", "step-03", "step-04"],
            )

            # Healing provider only saw Auditor + Scribe (the resume).
            self.assertEqual(set(healing_provider.calls_by_role.keys()), {"Auditor", "Scribe"})

            # Both re-executed steps succeeded.
            self.assertEqual(resume_payload["success_count"], 2)
            self.assertEqual(resume_payload["failure_count"], 0)

            # Final ledger state: every step succeeded (latest entry
            # per step wins — Auditor's new succeeded entry replaces
            # the old failed one).
            ledger = ForgeLedger(root=Path(tmp))
            workflow_id = resume_payload["workflow_id"]
            for role in DEFAULT_ROLE_SEQUENCE:
                step_id = next(
                    e.step_id for e in ledger.find_by_workflow(workflow_id) if e.role == role
                )
                latest = ledger.find_step(workflow_id, step_id)
                assert latest is not None
                self.assertEqual(latest.status, "succeeded", msg=f"{role} should be succeeded after resume")

    def test_resume_writes_a_new_reflection_replacing_the_old_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            failing = StubProvider(raise_for_role="Architect")
            with redirect_stdout(io.StringIO()):
                cmd_forge_run(
                    _ns_run(tmp),
                    provider_factory=_factory_for(failing),
                    auditor_gates={},
                )

            # The original reflection records the failure.
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                seed_payload_run = json.loads(stdout.getvalue() or "{}")  # noqa: F841
            ledger = ForgeLedger(root=Path(tmp))
            workflow_id = ledger.load()[0].workflow_id
            original = load_forge_reflection(Path(tmp), workflow_id)
            assert original is not None
            self.assertEqual(original.final_status, "failure")
            self.assertEqual(original.failure_count, 1)

            # Resume with healing provider.
            healing = StubProvider()
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_resume(
                    _ns_resume(tmp),
                    provider_factory=_factory_for(healing),
                    auditor_gates={},
                )
            self.assertEqual(code, SUCCESS)

            # New reflection has final_status=success.
            updated = load_forge_reflection(Path(tmp), workflow_id)
            assert updated is not None
            self.assertEqual(updated.final_status, "success")
            self.assertEqual(updated.failure_count, 0)
            self.assertEqual(updated.success_count, len(DEFAULT_ROLE_SEQUENCE))


# ---- Resume after Auditor gate failure --------------------------------


class ResumeAfterGateFailureTests(unittest.TestCase):
    def test_resume_with_passing_gates_recovers_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Seed run: provider succeeds for everyone but Auditor's
            # gates fail.
            failing_gates = {
                "diff-reviewed-against-architecture": lambda *args, **kw: VerificationResult(
                    name="diff-reviewed-against-architecture", passed=True
                ),
                "no-invariant-violation": lambda *args, **kw: VerificationResult(
                    name="no-invariant-violation", passed=False, detail="seed failure"
                ),
                "test-evidence-recorded": lambda *args, **kw: VerificationResult(
                    name="test-evidence-recorded", passed=True
                ),
            }
            stub = StubProvider()
            with redirect_stdout(io.StringIO()):
                code = cmd_forge_run(
                    _ns_run(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates=failing_gates,
                )
            self.assertEqual(code, OPERATIONAL_FAILURE)

            # Resume with passing gates.
            passing_gates = {
                "diff-reviewed-against-architecture": lambda *args, **kw: VerificationResult(
                    name="diff-reviewed-against-architecture", passed=True
                ),
                "no-invariant-violation": lambda *args, **kw: VerificationResult(
                    name="no-invariant-violation", passed=True
                ),
                "test-evidence-recorded": lambda *args, **kw: VerificationResult(
                    name="test-evidence-recorded", passed=True
                ),
            }
            stub2 = StubProvider()
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_resume(
                    _ns_resume(tmp),
                    provider_factory=_factory_for(stub2),
                    auditor_gates=passing_gates,
                )
            payload = json.loads(stdout.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["resume_step_id"], "step-05")  # Auditor
            # Auditor + Scribe re-executed.
            self.assertEqual(set(stub2.calls_by_role.keys()), {"Auditor", "Scribe"})


# ---- Resume by --workflow ----------------------------------------------


class ResumeByWorkflowIdTests(unittest.TestCase):
    def test_resume_picks_specified_workflow_over_latest(self) -> None:
        """Run two workflows; resume the older one explicitly."""
        with tempfile.TemporaryDirectory() as tmp:
            # First run fails on Architect.
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                cmd_forge_run(
                    _ns_run(tmp, task="task A"),
                    provider_factory=_factory_for(StubProvider(raise_for_role="Architect")),
                    auditor_gates={},
                )
            run1_workflow = json.loads(stdout.getvalue())["workflow_id"]

            # Second run also fails (different task).
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                cmd_forge_run(
                    _ns_run(tmp, task="task B"),
                    provider_factory=_factory_for(StubProvider(raise_for_role="Skald")),
                    auditor_gates={},
                )
            run2_workflow = json.loads(stdout.getvalue())["workflow_id"]
            self.assertNotEqual(run1_workflow, run2_workflow)

            # Resume the OLDER one explicitly.
            stub = StubProvider()
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_resume(
                    _ns_resume(tmp, workflow=run1_workflow),
                    provider_factory=_factory_for(stub),
                    auditor_gates={},
                )
            payload = json.loads(stdout.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["workflow_id"], run1_workflow)
            self.assertEqual(payload["task"], "task A")
            # Resume started from Architect (Architect failed in run 1).
            self.assertEqual(payload["resume_step_id"], "step-02")

    def test_resume_with_no_workflow_picks_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # First run succeeds.
            with redirect_stdout(io.StringIO()):
                cmd_forge_run(
                    _ns_run(tmp, task="task A"),
                    provider_factory=_factory_for(StubProvider()),
                    auditor_gates={},
                )

            # Second run fails on Auditor.
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                cmd_forge_run(
                    _ns_run(tmp, task="task B"),
                    provider_factory=_factory_for(StubProvider(raise_for_role="Auditor")),
                    auditor_gates={},
                )
            run2_workflow = json.loads(stdout.getvalue())["workflow_id"]

            # Resume without --workflow picks task B (the latest entry).
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_resume(
                    _ns_resume(tmp),
                    provider_factory=_factory_for(StubProvider()),
                    auditor_gates={},
                )
            payload = json.loads(stdout.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["workflow_id"], run2_workflow)


# ---- Resume edge cases -------------------------------------------------


class ResumeNoOpTests(unittest.TestCase):
    def test_resume_when_every_step_already_succeeded_returns_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Seed a successful run.
            with redirect_stdout(io.StringIO()):
                cmd_forge_run(
                    _ns_run(tmp),
                    provider_factory=_factory_for(StubProvider()),
                    auditor_gates={},
                )

            # Resume: nothing to do.
            stub = StubProvider()
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_resume(
                    _ns_resume(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates={},
                )
            payload = json.loads(stdout.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertTrue(payload["noop"])
            self.assertIn("Every step already succeeded", payload["message"])
            # Provider was NOT called during the no-op resume.
            self.assertEqual(stub.run_count, 0)


class ResumeUserErrorTests(unittest.TestCase):
    def test_no_ledger_entries_returns_user_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = cmd_forge_resume(
                    _ns_resume(tmp),
                    provider_factory=_factory_for(StubProvider()),
                    auditor_gates={},
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("nothing to resume", stderr.getvalue())

    def test_unknown_workflow_returns_user_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Seed a run so the ledger isn't empty.
            with redirect_stdout(io.StringIO()):
                cmd_forge_run(
                    _ns_run(tmp),
                    provider_factory=_factory_for(StubProvider()),
                    auditor_gates={},
                )
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = cmd_forge_resume(
                    _ns_resume(tmp, workflow="WF-NOT-A-WORKFLOW"),
                    provider_factory=_factory_for(StubProvider()),
                    auditor_gates={},
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("WF-NOT-A-WORKFLOW", stderr.getvalue())

    def test_missing_provider_returns_user_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ns = _ns_resume(tmp, provider="")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = cmd_forge_resume(ns)
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("forge resume requires --provider", stderr.getvalue())


# ---- Resume preserves workflow_id continuity ---------------------------


class ResumeWorkflowIdContinuityTests(unittest.TestCase):
    def test_resumed_steps_share_the_original_workflow_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                cmd_forge_run(
                    _ns_run(tmp),
                    provider_factory=_factory_for(StubProvider(raise_for_role="Auditor")),
                    auditor_gates={},
                )
            ledger = ForgeLedger(root=Path(tmp))
            original_workflow = ledger.load()[0].workflow_id

            with redirect_stdout(io.StringIO()):
                cmd_forge_resume(
                    _ns_resume(tmp),
                    provider_factory=_factory_for(StubProvider()),
                    auditor_gates={},
                )

            # Every entry in the ledger shares the same workflow_id.
            workflow_ids = {e.workflow_id for e in ledger.load()}
            self.assertEqual(workflow_ids, {original_workflow})


if __name__ == "__main__":
    unittest.main()
