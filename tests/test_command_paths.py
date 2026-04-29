"""Coverage tests for several CLI command paths that lack direct tests.

Focused on cheap, isolated handler paths that are pure-Python and
require no network, no API keys, and no real provider calls. Each
test exercises both the happy path and at least one error or JSON
variant of the same handler to lift line coverage on
``mythic_vibe_cli.commands``.

Slice 1.4 is tests-only — none of these tests modify production
behaviour or call into a code change.
"""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli import app
from mythic_vibe_cli.exit_codes import (
    SUCCESS,
    USER_INPUT_ERROR,
    VERIFICATION_FAILURE,
)


def _silent_init(root: Path, *, goal: str = "coverage-test") -> None:
    with redirect_stdout(io.StringIO()):
        app.main(["init", "--goal", goal, "--path", str(root)])


class CmdSyncTests(unittest.TestCase):
    """``mythic-vibe sync`` previously lacked direct tests. Cover the
    dry-run paths only — the live-network path requires an internet
    connection and is exercised by integration runs, not the local
    suite. The ``sync`` subparser does not accept ``--path``, so
    these tests build the Namespace directly rather than going
    through ``app.main``.
    """

    def test_sync_dry_run_text_output(self) -> None:
        import argparse as argparse_module

        from mythic_vibe_cli import commands

        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse_module.Namespace(path=tmp, dry_run=True, json=False)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = commands.cmd_sync(ns)
            self.assertEqual(code, SUCCESS)
            output = stdout.getvalue()
            self.assertIn("Dry run", output)
            self.assertIn("Cache", output)

    def test_sync_dry_run_json_output(self) -> None:
        import argparse as argparse_module

        from mythic_vibe_cli import commands

        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse_module.Namespace(path=tmp, dry_run=True, json=True)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = commands.cmd_sync(ns)
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["dry_run"])
            self.assertEqual(payload["command"], "sync")
            self.assertIn("source", payload)
            self.assertIn("cache_file", payload)


class CmdCodexLogTests(unittest.TestCase):
    """Cover ``mythic-vibe codex-log`` dry-run, happy, and bad-phase paths."""

    def test_codex_log_dry_run_writes_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _silent_init(root)
            devlog_path = root / "docs" / "DEVLOG.md"
            devlog_before = devlog_path.read_text(encoding="utf-8") if devlog_path.exists() else ""

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    [
                        "codex-log",
                        "--phase",
                        "plan",
                        "--response",
                        "Captured plan from Codex",
                        "--dry-run",
                        "--path",
                        str(root),
                    ]
                )
            self.assertEqual(code, SUCCESS)
            self.assertIn("Dry run", stdout.getvalue())
            devlog_after = devlog_path.read_text(encoding="utf-8") if devlog_path.exists() else ""
            self.assertEqual(devlog_before, devlog_after)

    def test_codex_log_records_response_into_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _silent_init(root)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    [
                        "codex-log",
                        "--phase",
                        "plan",
                        "--response",
                        "Captured plan from Codex",
                        "--path",
                        str(root),
                    ]
                )
            self.assertEqual(code, SUCCESS)
            self.assertIn("Codex response logged", stdout.getvalue())
            devlog = (root / "docs" / "DEVLOG.md").read_text(encoding="utf-8")
            self.assertIn("Captured plan from Codex", devlog)

    def test_codex_log_rejects_unknown_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _silent_init(root)
            stderr = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                # argparse blocks unknown phases at parse time, so the
                # subprocess returns code 2 via SystemExit rather than
                # going through our handler. We confirm that argparse
                # does the gating, not the handler.
                with self.assertRaises(SystemExit) as cm:
                    app.main(
                        [
                            "codex-log",
                            "--phase",
                            "no-such-phase",
                            "--response",
                            "x",
                            "--path",
                            str(root),
                        ]
                    )
                self.assertEqual(cm.exception.code, 2)


class CmdStateShowTests(unittest.TestCase):
    """Cover ``mythic-vibe state show`` text + json + missing-file paths."""

    def test_state_show_text_after_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _silent_init(root)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["state", "show", "--path", str(root)])
            self.assertEqual(code, SUCCESS)
            output = stdout.getvalue()
            self.assertIn("Mythic project state", output)
            self.assertIn("Schema version", output)
            self.assertIn("Project ID", output)

    def test_state_show_json_after_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _silent_init(root)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["state", "show", "--json", "--path", str(root)])
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["ok"])
            self.assertIn("state", payload)
            self.assertIn("project_id", payload["state"])

    def test_state_show_reports_missing_status_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = app.main(["state", "show", "--path", tmp])
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("No mythic/status.json", stderr.getvalue())

    def test_state_show_missing_status_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["state", "show", "--json", "--path", tmp])
            self.assertEqual(code, USER_INPUT_ERROR)
            payload = json.loads(stdout.getvalue())
            self.assertFalse(payload["ok"])
            self.assertTrue(any("No mythic/status.json" in e for e in payload["errors"]))


class CmdStateValidateTests(unittest.TestCase):
    """Cover ``mythic-vibe state validate`` text + json + missing-file paths."""

    def test_state_validate_text_after_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _silent_init(root)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["state", "validate", "--path", str(root)])
            self.assertEqual(code, SUCCESS)
            output = stdout.getvalue()
            self.assertIn("validation", output.lower())

    def test_state_validate_json_after_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _silent_init(root)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["state", "validate", "--json", "--path", str(root)])
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["errors"], [])

    def test_state_validate_reports_missing_status_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = app.main(["state", "validate", "--path", tmp])
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("No mythic/status.json", stderr.getvalue())

    def test_state_validate_corrupt_payload_reports_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "status.json").write_text(
                json.dumps({"schema_version": 1, "current_phase": "no-such-phase"}),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["state", "validate", "--json", "--path", str(root)])
            self.assertEqual(code, VERIFICATION_FAILURE)
            payload = json.loads(stdout.getvalue())
            self.assertFalse(payload["ok"])
            self.assertGreater(len(payload["errors"]), 0)


class MainModuleSmokeTest(unittest.TestCase):
    """Cover ``mythic_vibe_cli/__main__.py`` so the entry-point boilerplate
    isn't permanently 0%. Importing the module exercises the import
    statement; the ``if __name__ == "__main__"`` line cannot be reached
    without a subprocess (and that path is already smoke-tested via
    ``test_python_module_entrypoint_renders_help`` in test_cli_kernel.py).
    """

    def test_main_module_imports_cleanly(self) -> None:
        import importlib

        module = importlib.import_module("mythic_vibe_cli.__main__")
        self.assertTrue(hasattr(module, "main"))


if __name__ == "__main__":
    unittest.main()
