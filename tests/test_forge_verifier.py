"""Tests for PH-03 slice 3.6 — forge verifier integration.

Two surfaces:

1. Each gate runner in ``forge_verifier`` exercised directly with
   real (or stubbed) project state.
2. Orchestrator integration through ``cmd_forge_run`` showing that
   a failing gate transitions the Auditor step to ``failed``,
   ``--strict`` aborts the run, and the default (non-strict)
   behaviour continues to the Scribe.
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

from mythic_vibe_cli.ai.providers.base import ProviderResponse, ProviderStatus
from mythic_vibe_cli.exit_codes import (
    OPERATIONAL_FAILURE,
    SUCCESS,
    UNSAFE_OPERATION_BLOCKED,
)
from mythic_vibe_cli.forge import cmd_forge_run
from mythic_vibe_cli.forge_ledger import ForgeLedger
from mythic_vibe_cli.forge_verifier import (
    DEFAULT_AUDITOR_GATES,
    gate_diff_reviewed,
    gate_no_invariant_violation,
    gate_test_evidence_recorded,
    run_auditor_gates,
)
from mythic_vibe_cli.workflow_agents import (
    AgentInput,
    AgentOutput,
    VerificationResult,
)
from mythic_vibe_cli.workflow_engine import WorkflowEngine


# ---- Stub provider (same shape as test_forge_run.StubProvider) ----------


class StubProvider:
    name = "stub"
    model = "test"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def validate_config(self) -> ProviderStatus:
        return ProviderStatus(configured=True, details=["stub"])

    def estimate(self, packet: object) -> object:
        from mythic_vibe_cli.ai.providers.base import Estimate

        return Estimate(input_tokens=0, output_tokens=0, cost_usd=0.0)

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:
        text = ""
        if isinstance(packet, dict):
            text = str(packet.get("text") or "")
        self.calls.append(text)
        return ProviderResponse(
            provider=self.name,
            model=self.model,
            content="Audit summary line\nFurther detail",
            packet_id="stub-pkt",
            dry_run=False,
        )


def _factory_for(provider: StubProvider):
    def factory(name: str, root: Path) -> StubProvider:
        return provider

    return factory


def _ns(tmp: str, **overrides: object) -> argparse.Namespace:
    base = {
        "path": tmp,
        "task": "Slice 3.6 e2e",
        "provider": "stub",
        "skip_ledger": False,
        "interactive": False,
        "strict": False,
        "json": True,
        "quiet": False,
        "verbose": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


# ---- gate_diff_reviewed -------------------------------------------------


class GateDiffReviewedTests(unittest.TestCase):
    def _agent_input(self) -> AgentInput:
        return AgentInput(role="Auditor", task="X", phase="verify")

    def _agent_output(self, raw: str = "") -> AgentOutput:
        return AgentOutput(role="Auditor", timestamp="t", raw_response=raw)

    def test_passes_when_collect_changed_files_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            with patch(
                "mythic_vibe_cli.forge_verifier.collect_changed_files",
                return_value=[],
            ):
                result = gate_diff_reviewed(
                    plan, self._agent_input(), self._agent_output(), Path(tmp)
                )
            self.assertTrue(result.passed)
            self.assertIn("no changed files", result.detail)

    def test_passes_when_response_mentions_every_changed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            audit = self._agent_output(raw="Reviewed src/foo.py and src/bar.py — both look clean")
            with patch(
                "mythic_vibe_cli.forge_verifier.collect_changed_files",
                return_value=["src/foo.py", "src/bar.py"],
            ):
                result = gate_diff_reviewed(plan, self._agent_input(), audit, Path(tmp))
            self.assertTrue(result.passed)
            self.assertIn("reviewed 2 changed files", result.detail)

    def test_fails_when_response_misses_a_changed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            audit = self._agent_output(raw="Reviewed src/foo.py")
            with patch(
                "mythic_vibe_cli.forge_verifier.collect_changed_files",
                return_value=["src/foo.py", "src/bar.py", "tests/test_x.py"],
            ):
                result = gate_diff_reviewed(plan, self._agent_input(), audit, Path(tmp))
            self.assertFalse(result.passed)
            self.assertIn("not mentioned", result.detail)

    def test_fails_when_response_is_empty_but_files_changed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            with patch(
                "mythic_vibe_cli.forge_verifier.collect_changed_files",
                return_value=["src/foo.py"],
            ):
                result = gate_diff_reviewed(
                    plan, self._agent_input(), self._agent_output(), Path(tmp)
                )
            self.assertFalse(result.passed)
            self.assertIn("empty audit response", result.detail)

    def test_passes_when_git_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            with patch(
                "mythic_vibe_cli.forge_verifier.collect_changed_files",
                side_effect=RuntimeError("git not on PATH"),
            ):
                result = gate_diff_reviewed(
                    plan, self._agent_input(), self._agent_output(), Path(tmp)
                )
            self.assertTrue(result.passed)
            self.assertIn("git unavailable", result.detail)


# ---- gate_no_invariant_violation ---------------------------------------


class GateInvariantViolationTests(unittest.TestCase):
    def test_passes_when_invariant_check_returns_no_errors(self) -> None:
        from mythic_vibe_cli.verify.invariant_checker import InvariantCheckResult

        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            agent_input = AgentInput(role="Auditor", task="X", phase="verify")
            agent_output = AgentOutput(role="Auditor", timestamp="t")
            stub_result = InvariantCheckResult(
                checked=["state schema", "boundary docs"],
                errors=[],
                warnings=[],
            )
            with patch(
                "mythic_vibe_cli.forge_verifier.check_invariants",
                return_value=stub_result,
            ):
                result = gate_no_invariant_violation(plan, agent_input, agent_output, Path(tmp))
            self.assertTrue(result.passed)
            self.assertIn("state schema", result.detail)

    def test_fails_with_summary_when_errors_present(self) -> None:
        from mythic_vibe_cli.verify.invariant_checker import InvariantCheckResult

        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            agent_input = AgentInput(role="Auditor", task="X", phase="verify")
            agent_output = AgentOutput(role="Auditor", timestamp="t")
            stub_result = InvariantCheckResult(
                checked=["state schema"],
                errors=["Missing repo boundary file: REPO_BOUNDARY.md", "Missing ADR-0001"],
                warnings=[],
            )
            with patch(
                "mythic_vibe_cli.forge_verifier.check_invariants",
                return_value=stub_result,
            ):
                result = gate_no_invariant_violation(plan, agent_input, agent_output, Path(tmp))
            self.assertFalse(result.passed)
            self.assertIn("2 invariant errors", result.detail)
            self.assertIn("Missing repo boundary file", result.detail)
            self.assertIn("(+1 more)", result.detail)

    def test_fails_when_check_invariants_crashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            agent_input = AgentInput(role="Auditor", task="X", phase="verify")
            agent_output = AgentOutput(role="Auditor", timestamp="t")
            with patch(
                "mythic_vibe_cli.forge_verifier.check_invariants",
                side_effect=RuntimeError("bad path"),
            ):
                result = gate_no_invariant_violation(plan, agent_input, agent_output, Path(tmp))
            self.assertFalse(result.passed)
            self.assertIn("invariant checker crashed", result.detail)


# ---- gate_test_evidence_recorded ---------------------------------------


class GateTestEvidenceRecordedTests(unittest.TestCase):
    def test_fails_when_no_latest_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            agent_input = AgentInput(role="Auditor", task="X", phase="verify")
            agent_output = AgentOutput(role="Auditor", timestamp="t")
            result = gate_test_evidence_recorded(plan, agent_input, agent_output, Path(tmp))
            self.assertFalse(result.passed)
            self.assertIn("no mythic/verifications/latest.json", result.detail)

    def test_passes_when_latest_verification_recorded_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ver_dir = Path(tmp) / "mythic" / "verifications"
            ver_dir.mkdir(parents=True)
            (ver_dir / "latest.json").write_text(
                json.dumps({"verification_id": "VER-ABC", "result": "pass"}),
                encoding="utf-8",
            )
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            agent_input = AgentInput(role="Auditor", task="X", phase="verify")
            agent_output = AgentOutput(role="Auditor", timestamp="t")
            result = gate_test_evidence_recorded(plan, agent_input, agent_output, Path(tmp))
            self.assertTrue(result.passed)
            self.assertIn("VER-ABC", result.detail)

    def test_fails_when_latest_verification_did_not_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ver_dir = Path(tmp) / "mythic" / "verifications"
            ver_dir.mkdir(parents=True)
            (ver_dir / "latest.json").write_text(
                json.dumps({"verification_id": "VER-XYZ", "result": "fail"}),
                encoding="utf-8",
            )
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            agent_input = AgentInput(role="Auditor", task="X", phase="verify")
            agent_output = AgentOutput(role="Auditor", timestamp="t")
            result = gate_test_evidence_recorded(plan, agent_input, agent_output, Path(tmp))
            self.assertFalse(result.passed)
            self.assertIn("did not pass", result.detail)


# ---- run_auditor_gates dispatcher --------------------------------------


class RunAuditorGatesTests(unittest.TestCase):
    def test_unknown_gate_name_fails_with_clear_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            agent_input = AgentInput(role="Auditor", task="X", phase="verify")
            agent_output = AgentOutput(role="Auditor", timestamp="t")
            results = run_auditor_gates(
                plan,
                agent_input,
                agent_output,
                Path(tmp),
                gate_names=("not-a-real-gate",),
                gates={},
            )
            self.assertEqual(len(results), 1)
            self.assertFalse(results[0].passed)
            self.assertIn("no runner registered", results[0].detail)

    def test_runner_exception_does_not_propagate(self) -> None:
        def bad_runner(plan, agent_input, agent_output, root):  # noqa: ARG001
            raise RuntimeError("runner exploded")

        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("X")
            agent_input = AgentInput(role="Auditor", task="X", phase="verify")
            agent_output = AgentOutput(role="Auditor", timestamp="t")
            results = run_auditor_gates(
                plan,
                agent_input,
                agent_output,
                Path(tmp),
                gate_names=("buggy",),
                gates={"buggy": bad_runner},
            )
            self.assertEqual(len(results), 1)
            self.assertFalse(results[0].passed)
            self.assertIn("runner crashed", results[0].detail)
            self.assertIn("runner exploded", results[0].detail)

    def test_default_gates_registered_for_three_canonical_names(self) -> None:
        self.assertEqual(
            set(DEFAULT_AUDITOR_GATES),
            {
                "diff-reviewed-against-architecture",
                "no-invariant-violation",
                "test-evidence-recorded",
            },
        )


# ---- Orchestrator integration ------------------------------------------


_PASS = lambda plan, ai, ao, root: VerificationResult(name="g", passed=True, detail="ok")  # noqa: E731
_FAIL = lambda plan, ai, ao, root: VerificationResult(name="g", passed=False, detail="bad")  # noqa: E731


def _all_pass_gates() -> dict:
    """Override the Auditor's contract gates with all-pass stubs that
    use the same names the contract declares, so the call resolves."""
    return {
        "diff-reviewed-against-architecture": lambda *args, **kw: VerificationResult(
            name="diff-reviewed-against-architecture", passed=True, detail="ok"
        ),
        "no-invariant-violation": lambda *args, **kw: VerificationResult(
            name="no-invariant-violation", passed=True, detail="ok"
        ),
        "test-evidence-recorded": lambda *args, **kw: VerificationResult(
            name="test-evidence-recorded", passed=True, detail="ok"
        ),
    }


def _one_failing_gate() -> dict:
    return {
        "diff-reviewed-against-architecture": lambda *args, **kw: VerificationResult(
            name="diff-reviewed-against-architecture", passed=True, detail="ok"
        ),
        "no-invariant-violation": lambda *args, **kw: VerificationResult(
            name="no-invariant-violation", passed=False, detail="boundary missing"
        ),
        "test-evidence-recorded": lambda *args, **kw: VerificationResult(
            name="test-evidence-recorded", passed=True, detail="ok"
        ),
    }


class AuditorAllGatesPassTests(unittest.TestCase):
    def test_auditor_step_succeeds_with_verification_results_attached(self) -> None:
        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_run(
                    _ns(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates=_all_pass_gates(),
                )
            payload = json.loads(stdout.getvalue())

            self.assertEqual(code, SUCCESS)
            statuses = {s["role"]: s["status"] for s in payload["steps"]}
            self.assertEqual(statuses["Auditor"], "succeeded")
            auditor_step = next(s for s in payload["steps"] if s["role"] == "Auditor")
            results = auditor_step["agent_output"]["verification_results"]
            self.assertEqual(len(results), 3)
            self.assertTrue(all(r["passed"] for r in results))


class AuditorGateFailureTests(unittest.TestCase):
    def test_auditor_step_fails_when_any_gate_fails_default_mode(self) -> None:
        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_run(
                    _ns(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates=_one_failing_gate(),
                )
            payload = json.loads(stdout.getvalue())

            # Default (non-strict) mode: Auditor fails, Scribe still
            # tries to run because non-strict continues. Scribe's
            # contract requires prior_outputs only, so it succeeds.
            self.assertEqual(code, OPERATIONAL_FAILURE)
            statuses = {s["role"]: s["status"] for s in payload["steps"]}
            self.assertEqual(statuses["Auditor"], "failed")
            self.assertEqual(statuses["Scribe"], "succeeded")

            # Auditor's failed_gates list is recorded.
            auditor_step = next(s for s in payload["steps"] if s["role"] == "Auditor")
            self.assertIn("no-invariant-violation", auditor_step["failed_gates"])

            # Ledger entry carries the failure note.
            ledger = ForgeLedger(root=Path(tmp))
            auditor_entry = next(
                e for e in ledger.load() if e.role == "Auditor" and e.status == "failed"
            )
            self.assertTrue(any("verification gates failed" in n for n in auditor_entry.notes))

    def test_strict_mode_aborts_run_when_auditor_gate_fails(self) -> None:
        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_run(
                    _ns(tmp, strict=True),
                    provider_factory=_factory_for(stub),
                    auditor_gates=_one_failing_gate(),
                )
            payload = json.loads(stdout.getvalue())

            self.assertEqual(code, UNSAFE_OPERATION_BLOCKED)
            self.assertTrue(payload["aborted"])
            statuses = {s["role"]: s["status"] for s in payload["steps"]}
            self.assertEqual(statuses["Auditor"], "failed")
            # Strict mode aborted before Scribe ran.
            self.assertEqual(statuses["Scribe"], "blocked")
            scribe_step = next(s for s in payload["steps"] if s["role"] == "Scribe")
            self.assertEqual(scribe_step["blocked_reason"], "verifier strict-mode abort")


class AuditorGatesOptOutTests(unittest.TestCase):
    """``auditor_gates={}`` opts out — used by slice-3.5 orchestration
    tests that don't care about gate logic."""

    def test_empty_gates_dict_opts_out_no_results_attached(self) -> None:
        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_run(
                    _ns(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates={},
                )
            payload = json.loads(stdout.getvalue())
            self.assertEqual(code, SUCCESS)

            auditor_step = next(s for s in payload["steps"] if s["role"] == "Auditor")
            self.assertEqual(auditor_step["status"], "succeeded")
            self.assertEqual(
                auditor_step["agent_output"]["verification_results"], []
            )


if __name__ == "__main__":
    unittest.main()
