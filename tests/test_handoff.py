from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from mythic_vibe_cli import app
from mythic_vibe_cli.exit_codes import SUCCESS


class HandoffCommandTests(unittest.TestCase):
    def _seed_project(self, root: Path) -> None:
        (root / "docs").mkdir(parents=True, exist_ok=True)
        (root / "tasks").mkdir(parents=True, exist_ok=True)
        (root / "mythic").mkdir(parents=True, exist_ok=True)
        (root / "mythic" / "status.json").write_text(
            json.dumps(
                {
                    "goal": "Ship Stage 10",
                    "current_phase": "reflect",
                    "completed_phases": ["intent", "constraints", "architecture", "plan", "build", "verify"],
                    "last_update": "2026-04-27T00:00:00Z",
                    "history": [],
                }
            ),
            encoding="utf-8",
        )

    def test_reflect_creates_handoff_and_resume_points_to_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_project(root)

            reflect_output = io.StringIO()
            with redirect_stdout(reflect_output):
                reflect_code = app.main(
                    [
                        "reflect",
                        "--path",
                        str(root),
                        "--summary",
                        "Wrap Stage 10 and preserve the next move.",
                        "--next-step",
                        "Start Stage 11",
                        "--note",
                        "Keep continuity high.",
                        "--json",
                    ]
                )

            reflect_payload = json.loads(reflect_output.getvalue())
            handoff = reflect_payload["handoff"]
            handoff_id = handoff["handoff_id"]

            self.assertEqual(reflect_code, SUCCESS)
            self.assertEqual(reflect_payload["command"], "reflect")
            self.assertEqual(handoff["session_type"], "reflect")
            self.assertEqual(handoff["objective"], "Wrap Stage 10 and preserve the next move.")
            self.assertTrue((root / "docs" / "SESSION_HANDOFF.md").exists())
            self.assertTrue((root / "mythic" / "handoffs" / "latest.json").exists())

            status_output = io.StringIO()
            with redirect_stdout(status_output):
                status_code = app.main(["status", "--path", str(root), "--json"])

            status_payload = json.loads(status_output.getvalue())
            self.assertEqual(status_code, SUCCESS)
            self.assertEqual(status_payload["latest_handoff_id"], handoff_id)
            self.assertEqual(status_payload["latest_handoff_next_step"], "Start Stage 11")
            self.assertEqual(status_payload["latest_handoff_path"], str(root / "docs" / "SESSION_HANDOFF.md"))

            resume_output = io.StringIO()
            with redirect_stdout(resume_output):
                resume_code = app.main(["resume", "--path", str(root), "--json"])

            resume_payload = json.loads(resume_output.getvalue())
            self.assertEqual(resume_code, SUCCESS)
            self.assertEqual(resume_payload["command"], "resume")
            self.assertEqual(resume_payload["handoff"]["handoff_id"], handoff_id)
            self.assertEqual(resume_payload["next_recommended_action"], "Start Stage 11")

    def test_handoff_show_and_latest_return_same_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_project(root)

            create_output = io.StringIO()
            with redirect_stdout(create_output):
                create_code = app.main(
                    [
                        "handoff",
                        "create",
                        "--path",
                        str(root),
                        "--summary",
                        "Create a reusable handoff record.",
                        "--json",
                    ]
                )

            create_payload = json.loads(create_output.getvalue())
            handoff_id = create_payload["handoff"]["handoff_id"]

            self.assertEqual(create_code, SUCCESS)
            self.assertEqual(create_payload["command"], "handoff create")

            latest_output = io.StringIO()
            with redirect_stdout(latest_output):
                latest_code = app.main(["handoff", "latest", "--path", str(root), "--json"])

            latest_payload = json.loads(latest_output.getvalue())
            self.assertEqual(latest_code, SUCCESS)
            self.assertEqual(latest_payload["command"], "handoff latest")
            self.assertEqual(latest_payload["handoff"]["handoff_id"], handoff_id)

            show_output = io.StringIO()
            with redirect_stdout(show_output):
                show_code = app.main(["handoff", "show", "--path", str(root), "--handoff-id", handoff_id, "--json"])

            show_payload = json.loads(show_output.getvalue())
            self.assertEqual(show_code, SUCCESS)
            self.assertEqual(show_payload["command"], "handoff show")
            self.assertEqual(show_payload["handoff"]["handoff_id"], handoff_id)
            self.assertIn("# Session Handoff", show_payload["handoff"]["markdown"])


if __name__ == "__main__":
    unittest.main()
