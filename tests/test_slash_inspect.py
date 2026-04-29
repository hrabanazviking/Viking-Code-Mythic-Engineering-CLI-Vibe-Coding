"""Tests for PH-02 slice 2.7 — slash help & introspection.

Covers:
- ``mythic-vibe slash inspect <name>`` for builtin entries with argparse subparsers
- ``mythic-vibe slash inspect <name>`` for interactive-local entries (help/reload/quit)
- ``mythic-vibe slash inspect <unknown>`` returns USER_INPUT_ERROR with a helpful message
- ``mythic-vibe slash inspect /verify`` accepts a leading slash
- JSON output payload shape
- Plugin-contributed slash entries resolve via the dispatcher contract
- REPL ``/help <name>`` routes to slash inspect under the hood
"""

from __future__ import annotations

import io
import json
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from mythic_vibe_cli import app
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR


class SlashInspectBuiltinTests(unittest.TestCase):
    def test_inspect_builtin_with_argparse_subparser(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["slash", "inspect", "verify", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            output = stdout.getvalue()
            self.assertIn("/verify", output)
            self.assertIn("Source: builtin", output)
            self.assertIn("Argparse help:", output)
            # The verify parser advertises --record in its help text.
            self.assertIn("--record", output)

    def test_inspect_accepts_leading_slash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["slash", "inspect", "/status", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            self.assertIn("/status", stdout.getvalue())

    def test_inspect_interactive_local_marks_no_argparse(self) -> None:
        """help / reload / quit live in the catalog only — no argparse subparser."""
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["slash", "inspect", "quit", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            output = stdout.getvalue()
            self.assertIn("/quit", output)
            self.assertIn("interactive-local", output)

    def test_inspect_intent_phase_capture_command(self) -> None:
        """slice-2.3 phase commands have a parent + capture subcommand;
        inspect should render the parent's help (which lists `capture`)."""
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["slash", "inspect", "intent", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            output = stdout.getvalue()
            self.assertIn("/intent", output)
            self.assertIn("capture", output)

    def test_inspect_unknown_returns_user_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = app.main(["slash", "inspect", "no-such-command", "--path", tmp])
            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("No slash command named 'no-such-command'", stderr.getvalue())

    def test_inspect_unknown_json_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["slash", "inspect", "no-such-command", "--json", "--path", tmp])
            self.assertEqual(code, USER_INPUT_ERROR)
            payload = json.loads(stdout.getvalue())
            self.assertFalse(payload["ok"])
            self.assertIn("errors", payload)


class SlashInspectJsonShapeTests(unittest.TestCase):
    def test_json_payload_for_builtin_with_argparse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["slash", "inspect", "scan", "--json", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["name"], "scan")
            self.assertEqual(payload["source"], "builtin")
            self.assertFalse(payload["interactive_local"])
            self.assertIn("entry", payload)
            self.assertEqual(payload["entry"]["name"], "scan")
            self.assertIsInstance(payload["argparse_help"], str)
            self.assertIn("scan", payload["argparse_help"])

    def test_json_payload_for_interactive_local_marks_no_argparse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["slash", "inspect", "reload", "--json", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["name"], "reload")
            self.assertTrue(payload["interactive_local"])
            self.assertIsNone(payload["argparse_help"])


class SlashInspectPluginContributedTests(unittest.TestCase):
    """Plugin-contributed entries resolve through the dispatcher.

    Reuses the synthetic-plugin fixture pattern from test_cli_kernel.
    """

    def _setup_synthetic_plugin(self, project_path: Path, package_name: str) -> None:
        plugin_dir = project_path / f"_synthetic_{package_name}"
        plugin_dir.mkdir()
        (plugin_dir / f"{package_name}.py").write_text(
            textwrap.dedent(
                """
                class Plugin:
                    @staticmethod
                    def slash_commands():
                        from mythic_vibe_cli.runtime.slash_commands import SlashCommandInfo
                        from mythic_vibe_cli.runtime.source_info import synthetic_source_info
                        return [
                            SlashCommandInfo(
                                name="audit-probe",
                                source="plugin",
                                source_info=synthetic_source_info(
                                    "audit_plugin:Plugin",
                                    source="audit_plugin",
                                    scope="project",
                                    origin="top-level",
                                ),
                                description="Append-only audit log",
                            ),
                        ]
                """
            ),
            encoding="utf-8",
        )

        from mythic_vibe_cli.plugins import PluginRegistry

        registry = PluginRegistry(project_path)
        registry.add(f"_synthetic_{package_name}.{package_name}:Plugin", hooks=[])

        import sys

        sys.path.insert(0, str(project_path))

    def _teardown_synthetic_plugin(self, project_path: Path, package_name: str) -> None:
        import sys

        path_str = str(project_path)
        if path_str in sys.path:
            sys.path.remove(path_str)
        sys.modules.pop(package_name, None)

    def test_inspect_plugin_contributed_entry(self) -> None:
        with tempfile.TemporaryDirectory() as project_root:
            project_path = Path(project_root)
            self._setup_synthetic_plugin(project_path, "inspect_audit_probe")
            try:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    code = app.main(
                        ["slash", "inspect", "audit-probe", "--json", "--path", str(project_path)]
                    )
                payload = json.loads(stdout.getvalue())
            finally:
                self._teardown_synthetic_plugin(project_path, "inspect_audit_probe")

            self.assertEqual(code, SUCCESS)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["name"], "audit-probe")
            self.assertEqual(payload["source"], "plugin")
            self.assertFalse(payload["interactive_local"])
            self.assertIsNone(payload["argparse_help"])
            self.assertIn("source_info", payload["entry"])
            self.assertEqual(payload["entry"]["source_info"]["scope"], "project")


class SlashInspectMissingNameTests(unittest.TestCase):
    def test_no_name_argparse_blocks(self) -> None:
        # argparse marks `name` as required positional, so missing arg
        # short-circuits before our handler runs.
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as cm, redirect_stderr(io.StringIO()):
                app.main(["slash", "inspect", "--path", tmp])
            self.assertEqual(cm.exception.code, 2)


class ReplHelpRoutingTests(unittest.TestCase):
    """The REPL's /help command, when given an argument, should route
    to `slash inspect <name>` so introspection comes from a single
    source of truth."""

    def test_repl_help_with_name_routes_to_slash_inspect(self) -> None:
        from mythic_vibe_cli.repl import run_shell

        captured: list[list[str]] = []

        def fake_main(argv: list[str]) -> int:
            captured.append(list(argv))
            return SUCCESS

        with tempfile.TemporaryDirectory() as tmp:
            stdin = io.StringIO("/help status\n/quit\n")
            stdout = io.StringIO()
            stderr = io.StringIO()
            run_shell(
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                main=fake_main,
                project_root=Path(tmp),
            )

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][:3], ["slash", "inspect", "--path"])
        self.assertEqual(captured[0][-1], "status")

    def test_repl_help_with_slash_prefixed_name_strips_slash(self) -> None:
        from mythic_vibe_cli.repl import run_shell

        captured: list[list[str]] = []

        def fake_main(argv: list[str]) -> int:
            captured.append(list(argv))
            return SUCCESS

        with tempfile.TemporaryDirectory() as tmp:
            stdin = io.StringIO("/help /verify\n/quit\n")
            stdout = io.StringIO()
            stderr = io.StringIO()
            run_shell(
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                main=fake_main,
                project_root=Path(tmp),
            )

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][-1], "verify")

    def test_repl_help_without_name_still_lists_catalog(self) -> None:
        from mythic_vibe_cli.repl import run_shell

        captured: list[list[str]] = []

        def fake_main(argv: list[str]) -> int:
            captured.append(list(argv))
            return SUCCESS

        with tempfile.TemporaryDirectory() as tmp:
            stdin = io.StringIO("/help\n/quit\n")
            stdout = io.StringIO()
            stderr = io.StringIO()
            run_shell(
                stdin=stdin,
                stdout=stdout,
                stderr=stderr,
                main=fake_main,
                project_root=Path(tmp),
            )

        # /help (no arg) should NOT call main; it prints inline.
        self.assertEqual(captured, [])
        self.assertIn("Builtin slash commands", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
