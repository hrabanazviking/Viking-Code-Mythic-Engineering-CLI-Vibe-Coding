"""Tests for the Textual TUI surface.

Two layers:

1. Pure-data tests on ``build_status_data(root)`` — no Textual needed.
2. Headless TUI tests via ``App.run_test()`` — Textual's built-in async test driver.

The Textual tests are skipped if Textual is not installed, but in this project
Textual is in the ``dev`` extras so those tests should always run in CI.
"""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path


textual_unavailable = False
try:
    import textual  # noqa: F401
except ImportError:
    textual_unavailable = True

from mythic_vibe_cli.tui.app import build_status_data  # noqa: E402


class StatusDataTests(unittest.TestCase):
    def test_empty_project_returns_safe_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = build_status_data(Path(tmp))

        # ProjectState default current_phase is "intent" — the TUI displays it as-is.
        self.assertEqual(data.phase, "intent")
        self.assertEqual(data.active_task_id, "(none)")
        self.assertEqual(data.last_verification_id, "(none)")
        self.assertEqual(data.latest_handoff_id, "(none)")
        self.assertEqual(data.plugins_enabled, 0)
        self.assertEqual(data.plugins_disabled, 0)
        self.assertTrue(data.refreshed_at)

    def test_status_data_to_dict_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = build_status_data(Path(tmp))
            payload = data.to_dict()

        for key in {
            "path",
            "phase",
            "active_task_id",
            "last_verification_id",
            "last_verification_result",
            "last_verification_level",
            "latest_handoff_id",
            "latest_handoff_created_at",
            "latest_handoff_next_step",
            "plugins_enabled",
            "plugins_disabled",
            "refreshed_at",
        }:
            self.assertIn(key, payload)

    def test_status_data_resolves_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            data = build_status_data(tmp_path)
        self.assertEqual(data.path, str(tmp_path))


