"""PH-02 slice 2.8 — parity tests across CLI, REPL, and TUI surfaces.

Locks in the invariant that every slash entry — builtin or
plugin-contributed — appears and resolves identically across:

- the CLI (``mythic-vibe slash list``, ``mythic-vibe slash inspect``)
- the shell REPL (``/help`` catalog and ``/help <name>`` routing)
- the Textual TUI picker (``gather_picker_entries``)
- the argparse subparser tree (for entries that have one)

This slice is test-only. No production code is changed.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mythic_vibe_cli import app
from mythic_vibe_cli.commands import COMMAND_HANDLERS, SLASH_LOCALS_WITHOUT_ARGPARSE
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.runtime.slash_commands import BUILTIN_SLASH_COMMANDS
from mythic_vibe_cli.tui.picker import gather_picker_entries


def _builtin_names() -> set[str]:
    return {entry.name for entry in BUILTIN_SLASH_COMMANDS}


class CatalogSurfaceParityTests(unittest.TestCase):
    """The catalog must surface identically through every consumer."""

    def test_cli_slash_list_matches_BUILTIN_SLASH_COMMANDS(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["slash", "list", "--source", "builtin", "--json", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            cli_names = {entry["name"] for entry in payload["builtin"]}
            self.assertEqual(cli_names, _builtin_names())

    def test_tui_picker_gathers_every_builtin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            entries = gather_picker_entries(Path(tmp))
            picker_builtin_names = {e.name for e in entries if e.source == "builtin"}
            self.assertEqual(picker_builtin_names, _builtin_names())

    def test_repl_help_lists_every_builtin_inline(self) -> None:
        from mythic_vibe_cli.repl import run_shell

        with tempfile.TemporaryDirectory() as tmp:
            stdin = io.StringIO("/help\n/quit\n")
            stdout = io.StringIO()
            run_shell(
                stdin=stdin,
                stdout=stdout,
                stderr=io.StringIO(),
                main=lambda argv: SUCCESS,
                project_root=Path(tmp),
            )
            text = stdout.getvalue()
            for name in _builtin_names():
                self.assertIn(f"/{name}", text, msg=f"REPL /help missing /{name}")

    def test_inspect_succeeds_for_every_catalog_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for name in sorted(_builtin_names()):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    code = app.main(["slash", "inspect", name, "--json", "--path", tmp])
                self.assertEqual(
                    code, SUCCESS, msg=f"slash inspect {name} returned {code}"
                )
                payload = json.loads(stdout.getvalue())
                self.assertTrue(payload["ok"], msg=f"slash inspect {name} not ok")
                self.assertEqual(payload["name"], name)
                self.assertEqual(payload["source"], "builtin")

    def test_every_non_local_catalog_entry_has_argparse_subparser(self) -> None:
        """Catalog entries that aren't interactive locals must have an
        argparse handler. This is the core slice-2.1 parity claim,
        re-asserted at the introspection level."""
        names = _builtin_names()
        argparse_handlers = set(COMMAND_HANDLERS.keys())
        for name in names - SLASH_LOCALS_WITHOUT_ARGPARSE:
            self.assertIn(
                name,
                argparse_handlers,
                msg=f"catalog entry {name} has no argparse handler",
            )

    def test_interactive_locals_have_no_argparse_subparser(self) -> None:
        """The three interactive-local entries must NOT also exist as
        argparse subcommands — they belong to the REPL/TUI surface
        only."""
        argparse_handlers = set(COMMAND_HANDLERS.keys())
        for name in SLASH_LOCALS_WITHOUT_ARGPARSE:
            self.assertNotIn(
                name,
                argparse_handlers,
                msg=f"interactive-local {name} unexpectedly registered as an argparse handler",
            )


class CatalogConsistencyAcrossSurfacesTests(unittest.TestCase):
    """The same catalog must be visible from every consumer at the same
    time — not just structurally identical sets, but identical dataclass
    payloads."""

    def test_cli_slash_list_descriptions_equal_BUILTIN_descriptions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["slash", "list", "--source", "builtin", "--json", "--path", tmp])
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            cli_by_name = {entry["name"]: entry["description"] for entry in payload["builtin"]}
            for entry in BUILTIN_SLASH_COMMANDS:
                self.assertEqual(
                    cli_by_name.get(entry.name),
                    entry.description,
                    msg=f"description drift for /{entry.name}",
                )

    def test_tui_picker_descriptions_equal_BUILTIN_descriptions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            picker_by_name = {
                e.name: e.description
                for e in gather_picker_entries(Path(tmp))
                if e.source == "builtin"
            }
            for entry in BUILTIN_SLASH_COMMANDS:
                self.assertEqual(
                    picker_by_name.get(entry.name),
                    entry.description,
                    msg=f"picker description drift for /{entry.name}",
                )


class PluginContributedParityTests(unittest.TestCase):
    """A plugin-contributed slash entry must surface identically across
    CLI, REPL inline help, and the TUI picker (it doesn't have an
    argparse subparser — that's the dispatch contract slice 2.6 will
    add)."""

    def _setup_plugin(self, project_root: Path, package_name: str) -> None:
        plugin_dir = project_root / f"_synthetic_{package_name}"
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
                                name="parity-probe",
                                source="plugin",
                                source_info=synthetic_source_info(
                                    "parity_probe:Plugin",
                                    source="parity_probe",
                                    scope="project",
                                    origin="top-level",
                                ),
                                description="Synthetic parity probe",
                            ),
                        ]
                """
            ),
            encoding="utf-8",
        )
        from mythic_vibe_cli.plugins import PluginRegistry

        registry = PluginRegistry(project_root)
        registry.add(f"_synthetic_{package_name}.{package_name}:Plugin", hooks=[])
        sys.path.insert(0, str(project_root))

    def _teardown_plugin(self, project_root: Path, package_name: str) -> None:
        path_str = str(project_root)
        if path_str in sys.path:
            sys.path.remove(path_str)
        sys.modules.pop(package_name, None)

    def test_plugin_slash_appears_in_every_surface(self) -> None:
        with tempfile.TemporaryDirectory() as project_root:
            project_path = Path(project_root)
            self._setup_plugin(project_path, "parity_probe")
            try:
                # CLI surface
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    code = app.main(["slash", "list", "--json", "--path", str(project_path)])
                self.assertEqual(code, SUCCESS)
                payload = json.loads(stdout.getvalue())
                cli_names = {item["name"] for item in payload["contributed"]}
                self.assertIn("parity-probe", cli_names)

                # TUI picker surface
                picker_names = {e.name for e in gather_picker_entries(project_path)}
                self.assertIn("parity-probe", picker_names)

                # REPL inline help surface
                from mythic_vibe_cli.repl import run_shell

                stdin = io.StringIO("/help\n/quit\n")
                repl_out = io.StringIO()
                run_shell(
                    stdin=stdin,
                    stdout=repl_out,
                    stderr=io.StringIO(),
                    main=lambda argv: SUCCESS,
                    project_root=project_path,
                )
                self.assertIn("/parity-probe", repl_out.getvalue())

                # Inspect surface
                inspect_out = io.StringIO()
                with redirect_stdout(inspect_out):
                    code = app.main(
                        ["slash", "inspect", "parity-probe", "--json", "--path", str(project_path)]
                    )
                self.assertEqual(code, SUCCESS)
                inspect_payload = json.loads(inspect_out.getvalue())
                self.assertTrue(inspect_payload["ok"])
                self.assertEqual(inspect_payload["source"], "plugin")
                self.assertIsNone(inspect_payload["argparse_help"])
            finally:
                self._teardown_plugin(project_path, "parity_probe")


