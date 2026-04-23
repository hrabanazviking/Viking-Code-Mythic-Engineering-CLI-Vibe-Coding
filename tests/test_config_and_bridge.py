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
            self.assertIn("coding assistant", packet)
            self.assertNotIn("coding copilot", packet)


if __name__ == "__main__":
    unittest.main()
