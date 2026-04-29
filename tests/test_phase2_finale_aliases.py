"""Tests for PH-02 slices 2.4 (`/provider`) and 2.5 (`/audit`).

Both slices add a single top-level argparse subcommand that
delegates to an existing handler, plus a matching entry in the
slash catalog. The tests assert:

- The subcommand parses cleanly.
- It routes through `COMMAND_HANDLERS` to the expected handler
  (no silent fall-through to dispatch errors).
- The slash catalog now includes the new entry.
- The TUI runner's path-aware allow-list includes the new command
  (so the TUI invocation forwards `--path`).

Slice 2.6's plugin-slash argv contract has its own test module.
"""

from __future__ import annotations

import argparse
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


from mythic_vibe_cli.app import build_parser  # noqa: E402
from mythic_vibe_cli.commands import COMMAND_HANDLERS  # noqa: E402
from mythic_vibe_cli.runtime.slash_commands import BUILTIN_SLASH_COMMANDS  # noqa: E402


# ---- Slice 2.4: /provider ---------------------------------------------


class ProviderAliasTests(unittest.TestCase):
    def test_argparse_accepts_provider_subcommand(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["provider"])
        self.assertEqual(ns.command, "provider")
        self.assertEqual(ns.path, ".")

    def test_argparse_accepts_provider_with_path_and_json(self) -> None:
        parser = build_parser()
        with tempfile.TemporaryDirectory() as tmp:
            ns = parser.parse_args(["provider", "--path", tmp, "--json"])
        self.assertEqual(ns.command, "provider")
        self.assertTrue(ns.json)

    def test_provider_handler_is_registered(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_providers, cmd_provider

        self.assertIs(COMMAND_HANDLERS["provider"], cmd_provider)
        # And the wrapper delegates to cmd_ai_providers — confirmed by
        # running it through a mock and observing the delegation.
        with mock.patch(
            "mythic_vibe_cli.commands.cmd_ai_providers", return_value=0
        ) as mocked:
            args = argparse.Namespace(path=".", json=False)
            self.assertEqual(cmd_provider(args), 0)
            mocked.assert_called_once_with(args)

    def test_slash_catalog_contains_provider(self) -> None:
        names = {entry.name for entry in BUILTIN_SLASH_COMMANDS}
        self.assertIn("provider", names)

    def test_provider_command_runs_end_to_end(self) -> None:
        from mythic_vibe_cli.commands import cmd_provider

        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(path=tmp, json=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_provider(args)

        self.assertEqual(exit_code, 0)
        # JSON output must mention at least the always-available provider.
        self.assertIn("copy-paste", buf.getvalue())


# ---- Slice 2.5: /audit ------------------------------------------------


class AuditAliasTests(unittest.TestCase):
    def test_argparse_accepts_audit_subcommand(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["audit"])
        self.assertEqual(ns.command, "audit")
        self.assertEqual(ns.path, ".")

    def test_argparse_accepts_audit_with_path(self) -> None:
        parser = build_parser()
        with tempfile.TemporaryDirectory() as tmp:
            ns = parser.parse_args(["audit", "--path", tmp])
        self.assertEqual(ns.command, "audit")

    def test_audit_handler_is_registered(self) -> None:
        from mythic_vibe_cli.commands import cmd_audit, cmd_doctor

        self.assertIs(COMMAND_HANDLERS["audit"], cmd_audit)
        # cmd_audit forces json=True before delegating to cmd_doctor.
        with mock.patch(
            "mythic_vibe_cli.commands.cmd_doctor", return_value=0
        ) as mocked:
            args = argparse.Namespace(path=".")
            cmd_audit(args)
            self.assertTrue(getattr(args, "json", False))
            mocked.assert_called_once()

    def test_slash_catalog_contains_audit(self) -> None:
        names = {entry.name for entry in BUILTIN_SLASH_COMMANDS}
        self.assertIn("audit", names)

    def test_audit_command_emits_json_on_a_fresh_project(self) -> None:
        from mythic_vibe_cli.commands import cmd_audit

        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(path=tmp)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                # cmd_doctor exits non-zero on a non-Mythic dir; the alias
                # itself must not raise and must produce JSON regardless.
                cmd_audit(args)

        # The JSON envelope's diagnostic shape is enough — even on a
        # bare temp dir, doctor emits a structured "errors" list.
        rendered = stdout.getvalue()
        self.assertIn("errors", rendered)
        self.assertIn("\"ok\":", rendered)


# ---- TUI runner allow-list ---------------------------------------------


class TuiRunnerForwardsPathForNewAliases(unittest.TestCase):
    """Slice 2.4 / 2.5 added two path-aware commands; the TUI's
    `command_for_builtin` allow-list has to include them or the
    operator's project path silently drops on launch."""

    def test_provider_invocation_forwards_path(self) -> None:
        from mythic_vibe_cli.tui.runner import command_for_builtin

        with tempfile.TemporaryDirectory() as tmp:
            spec = command_for_builtin("provider", project_root=Path(tmp))
        self.assertIn("--path", spec.argv)
        self.assertIn(str(Path(tmp)), spec.argv)
        self.assertEqual(spec.label, "/provider")

    def test_audit_invocation_forwards_path(self) -> None:
        from mythic_vibe_cli.tui.runner import command_for_builtin

        with tempfile.TemporaryDirectory() as tmp:
            spec = command_for_builtin("audit", project_root=Path(tmp))
        self.assertIn("--path", spec.argv)
        self.assertIn(str(Path(tmp)), spec.argv)
        self.assertEqual(spec.label, "/audit")


if __name__ == "__main__":
    unittest.main()
