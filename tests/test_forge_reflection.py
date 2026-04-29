"""Tests for PH-03 slice 3.7 — forge reflection capture.

Covers:

1. Pure-data layer: ``ForgeReflection`` / ``ForgeStepReflection``
   round-trip; ``build_forge_reflection`` from a fixture ledger;
   ``render_forge_reflection_markdown`` shape; ``write_forge_reflection``
   + ``load_forge_reflection`` round-trip on disk.

2. Orchestrator integration: ``cmd_forge_run`` writes both .md and
   .json sidecars by default; ``--skip-reflection`` suppresses the
   write; the JSON output payload reports the reflection paths.

3. CLI inspection surface: ``forge reflection list/show/latest``
   and dispatcher fall-through.
"""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from mythic_vibe_cli import app
from mythic_vibe_cli.ai.providers.base import ProviderResponse, ProviderStatus
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.forge import cmd_forge_reflection_dispatch, cmd_forge_run
from mythic_vibe_cli.forge_ledger import ForgeLedger, ForgeLedgerEntry
from mythic_vibe_cli.forge_reflection import (
    REFLECTION_SCHEMA_VERSION,
    ForgeReflection,
    ForgeStepReflection,
    build_forge_reflection,
    list_forge_reflections,
    load_forge_reflection,
    reflection_paths,
    render_forge_reflection_markdown,
    write_forge_reflection,
)
from mythic_vibe_cli.workflow_agents import AgentInput, AgentOutput, VerificationResult
from mythic_vibe_cli.workflow_engine import DEFAULT_ROLE_SEQUENCE, WorkflowEngine


# ---- Stub provider (deterministic, slice-3.5/3.6 style) -----------------


