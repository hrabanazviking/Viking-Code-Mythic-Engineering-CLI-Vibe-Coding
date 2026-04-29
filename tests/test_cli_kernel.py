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

    def test_workflow_run_dry_run_loads_existing_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(["workflow", "plan", "--task", "Preview from disk", "--path", str(root), "--role", "Skald", "--role", "Auditor"])

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["workflow", "run", "--path", str(root), "--dry-run", "--json"])

            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["command"], "workflow run")
            self.assertEqual(payload["provider_execution"], "disabled")
            self.assertEqual([step["role"] for step in payload["steps"]], ["Skald", "Auditor"])
            self.assertFalse(payload["steps"][0]["would_execute_provider"])

    def test_workflow_run_packets_only_validates_existing_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "tasks").mkdir(parents=True, exist_ok=True)
            (root / "mythic").mkdir(parents=True, exist_ok=True)
            (root / "tasks" / "current_GOALS.md").write_text("Ship ready packets\n", encoding="utf-8")
            (root / "docs" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "mythic" / "plan.md").write_text("# Plan\n", encoding="utf-8")
            (root / "mythic" / "loop.md").write_text("# Loop\n", encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Validate packets",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--role",
                        "Auditor",
                        "--packets",
                    ]
                )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["workflow", "run", "--path", str(root), "--dry-run", "--packets-only", "--json"])

            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertTrue(payload["packets_only"])
            self.assertTrue(payload["packets_ready"])
            self.assertEqual([item["role"] for item in payload["packet_status"]], ["Skald", "Auditor"])
            self.assertTrue(all(item["found"] for item in payload["packet_status"]))

    def test_workflow_run_packets_only_blocks_missing_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(["workflow", "plan", "--task", "Missing packets", "--path", str(root), "--role", "Skald"])

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["workflow", "run", "--path", str(root), "--dry-run", "--packets-only", "--json"])

            payload = json.loads(output.getvalue())

            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertFalse(payload["packets_ready"])
            self.assertEqual(payload["packet_status"][0]["role"], "Skald")
            self.assertFalse(payload["packet_status"][0]["found"])

    def test_workflow_packets_lists_readiness_for_saved_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "tasks").mkdir(parents=True, exist_ok=True)
            (root / "mythic").mkdir(parents=True, exist_ok=True)
            (root / "tasks" / "current_GOALS.md").write_text("List workflow packets\n", encoding="utf-8")
            (root / "docs" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "mythic" / "plan.md").write_text("# Plan\n", encoding="utf-8")
            (root / "mythic" / "loop.md").write_text("# Loop\n", encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "List packets",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--role",
                        "Auditor",
                        "--packets",
                    ]
                )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["workflow", "packets", "--path", str(root), "--json"])

            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["command"], "workflow packets")
            self.assertTrue(payload["packets_ready"])
            self.assertEqual([item["role"] for item in payload["packet_status"]], ["Skald", "Auditor"])
            self.assertTrue(all(item["packet_id"] for item in payload["packet_status"]))

    def test_workflow_packets_missing_only_filters_ready_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "workflow",
                        "packets",
                        "--path",
                        str(root),
                        "--task",
                        "Missing only",
                        "--role",
                        "Skald",
                        "--missing-only",
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertFalse(payload["packets_ready"])
            self.assertEqual(len(payload["packet_status"]), 1)
            self.assertEqual(payload["packet_status"][0]["role"], "Skald")
            self.assertFalse(payload["packet_status"][0]["found"])

    def test_workflow_run_blocks_real_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(["workflow", "run", "--path", tmp, "--task", "No live execution"])

            self.assertEqual(code, UNSAFE_OPERATION_BLOCKED)
            self.assertIn("dry-run", output.getvalue())

    def test_workflow_plan_stamps_workflow_id_on_generated_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Stamp packets with workflow id",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--packets",
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertTrue(payload["workflow_id"].startswith("WF-"))
            self.assertEqual(payload["plan"]["workflow_id"], payload["workflow_id"])
            self.assertEqual(len(payload["packet_artifacts"]), 1)
            artifact = payload["packet_artifacts"][0]
            self.assertEqual(artifact["workflow_id"], payload["workflow_id"])
            self.assertEqual(artifact["workflow_step_id"], "step-01")
            metadata_path = Path(artifact["metadata_path"])
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["workflow_id"], payload["workflow_id"])
            self.assertEqual(metadata["workflow_step_id"], "step-01")

    def test_workflow_packets_matches_by_workflow_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "ID-based match",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--role",
                        "Auditor",
                        "--packets",
                    ]
                )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["workflow", "packets", "--path", str(root), "--json"])

            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertTrue(payload["packets_ready"])
            self.assertTrue(payload["workflow_id"].startswith("WF-"))
            self.assertEqual(len(payload["packet_status"]), 2)
            for item in payload["packet_status"]:
                self.assertTrue(item["found"])
                self.assertEqual(item["match_strategy"], "id")
                self.assertEqual(item["workflow_id"], payload["workflow_id"])

    def test_workflow_packets_falls_back_to_text_match_for_legacy_plans(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Legacy text match",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--packets",
                    ]
                )

            plan_path = root / "mythic" / "workflow_plan.json"
            plan_payload = json.loads(plan_path.read_text(encoding="utf-8"))
            plan_payload.pop("workflow_id", None)
            plan_path.write_text(json.dumps(plan_payload, indent=2) + "\n", encoding="utf-8")

            packet_dir = root / "mythic" / "packets"
            for meta_path in packet_dir.glob("PKT-*.meta.json"):
                meta_payload = json.loads(meta_path.read_text(encoding="utf-8"))
                meta_payload.pop("workflow_id", None)
                meta_payload.pop("workflow_step_id", None)
                meta_path.write_text(json.dumps(meta_payload, indent=2) + "\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["workflow", "packets", "--path", str(root), "--json"])

            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertTrue(payload["packets_ready"])
            self.assertIsNone(payload["workflow_id"])
            self.assertEqual(payload["packet_status"][0]["match_strategy"], "text")
            self.assertIsNone(payload["packet_status"][0]["workflow_id"])

    def test_packet_create_embeds_method_excerpts_when_corpus_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "docs" / "mythic_source"
            corpus.mkdir(parents=True)
            (corpus / "verification.md").write_text(
                "# Verification Method\n\n"
                "Verify that result matches intent, not just that code ran.\n\n"
                "# Failure Modes\n\n"
                "Watch for silent test skips.\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "packet",
                        "create",
                        "--task",
                        "Audit the new gate",
                        "--phase",
                        "verify",
                        "--role",
                        "Auditor",
                        "--path",
                        str(root),
                        "--format",
                        "json",
                        "--json",
                    ]
                )
            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            packet_path = Path(payload["output_file"])
            packet_payload = json.loads(packet_path.read_text(encoding="utf-8"))
            sections = [excerpt["section"] for excerpt in packet_payload["method_excerpts"]]
            self.assertEqual(sections, ["verification method", "failure modes"])
            self.assertIn("matches intent", packet_payload["method_excerpts"][0]["text"])
            self.assertEqual(packet_payload["method_excerpts"][0]["source_path"], "verification.md")

    def test_packet_create_markdown_includes_method_excerpts_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "docs" / "mythic_source"
            corpus.mkdir(parents=True)
            (corpus / "principles.md").write_text(
                "# Principles\n\nHold to the simplest design that solves the intent.\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "packet",
                        "create",
                        "--task",
                        "Frame the capability",
                        "--phase",
                        "intent",
                        "--role",
                        "Skald",
                        "--path",
                        str(root),
                        "--json",
                    ]
                )
            payload = json.loads(output.getvalue())
            packet_path = Path(payload["output_file"])
            text = packet_path.read_text(encoding="utf-8")

            self.assertEqual(code, SUCCESS)
            self.assertIn("## 12. Method Excerpts", text)
            self.assertIn("### Principles — `principles.md`", text)
            self.assertIn("simplest design", text)
            self.assertLess(text.index("## 12. Method Excerpts"), text.index("### SAFETY"))

    def test_packet_create_omits_method_section_when_corpus_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "packet",
                        "create",
                        "--task",
                        "No corpus available",
                        "--phase",
                        "build",
                        "--role",
                        "Forge Worker",
                        "--path",
                        str(root),
                        "--format",
                        "json",
                        "--json",
                    ]
                )
            payload = json.loads(output.getvalue())
            packet_path = Path(payload["output_file"])
            packet_payload = json.loads(packet_path.read_text(encoding="utf-8"))

            self.assertEqual(code, SUCCESS)
            self.assertEqual(packet_payload["method_excerpts"], [])
            markdown_path = packet_path.with_suffix(".md")
            if markdown_path.exists():
                self.assertNotIn("## 12. Method Excerpts", markdown_path.read_text(encoding="utf-8"))

    def test_workflow_history_lists_saved_plans_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(["workflow", "plan", "--task", "First saved", "--path", str(root), "--role", "Skald"])
                app.main(["workflow", "plan", "--task", "Second saved", "--path", str(root), "--role", "Auditor"])

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["workflow", "history", "--path", str(root), "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["command"], "workflow history")
            self.assertEqual(payload["count"], 2)
            self.assertEqual(payload["total"], 2)
            self.assertEqual([entry["task"] for entry in payload["entries"]], ["Second saved", "First saved"])
            self.assertTrue(payload["entries"][0]["workflow_id"].startswith("WF-"))

    def test_workflow_history_dry_run_does_not_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(["workflow", "plan", "--task", "Dry preview", "--path", str(root), "--role", "Skald", "--dry-run"])

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["workflow", "history", "--path", str(root), "--json"])
            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["count"], 0)
            self.assertEqual(payload["total"], 0)
            self.assertFalse((root / "mythic" / "workflow_history.json").exists())

    def test_workflow_history_limit_caps_returned_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                for index in range(3):
                    app.main(
                        ["workflow", "plan", "--task", f"Task {index}", "--path", str(root), "--role", "Skald"]
                    )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    ["workflow", "history", "--path", str(root), "--limit", "2", "--json"]
                )
            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["count"], 2)
            self.assertEqual(payload["total"], 3)
            self.assertEqual([entry["task"] for entry in payload["entries"]], ["Task 2", "Task 1"])

    def test_workflow_history_empty_returns_friendly_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["workflow", "history", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            self.assertIn("No workflow history recorded yet", output.getvalue())

    def test_packet_list_filters_by_workflow_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "First workflow",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--packets",
                    ]
                )
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Second workflow",
                        "--path",
                        str(root),
                        "--role",
                        "Auditor",
                        "--packets",
                    ]
                )

            unfiltered_output = io.StringIO()
            with redirect_stdout(unfiltered_output):
                code = app.main(["packet", "list", "--path", str(root), "--json"])

            unfiltered = json.loads(unfiltered_output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(len(unfiltered["packets"]), 2)
            self.assertIsNone(unfiltered["filters"]["workflow_id"])
            target_id = unfiltered["packets"][0]["workflow_id"]
            self.assertTrue(target_id.startswith("WF-"))

            filtered_output = io.StringIO()
            with redirect_stdout(filtered_output):
                filtered_code = app.main(
                    ["packet", "list", "--path", str(root), "--workflow", target_id, "--json"]
                )

            filtered = json.loads(filtered_output.getvalue())
            self.assertEqual(filtered_code, SUCCESS)
            self.assertEqual(filtered["filters"]["workflow_id"], target_id)
            self.assertEqual(len(filtered["packets"]), 1)
            self.assertEqual(filtered["packets"][0]["workflow_id"], target_id)

            step_output = io.StringIO()
            with redirect_stdout(step_output):
                step_code = app.main(
                    [
                        "packet",
                        "list",
                        "--path",
                        str(root),
                        "--workflow",
                        target_id,
                        "--step",
                        "step-01",
                        "--json",
                    ]
                )

            step_payload = json.loads(step_output.getvalue())
            self.assertEqual(step_code, SUCCESS)
            self.assertEqual(step_payload["filters"]["workflow_step_id"], "step-01")
            self.assertEqual(len(step_payload["packets"]), 1)
            self.assertEqual(step_payload["packets"][0]["workflow_step_id"], "step-01")

    def test_packet_list_step_requires_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(["packet", "list", "--path", tmp, "--step", "step-01"])

            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("--step requires --workflow", output.getvalue())

    def test_packet_list_latest_workflow_filters_to_saved_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "First saved",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--packets",
                    ]
                )
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Second saved",
                        "--path",
                        str(root),
                        "--role",
                        "Auditor",
                        "--packets",
                    ]
                )

            saved_id = json.loads((root / "mythic" / "workflow_plan.json").read_text(encoding="utf-8"))["workflow_id"]

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    ["packet", "list", "--path", str(root), "--latest-workflow", "--json"]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["latest_workflow_id"], saved_id)
            self.assertEqual(payload["filters"]["workflow_id"], saved_id)
            self.assertEqual(len(payload["packets"]), 1)
            self.assertEqual(payload["packets"][0]["workflow_id"], saved_id)

    def test_packet_list_latest_workflow_conflicts_with_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(
                    [
                        "packet",
                        "list",
                        "--path",
                        tmp,
                        "--latest-workflow",
                        "--workflow",
                        "WF-x",
                    ]
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("--latest-workflow cannot be combined with --workflow", output.getvalue())

    def test_packet_list_latest_workflow_errors_when_plan_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(["packet", "list", "--path", tmp, "--latest-workflow"])
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("Workflow plan not found", output.getvalue())

    def test_packet_list_latest_workflow_with_step_narrows_further(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Latest narrow",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--role",
                        "Auditor",
                        "--packets",
                    ]
                )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "packet",
                        "list",
                        "--path",
                        str(root),
                        "--latest-workflow",
                        "--step",
                        "step-02",
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["filters"]["workflow_step_id"], "step-02")
            self.assertEqual(len(payload["packets"]), 1)
            self.assertEqual(payload["packets"][0]["workflow_step_id"], "step-02")

    def test_packet_show_resolves_by_workflow_and_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Show by workflow",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--role",
                        "Auditor",
                        "--packets",
                    ]
                )

            list_output = io.StringIO()
            with redirect_stdout(list_output):
                app.main(["packet", "list", "--path", str(root), "--json"])
            listing = json.loads(list_output.getvalue())
            target = next(p for p in listing["packets"] if p["workflow_step_id"] == "step-02")

            show_output = io.StringIO()
            with redirect_stdout(show_output):
                code = app.main(
                    [
                        "packet",
                        "show",
                        "--path",
                        str(root),
                        "--workflow",
                        target["workflow_id"],
                        "--step",
                        "step-02",
                        "--json",
                    ]
                )

            payload = json.loads(show_output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["packet_id"], target["packet_id"])
            self.assertEqual(payload["packet"]["workflow_step_id"], "step-02")

    def test_packet_show_workflow_addressing_requires_both_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(["packet", "show", "--path", tmp, "--workflow", "WF-x", "--json"])
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("requires both --workflow and --step", output.getvalue())

    def test_packet_show_rejects_packet_id_with_workflow_addressing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(
                    [
                        "packet",
                        "show",
                        "--path",
                        tmp,
                        "--packet-id",
                        "PKT-000001",
                        "--workflow",
                        "WF-x",
                        "--step",
                        "step-01",
                    ]
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("--packet-id cannot be combined", output.getvalue())

    def test_packet_show_unknown_workflow_step_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(
                    [
                        "packet",
                        "show",
                        "--path",
                        tmp,
                        "--workflow",
                        "WF-nope",
                        "--step",
                        "step-99",
                    ]
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("No packet stamped with workflow", output.getvalue())

    def test_packet_diff_accepts_workflow_step_shorthand(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Diff by workflow",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--role",
                        "Auditor",
                        "--packets",
                    ]
                )

            list_output = io.StringIO()
            with redirect_stdout(list_output):
                app.main(["packet", "list", "--path", str(root), "--json"])
            listing = json.loads(list_output.getvalue())
            workflow_id = listing["packets"][0]["workflow_id"]

            diff_output = io.StringIO()
            with redirect_stdout(diff_output):
                code = app.main(
                    [
                        "packet",
                        "diff",
                        "--path",
                        str(root),
                        "--left",
                        f"{workflow_id}:step-01",
                        "--right",
                        f"{workflow_id}:step-02",
                        "--json",
                    ]
                )

            payload = json.loads(diff_output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["command"], "packet diff")
            self.assertEqual(payload["left_ref"], f"{workflow_id}:step-01")
            self.assertEqual(payload["right_ref"], f"{workflow_id}:step-02")
            self.assertTrue(payload["left"].startswith("PKT-"))
            self.assertTrue(payload["right"].startswith("PKT-"))
            self.assertNotEqual(payload["left"], payload["right"])

    def test_packet_show_previous_workflow_resolves_from_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Older saved",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--packets",
                    ]
                )
                older_id = json.loads((root / "mythic" / "workflow_plan.json").read_text(encoding="utf-8"))["workflow_id"]
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Newer saved",
                        "--path",
                        str(root),
                        "--role",
                        "Auditor",
                        "--packets",
                    ]
                )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "packet",
                        "show",
                        "--path",
                        str(root),
                        "--previous-workflow",
                        "--step",
                        "step-01",
                        "--json",
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["packet"]["workflow_id"], older_id)
            self.assertEqual(payload["packet"]["workflow_step_id"], "step-01")

    def test_packet_show_previous_workflow_requires_history_depth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    ["workflow", "plan", "--task", "Only one", "--path", str(root), "--role", "Skald"]
                )

            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(
                    ["packet", "show", "--path", str(root), "--previous-workflow", "--step", "step-01"]
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("No previous workflow recorded", output.getvalue())

    def test_packet_show_previous_workflow_conflicts_with_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(
                    [
                        "packet",
                        "show",
                        "--path",
                        tmp,
                        "--latest-workflow",
                        "--previous-workflow",
                        "--step",
                        "step-01",
                    ]
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("--latest-workflow cannot be combined with --previous-workflow", output.getvalue())

    def test_packet_diff_supports_latest_and_previous_sentinels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Older saved",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--packets",
                    ]
                )
                older_id = json.loads((root / "mythic" / "workflow_plan.json").read_text(encoding="utf-8"))["workflow_id"]
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Newer saved",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--packets",
                    ]
                )
                newer_id = json.loads((root / "mythic" / "workflow_plan.json").read_text(encoding="utf-8"))["workflow_id"]

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "packet",
                        "diff",
                        "--path",
                        str(root),
                        "--left",
                        "LATEST:step-01",
                        "--right",
                        "PREVIOUS:step-01",
                        "--json",
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["left_ref"], "LATEST:step-01")
            self.assertEqual(payload["right_ref"], "PREVIOUS:step-01")
            self.assertNotEqual(payload["left"], payload["right"])
            list_output = io.StringIO()
            with redirect_stdout(list_output):
                app.main(["packet", "list", "--path", str(root), "--json"])
            packets = json.loads(list_output.getvalue())["packets"]
            left_packet = next(p for p in packets if p["packet_id"] == payload["left"])
            right_packet = next(p for p in packets if p["packet_id"] == payload["right"])
            self.assertEqual(left_packet["workflow_id"], newer_id)
            self.assertEqual(right_packet["workflow_id"], older_id)

    def test_packet_diff_previous_sentinel_errors_without_history_depth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Only one saved",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--packets",
                    ]
                )

            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(
                    [
                        "packet",
                        "diff",
                        "--path",
                        str(root),
                        "--left",
                        "LATEST:step-01",
                        "--right",
                        "PREVIOUS:step-01",
                    ]
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("No previous workflow recorded", output.getvalue())

    def test_packet_show_latest_workflow_resolves_from_saved_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Latest workflow show",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--role",
                        "Auditor",
                        "--packets",
                    ]
                )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "packet",
                        "show",
                        "--path",
                        str(root),
                        "--latest-workflow",
                        "--step",
                        "step-02",
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["packet"]["workflow_step_id"], "step-02")
            saved_plan = json.loads((root / "mythic" / "workflow_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["packet"]["workflow_id"], saved_plan["workflow_id"])

    def test_packet_show_latest_workflow_requires_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(["packet", "show", "--path", tmp, "--latest-workflow"])
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("--latest-workflow requires --step", output.getvalue())

    def test_packet_show_latest_workflow_errors_when_plan_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(
                    ["packet", "show", "--path", tmp, "--latest-workflow", "--step", "step-01"]
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("Workflow plan not found", output.getvalue())

    def test_packet_show_latest_workflow_errors_when_plan_lacks_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Strip id",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                    ]
                )
            plan_path = root / "mythic" / "workflow_plan.json"
            payload = json.loads(plan_path.read_text(encoding="utf-8"))
            payload.pop("workflow_id", None)
            plan_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(
                    ["packet", "show", "--path", str(root), "--latest-workflow", "--step", "step-01"]
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("no workflow_id", output.getvalue())

    def test_packet_diff_latest_workflow_accepts_bare_step_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Latest workflow diff",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--role",
                        "Auditor",
                        "--packets",
                    ]
                )

            saved_id = json.loads((root / "mythic" / "workflow_plan.json").read_text(encoding="utf-8"))["workflow_id"]

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "packet",
                        "diff",
                        "--path",
                        str(root),
                        "--latest-workflow",
                        "--left",
                        "step-01",
                        "--right",
                        "step-02",
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["latest_workflow_id"], saved_id)
            self.assertEqual(payload["left_ref"], "step-01")
            self.assertEqual(payload["right_ref"], "step-02")
            self.assertTrue(payload["left"].startswith("PKT-"))
            self.assertTrue(payload["right"].startswith("PKT-"))
            self.assertNotEqual(payload["left"], payload["right"])

    def test_packet_diff_latest_workflow_falls_through_for_pkt_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Mixed refs",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--role",
                        "Auditor",
                        "--packets",
                    ]
                )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "packet",
                        "diff",
                        "--path",
                        str(root),
                        "--latest-workflow",
                        "--left",
                        "PKT-000001",
                        "--right",
                        "step-02",
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["left"], "PKT-000001")
            self.assertEqual(payload["left_ref"], "PKT-000001")
            self.assertEqual(payload["right_ref"], "step-02")

    def test_packet_diff_unknown_workflow_step_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Diff bad ref",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--packets",
                    ]
                )

            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(
                    [
                        "packet",
                        "diff",
                        "--path",
                        str(root),
                        "--left",
                        "WF-nope:step-01",
                        "--right",
                        "WF-nope:step-02",
                    ]
                )
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("No packet stamped with workflow WF-nope", output.getvalue())

    def test_packet_list_workflow_filter_excludes_legacy_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "workflow",
                        "plan",
                        "--task",
                        "Mixed legacy",
                        "--path",
                        str(root),
                        "--role",
                        "Skald",
                        "--packets",
                    ]
                )
                app.main(
                    [
                        "packet",
                        "create",
                        "--task",
                        "Legacy untracked packet",
                        "--phase",
                        "build",
                        "--path",
                        str(root),
                    ]
                )

            unfiltered_output = io.StringIO()
            with redirect_stdout(unfiltered_output):
                app.main(["packet", "list", "--path", str(root), "--json"])
            unfiltered = json.loads(unfiltered_output.getvalue())
            self.assertEqual(len(unfiltered["packets"]), 2)
            workflow_id = next(p["workflow_id"] for p in unfiltered["packets"] if p.get("workflow_id"))

            filtered_output = io.StringIO()
            with redirect_stdout(filtered_output):
                code = app.main(
                    ["packet", "list", "--path", str(root), "--workflow", workflow_id, "--json"]
                )
            filtered = json.loads(filtered_output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(len(filtered["packets"]), 1)
            self.assertEqual(filtered["packets"][0]["workflow_id"], workflow_id)

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