class HelpSurfaceParityTests(unittest.TestCase):
    """The REPL's /help <name> path must produce the same content the
    user would see at the CLI."""

    def test_repl_help_with_name_invokes_slash_inspect_with_path(self) -> None:
        from mythic_vibe_cli.repl import run_shell

        captured: list[list[str]] = []

        def fake_main(argv: list[str]) -> int:
            captured.append(list(argv))
            return SUCCESS

        with tempfile.TemporaryDirectory() as tmp:
            stdin = io.StringIO("/help status\n/quit\n")
            run_shell(
                stdin=stdin,
                stdout=io.StringIO(),
                stderr=io.StringIO(),
                main=fake_main,
                project_root=Path(tmp),
            )

        self.assertEqual(len(captured), 1)
        argv = captured[0]
        self.assertEqual(argv[0], "slash")
        self.assertEqual(argv[1], "inspect")
        self.assertIn("--path", argv)
        # Final positional is the name being inspected.
        self.assertEqual(argv[-1], "status")

    def test_unknown_name_at_cli_and_repl_both_return_user_input_error(self) -> None:
        # CLI path
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(["slash", "inspect", "totally-bogus", "--json", "--path", tmp])
            self.assertEqual(code, USER_INPUT_ERROR)

        # REPL path: /help totally-bogus should call main(["slash", "inspect", ..., "totally-bogus"])
        # which in turn returns USER_INPUT_ERROR. The REPL surfaces the code but stays alive.
        from mythic_vibe_cli.repl import run_shell

        captured_codes: list[int] = []

        def fake_main_returning_user_error(argv: list[str]) -> int:
            captured_codes.append(USER_INPUT_ERROR)
            return USER_INPUT_ERROR

        with tempfile.TemporaryDirectory() as tmp:
            stdin = io.StringIO("/help totally-bogus\n/quit\n")
            stderr = io.StringIO()
            run_shell(
                stdin=stdin,
                stdout=io.StringIO(),
                stderr=stderr,
                main=fake_main_returning_user_error,
                project_root=Path(tmp),
            )

        self.assertEqual(captured_codes, [USER_INPUT_ERROR])
        self.assertIn("slash inspect exit code", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
