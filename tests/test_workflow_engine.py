from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.workflow_engine import DEFAULT_ROLE_SEQUENCE, WorkflowEngine


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


if __name__ == "__main__":
    unittest.main()
