from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from mythic_vibe_cli import app
from mythic_vibe_cli.exit_codes import SUCCESS


class UxCommandTests(unittest.TestCase):
    def test_examples_guide_and_tutorial_emit_json(self) -> None:
        for command in ["examples", "guide", "tutorial"]:
            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main([command, "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["command"], command)

    def test_next_uses_project_status_to_recommend_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "status.json").write_text(
                json.dumps(
                    {
                        "goal": "Ship ergonomic commands",
                        "current_phase": "plan",
                        "completed_phases": ["intent", "constraints", "architecture", "plan"],
                        "last_update": "2026-04-27T00:00:00Z",
                        "history": [],
                    }
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["next", "--path", tmp, "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["next_phase"], "build")
            self.assertIn("pytest", payload["verification"])
            self.assertEqual(payload["source"], "phase")

    def test_next_prioritizes_failed_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic" / "verifications").mkdir(parents=True)
            (root / "mythic" / "status.json").write_text(
                json.dumps(
                    {
                        "goal": "Ship ergonomic commands",
                        "current_phase": "build",
                        "completed_phases": ["intent", "constraints", "architecture", "plan", "build"],
                        "history": [],
                    }
                ),
                encoding="utf-8",
            )
            (root / "mythic" / "verifications" / "latest.json").write_text(
                json.dumps(
                    {
                        "verification_id": "VER-FAILED",
                        "result": "fail",
                        "errors": ["pytest failed"],
                        "blocked_reasons": [],
                    }
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["next", "--path", tmp, "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["source"], "verification")
            self.assertEqual(payload["next_phase"], "verify")
            self.assertEqual(payload["latest_verification_id"], "VER-FAILED")
            self.assertIn("pytest failed", payload["verification_errors"])

    def test_next_uses_latest_handoff_when_verification_passed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic" / "handoffs").mkdir(parents=True)
            (root / "mythic" / "verifications").mkdir(parents=True)
            (root / "mythic" / "status.json").write_text(
                json.dumps(
                    {
                        "goal": "Ship ergonomic commands",
                        "current_phase": "build",
                        "completed_phases": ["intent", "constraints", "architecture", "plan", "build"],
                        "history": [],
                    }
                ),
                encoding="utf-8",
            )
            (root / "mythic" / "verifications" / "latest.json").write_text(
                json.dumps({"verification_id": "VER-PASS", "result": "pass"}),
                encoding="utf-8",
            )
            handoff = {
                "handoff_id": "HND-TEST",
                "timestamp": "2026-04-27T00:00:00Z",
                "objective": "Continue command examples",
                "intent": "Carry forward UX polish.",
                "next_steps": ["Add argparse epilog examples for high-traffic commands."],
            }
            (root / "mythic" / "handoffs" / "latest.json").write_text(json.dumps(handoff), encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["next", "--path", tmp, "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["source"], "handoff")
            self.assertEqual(payload["next_action"], "Add argparse epilog examples for high-traffic commands.")
            self.assertEqual(payload["latest_verification_result"], "pass")

    def test_explain_phase_and_artifact_are_machine_readable(self) -> None:
        phase_output = io.StringIO()
        with redirect_stdout(phase_output):
            phase_code = app.main(["explain", "phase", "verify", "--json"])

        artifact_output = io.StringIO()
        with redirect_stdout(artifact_output):
            artifact_code = app.main(["explain", "artifact", "handoff", "--json"])

        phase_payload = json.loads(phase_output.getvalue())
        artifact_payload = json.loads(artifact_output.getvalue())
        self.assertEqual(phase_code, SUCCESS)
        self.assertEqual(artifact_code, SUCCESS)
        self.assertEqual(phase_payload["phase"]["name"], "verify")
        self.assertEqual(artifact_payload["artifact"], "handoff")
        self.assertIn("SESSION_HANDOFF", artifact_payload["path"])

    def test_completion_outputs_requested_shell_script(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            code = app.main(["completion", "--shell", "powershell"])

        self.assertEqual(code, SUCCESS)
        self.assertIn("Register-ArgumentCompleter", output.getvalue())
        self.assertIn("mythic-vibe", output.getvalue())


if __name__ == "__main__":
    unittest.main()
