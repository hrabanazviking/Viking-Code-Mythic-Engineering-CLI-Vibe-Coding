from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from mythic_vibe_cli.context.companion import (
    build_companion_context,
    find_relevant_files,
    render_companion_context,
)


class CompanionContextTests(unittest.TestCase):
    def test_find_relevant_files_scores_path_and_content_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
            (root / "mythic_vibe_cli" / "memory").mkdir(parents=True)
            (root / "mythic_vibe_cli" / "memory" / "store.py").write_text(
                "class MemoryStore:\n    pass\n",
                encoding="utf-8",
            )
            (root / "mythic_vibe_cli" / "app.py").write_text(
                "def main():\n    return 0\n",
                encoding="utf-8",
            )

            results = find_relevant_files(root, "Find the memory system")

        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].path, "mythic_vibe_cli/memory/store.py")
        self.assertGreater(results[0].score, 0)

    def test_render_companion_context_includes_repo_shape_and_relevant_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Example\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname='example'\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_memory.py").write_text("def test_memory(): pass\n", encoding="utf-8")
            (root / "mythic_vibe_cli" / "memory").mkdir(parents=True)
            (root / "mythic_vibe_cli" / "memory" / "store.py").write_text(
                "memory recall session summary\n",
                encoding="utf-8",
            )

            text = render_companion_context(
                build_companion_context(root, "Find memory recall")
            )

        self.assertIn("Repository context", text)
        self.assertIn("Languages:", text)
        self.assertIn("Test commands:", text)
        self.assertIn("mythic_vibe_cli/memory/store.py", text)


if __name__ == "__main__":
    unittest.main()
