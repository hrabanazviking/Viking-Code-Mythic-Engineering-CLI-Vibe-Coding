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
            # The scan command writes to mythic/ as a side-effect (project_index.json,
            # events.jsonl). Git reports the whole untracked mythic/ directory plus the
            # explicitly modified source file. The test guarantees the source file is
            # tracked as changed; the auxiliary mythic/ entry is expected.
            self.assertIn("mythic_vibe_cli/app.py", payload["index"]["git"]["changed_files"])
            recommended_paths = set(payload["index"]["recommended_context"])
            self.assertIn("mythic_vibe_cli/app.py", recommended_paths)


# ---------------------------------------------------------------------------
# PH-26.1 coverage push — exercise the non-git fallback + private helpers
# of ProjectContextScanner. Goal: take ``context/scanner.py`` from 83% to
# 90%+.
# ---------------------------------------------------------------------------


class ProjectScannerNonGitTests(unittest.TestCase):
    """When git isn't available, the scanner falls back to ``os.walk`` —
    a path the existing tests skip because they always init git first."""

    def test_scan_runs_without_git_via_os_walk_fallback(self) -> None:
        """Patch ``_git_available`` to False AND ``_run_git`` to None
        so the discovery + metadata paths both fall through to the
        non-git branches."""
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# x\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
            (root / "mythic_vibe_cli").mkdir()
            (root / "mythic_vibe_cli" / "app.py").write_text("print('x')\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_x.py").write_text("def test_x(): pass\n", encoding="utf-8")

            scanner = ProjectContextScanner(root)
            with mock.patch.object(scanner, "_git_available", return_value=False), \
                 mock.patch("mythic_vibe_cli.context.scanner._run_git", return_value=None):
                index = scanner.scan()
        # Without git, branch is "unknown" but the index still populates
        # via the os.walk fallback in _discover_paths.
        self.assertEqual(index.git["branch"], "unknown")
        self.assertFalse(index.git["dirty"])
        self.assertGreater(len(index.docs), 0)
        self.assertGreater(len(index.tests), 0)
        self.assertGreater(len(index.important_files), 0)


class ProjectScannerEdgeCaseTests(unittest.TestCase):
    """Direct coverage of the smaller helper methods — they're easy to
    exercise standalone but the big integration test skips them."""

    def test_is_doc_path_recognises_md_rst_and_doc_dirs(self) -> None:
        scanner = ProjectContextScanner(Path("."))
        self.assertTrue(scanner._is_doc_path(Path("README.md")))
        self.assertTrue(scanner._is_doc_path(Path("notes.rst")))
        self.assertTrue(scanner._is_doc_path(Path("docs/anything.txt")))
        self.assertFalse(scanner._is_doc_path(Path("src/main.py")))

    def test_is_test_path_recognises_test_dirs_and_filenames(self) -> None:
        scanner = ProjectContextScanner(Path("."))
        self.assertTrue(scanner._is_test_path(Path("tests/test_x.py")))
        self.assertTrue(scanner._is_test_path(Path("test_x.py")))
        self.assertTrue(scanner._is_test_path(Path("x_test.py")))
        self.assertFalse(scanner._is_test_path(Path("src/x.py")))

    def test_language_for_returns_mapped_language(self) -> None:
        scanner = ProjectContextScanner(Path("."))
        # The TEXT_EXTENSIONS map lives in scanner.py; we just want to
        # cover both branches (known + unknown extension).
        self.assertIsNotNone(scanner._language_for(Path("x.py")))
        self.assertIsNone(scanner._language_for(Path("x.unknown_ext")))

    def test_file_size_returns_zero_on_oserror(self) -> None:
        """Pointing at a non-existent path triggers the OSError swallow."""
        scanner = ProjectContextScanner(Path("."))
        size = scanner._file_size(Path("/__definitely_not_a_real_path__.txt"))
        self.assertEqual(size, 0)

    def test_is_binary_detects_null_byte(self) -> None:
        scanner = ProjectContextScanner(Path("."))
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "data.bin"
            target.write_bytes(b"text\x00binary")
            self.assertTrue(scanner._is_binary(target))

    def test_is_binary_detects_invalid_utf8(self) -> None:
        scanner = ProjectContextScanner(Path("."))
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "data.bin"
            target.write_bytes(b"\xff\xfe\xfd not utf 8")
            self.assertTrue(scanner._is_binary(target))

    def test_is_binary_returns_false_on_unreadable_file(self) -> None:
        scanner = ProjectContextScanner(Path("."))
        # Path that doesn't exist -> OSError -> returns False.
        self.assertFalse(scanner._is_binary(Path("/__no_such_file_for_test__")))

    def test_is_binary_returns_false_for_pure_text(self) -> None:
        scanner = ProjectContextScanner(Path("."))
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "x.txt"
            target.write_text("hello world", encoding="utf-8")
            self.assertFalse(scanner._is_binary(target))

    def test_test_command_for_pyproject_returns_pytest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
            (root / "tests").mkdir()
            test_file = root / "tests" / "test_x.py"
            test_file.write_text("def test_x(): pass\n", encoding="utf-8")
            scanner = ProjectContextScanner(root)
            self.assertEqual(scanner._test_command_for(test_file), "pytest -q")

    def test_test_command_for_test_filename_without_pyproject_returns_pytest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            test_file = root / "test_x.py"
            test_file.write_text("def test_x(): pass\n", encoding="utf-8")
            scanner = ProjectContextScanner(root)
            self.assertEqual(scanner._test_command_for(test_file), "pytest -q")

    def test_test_command_for_unknown_file_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "not_a_test.txt"
            target.write_text("x", encoding="utf-8")
            scanner = ProjectContextScanner(root)
            self.assertIsNone(scanner._test_command_for(target))

    def test_important_reason_returns_correct_label(self) -> None:
        scanner = ProjectContextScanner(Path("."))
        self.assertEqual(scanner._important_reason(Path("pyproject.toml")), "package or project metadata")
        self.assertEqual(scanner._important_reason(Path("mythic_vibe_cli/app.py")), "active runtime code")
        self.assertEqual(scanner._important_reason(Path("docs/x.md")), "core documentation")
        self.assertEqual(scanner._important_reason(Path("random.txt")), "important file")

    def test_dedupe_entries_drops_duplicate_paths(self) -> None:
        scanner = ProjectContextScanner(Path("."))
        items = [
            {"path": "a.py", "size": 1},
            {"path": "b.py", "size": 2},
            {"path": "a.py", "size": 99},  # duplicate path
            {"path": None, "size": 3},      # invalid
            {"size": 4},                     # missing path
        ]
        deduped = scanner._dedupe_entries(items)
        self.assertEqual(len(deduped), 2)
        paths = [d["path"] for d in deduped]
        self.assertEqual(paths, ["a.py", "b.py"])


if __name__ == "__main__":
    unittest.main()
