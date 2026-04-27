from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from mythic_vibe_cli import app
from mythic_vibe_cli.context.scanner import ProjectContextScanner
from mythic_vibe_cli.exit_codes import SUCCESS


class ProjectScanTests(unittest.TestCase):
    def _git(self, root: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)

    def test_scan_builds_project_index_and_honors_git_and_mythic_ignores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            self._git(root, "init")
            self._git(root, "config", "user.name", "Codex")
            self._git(root, "config", "user.email", "codex@example.com")

            (root / "README.md").write_text("# Example\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")
            (root / "mythic_vibe_cli").mkdir()
            (root / "mythic_vibe_cli" / "app.py").write_text("print('hello')\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "vendor").mkdir()
            (root / "vendor" / "secret.txt").write_text("ignore me\n", encoding="utf-8")
            (root / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
            (root / ".mythicignore").write_text("vendor/\n", encoding="utf-8")
            (root / "ignored.txt").write_text("ignored by git\n", encoding="utf-8")

            self._git(root, "add", ".")
            self._git(root, "commit", "-m", "baseline")

            (root / "mythic_vibe_cli" / "app.py").write_text("print('changed')\n", encoding="utf-8")
            (root / "new_file.py").write_text("print('new')\n", encoding="utf-8")

            scanner = ProjectContextScanner(root)
            index = scanner.scan()

            self.assertEqual(index.root, str(root))
            self.assertTrue(index.git["dirty"])
            self.assertIn("mythic_vibe_cli/app.py", index.git["changed_files"])
            self.assertIn("new_file.py", index.git["changed_files"])
            self.assertIn("python", index.languages)
            self.assertGreaterEqual(index.languages["python"]["files"], 2)
            self.assertTrue(any(item["path"] == "README.md" for item in index.important_files))
            self.assertTrue(any(item["path"] == "docs/ARCHITECTURE.md" for item in index.docs))
            self.assertTrue(any(item["path"] == "tests/test_app.py" for item in index.tests))
            self.assertTrue(any(item["path"] == "vendor/secret.txt" for item in index.ignored))
            self.assertFalse(any(item["path"] == "ignored.txt" for item in index.ignored))

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["scan", "--path", str(root), "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["command"], "scan")
            self.assertEqual(payload["index"]["root"], str(root))
            self.assertTrue(payload["index"]["git"]["dirty"])
            self.assertTrue(Path(payload["index_path"]).exists())

    def test_scan_changed_only_limits_recommended_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            self._git(root, "init")
            self._git(root, "config", "user.name", "Codex")
            self._git(root, "config", "user.email", "codex@example.com")

            (root / "README.md").write_text("# Example\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname = 'example'\n", encoding="utf-8")
            (root / "mythic_vibe_cli").mkdir()
            (root / "mythic_vibe_cli" / "app.py").write_text("print('hello')\n", encoding="utf-8")
            self._git(root, "add", ".")
            self._git(root, "commit", "-m", "baseline")

            (root / "mythic_vibe_cli" / "app.py").write_text("print('changed')\n", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["scan", "--path", str(root), "--changed", "--json"])

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["command"], "scan")
            self.assertEqual(payload["index"]["git"]["changed_files"], ["mythic_vibe_cli/app.py"])
            self.assertTrue(all(path == "mythic_vibe_cli/app.py" for path in payload["index"]["recommended_context"]))


if __name__ == "__main__":
    unittest.main()