@unittest.skipIf(textual_unavailable, "textual not installed")
class TuiEventsPanelTests(unittest.TestCase):
    def test_recent_events_panel_renders_logged_entries(self) -> None:
        from mythic_vibe_cli.runtime.event_log import append_event, event_log_path_for
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                root_path = Path(tmp)
                log_path = event_log_path_for(root_path)
                append_event(log_path, "before_scan", {"path": str(root_path)})
                append_event(log_path, "after_scan", {"path": str(root_path)})

                app = MythicTuiApp(root_path)
                async with app.run_test() as pilot:
                    await pilot.pause()
                    panel = app.screen.query_one("#events-panel")
                    return str(panel.render())

        rendered = asyncio.run(run_test())
        self.assertIn("before_scan", rendered)
        self.assertIn("after_scan", rendered)

    def test_recent_events_panel_shows_placeholder_when_empty(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    panel = app.screen.query_one("#events-panel")
                    return str(panel.render())

        rendered = asyncio.run(run_test())
        self.assertIn("no events recorded", rendered)


@unittest.skipIf(textual_unavailable, "textual not installed")
class TuiHeadlessTests(unittest.TestCase):
    def test_status_screen_renders_panels_in_headless_mode(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> tuple[bool, str, str]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    status_widget = app.screen.query_one("#panel-status")
                    verify_widget = app.screen.query_one("#panel-verify")
                    handoff_widget = app.screen.query_one("#panel-handoff")
                    plugins_widget = app.screen.query_one("#panel-plugins")
                    footer_widget = app.screen.query_one("#footer-line")
                    rendered_status = str(status_widget.render())
                    rendered_handoff = str(handoff_widget.render())
                    rendered_footer = str(footer_widget.render())
                    rendered_verify = str(verify_widget.render())
                    rendered_plugins = str(plugins_widget.render())
                    return (
                        all(["Path:" in rendered_status, "Phase:" in rendered_status]),
                        rendered_handoff,
                        rendered_footer + rendered_verify + rendered_plugins,
                    )

        all_panels_present, rendered_handoff, rest = asyncio.run(run_test())
        self.assertTrue(all_panels_present)
        self.assertIn("ID:", rendered_handoff)
        self.assertIn("Last refresh:", rest)

    def test_quit_binding_does_not_raise(self) -> None:
        """Pressing 'q' should trigger the quit action without raising. Textual's
        run_test context exits cleanly when the app exits via the binding."""
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    await pilot.press("q")
                    await pilot.pause()

        # Should complete without raising.
        asyncio.run(run_test())


@unittest.skipIf(textual_unavailable, "textual not installed")
class SlashPickerTests(unittest.TestCase):
    def test_gather_picker_entries_includes_builtins(self) -> None:
        from mythic_vibe_cli.tui.picker import gather_picker_entries

        with tempfile.TemporaryDirectory() as tmp:
            entries = gather_picker_entries(Path(tmp))
        names = {entry.name for entry in entries}
        for required in {"help", "status", "scan", "verify", "quit"}:
            self.assertIn(required, names)

    def test_filter_entries_substring_matches_name_or_description(self) -> None:
        from mythic_vibe_cli.tui.picker import PickerEntry, filter_entries

        entries = [
            PickerEntry(name="scan", description="Run a project context scan", source="builtin"),
            PickerEntry(name="status", description="Show project state", source="builtin"),
            PickerEntry(name="verify", description="Run verification checks", source="builtin"),
        ]
        # Match by name
        scan_only = filter_entries(entries, "scan")
        self.assertEqual([e.name for e in scan_only], ["scan"])
        # Match by description (case-insensitive)
        check_match = filter_entries(entries, "CHECKS")
        self.assertEqual([e.name for e in check_match], ["verify"])
        # Empty query returns all
        all_entries = filter_entries(entries, "")
        self.assertEqual(len(all_entries), 3)

    def test_picker_renders_options_and_filters_on_input(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> tuple[int, int]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    await pilot.press("slash")
                    await pilot.pause()
                    picker = app.screen
                    option_list = picker.query_one("#picker-list")
                    initial_count = option_list.option_count
                    search = picker.query_one("#picker-search")
                    search.value = "scan"
                    await pilot.pause()
                    filtered_count = option_list.option_count
                    return initial_count, filtered_count

        initial, filtered = asyncio.run(run_test())
        self.assertGreater(initial, 5)
        self.assertGreaterEqual(filtered, 1)
        self.assertLess(filtered, initial)

    def test_picker_escape_pops_back_to_status_screen(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp, StatusScreen

        async def run_test() -> bool:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    await pilot.press("slash")
                    await pilot.pause()
                    picker_active = type(app.screen).__name__ == "SlashPickerScreen"
                    await pilot.press("escape")
                    await pilot.pause()
                    back_to_status = isinstance(app.screen, StatusScreen)
                    return picker_active and back_to_status

        self.assertTrue(asyncio.run(run_test()))

    def test_command_preview_shows_selected_entry_metadata(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.picker import CommandPreviewScreen, PickerEntry

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    entry = PickerEntry(
                        name="audit",
                        description="Append audit log",
                        source="plugin",
                        source_info_path="audit_plugin:Plugin",
                    )
                    app.push_screen(CommandPreviewScreen(entry))
                    await pilot.pause()
                    card = app.screen.query_one("#preview-card")
                    return str(card.render())

        rendered = asyncio.run(run_test())
        self.assertIn("plugin", rendered)
        self.assertIn("audit_plugin:Plugin", rendered)
        self.assertIn("Append audit log", rendered)


@unittest.skipIf(textual_unavailable, "textual not installed")
class RunningCommandScreenTests(unittest.TestCase):
    def test_command_for_builtin_uses_current_python(self) -> None:
        import sys as _sys
        from mythic_vibe_cli.tui.runner import command_for_builtin

        spec = command_for_builtin("status")
        self.assertEqual(spec.argv[0], _sys.executable)
        self.assertEqual(spec.argv[1:4], ["-m", "mythic_vibe_cli", "status"])
        self.assertEqual(spec.label, "/status")

    def test_command_for_builtin_appends_path_for_path_aware_commands(self) -> None:
        from mythic_vibe_cli.tui.runner import command_for_builtin

        with tempfile.TemporaryDirectory() as tmp:
            spec = command_for_builtin("status", project_root=Path(tmp))
            self.assertIn("--path", spec.argv)
            self.assertIn(str(Path(tmp)), spec.argv)

    def test_command_for_builtin_skips_path_for_help(self) -> None:
        from mythic_vibe_cli.tui.runner import command_for_builtin

        with tempfile.TemporaryDirectory() as tmp:
            spec = command_for_builtin("help", project_root=Path(tmp))
            self.assertNotIn("--path", spec.argv)

    def test_runner_screen_runs_to_completion_and_shows_exit_code(self) -> None:
        """Run a guaranteed-fast subprocess via RunSpec and assert the exit code
        eventually appears in the rendered card."""
        import sys as _sys
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.runner import RunningCommandScreen, RunSpec

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    spec = RunSpec(
                        label="/echo-test",
                        argv=[_sys.executable, "-c", "import sys; sys.exit(0)"],
                    )
                    app.push_screen(RunningCommandScreen(spec, cwd=Path(tmp)))
                    # Allow the subprocess to start and finish + at least one tick.
                    for _ in range(20):
                        await pilot.pause()
                    card = app.screen.query_one("#runner-card")
                    return str(card.render())

        rendered = asyncio.run(run_test())
        self.assertIn("Exit code:", rendered)
        self.assertIn("0", rendered)

    def test_runner_screen_captures_non_zero_exit(self) -> None:
        import sys as _sys
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.runner import RunningCommandScreen, RunSpec

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    spec = RunSpec(
                        label="/fail-test",
                        argv=[_sys.executable, "-c", "import sys; sys.exit(3)"],
                    )
                    app.push_screen(RunningCommandScreen(spec, cwd=Path(tmp)))
                    for _ in range(20):
                        await pilot.pause()
                    return str(app.screen.query_one("#runner-card").render())

        rendered = asyncio.run(run_test())
        self.assertIn("Exit code:", rendered)
        self.assertIn("3", rendered)

    def test_preview_screen_runs_builtin_via_r_binding(self) -> None:
        """Press r on the preview screen for a builtin → RunningCommandScreen
        is pushed and runs to completion."""
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.picker import CommandPreviewScreen, PickerEntry
        from mythic_vibe_cli.tui.runner import RunningCommandScreen

        async def run_test() -> bool:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    entry = PickerEntry(name="status", description="Show project state", source="builtin")
                    app.push_screen(CommandPreviewScreen(entry, project_root=Path(tmp)))
                    await pilot.pause()
                    # Override sys.executable in argv? Just press r and verify
                    # screen transition. We don't care about the specific exit
                    # code here — only that the runner screen is reached.
                    await pilot.press("r")
                    await pilot.pause()
                    return isinstance(app.screen, RunningCommandScreen)

        # Cannot redirect sys.executable for the subprocess invocation, so we
        # depend on `mythic-vibe status` being importable from the running
        # interpreter (it is — we're testing in this very project).
        self.assertTrue(asyncio.run(run_test()))

    def test_preview_screen_does_not_run_non_builtin_entry(self) -> None:
        """Press r on a plugin-source entry → no transition; preview stays."""
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.picker import CommandPreviewScreen, PickerEntry

        async def run_test() -> bool:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    entry = PickerEntry(
                        name="audit",
                        description="Plugin audit cmd",
                        source="plugin",
                        source_info_path="audit_plugin:Plugin",
                    )
                    app.push_screen(CommandPreviewScreen(entry, project_root=Path(tmp)))
                    await pilot.pause()
                    await pilot.press("r")
                    await pilot.pause()
                    return isinstance(app.screen, CommandPreviewScreen)

        self.assertTrue(asyncio.run(run_test()))


class CmdTuiFallbackTests(unittest.TestCase):
    def test_missing_textual_returns_operational_failure_with_helpful_error(self) -> None:
        """If textual cannot be imported, cmd_tui surfaces a helpful error and
        returns OPERATIONAL_FAILURE rather than raising."""
        import contextlib
        import io as _io
        import sys as _sys

        from mythic_vibe_cli.commands import cmd_tui
        from mythic_vibe_cli.exit_codes import OPERATIONAL_FAILURE

        class _Args:
            path = "."

        # Force the import to fail by stashing-out the tui module from sys.modules
        # and inserting a sentinel that raises ImportError on attribute access.
        saved = {
            name: _sys.modules[name]
            for name in list(_sys.modules)
            if name == "mythic_vibe_cli.tui" or name.startswith("mythic_vibe_cli.tui.")
        }
        for name in list(saved):
            del _sys.modules[name]
        # Insert a broken sentinel so `from .tui.app import run_tui` raises ImportError.
        broken = type(_sys)("mythic_vibe_cli.tui")
        broken.__path__ = []  # type: ignore[attr-defined]
        _sys.modules["mythic_vibe_cli.tui"] = broken

        stderr_buf = _io.StringIO()
        try:
            with contextlib.redirect_stderr(stderr_buf):
                code = cmd_tui(_Args())  # type: ignore[arg-type]
        finally:
            for name in list(_sys.modules):
                if name == "mythic_vibe_cli.tui" or name.startswith("mythic_vibe_cli.tui."):
                    del _sys.modules[name]
            _sys.modules.update(saved)

        self.assertEqual(code, OPERATIONAL_FAILURE)
        self.assertIn("Textual is not installed", stderr_buf.getvalue())


if __name__ == "__main__":
    unittest.main()
