from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

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
            self.assertEqual(len(loaded.sources), 3)

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
            self.assertIn("## Prompt To Paste", packet)
            self.assertIn("Current phase: plan", packet)

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


if __name__ == "__main__":
    unittest.main()
