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
from mythic_vibe_cli.persistence.json_store import JsonStateStore
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
            self.assertEqual(result.backup_path.suffix, ".corrupt")
            self.assertEqual(payload["schema_version"], CURRENT_STATE_SCHEMA_VERSION)
            self.assertEqual(validate_state_payload(payload).errors, [])

    def test_invalid_encoding_status_migration_quarantines_and_recovers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mythic = root / "mythic"
            mythic.mkdir()
            status = mythic / "status.json"
            status.write_bytes(b"\xff\xfe\x00\x00")

            result = migrate_project_state(root, default_goal="Recovered")
            payload = json.loads(status.read_text(encoding="utf-8"))

            self.assertTrue(result.recovered_corrupt)
            self.assertIsNotNone(result.backup_path)
            self.assertEqual(result.backup_path.read_bytes(), b"\xff\xfe\x00\x00")
            self.assertEqual(payload["goal"], "Recovered")
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

    def test_state_write_preserves_backup_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = JsonStateStore(root)
            first = ProjectState(goal="first")
            second = ProjectState(goal="second")

            store.write_state(first)
            store.write_state(second)

            backups = list((root / "mythic" / "backups").glob("status.json.*.bak"))
            self.assertEqual(len(backups), 1)
            backup_payload = json.loads(backups[0].read_text(encoding="utf-8"))
            current_payload = json.loads((root / "mythic" / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(backup_payload["goal"], "first")
            self.assertEqual(current_payload["goal"], "second")

    def test_state_write_uses_recoverable_cross_process_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = JsonStateStore(root)

            store.write_state(ProjectState(goal="cross-process lock"))

            self.assertTrue((root / "mythic" / "status.json.lock").exists())
            payload = json.loads((root / "mythic" / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["goal"], "cross-process lock")


if __name__ == "__main__":
    unittest.main()
