from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from mythic_vibe_cli import app
from mythic_vibe_cli.core.state import CURRENT_STATE_SCHEMA_VERSION, ProjectState, validate_state_payload
from mythic_vibe_cli.exit_codes import SUCCESS, VERIFICATION_FAILURE
from mythic_vibe_cli.persistence.migrations import migrate_project_state


class ProjectStateTests(unittest.TestCase):
    def test_migrate_legacy_status_creates_backup_and_preserves_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mythic = root / "mythic"
            mythic.mkdir()
            status = mythic / "status.json"
            status.write_text(
                json.dumps(
                    {
                        "goal": "Ship the state engine",
                        "current_phase": "build",
                        "completed_phases": ["intent", "build"],
                        "last_update": "2026-04-24 20:00:00Z",
                        "history": [{"time": "2026-04-24 20:00:00Z", "phase": "build", "update": "Built it"}],
                    }
                ),
                encoding="utf-8",
            )

            result = migrate_project_state(root)
            payload = json.loads(status.read_text(encoding="utf-8"))

            self.assertTrue(result.migrated)
            self.assertIsNotNone(result.backup_path)
            self.assertTrue(result.backup_path and result.backup_path.exists())
            self.assertEqual(payload["schema_version"], CURRENT_STATE_SCHEMA_VERSION)
            self.assertEqual(payload["goal"], "Ship the state engine")
            self.assertEqual(payload["history"][0]["summary"], "Built it")
            self.assertEqual(validate_state_payload(payload).errors, [])

    def test_corrupt_status_migration_recovers_with_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mythic = root / "mythic"
            mythic.mkdir()
            status = mythic / "status.json"
            status.write_text("{broken", encoding="utf-8")

            result = migrate_project_state(root)
            payload = json.loads(status.read_text(encoding="utf-8"))

            self.assertTrue(result.recovered_corrupt)
            self.assertIsNotNone(result.backup_path)
            self.assertEqual(result.backup_path.read_text(encoding="utf-8"), "{broken")
            self.assertEqual(payload["schema_version"], CURRENT_STATE_SCHEMA_VERSION)
            self.assertEqual(validate_state_payload(payload).errors, [])

    def test_state_validate_fails_invalid_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mythic = root / "mythic"
            mythic.mkdir()
            payload = ProjectState(goal="Bad phase").to_dict()
            payload["current_phase"] = "wandering"
            (mythic / "status.json").write_text(json.dumps(payload), encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["state", "validate", "--path", tmp, "--json"])

            body = json.loads(output.getvalue())
            self.assertEqual(code, VERIFICATION_FAILURE)
            self.assertFalse(body["ok"])
            self.assertIn("Invalid current_phase: wandering", body["errors"])

    def test_db_migrate_creates_schema_versioned_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["db", "migrate", "--path", tmp, "--json"])

            body = json.loads(output.getvalue())
            payload = json.loads((Path(tmp) / "mythic" / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(code, SUCCESS)
            self.assertTrue(body["state_migration"]["created"])
            self.assertEqual(payload["schema_version"], CURRENT_STATE_SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
