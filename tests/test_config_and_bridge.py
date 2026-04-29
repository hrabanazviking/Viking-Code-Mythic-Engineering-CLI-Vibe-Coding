from __future__ import annotations

import os
from contextlib import redirect_stdout
import io
import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli import app
from mythic_vibe_cli.ai.prompts.roles import PACKET_ROLES, ROLE_PRESETS
from mythic_vibe_cli.codex_bridge import CodexBridge, CodexPacketRequest
from mythic_vibe_cli.config import ConfigStore


class ConfigAndBridgeTests(unittest.TestCase):
    def test_config_layering_with_project_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            xdg = root / "xdg"
            project = root / "project"
            home.mkdir(parents=True, exist_ok=True)
            xdg.mkdir(parents=True, exist_ok=True)
            project.mkdir(parents=True, exist_ok=True)

            (home / ".mythic-vibe.json").write_text('{"codex": {"excerpt_limit": 900}}', encoding="utf-8")
            (xdg / "mythic-vibe" / "config.json").parent.mkdir(parents=True, exist_ok=True)
            (xdg / "mythic-vibe" / "config.json").write_text(
                '{"codex": {"packet_char_budget": 7000}}', encoding="utf-8"
            )
            (project / ".mythic-vibe.json").write_text(
                '{"codex": {"excerpt_limit": 1300, "auto_compact": false}}', encoding="utf-8"
            )

            old_home = os.environ.get("HOME")
            old_xdg = os.environ.get("XDG_CONFIG_HOME")
            try:
                os.environ["HOME"] = str(home)
                os.environ["XDG_CONFIG_HOME"] = str(xdg)
                loaded = ConfigStore(project).load()
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home
                if old_xdg is None:
                    os.environ.pop("XDG_CONFIG_HOME", None)
                else:
                    os.environ["XDG_CONFIG_HOME"] = old_xdg

            self.assertEqual(loaded.config.excerpt_limit, 1300)
            self.assertEqual(loaded.config.packet_char_budget, 7000)
            self.assertFalse(loaded.config.auto_compact)
            self.assertEqual(loaded.config.method_source, "https://github.com/hrabanazviking/Mythic-Engineering")
            self.assertEqual(len(loaded.sources), 3)

    def test_method_source_config_layering_and_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            project = root / "project"
            home.mkdir(parents=True, exist_ok=True)
            project.mkdir(parents=True, exist_ok=True)
            (home / ".mythic-vibe.json").write_text(
                '{"method": {"source": "https://github.com/home/method"}}',
                encoding="utf-8",
            )
            (project / ".mythic-vibe.json").write_text(
                '{"method": {"source": "https://github.com/project/method"}}',
                encoding="utf-8",
            )

            old_home = os.environ.get("HOME")
            old_source = os.environ.get("MYTHIC_METHOD_SOURCE")
            try:
                os.environ["HOME"] = str(home)
                loaded = ConfigStore(project).load()
                self.assertEqual(loaded.config.method_source, "https://github.com/project/method")

                os.environ["MYTHIC_METHOD_SOURCE"] = "https://github.com/env/method"
                loaded = ConfigStore(project).load()
                self.assertEqual(loaded.config.method_source, "https://github.com/env/method")
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home
                if old_source is None:
                    os.environ.pop("MYTHIC_METHOD_SOURCE", None)
                else:
                    os.environ["MYTHIC_METHOD_SOURCE"] = old_source

    def test_config_json_reports_method_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath(".mythic-vibe.json").write_text(
                '{"method": {"source": "https://github.com/project/method"}}',
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["config", "--path", tmp, "--json"])

            payload = json.loads(output.getvalue())

            self.assertEqual(code, 0)
            self.assertEqual(payload["config"]["method.source"], "https://github.com/project/method")

    def test_codex_bridge_auto_compacts_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "tasks").mkdir(parents=True, exist_ok=True)
            (root / "mythic").mkdir(parents=True, exist_ok=True)

            long_text = "A" * 5000
            (root / "tasks" / "current_GOALS.md").write_text(long_text, encoding="utf-8")
            (root / "docs" / "ARCHITECTURE.md").write_text(long_text, encoding="utf-8")
            (root / "mythic" / "plan.md").write_text(long_text, encoding="utf-8")
            (root / "mythic" / "loop.md").write_text(long_text, encoding="utf-8")

            (root / ".mythic-vibe.json").write_text(
                '{"codex": {"excerpt_limit": 3000, "packet_char_budget": 1200, "auto_compact": true}}',
                encoding="utf-8",
            )

            bridge = CodexBridge(root)
            packet = bridge._render_packet(CodexPacketRequest(task="x", phase="plan", audience="beginner"))
            self.assertIn("[truncated by mythic-vibe]", packet)
            # Keep this test focused on compaction behavior, not exact prompt phrasing.
            self.assertIn("## 1. Role", packet)
            self.assertIn("Phase: plan", packet)

    def test_skald_is_first_class_packet_role(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "tasks").mkdir(parents=True, exist_ok=True)
            (root / "mythic").mkdir(parents=True, exist_ok=True)
            (root / "tasks" / "current_GOALS.md").write_text("Name the next capability\n", encoding="utf-8")
            (root / "docs" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "mythic" / "plan.md").write_text("# Plan\n", encoding="utf-8")
            (root / "mythic" / "loop.md").write_text("# Loop\n", encoding="utf-8")

            bridge = CodexBridge(root)
            packet = bridge._render_packet(
                CodexPacketRequest(task="Frame the feature vision", phase="intent", audience="advanced", role="Skald")
            )

            self.assertIn("Skald", PACKET_ROLES)
            self.assertIn("Skald", ROLE_PRESETS)
            self.assertIn("Role: Skald", packet)
            self.assertIn("Preserve the true purpose", packet)

    def test_codex_bridge_writes_project_index_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "tasks").mkdir(parents=True, exist_ok=True)
            (root / "mythic").mkdir(parents=True, exist_ok=True)
            (root / "mythic_vibe_cli").mkdir(parents=True, exist_ok=True)
            (root / "tests").mkdir(parents=True, exist_ok=True)

            (root / "tasks" / "current_GOALS.md").write_text("Ship the packet engine\n", encoding="utf-8")
            (root / "docs" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "mythic" / "plan.md").write_text("# Plan\n", encoding="utf-8")
            (root / "mythic" / "loop.md").write_text("# Loop\n", encoding="utf-8")
            (root / "mythic_vibe_cli" / "app.py").write_text("print('hello')\n", encoding="utf-8")
            (root / "tests" / "test_smoke.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

            bridge = CodexBridge(root)
            packet_path = bridge.create_packet(CodexPacketRequest(task="scan context", phase="build", audience="advanced"))
            packet = packet_path.read_text(encoding="utf-8")
            index_path = root / "mythic" / "project_index.json"
            index = index_path.read_text(encoding="utf-8")

            self.assertTrue(packet_path.exists())
            self.assertTrue(index_path.exists())
            self.assertIn("### PROJECT INDEX", packet)
            self.assertIn("recommended_context", packet)
            self.assertIn("mythic_vibe_cli/app.py", index)
            self.assertIn("tests/test_smoke.py", index)

    def test_codex_bridge_weights_budget_toward_priority_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "tasks").mkdir(parents=True, exist_ok=True)
            (root / "mythic").mkdir(parents=True, exist_ok=True)

            long_text = "B" * 4000
            (root / "tasks" / "current_GOALS.md").write_text(long_text, encoding="utf-8")
            (root / "docs" / "ARCHITECTURE.md").write_text(long_text, encoding="utf-8")
            (root / "mythic" / "plan.md").write_text(long_text, encoding="utf-8")
            (root / "mythic" / "loop.md").write_text(long_text, encoding="utf-8")
            (root / ".mythic-vibe.json").write_text(
                '{"codex": {"excerpt_limit": 5000, "packet_char_budget": 1000, "auto_compact": true}}',
                encoding="utf-8",
            )

            bridge = CodexBridge(root)
            sections = {
                "goals": "G" * 4000,
                "architecture": "A" * 4000,
                "plan": "P" * 4000,
                "loop": "L" * 4000,
                "project_index": "I" * 4000,
                "allowed_files": "F" * 4000,
                "forbidden_files": "X" * 4000,
                "invariants": "N" * 4000,
                "verification": "V" * 4000,
            }
            compacted = bridge._compact_sections(sections, 1000)

            self.assertGreater(len(compacted["project_index"]), len(compacted["loop"]))
            self.assertGreater(len(compacted["architecture"]), len(compacted["goals"]))
            self.assertGreater(len(compacted["verification"]), len(compacted["loop"]))