class StubProvider:
    name = "stub"

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
        return ProviderResponse(
            provider=self.name,
            model="t",
            content=f"{role} summary line\nfollow-up text",
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
        "task": "Slice 3.7 reflection",
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


# ---- Pure-data layer ---------------------------------------------------


class ForgeStepReflectionRoundTripTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        original = ForgeStepReflection(
            step_id="step-02",
            role="Architect",
            phase="architecture",
            status="succeeded",
            summary="Defined boundaries",
            failed_gates=(),
            notes=("clean run",),
            duration_ms=1500,
        )
        rebuilt = ForgeStepReflection.from_dict(original.to_dict())
        self.assertEqual(rebuilt, original)

    def test_invalid_duration_decoded_to_none(self) -> None:
        payload = {
            "step_id": "s",
            "role": "r",
            "phase": "p",
            "status": "succeeded",
            "duration_ms": "not-a-number",
        }
        rebuilt = ForgeStepReflection.from_dict(payload)
        self.assertIsNone(rebuilt.duration_ms)


class ForgeReflectionRoundTripTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        steps = (
            ForgeStepReflection(step_id="step-01", role="Skald", phase="intent", status="succeeded"),
            ForgeStepReflection(step_id="step-02", role="Architect", phase="architecture", status="failed",
                                failed_gates=("g1",), notes=("explanation",)),
        )
        original = ForgeReflection(
            schema_version=REFLECTION_SCHEMA_VERSION,
            workflow_id="WF-X",
            task="example",
            created_at="2026-04-29T22:00:00Z",
            completed_at="2026-04-29T22:00:30Z",
            final_status="failure",
            success_count=1,
            failure_count=1,
            blocked_count=0,
            aborted=False,
            steps=steps,
            next_step_recommendation="Fix and retry.",
        )
        rebuilt = ForgeReflection.from_dict(original.to_dict())
        self.assertEqual(rebuilt, original)


# ---- build_forge_reflection -------------------------------------------


def _seed_ledger(tmp: str, statuses: dict[str, str]) -> tuple[WorkflowEngine, str]:
    """Seed a ledger with one entry per role using the given statuses.
    Returns the engine + workflow_id for follow-up assertions."""
    engine = WorkflowEngine(root=Path(tmp))
    plan = engine.build_plan("seed")
    ledger = ForgeLedger(root=Path(tmp))
    for plan_step in plan.steps:
        agent_input = AgentInput(
            role=plan_step.role,
            task="seed",
            phase=plan_step.phase,
            workflow_id=plan.workflow_id,
            workflow_step_id=plan_step.step_id,
        )
        status = statuses.get(plan_step.role, "succeeded")
        agent_output: AgentOutput | None = None
        if status == "succeeded":
            agent_output = AgentOutput(
                role=plan_step.role,
                timestamp="2026-04-29T22:00:00Z",
                workflow_id=plan.workflow_id,
                workflow_step_id=plan_step.step_id,
                summary=f"{plan_step.role} succeeded",
            )
        ledger.append(
            ForgeLedgerEntry(
                workflow_id=plan.workflow_id or "",
                step_id=plan_step.step_id,
                role=plan_step.role,
                status=status,
                started_at="2026-04-29T22:00:00Z",
                agent_input=agent_input,
                agent_output=agent_output,
                duration_ms=100,
            )
        )
    return engine, plan.workflow_id or ""


class BuildForgeReflectionTests(unittest.TestCase):
    def test_all_succeed_yields_success_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine, workflow_id = _seed_ledger(tmp, {})
            plan = engine.load_plan() if False else engine.build_plan("seed")
            ledger = ForgeLedger(root=Path(tmp))
            # Re-build plan with same workflow id used in seeding.
            # _seed_ledger did its own plan; we need to read it back from
            # the ledger. The plan we just built has a different
            # workflow_id, so we look up what's actually in the ledger.
            entries = ledger.find_by_workflow(workflow_id)
            self.assertGreater(len(entries), 0)

            # Build a reflection using a plan whose workflow_id matches.
            # WorkflowEngine.build_plan generates a fresh id each time;
            # for the test we mutate the plan to align.
            from dataclasses import replace as _replace

            aligned_plan = _replace(plan, workflow_id=workflow_id)
            reflection = build_forge_reflection(aligned_plan, ledger)

            self.assertEqual(reflection.final_status, "success")
            self.assertEqual(reflection.success_count, len(DEFAULT_ROLE_SEQUENCE))
            self.assertEqual(reflection.failure_count, 0)
            self.assertEqual(reflection.workflow_id, workflow_id)
            self.assertIn("Cycle completed", reflection.next_step_recommendation)

    def test_failed_step_yields_failure_status_and_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine, workflow_id = _seed_ledger(tmp, {"Auditor": "failed"})
            from dataclasses import replace as _replace

            plan = _replace(engine.build_plan("seed"), workflow_id=workflow_id)
            ledger = ForgeLedger(root=Path(tmp))
            reflection = build_forge_reflection(plan, ledger)

            self.assertEqual(reflection.final_status, "failure")
            self.assertEqual(reflection.failure_count, 1)
            self.assertIn("Auditor", reflection.next_step_recommendation)
            self.assertIn("forge resume", reflection.next_step_recommendation)

    def test_aborted_takes_precedence_over_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine, workflow_id = _seed_ledger(tmp, {"Cartographer": "blocked"})
            from dataclasses import replace as _replace

            plan = _replace(engine.build_plan("seed"), workflow_id=workflow_id)
            ledger = ForgeLedger(root=Path(tmp))
            reflection = build_forge_reflection(plan, ledger, aborted=True)
            self.assertEqual(reflection.final_status, "aborted")
            self.assertTrue(reflection.aborted)
            self.assertIn("aborted at gate", reflection.next_step_recommendation)

    def test_no_ledger_entries_yields_no_steps_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(root=Path(tmp))
            plan = engine.build_plan("seed")
            # Empty ledger; no entries for this workflow.
            ledger = ForgeLedger(root=Path(tmp))
            reflection = build_forge_reflection(plan, ledger)
            self.assertEqual(reflection.success_count, 0)
            # All steps land as not-run because none were in the ledger.
            for step in reflection.steps:
                self.assertEqual(step.status, "not-run")

    def test_auditor_failed_gates_surface_in_step_reflection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine, workflow_id = _seed_ledger(tmp, {"Auditor": "succeeded"})
            from dataclasses import replace as _replace

            # Mutate the Auditor entry in place to add failed gates.
            ledger = ForgeLedger(root=Path(tmp))
            auditor_entry = next(e for e in ledger.find_by_workflow(workflow_id) if e.role == "Auditor")
            ledger.update_step(
                auditor_entry.workflow_id,
                auditor_entry.step_id,
                status="failed",
                agent_output=AgentOutput(
                    role="Auditor",
                    timestamp="2026-04-29T22:00:00Z",
                    workflow_id=workflow_id,
                    workflow_step_id=auditor_entry.step_id,
                    summary="Auditor saw violations",
                    verification_results=(
                        VerificationResult(name="diff-reviewed-against-architecture", passed=True),
                        VerificationResult(name="no-invariant-violation", passed=False, detail="boundary missing"),
                    ),
                ),
            )

            plan = _replace(engine.build_plan("seed"), workflow_id=workflow_id)
            reflection = build_forge_reflection(plan, ledger)

            auditor_step = next(s for s in reflection.steps if s.role == "Auditor")
            self.assertEqual(auditor_step.status, "failed")
            self.assertEqual(auditor_step.failed_gates, ("no-invariant-violation",))


# ---- Markdown rendering ------------------------------------------------


class RenderMarkdownTests(unittest.TestCase):
    def test_markdown_contains_canonical_sections(self) -> None:
        reflection = ForgeReflection(
            schema_version=1,
            workflow_id="WF-MD",
            task="render test",
            created_at="2026-04-29T22:00:00Z",
            completed_at="2026-04-29T22:00:30Z",
            final_status="success",
            success_count=2,
            failure_count=0,
            blocked_count=0,
            aborted=False,
            steps=(
                ForgeStepReflection(
                    step_id="step-01", role="Skald", phase="intent",
                    status="succeeded", summary="captured intent",
                    duration_ms=100,
                ),
                ForgeStepReflection(
                    step_id="step-02", role="Architect", phase="architecture",
                    status="succeeded", summary="declared boundaries",
                ),
            ),
            next_step_recommendation="Cycle completed.",
        )
        md = render_forge_reflection_markdown(reflection)
        self.assertIn("# Forge Reflection", md)
        self.assertIn("- Workflow: WF-MD", md)
        self.assertIn("- Task: render test", md)
        self.assertIn("- Final status: **success**", md)
        self.assertIn("## Per-role outcomes", md)
        self.assertIn("step-01 :: Skald", md)
        self.assertIn("> captured intent", md)
        self.assertIn("Duration: 100 ms", md)
        self.assertIn("## Next step", md)
        self.assertIn("Cycle completed.", md)

    def test_markdown_lists_failed_gates(self) -> None:
        reflection = ForgeReflection(
            schema_version=1,
            workflow_id="WF-FAIL",
            task="audit",
            created_at="t",
            completed_at="t",
            final_status="failure",
            success_count=0,
            failure_count=1,
            blocked_count=0,
            aborted=False,
            steps=(
                ForgeStepReflection(
                    step_id="step-05", role="Auditor", phase="verify",
                    status="failed",
                    failed_gates=("no-invariant-violation", "test-evidence-recorded"),
                    notes=("verification gates failed: ...",),
                ),
            ),
            next_step_recommendation="Address.",
        )
        md = render_forge_reflection_markdown(reflection)
        self.assertIn("Failed gates:", md)
        self.assertIn("no-invariant-violation", md)
        self.assertIn("test-evidence-recorded", md)
        self.assertIn("verification gates failed:", md)


# ---- write_forge_reflection / load_forge_reflection -------------------


class WriteAndLoadTests(unittest.TestCase):
    def _sample(self) -> ForgeReflection:
        return ForgeReflection(
            schema_version=1,
            workflow_id="WF-DISK",
            task="persistence",
            created_at="t",
            completed_at="t",
            final_status="success",
            success_count=1,
            failure_count=0,
            blocked_count=0,
            aborted=False,
            steps=(
                ForgeStepReflection(
                    step_id="step-01", role="Skald", phase="intent", status="succeeded"
                ),
            ),
            next_step_recommendation="ok",
        )

    def test_write_creates_both_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path, md_path = write_forge_reflection(Path(tmp), self._sample())
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            self.assertEqual(json_path.suffix, ".json")
            self.assertEqual(md_path.suffix, ".md")

    def test_round_trip_via_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original = self._sample()
            write_forge_reflection(Path(tmp), original)
            rebuilt = load_forge_reflection(Path(tmp), original.workflow_id)
            self.assertIsNotNone(rebuilt)
            assert rebuilt is not None
            self.assertEqual(rebuilt, original)

    def test_load_missing_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(load_forge_reflection(Path(tmp), "WF-NOPE"))

    def test_load_corrupt_json_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path, _ = reflection_paths(Path(tmp), "WF-X")
            json_path.parent.mkdir(parents=True)
            json_path.write_text("{not valid json", encoding="utf-8")
            self.assertIsNone(load_forge_reflection(Path(tmp), "WF-X"))


class ListReflectionsTests(unittest.TestCase):
    def test_list_returns_workflow_ids_sorted_oldest_first(self) -> None:
        import time

        with tempfile.TemporaryDirectory() as tmp:
            for workflow_id in ("WF-A", "WF-B", "WF-C"):
                reflection = ForgeReflection(
                    schema_version=1,
                    workflow_id=workflow_id,
                    task="t",
                    created_at="t",
                    completed_at="t",
                    final_status="success",
                    success_count=0,
                    failure_count=0,
                    blocked_count=0,
                    aborted=False,
                    steps=(),
                    next_step_recommendation="",
                )
                write_forge_reflection(Path(tmp), reflection)
                time.sleep(0.01)  # ensure mtime ordering

            ids = list_forge_reflections(Path(tmp))
            self.assertEqual(ids, ["WF-A", "WF-B", "WF-C"])

    def test_list_returns_empty_when_dir_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(list_forge_reflections(Path(tmp)), [])


# ---- Orchestrator integration -----------------------------------------


class ForgeRunWritesReflectionTests(unittest.TestCase):
    def test_default_run_writes_both_sidecars(self) -> None:
        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = cmd_forge_run(
                    _ns_run(tmp),
                    provider_factory=_factory_for(stub),
                    auditor_gates={},
                )
            payload = json.loads(stdout.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertIsNotNone(payload["reflection_json_path"])
            self.assertIsNotNone(payload["reflection_markdown_path"])
            self.assertTrue(Path(payload["reflection_json_path"]).exists())
            self.assertTrue(Path(payload["reflection_markdown_path"]).exists())

            # Reflection content matches what build_forge_reflection
            # would produce now.
            workflow_id = payload["workflow_id"]
            rebuilt = load_forge_reflection(Path(tmp), workflow_id)
            self.assertIsNotNone(rebuilt)
            assert rebuilt is not None
            self.assertEqual(rebuilt.final_status, "success")
            self.assertEqual(rebuilt.success_count, len(DEFAULT_ROLE_SEQUENCE))

    def test_skip_reflection_writes_no_sidecars(self) -> None:
        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                cmd_forge_run(
                    _ns_run(tmp, skip_reflection=True),
                    provider_factory=_factory_for(stub),
                    auditor_gates={},
                )
            payload = json.loads(stdout.getvalue())
            self.assertIsNone(payload["reflection_json_path"])
            self.assertIsNone(payload["reflection_markdown_path"])
            # No reflection files on disk.
            self.assertEqual(list_forge_reflections(Path(tmp)), [])

    def test_skip_ledger_implies_skip_reflection(self) -> None:
        """When the ledger is suppressed, building a reflection makes
        no sense (nothing to read from). The orchestrator should not
        attempt the write."""
        stub = StubProvider()
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                cmd_forge_run(
                    _ns_run(tmp, skip_ledger=True),
                    provider_factory=_factory_for(stub),
                    auditor_gates={},
                )
            payload = json.loads(stdout.getvalue())
            self.assertIsNone(payload["reflection_json_path"])


# ---- forge reflection list / show / latest ---------------------------


def _seed_with_run(tmp: str, *, count: int = 1) -> list[str]:
    """Run the forge ``count`` times with distinct tasks, return the
    list of workflow ids."""
    workflow_ids: list[str] = []
    for i in range(count):
        stub = StubProvider()
        ns = _ns_run(tmp, task=f"seed task {i}")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            cmd_forge_run(ns, provider_factory=_factory_for(stub), auditor_gates={})
        payload = json.loads(stdout.getvalue())
        workflow_ids.append(payload["workflow_id"])
    return workflow_ids


class ForgeReflectionListTests(unittest.TestCase):
    def test_list_after_run_reports_workflow_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ids = _seed_with_run(tmp, count=2)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    ["forge", "reflection", "list", "--path", tmp, "--json"]
                )
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["count"], 2)
            self.assertEqual(set(payload["workflow_ids"]), set(ids))

    def test_list_empty_project_reports_no_reflections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["forge", "reflection", "list", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            self.assertIn("No forge reflections recorded", stdout.getvalue())


class ForgeReflectionShowTests(unittest.TestCase):
    def test_show_renders_markdown_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ids = _seed_with_run(tmp, count=1)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    ["forge", "reflection", "show", "--workflow", ids[0], "--path", tmp]
                )
            self.assertEqual(code, SUCCESS)
            output = stdout.getvalue()
            self.assertIn("# Forge Reflection", output)
            self.assertIn(ids[0], output)
            self.assertIn("## Per-role outcomes", output)

    def test_show_json_returns_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ids = _seed_with_run(tmp, count=1)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    [
                        "forge", "reflection", "show",
                        "--workflow", ids[0],
                        "--path", tmp,
                        "--json",
                    ]
                )
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["reflection"]["workflow_id"], ids[0])

    def test_show_unknown_workflow_returns_user_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = app.main(
                    [
                        "forge", "reflection", "show",
                        "--workflow", "WF-NOPE",
                        "--path", tmp,
                    ]
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("No reflection found", stderr.getvalue())


class ForgeReflectionLatestTests(unittest.TestCase):
    def test_latest_after_two_runs_picks_the_newer_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ids = _seed_with_run(tmp, count=2)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    ["forge", "reflection", "latest", "--path", tmp, "--json"]
                )
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["reflection"]["workflow_id"], ids[-1])

    def test_latest_empty_project_reports_no_reflections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["forge", "reflection", "latest", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            self.assertIn("No forge reflections recorded", stdout.getvalue())


class ReflectionDispatcherFallthroughTests(unittest.TestCase):
    def test_unknown_subcommand_emits_visible_error(self) -> None:
        ns = argparse.Namespace(reflection_command="bogus")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = cmd_forge_reflection_dispatch(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        self.assertIn("Unknown forge reflection subcommand", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
