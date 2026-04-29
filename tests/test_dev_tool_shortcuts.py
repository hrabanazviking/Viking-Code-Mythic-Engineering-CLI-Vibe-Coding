"""Tests for the PH-02 slice 2.2 developer-tool shortcuts.

Each handler is a thin wrapper around either runtime.exec (for tools
that shell out) or pure-Python helpers (scaffold, changelog, version).
The tests favour deterministic dry-run / JSON paths so they don't
require pytest/ruff/mypy themselves to be installed in the project
under test.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli import app, commands
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR


class TestShortcutDryRunTests(unittest.TestCase):
    """Dry-run paths build the argv but never invoke the tool."""

    def test_test_dry_run_shows_default_pytest_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["test", "--dry-run", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            self.assertIn("Dry run", stdout.getvalue())
            self.assertIn("pytest", stdout.getvalue())

    def test_test_dry_run_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["test", "--dry-run", "--json", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["dry_run"])
            self.assertEqual(payload["command"], "test")
            self.assertIn("argv", payload)

    def test_lint_dry_run_default_argv_is_ruff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["lint", "--dry-run", "--json", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["argv"][0], "ruff")
            self.assertIn("check", payload["argv"])

    def test_typecheck_dry_run_default_argv_is_mypy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["typecheck", "--dry-run", "--json", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["argv"][0], "mypy")

    def test_lint_command_override_uses_user_argv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    [
                        "lint",
                        "--dry-run",
                        "--json",
                        "--command",
                        "ruff",
                        "check",
                        "src/",
                        "--path",
                        tmp,
                    ]
                )
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["argv"], ["ruff", "check", "src/"])


class ScaffoldAdrTests(unittest.TestCase):
    def test_scaffold_adr_writes_numbered_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    [
                        "scaffold",
                        "adr",
                        "--title",
                        "Pin Python 3.11",
                        "--path",
                        tmp,
                        "--json",
                    ]
                )
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["number"], 1)
            self.assertIn("ADR-0001-pin-python-3-11.md", payload["target"])

            target = Path(payload["target"])
            self.assertTrue(target.exists())
            content = target.read_text(encoding="utf-8")
            self.assertIn("Pin Python 3.11", content)
            self.assertIn("ADR-0001", content)

    def test_scaffold_adr_auto_increments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for title in ("First", "Second"):
                with redirect_stdout(io.StringIO()):
                    code = app.main(
                        ["scaffold", "adr", "--title", title, "--path", tmp]
                    )
                self.assertEqual(code, SUCCESS)
            adr_dir = Path(tmp) / "docs" / "ADRS"
            files = sorted(p.name for p in adr_dir.glob("ADR-*.md"))
            self.assertEqual(files, ["ADR-0001-first.md", "ADR-0002-second.md"])

    def test_scaffold_adr_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    [
                        "scaffold",
                        "adr",
                        "--title",
                        "Dry run only",
                        "--dry-run",
                        "--path",
                        tmp,
                    ]
                )
            self.assertEqual(code, SUCCESS)
            self.assertIn("Dry run", stdout.getvalue())
            self.assertFalse((Path(tmp) / "docs" / "ADRS").exists())

    # NOTE: ``cmd_scaffold`` checks ``target.exists()`` before writing as
    # belt-and-suspenders defence against a concurrent write race. The
    # check is structurally unreachable through the auto-numbering logic
    # alone (``_next_adr_number`` always returns highest_existing + 1, so
    # the new target slot is never occupied). A unit test that
    # *manufactures* a collision is contrived enough to be misleading
    # about real behaviour; the defensive check stays in code without a
    # paired test.

    def test_scaffold_unknown_artefact_returns_user_error(self) -> None:
        from contextlib import redirect_stderr

        ns = argparse.Namespace(path=".", artefact="taskography", title="x")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = commands.cmd_scaffold(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        self.assertIn("not yet implemented", stderr.getvalue())


class ChangelogTests(unittest.TestCase):
    def test_changelog_prints_unreleased_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CHANGELOG.md").write_text(
                "# Changelog\n\n## [Unreleased]\n\n### Added\n\n- Foo\n\n## [0.1.0]\n\n- Init\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["changelog", "--path", str(root)])
            self.assertEqual(code, SUCCESS)
            self.assertIn("[Unreleased]", stdout.getvalue())
            self.assertIn("- Foo", stdout.getvalue())
            self.assertNotIn("[0.1.0]", stdout.getvalue())

    def test_changelog_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CHANGELOG.md").write_text(
                "## [Unreleased]\n\n- Bar\n",
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["changelog", "--json", "--path", str(root)])
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertIn("[Unreleased]", payload["unreleased"])
            self.assertEqual(payload["warnings"], [])

    def test_changelog_warns_when_no_unreleased_section(self) -> None:
        from contextlib import redirect_stderr

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CHANGELOG.md").write_text("# Changelog\n\n## [0.1.0]\n", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = app.main(["changelog", "--path", str(root)])
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("does not contain an [Unreleased]", stderr.getvalue())

    def test_changelog_missing_file_reports_error(self) -> None:
        from contextlib import redirect_stderr

        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = app.main(["changelog", "--path", tmp])
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("not found", stderr.getvalue())

    def test_changelog_check_missing_validator_reports_error(self) -> None:
        from contextlib import redirect_stderr

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CHANGELOG.md").write_text("## [Unreleased]\n", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = app.main(["changelog", "--check", "--path", str(root)])
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("Validator script not found", stderr.getvalue())


class VersionTests(unittest.TestCase):
    def test_version_prints_cli_version(self) -> None:
        from mythic_vibe_cli import __version__

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = app.main(["version"])
        self.assertEqual(code, SUCCESS)
        self.assertIn(__version__, stdout.getvalue())

    def test_version_json_includes_python_and_platform(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = app.main(["version", "--json"])
        self.assertEqual(code, SUCCESS)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["command"], "version")
        self.assertIn("mythic_vibe_cli", payload)
        self.assertIn("python", payload)
        self.assertIn("platform", payload)
        self.assertIn("executable", payload)

    def test_version_verbose_flag_extends_text_output(self) -> None:
        import platform

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = app.main(["version", "--verbose"])
        self.assertEqual(code, SUCCESS)
        output = stdout.getvalue()
        self.assertIn("Python", output)
        self.assertIn(platform.python_version(), output)


if __name__ == "__main__":
    unittest.main()
