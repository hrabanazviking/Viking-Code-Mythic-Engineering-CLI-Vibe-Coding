from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from mythic_vibe_cli import app, commands
from mythic_vibe_cli.cli import COMMAND_HANDLERS
from mythic_vibe_cli.exit_codes import (
    EXIT_CODE_POLICY,
    OPERATIONAL_FAILURE,
    SUCCESS,
    UNSAFE_OPERATION_BLOCKED,
    USER_INPUT_ERROR,
    VERIFICATION_FAILURE,
)


class CliKernelTests(unittest.TestCase):
    def test_python_module_entrypoint_renders_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "mythic_vibe_cli", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, SUCCESS)
        self.assertIn("mythic-vibe", result.stdout)
        self.assertIn("doctor", result.stdout)

    def test_command_registry_preserves_current_commands_and_aliases(self) -> None:
        expected = {
            "init",
            "start",
            "imbue",
            "checkin",
            "reflect",
            "handoff",
            "resume",
            "examples",
            "guide",
            "next",
            "explain",
            "tutorial",
            "completion",
            "status",
            "scan",
            "import-md",
            "codex-pack",
            "evoke",
            "packet",
            "workflow",
            "codex-log",
            "ai",
            "sync",
            "method",
            "doctor",
            "scry",
            "weave",
            "prune",
            "heal",
            "oath",
            "grimoire",
            "plugin",
            "config",
            "state",
            "db",
            "plunder",
            "verify",
        }

        self.assertEqual(set(COMMAND_HANDLERS), expected)
        self.assertIs(COMMAND_HANDLERS["start"], COMMAND_HANDLERS["init"])
        self.assertIs(COMMAND_HANDLERS["imbue"], COMMAND_HANDLERS["init"])
        self.assertIs(COMMAND_HANDLERS["evoke"], COMMAND_HANDLERS["codex-pack"])
        self.assertIs(COMMAND_HANDLERS["scry"], COMMAND_HANDLERS["doctor"])
        self.assertIs(COMMAND_HANDLERS, commands.COMMAND_HANDLERS)
        self.assertIs(COMMAND_HANDLERS, app.COMMAND_HANDLERS)

    def test_exit_code_policy_names_current_contract(self) -> None:
        self.assertEqual(
            set(EXIT_CODE_POLICY),
            {
                SUCCESS,
                OPERATIONAL_FAILURE,
                USER_INPUT_ERROR,
                VERIFICATION_FAILURE,
                UNSAFE_OPERATION_BLOCKED,
            },
        )
        self.assertEqual(USER_INPUT_ERROR, 2)
        self.assertEqual(UNSAFE_OPERATION_BLOCKED, 4)

    def test_status_json_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "status.json").write_text(
                json.dumps(
                    {
                        "goal": "Build a real CLI",
                        "current_phase": "plan",
                        "completed_phases": ["intent", "plan"],
                        "last_update": "2026-04-24 00:00:00Z",
                        "history": [],
                    }
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["status", "--path", tmp, "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertTrue(payload["status_found"])
            self.assertTrue(payload["valid"])
            self.assertEqual(payload["goal"], "Build a real CLI")
            self.assertEqual(payload["current_phase"], "plan")
            self.assertEqual(payload["progress_percent"], 28)

    def test_quiet_suppresses_success_text(self) -> None:
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(output):
            code = app.main(["status", "--path", tmp, "--quiet"])

        self.assertEqual(code, SUCCESS)
        self.assertEqual(output.getvalue(), "")

    def test_init_dry_run_does_not_create_project_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "preview"
            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["init", "--goal", "Preview only", "--path", str(project), "--dry-run"])

            self.assertEqual(code, SUCCESS)
            self.assertFalse(project.exists())
            self.assertIn("Dry run", output.getvalue())

    def test_packet_create_list_and_show_persist_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "tasks").mkdir(parents=True, exist_ok=True)
            (root / "mythic").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "tasks" / "current_GOALS.md").write_text("Ship packets\n", encoding="utf-8")
            (root / "mythic" / "plan.md").write_text("# Plan\n", encoding="utf-8")
            (root / "mythic" / "loop.md").write_text("# Loop\n", encoding="utf-8")

            create_output = io.StringIO()
            with redirect_stdout(create_output):
                create_code = app.main(
                    [
                        "packet",
                        "create",
                        "--task",
                        "wire packet storage",
                        "--phase",
                        "build",
                        "--path",
                        str(root),
                        "--json",
                    ]
                )

            packet_dir = root / "mythic" / "packets"
            metadata_files = sorted(packet_dir.glob("PKT-*.meta.json"))
            packet_files = sorted(packet_dir.glob("PKT-*.md"))
            self.assertEqual(create_code, SUCCESS)
            self.assertTrue(metadata_files)
            self.assertTrue(packet_files)

            payload = json.loads(create_output.getvalue())
            self.assertEqual(payload["command"], "packet create")
            self.assertEqual(payload["role"], "Forge Worker")
            self.assertTrue(Path(payload["output_file"]).exists())

            original_packet_path = Path(payload["output_file"])
            modified_source = root / "external_packet.md"
            modified_source.write_text(
                original_packet_path.read_text(encoding="utf-8") + "\nEXTRA DIFFERENCE\n",
                encoding="utf-8",
            )

            ingest_output = io.StringIO()
            with redirect_stdout(ingest_output):
                ingest_code = app.main(["packet", "ingest", "--path", str(root), "--source", str(modified_source), "--json"])

            ingest_payload = json.loads(ingest_output.getvalue())
            self.assertEqual(ingest_code, SUCCESS)
            self.assertEqual(ingest_payload["command"], "packet ingest")
            self.assertEqual(ingest_payload["packet"]["packet_id"], "PKT-000002")
            self.assertEqual(ingest_payload["packet"]["source_path"], str(modified_source))

            list_output = io.StringIO()
            with redirect_stdout(list_output):
                list_code = app.main(["packet", "list", "--path", str(root), "--json"])

            listing = json.loads(list_output.getvalue())
            self.assertEqual(list_code, SUCCESS)
            self.assertEqual(listing["command"], "packet list")
            self.assertEqual(len(listing["packets"]), 2)
            self.assertEqual(listing["packets"][0]["packet_id"], "PKT-000001")
            self.assertEqual(listing["packets"][1]["packet_id"], "PKT-000002")

            diff_output = io.StringIO()
            with redirect_stdout(diff_output):
                diff_code = app.main(["packet", "diff", "--path", str(root), "--left", "PKT-000001", "--right", "PKT-000002", "--json"])

            diff_payload = json.loads(diff_output.getvalue())
            self.assertEqual(diff_code, SUCCESS)
            self.assertEqual(diff_payload["command"], "packet diff")
            self.assertIn("EXTRA DIFFERENCE", diff_payload["diff"])

            show_output = io.StringIO()
            with redirect_stdout(show_output):
                show_code = app.main(["packet", "show", "--path", str(root), "--packet-id", "PKT-000001", "--json"])

            shown = json.loads(show_output.getvalue())
            self.assertEqual(show_code, SUCCESS)
            self.assertEqual(shown["packet"]["packet_id"], "PKT-000001")
            self.assertIn("### PROJECT INDEX", shown["text"])

    def test_packet_create_json_format_writes_manifest_and_safety_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "tasks").mkdir(parents=True, exist_ok=True)
            (root / "mythic").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "tasks" / "current_GOALS.md").write_text("Ship packets\n", encoding="utf-8")
            (root / "mythic" / "plan.md").write_text("# Plan\n", encoding="utf-8")
            (root / "mythic" / "loop.md").write_text("# Loop\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "packet",
                        "create",
                        "--task",
                        "render json",
                        "--phase",
                        "build",
                        "--role",
                        "Architect",
                        "--format",
                        "json",
                        "--path",
                        str(root),
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            packet_path = Path(payload["output_file"])
            manifest_path = root / "mythic" / "context_sources.json"

            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["role"], "Architect")
            self.assertEqual(payload["format"], "json")
            self.assertTrue(packet_path.exists())
            self.assertTrue(manifest_path.exists())
            packet_payload = json.loads(packet_path.read_text(encoding="utf-8"))
            manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(packet_payload["role"], "Architect")
            self.assertEqual(packet_payload["required_output_format"], "strict JSON")
            self.assertIn("files_in_scope", packet_payload)
            self.assertIn("selected_sources", manifest_payload)
            self.assertIn("mythic/project_index.json", {item["path"] for item in manifest_payload["selected_sources"]})

    def test_workflow_plan_writes_orchestration_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Coordinate the next implementation slice",
                        "--path",
                        str(root),
                        "--audience",
                        "beginner",
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            plan_path = root / "mythic" / "workflow_plan.json"
            stored = json.loads(plan_path.read_text(encoding="utf-8"))

            self.assertEqual(code, SUCCESS)
            self.assertTrue(plan_path.exists())
            self.assertEqual(payload["command"], "workflow plan")
            self.assertFalse(payload["dry_run"])
            self.assertEqual(payload["output_file"], str(plan_path))
            self.assertEqual(stored["steps"][0]["role"], "Skald")
            self.assertEqual(stored["steps"][-1]["role"], "Scribe")
            self.assertEqual(payload["packet_requests"][0]["role"], "Skald")
            self.assertEqual(payload["packet_requests"][0]["audience"], "beginner")
            self.assertEqual(payload["packet_requests"][0]["output_format"], "markdown")

    def test_workflow_plan_can_generate_step_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "tasks").mkdir(parents=True, exist_ok=True)
            (root / "mythic").mkdir(parents=True, exist_ok=True)
            (root / "tasks" / "current_GOALS.md").write_text("Ship workflow packets\n", encoding="utf-8")
            (root / "docs" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "mythic" / "plan.md").write_text("# Plan\n", encoding="utf-8")
            (root / "mythic" / "loop.md").write_text("# Loop\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Generate role packets",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--role",
                        "Auditor",
                        "--packets",
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            packet_paths = [Path(item["packet_path"]) for item in payload["packet_artifacts"]]

            self.assertEqual(code, SUCCESS)
            self.assertEqual([item["role"] for item in payload["packet_artifacts"]], ["Skald", "Auditor"])
            self.assertEqual(len(packet_paths), 2)
            self.assertTrue(all(path.exists() for path in packet_paths))
            self.assertEqual(packet_paths[0].name, "PKT-000001.md")
            self.assertEqual(packet_paths[1].name, "PKT-000002.md")

    def test_workflow_plan_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Preview orchestration",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--role",
                        "Auditor",
                        "--dry-run",
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertFalse((root / "mythic" / "workflow_plan.json").exists())
            self.assertTrue(payload["dry_run"])
            self.assertEqual([step["role"] for step in payload["plan"]["steps"]], ["Skald", "Auditor"])
            self.assertEqual(payload["plan"]["steps"][0]["handoff_to"], "Auditor")

    def test_grimoire_json_has_no_human_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["grimoire", "add", "my_pkg.plugin:Plugin", "--path", tmp, "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["command"], "grimoire add")
            self.assertEqual(payload["plugins"], ["my_pkg.plugin:Plugin"])

    def test_ai_providers_test_run_and_ingest_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir(parents=True, exist_ok=True)

            providers_output = io.StringIO()
            with redirect_stdout(providers_output):
                providers_code = app.main(["ai", "providers", "--json"])

            providers_payload = json.loads(providers_output.getvalue())
            self.assertEqual(providers_code, SUCCESS)
            self.assertIn("copy-paste", providers_payload["providers"])
            self.assertIn("local", providers_payload["providers"])

            test_output = io.StringIO()
            with redirect_stdout(test_output):
                test_code = app.main(["ai", "test", "--provider", "copy-paste", "--packet", "hello", "--json"])

            test_payload = json.loads(test_output.getvalue())
            self.assertEqual(test_code, SUCCESS)
            self.assertEqual(test_payload["provider"], "copy-paste")
            self.assertTrue(test_payload["configured"])
            self.assertIn("estimate", test_payload)

            run_output = io.StringIO()
            with redirect_stdout(run_output):
                run_code = app.main(["ai", "run", "--provider", "copy-paste", "--packet", "hello", "--dry-run", "--json"])

            run_payload = json.loads(run_output.getvalue())
            self.assertEqual(run_code, SUCCESS)
            self.assertEqual(run_payload["provider"], "copy-paste")
            self.assertTrue(run_payload["dry_run"])

            ingest_output = io.StringIO()
            with redirect_stdout(ingest_output):
                ingest_code = app.main(
                    [
                        "ai",
                        "ingest-response",
                        "--path",
                        str(root),
                        "--provider",
                        "copy-paste",
                        "--model",
                        "manual",
                        "--packet-id",
                        "PKT-000001",
                        "--response",
                        "ok",
                        "--json",
                    ]
                )

            ingest_payload = json.loads(ingest_output.getvalue())
            ingest_path = root / "mythic" / "ai" / "latest_response.json"
            self.assertEqual(ingest_code, SUCCESS)
            self.assertTrue(ingest_path.exists())
            self.assertFalse(ingest_payload["payload"]["applied"])

    def test_verify_records_artifacts_and_unblocks_reflect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir(parents=True, exist_ok=True)
            (root / "tests" / "test_smoke.py").write_text(
                "def test_smoke():\n    assert True\n",
                encoding="utf-8",
            )

            blocked_output = io.StringIO()
            with redirect_stdout(blocked_output), redirect_stderr(blocked_output):
                blocked_code = app.main(
                    [
                        "checkin",
                        "--path",
                        str(root),
                        "--phase",
                        "reflect",
                        "--update",
                        "attempted reflect without verification",
                    ]
                )

            self.assertEqual(blocked_code, USER_INPUT_ERROR)
            self.assertIn("verification", blocked_output.getvalue().lower())

            verify_output = io.StringIO()
            with redirect_stdout(verify_output):
                verify_code = app.main(["verify", "--path", str(root), "--commands", "--json"])

            verify_payload = json.loads(verify_output.getvalue())
            self.assertEqual(verify_code, SUCCESS)
            self.assertEqual(verify_payload["result"], "pass")
            self.assertEqual(verify_payload["level"], "unit")
            self.assertTrue(Path(verify_payload["artifact_path"]).exists())
            self.assertTrue((root / "mythic" / "verifications" / "latest.json").exists())

            reflect_output = io.StringIO()
            with redirect_stdout(reflect_output):
                reflect_code = app.main(
                    [
                        "checkin",
                        "--path",
                        str(root),
                        "--phase",
                        "reflect",
                        "--update",
                        "verification complete",
                    ]
                )

            self.assertEqual(reflect_code, SUCCESS)
            self.assertIn("Mythic check-in recorded.", reflect_output.getvalue())


if __name__ == "__main__":
    unittest.main()
