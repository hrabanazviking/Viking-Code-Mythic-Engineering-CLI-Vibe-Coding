from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.workflow import MythicRunConfig, MythicWorkflow


class MythicWorkflowTests(unittest.TestCase):
    def test_checkin_preserves_phase_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            workflow.init_project(MythicRunConfig(goal="Test", noob_mode=False), method_source="test")
            workflow.check_in("build", "did build")
            workflow.check_in("intent", "rechecked intent")

            status = json.loads((root / "mythic" / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["completed_phases"], ["build", "intent"])

    def test_doctor_reports_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = MythicWorkflow(root)
            errors, warnings = workflow.doctor()
            self.assertTrue(errors)
            self.assertFalse(any("Invalid JSON" in item for item in errors))
            self.assertEqual(warnings, [])

    def test_status_summary_handles_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mythic = root / "mythic"
            mythic.mkdir(parents=True, exist_ok=True)
            (mythic / "status.json").write_text("{broken", encoding="utf-8")

            workflow = MythicWorkflow(root)
            summary = workflow.status_summary()
            self.assertIn("Goal:", summary)


if __name__ == "__main__":
    unittest.main()
