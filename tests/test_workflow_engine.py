from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.workflow_engine import (
    DEFAULT_ROLE_SEQUENCE,
    WORKFLOW_HISTORY_LIMIT,
    WorkflowEngine,
    WorkflowPlan,
)


class WorkflowEngineTests(unittest.TestCase):
    def test_default_plan_orders_the_six_mythic_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(Path(tmp))

            plan = engine.build_plan("Build a role-aware workflow engine")

            self.assertEqual(tuple(step.role for step in plan.steps), DEFAULT_ROLE_SEQUENCE)
            self.assertEqual(tuple(step.phase for step in plan.steps), ("intent", "architecture", "plan", "build", "verify", "reflect"))
            self.assertEqual(plan.steps[0].handoff_to, "Architect")
            self.assertEqual(plan.steps[-1].handoff_to, None)
            self.assertIn("Name the deeper purpose", plan.steps[0].objective)

    def test_plan_exports_packet_requests_without_provider_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(Path(tmp))

            requests = engine.build_plan("Ship orchestration").packet_requests(audience="beginner")

            self.assertEqual(requests[0].role, "Skald")
            self.assertEqual(requests[0].phase, "intent")
            self.assertEqual(requests[-1].role, "Scribe")
            self.assertIn("Step objective:", requests[0].task)
            self.assertTrue(all(request.audience == "beginner" for request in requests))

    def test_write_plan_persists_durable_orchestration_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = WorkflowEngine(root)

            path = engine.write_plan("Coordinate the next build")
            payload = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(path, root / "mythic" / "workflow_plan.json")
            self.assertEqual(payload["task"], "Coordinate the next build")
            self.assertEqual(payload["steps"][0]["role"], "Skald")
            self.assertEqual(payload["steps"][0]["handoff_to"], "Architect")

    def test_unknown_role_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(Path(tmp))

            with self.assertRaisesRegex(ValueError, "Unsupported workflow roles"):
                engine.build_plan("Bad role", role_sequence=("Skald", "Unknown"))

    def test_build_plan_assigns_workflow_id_and_propagates_into_packet_requests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(Path(tmp))

            plan = engine.build_plan("Trace packet readiness by id")

            self.assertIsNotNone(plan.workflow_id)
            assert plan.workflow_id is not None
            self.assertTrue(plan.workflow_id.startswith("WF-"))
            self.assertEqual(plan.workflow_id.count("-"), 2)
            requests = plan.packet_requests()
            self.assertTrue(all(request.workflow_id == plan.workflow_id for request in requests))
            self.assertEqual(
                [request.workflow_step_id for request in requests],
                [step.step_id for step in plan.steps],
            )

    def test_workflow_id_round_trips_through_to_dict_and_from_dict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(Path(tmp))

            plan = engine.build_plan("Persist the workflow id")
            payload = plan.to_dict()
            restored = WorkflowPlan.from_dict(payload)

            self.assertIn("workflow_id", payload)
            self.assertEqual(restored.workflow_id, plan.workflow_id)

    def test_write_plan_appends_workflow_history_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = WorkflowEngine(root)

            engine.write_plan("First saved")
            engine.write_plan("Second saved", role_sequence=("Skald",))

            history = engine.load_history()
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["task"], "First saved")
            self.assertEqual(history[1]["task"], "Second saved")
            self.assertTrue(history[0]["workflow_id"].startswith("WF-"))
            self.assertEqual(history[1]["role_sequence"], ["Skald"])
            history_path = engine.history_path()
            payload = json.loads(history_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["version"], 1)
            self.assertEqual(len(payload["entries"]), 2)

    def test_history_trims_to_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = WorkflowEngine(root)

            for index in range(WORKFLOW_HISTORY_LIMIT + 5):
                engine.write_plan(f"task-{index:03d}", role_sequence=("Skald",))

            history = engine.load_history()
            self.assertEqual(len(history), WORKFLOW_HISTORY_LIMIT)
            self.assertEqual(history[0]["task"], f"task-{5:03d}")
            self.assertEqual(history[-1]["task"], f"task-{WORKFLOW_HISTORY_LIMIT + 4:03d}")

    def test_load_history_returns_empty_list_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = WorkflowEngine(Path(tmp))
            self.assertEqual(engine.load_history(), [])

    def test_legacy_plan_without_workflow_id_still_loads(self) -> None:
        legacy_payload = {
            "task": "Older plan with no id",
            "created_at": "2026-04-29T00:00:00Z",
            "steps": [
                {
                    "step_id": "step-01",
                    "role": "Skald",
                    "phase": "intent",
                    "objective": "Frame the work",
                    "identity": "Sigrún Ljósbrá",
                    "focus": "vision",
                    "system_prompt": "You are the Skald.",
                    "invariants": [],
                    "verification": [],
                    "handoff_to": None,
                }
            ],
        }

        plan = WorkflowPlan.from_dict(legacy_payload)

        self.assertIsNone(plan.workflow_id)
        requests = plan.packet_requests()
        self.assertIsNone(requests[0].workflow_id)
        self.assertEqual(requests[0].workflow_step_id, "step-01")


if __name__ == "__main__":
    unittest.main()