class PacketWriterConcurrencyTests(unittest.TestCase):
    def test_concurrent_packet_creates_serialize_via_mutation_queue(self) -> None:
        import threading

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tasks").mkdir(parents=True, exist_ok=True)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "mythic").mkdir(parents=True, exist_ok=True)
            (root / "tasks" / "current_GOALS.md").write_text("Concurrent goal\n", encoding="utf-8")

            bridge = CodexBridge(root)

            errors: list[BaseException] = []
            results: list[Path] = []
            results_lock = threading.Lock()

            def worker(task: str) -> None:
                try:
                    request = CodexPacketRequest(
                        task=task,
                        phase="build",
                        audience="advanced",
                        role="Forge Worker",
                        output_format="markdown",
                    )
                    out = bridge.create_packet(request)
                    with results_lock:
                        results.append(out)
                except BaseException as exc:  # noqa: BLE001 - capture for assertion
                    errors.append(exc)

            threads = [threading.Thread(target=worker, args=(f"task-{index}",)) for index in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10.0)

            self.assertEqual(errors, [])
            self.assertEqual(len(results), 8)
            packet_dir = root / "mythic" / "packets"
            written = sorted(packet_dir.glob("PKT-*.md"))
            self.assertEqual(len(written), 8)
            packet_ids = {path.stem for path in written}
            self.assertEqual(len(packet_ids), 8)
            for path in written:
                content = path.read_text(encoding="utf-8")
                self.assertIn("# Mythic Engineering Task Packet", content)
                self.assertIn("## 1. Role", content)


if __name__ == "__main__":
    unittest.main()
