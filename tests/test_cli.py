from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.cli import main


class MythicCliRitualTests(unittest.TestCase):
    def test_imbue_creates_system_vision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = main(["imbue", "--goal", "Build a test system", "--path", tmp])
            self.assertEqual(code, 0)
            vision = Path(tmp) / "SYSTEM_VISION.md"
            self.assertTrue(vision.exists())

    def test_grimoire_add_and_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            add_code = main(["grimoire", "add", "my_pkg.plugin:Plugin", "--path", tmp])
            self.assertEqual(add_code, 0)

            registry = Path(tmp) / "mythic" / "plugins.json"
            payload = json.loads(registry.read_text(encoding="utf-8"))
            self.assertIn("my_pkg.plugin:Plugin", payload["plugins"])

            list_code = main(["grimoire", "list", "--path", tmp])
            self.assertEqual(list_code, 0)

    def test_db_migrate_creates_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = main(["db", "migrate", "--path", tmp])
            self.assertEqual(code, 0)
            self.assertTrue((Path(tmp) / "mythic" / "weave.db").exists())


if __name__ == "__main__":
    unittest.main()
