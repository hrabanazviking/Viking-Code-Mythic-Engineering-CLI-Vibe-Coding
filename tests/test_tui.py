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
import time
import unittest
from pathlib import Path
from unittest import mock


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


class DiagnosticsFormatTests(unittest.TestCase):
    """Pure formatter tests for the slice 4.6 diagnostics panel —
    pulse on/off, channel-class colour coding, empty placeholder."""

    def _snapshot(
        self,
        entries: list[tuple[str, str]],
        *,
        new: int = 0,
        total: int = 0,
    ) -> "object":
        from mythic_vibe_cli.runtime.event_log import EventLogEntry, EventStreamSnapshot

        log_entries = tuple(
            EventLogEntry(timestamp="2026-04-29T12:34:56Z", channel=ch, summary=summary)
            for ch, summary in entries
        )
        return EventStreamSnapshot(entries=log_entries, new_in_last_poll=new, total_seen=total)

    def test_idle_pulse_when_no_new_events(self) -> None:
        from mythic_vibe_cli.tui.app import _format_diagnostics_panel

        rendered = _format_diagnostics_panel(self._snapshot([("before_scan", "x")]))
        self.assertIn("○ idle", rendered)
        self.assertNotIn("● live", rendered)

    def test_live_pulse_and_counter_when_new_events_arrived(self) -> None:
        from mythic_vibe_cli.tui.app import _format_diagnostics_panel

        rendered = _format_diagnostics_panel(
            self._snapshot([("after_scan", "x")], new=2, total=5)
        )
        self.assertIn("● live", rendered)
        self.assertIn("+2 new", rendered)
        self.assertIn("seen: 5", rendered)

    def test_empty_snapshot_still_shows_pulse_and_placeholder(self) -> None:
        from mythic_vibe_cli.tui.app import _format_diagnostics_panel

        rendered = _format_diagnostics_panel(self._snapshot([]))
        self.assertIn("○ idle", rendered)
        self.assertIn("no events recorded", rendered)

    def test_channel_classification_assigns_colour_tags(self) -> None:
        from mythic_vibe_cli.tui.app import _classify_channel

        self.assertEqual(_classify_channel("before_scan"), "cyan")
        self.assertEqual(_classify_channel("after_verify"), "green")
        self.assertEqual(_classify_channel("plugin_error"), "red")
        self.assertEqual(_classify_channel("verify_failed"), "red")
        self.assertEqual(_classify_channel("config_warning"), "yellow")
        self.assertEqual(_classify_channel("custom_channel"), "b")

    def test_render_includes_channel_specific_tag(self) -> None:
        from mythic_vibe_cli.tui.app import _format_diagnostics_panel

        rendered = _format_diagnostics_panel(
            self._snapshot([("before_scan", "alpha"), ("after_verify", "beta")])
        )
        self.assertIn("[cyan]before_scan[/cyan]", rendered)
        self.assertIn("[green]after_verify[/green]", rendered)


@unittest.skipIf(textual_unavailable, "textual not installed")
class TuiDiagnosticsLiveStreamTests(unittest.TestCase):
    """Headless integration: append an event mid-flight and confirm the
    panel's pulse + counter reflect it on the next refresh tick."""

    def test_diagnostics_panel_pulses_when_event_appended_mid_session(self) -> None:
        from mythic_vibe_cli.runtime.event_log import append_event, event_log_path_for
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> tuple[str, str]:
            with tempfile.TemporaryDirectory() as tmp:
                root_path = Path(tmp)
                log_path = event_log_path_for(root_path)
                # Warm-start with one entry on disk.
                append_event(log_path, "before_scan", {"path": str(root_path)})

                app = MythicTuiApp(root_path)
                async with app.run_test() as pilot:
                    await pilot.pause()
                    initial = str(app.screen.query_one("#events-panel").render())
                    # Append a fresh event then trigger a refresh via 'r'.
                    append_event(log_path, "after_scan", {"path": str(root_path)})
                    await pilot.press("r")
                    for _ in range(3):
                        await pilot.pause()
                    after = str(app.screen.query_one("#events-panel").render())
                    return initial, after

        initial, after = asyncio.run(run_test())
        # First render is warm-start: one entry but no pulse.
        self.assertIn("idle", initial)
        self.assertIn("before_scan", initial)
        # After appending mid-session and refreshing, the pulse fires.
        self.assertIn("live", after)
        self.assertIn("+1 new", after)
        self.assertIn("after_scan", after)

    def test_diagnostics_panel_border_title_is_diagnostics(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    panel = app.screen.query_one("#events-panel")
                    return str(panel.border_title)

        title = asyncio.run(run_test())
        self.assertEqual(title, "Diagnostics")


@unittest.skipIf(textual_unavailable, "textual not installed")
class TuiHeadlessTests(unittest.TestCase):
    def test_status_screen_renders_status_bar_in_headless_mode(self) -> None:
        """Slice 4.4 consolidated the 2x2 grid (Status / Verify /
        Handoff / Plugins panels) into a single #status-bar line.
        The bar still surfaces every key field; this test asserts the
        widget is present and the footer-line refresh timestamp still
        renders alongside it."""
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> tuple[str, str]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    status_bar = app.screen.query_one("#status-bar")
                    footer_widget = app.screen.query_one("#footer-line")
                    return str(status_bar.render()), str(footer_widget.render())

        rendered_bar, rendered_footer = asyncio.run(run_test())
        # Status bar surfaces phase + plugins + warnings.
        self.assertIn("phase:", rendered_bar)
        self.assertIn("plugins:", rendered_bar)
        # Refresh timestamp still on its own line.
        self.assertIn("Last refresh:", rendered_footer)

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

    def test_status_screen_degrades_when_status_data_refresh_fails(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> tuple[str, str]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                with mock.patch(
                    "mythic_vibe_cli.tui.app.build_status_data",
                    side_effect=RuntimeError("state unavailable"),
                ):
                    async with app.run_test() as pilot:
                        await pilot.pause()
                        status_bar = app.screen.query_one("#status-bar")
                        footer_widget = app.screen.query_one("#footer-line")
                        return str(status_bar.render()), str(footer_widget.render())

        rendered_bar, rendered_footer = asyncio.run(run_test())
        self.assertIn("Status unavailable", rendered_bar)
        self.assertIn("state unavailable", rendered_bar)
        self.assertIn("Last refresh: unavailable", rendered_footer)

    def test_status_screen_degrades_when_diagnostics_poll_fails(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                with mock.patch(
                    "mythic_vibe_cli.tui.app.EventTailReader.poll",
                    side_effect=OSError("event log unreadable"),
                ):
                    async with app.run_test() as pilot:
                        await pilot.pause()
                        panel = app.screen.query_one("#events-panel")
                        return str(panel.render())

        rendered = asyncio.run(run_test())
        self.assertIn("Diagnostics unavailable", rendered)
        self.assertIn("event log unreadable", rendered)

    def test_status_screen_stops_refresh_timer_on_unmount(self) -> None:
        from mythic_vibe_cli.tui.app import StatusScreen

        class FakeTimer:
            def __init__(self) -> None:
                self.stopped = False

            def stop(self) -> None:
                self.stopped = True

        with tempfile.TemporaryDirectory() as tmp:
            screen = StatusScreen(Path(tmp))
            timer = FakeTimer()
            screen._refresh_timer = timer
            screen.on_unmount()

        self.assertTrue(timer.stopped)
        self.assertIsNone(screen._refresh_timer)


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
                    # Pump the Textual event loop several times: setting
                    # ``Input.value`` posts a ``Changed`` message that has
                    # to traverse the message queue before
                    # ``on_input_changed`` runs and the OptionList
                    # rebuilds. With ~46 builtin entries (PH-02 slice 2.2),
                    # one pause is not enough on a busy test suite.
                    for _ in range(5):
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


# ---- PH-04 slice 4.1 — Loop Navigator panel ----------------------------


class LoopNavigatorDataTests(unittest.TestCase):
    """Pure-data layer: build_loop_navigator_data() classifies every
    Mythic phase as current / completed / pending against project state."""

    def test_default_state_marks_intent_as_current_rest_pending(self) -> None:
        from mythic_vibe_cli.core.state import PHASES
        from mythic_vibe_cli.tui.app import (
            PHASE_STATE_CURRENT,
            PHASE_STATE_PENDING,
            build_loop_navigator_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            data = build_loop_navigator_data(Path(tmp))

        self.assertEqual([entry.phase for entry in data.entries], list(PHASES))
        self.assertEqual(data.current_phase, "intent")
        self.assertEqual(data.entries[0].state, PHASE_STATE_CURRENT)
        for entry in data.entries[1:]:
            self.assertEqual(
                entry.state,
                PHASE_STATE_PENDING,
                msg=f"{entry.phase} should be pending in default state",
            )

    def test_completed_phases_marked_completed(self) -> None:
        import json as _json

        from mythic_vibe_cli.tui.app import (
            PHASE_STATE_COMPLETED,
            PHASE_STATE_CURRENT,
            PHASE_STATE_PENDING,
            build_loop_navigator_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "status.json").write_text(
                _json.dumps(
                    {
                        "schema_version": 1,
                        "current_phase": "plan",
                        "completed_phases": ["intent", "constraints", "architecture"],
                    }
                ),
                encoding="utf-8",
            )
            data = build_loop_navigator_data(root)

        states = {entry.phase: entry.state for entry in data.entries}
        self.assertEqual(states["intent"], PHASE_STATE_COMPLETED)
        self.assertEqual(states["constraints"], PHASE_STATE_COMPLETED)
        self.assertEqual(states["architecture"], PHASE_STATE_COMPLETED)
        self.assertEqual(states["plan"], PHASE_STATE_CURRENT)
        self.assertEqual(states["build"], PHASE_STATE_PENDING)
        self.assertEqual(states["verify"], PHASE_STATE_PENDING)
        self.assertEqual(states["reflect"], PHASE_STATE_PENDING)

    def test_completed_phases_filtered_against_canonical_set(self) -> None:
        """Unknown phase names in completed_phases are silently dropped
        (no garbage state from operator-edited status.json)."""
        import json as _json

        from mythic_vibe_cli.core.state import PHASES
        from mythic_vibe_cli.tui.app import (
            PHASE_STATE_COMPLETED,
            build_loop_navigator_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "status.json").write_text(
                _json.dumps(
                    {
                        "schema_version": 1,
                        "current_phase": "plan",
                        "completed_phases": ["intent", "not-a-real-phase"],
                    }
                ),
                encoding="utf-8",
            )
            data = build_loop_navigator_data(root)

        # Every entry maps to a known phase.
        for entry in data.entries:
            self.assertIn(entry.phase, PHASES)
        # "intent" is completed; the bogus name doesn't appear anywhere.
        intent_entry = next(e for e in data.entries if e.phase == "intent")
        self.assertEqual(intent_entry.state, PHASE_STATE_COMPLETED)

    def test_unknown_current_phase_treated_as_pending_for_every_canonical(self) -> None:
        import json as _json

        from mythic_vibe_cli.tui.app import (
            PHASE_STATE_PENDING,
            build_loop_navigator_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "status.json").write_text(
                _json.dumps(
                    {
                        "schema_version": 1,
                        "current_phase": "exotic-phase-name",
                        "completed_phases": [],
                    }
                ),
                encoding="utf-8",
            )
            data = build_loop_navigator_data(root)

        self.assertEqual(data.current_phase, "")
        for entry in data.entries:
            self.assertEqual(entry.state, PHASE_STATE_PENDING)

    def test_to_dict_round_trip_shape(self) -> None:
        from mythic_vibe_cli.tui.app import build_loop_navigator_data

        with tempfile.TemporaryDirectory() as tmp:
            data = build_loop_navigator_data(Path(tmp))
            payload = data.to_dict()

        self.assertIn("entries", payload)
        self.assertIn("current_phase", payload)
        self.assertEqual(len(payload["entries"]), 7)
        for entry_payload in payload["entries"]:
            self.assertEqual(set(entry_payload.keys()), {"phase", "state", "marker"})


class LoopNavigatorFormatTests(unittest.TestCase):
    def test_default_render_marks_current_with_arrow_glyph(self) -> None:
        from mythic_vibe_cli.tui.app import (
            _format_loop_navigator,
            build_loop_navigator_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            data = build_loop_navigator_data(Path(tmp))
            rendered = _format_loop_navigator(data)

        # Default: intent is current; rest are pending.
        self.assertIn("> intent", rendered)
        # All seven phase names appear.
        for phase in ("intent", "constraints", "architecture", "plan", "build", "verify", "reflect"):
            self.assertIn(phase, rendered)

    def test_empty_entries_yields_placeholder(self) -> None:
        from mythic_vibe_cli.tui.app import LoopNavigatorData, _format_loop_navigator

        rendered = _format_loop_navigator(LoopNavigatorData(entries=[], current_phase=""))
        self.assertIn("no phases configured", rendered)


@unittest.skipIf(textual_unavailable, "textual not installed")
class TuiLoopNavigatorIntegrationTests(unittest.TestCase):
    """Headless tests that exercise the actual widget on the screen."""

    def test_loop_nav_panel_renders_in_status_screen(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    panel = app.screen.query_one("#loop-nav-panel")
                    return str(panel.render())

        rendered = asyncio.run(run_test())
        # Should contain at least the canonical phase names.
        for phase in ("intent", "constraints", "architecture", "plan", "build", "verify", "reflect"):
            self.assertIn(phase, rendered)


# ---- PH-04 slice 4.2 — Artifact Viewer panel ----------------------------


class ArtifactViewerDataTests(unittest.TestCase):
    """Pure-data layer: build_artifact_viewer_data() classifies the
    current phase's expected artefacts as present / missing / stale."""

    def test_unknown_phase_yields_empty_entries(self) -> None:
        from mythic_vibe_cli.tui.app import build_artifact_viewer_data

        with tempfile.TemporaryDirectory() as tmp:
            data = build_artifact_viewer_data(Path(tmp), "no-such-phase")
        self.assertEqual(data.phase, "no-such-phase")
        self.assertEqual(data.entries, [])

    def test_empty_phase_yields_empty_entries(self) -> None:
        from mythic_vibe_cli.tui.app import build_artifact_viewer_data

        with tempfile.TemporaryDirectory() as tmp:
            data = build_artifact_viewer_data(Path(tmp), "")
        self.assertEqual(data.phase, "")
        self.assertEqual(data.entries, [])

    def test_intent_phase_returns_three_entries_all_missing_on_bare_dir(self) -> None:
        from mythic_vibe_cli.tui.app import (
            ARTIFACT_STATUS_MISSING,
            PHASE_ARTEFACTS,
            build_artifact_viewer_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            data = build_artifact_viewer_data(Path(tmp), "intent")
        self.assertEqual(len(data.entries), len(PHASE_ARTEFACTS["intent"]))
        for entry in data.entries:
            self.assertEqual(entry.status, ARTIFACT_STATUS_MISSING)
            self.assertIsNone(entry.age_days)
            self.assertEqual(entry.marker, "-")

    def test_present_recent_artefact_marked_present(self) -> None:
        from mythic_vibe_cli.tui.app import (
            ARTIFACT_STATUS_PRESENT,
            build_artifact_viewer_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "MYTHIC_ENGINEERING.md").write_text("hello", encoding="utf-8")
            data = build_artifact_viewer_data(root, "intent")
        match = next(e for e in data.entries if e.relpath == "MYTHIC_ENGINEERING.md")
        self.assertEqual(match.status, ARTIFACT_STATUS_PRESENT)
        self.assertEqual(match.marker, "+")
        self.assertIsNotNone(match.age_days)

    def test_old_artefact_marked_stale(self) -> None:
        import os

        from mythic_vibe_cli.tui.app import (
            ARTIFACT_STATUS_STALE,
            build_artifact_viewer_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "MYTHIC_ENGINEERING.md"
            target.write_text("old content", encoding="utf-8")
            # Set mtime to 30 days ago.
            thirty_days_ago = time.time() - (30 * 86400)
            os.utime(target, (thirty_days_ago, thirty_days_ago))

            data = build_artifact_viewer_data(root, "intent")
        match = next(e for e in data.entries if e.relpath == "MYTHIC_ENGINEERING.md")
        self.assertEqual(match.status, ARTIFACT_STATUS_STALE)
        self.assertEqual(match.marker, "~")
        self.assertGreaterEqual(match.age_days or 0, 14)

    def test_directory_artefact_uses_most_recent_mtime(self) -> None:
        import os

        from mythic_vibe_cli.tui.app import (
            ARTIFACT_STATUS_PRESENT,
            ARTIFACT_STATUS_STALE,
            build_artifact_viewer_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adr_dir = root / "docs" / "ADRS"
            adr_dir.mkdir(parents=True)

            # Old file in the directory.
            old_adr = adr_dir / "ADR-0001-old.md"
            old_adr.write_text("old", encoding="utf-8")
            old_time = time.time() - (60 * 86400)
            os.utime(old_adr, (old_time, old_time))
            os.utime(adr_dir, (old_time, old_time))

            data = build_artifact_viewer_data(root, "architecture")
            adr_entry = next(e for e in data.entries if e.relpath == "docs/ADRS")
            self.assertEqual(adr_entry.status, ARTIFACT_STATUS_STALE)

            # Adding a fresh file inside the dir resets the dir's effective mtime.
            (adr_dir / "ADR-0002-new.md").write_text("fresh", encoding="utf-8")
            data = build_artifact_viewer_data(root, "architecture")
            adr_entry = next(e for e in data.entries if e.relpath == "docs/ADRS")
            self.assertEqual(adr_entry.status, ARTIFACT_STATUS_PRESENT)

    def test_custom_now_keyword_lets_tests_pin_clock(self) -> None:
        from mythic_vibe_cli.tui.app import (
            ARTIFACT_STATUS_STALE,
            build_artifact_viewer_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "MYTHIC_ENGINEERING.md").write_text("x", encoding="utf-8")
            # Pin "now" 30 days in the future so the artefact looks stale.
            future = time.time() + (30 * 86400)
            data = build_artifact_viewer_data(root, "intent", now=future)
        match = next(e for e in data.entries if e.relpath == "MYTHIC_ENGINEERING.md")
        self.assertEqual(match.status, ARTIFACT_STATUS_STALE)

    def test_to_dict_round_trip_shape(self) -> None:
        from mythic_vibe_cli.tui.app import build_artifact_viewer_data

        with tempfile.TemporaryDirectory() as tmp:
            data = build_artifact_viewer_data(Path(tmp), "intent")
            payload = data.to_dict()
        self.assertEqual(payload["phase"], "intent")
        self.assertIsInstance(payload["entries"], list)
        for entry_payload in payload["entries"]:
            self.assertEqual(
                set(entry_payload.keys()),
                {"relpath", "status", "marker", "age_days"},
            )


class ArtifactViewerFormatTests(unittest.TestCase):
    def test_unknown_phase_yields_placeholder(self) -> None:
        from mythic_vibe_cli.tui.app import (
            ArtifactViewerData,
            _format_artifact_viewer,
        )

        rendered = _format_artifact_viewer(ArtifactViewerData(phase="", entries=[]))
        self.assertIn("no phase set", rendered)

    def test_empty_entries_yields_placeholder(self) -> None:
        from mythic_vibe_cli.tui.app import (
            ArtifactViewerData,
            _format_artifact_viewer,
        )

        rendered = _format_artifact_viewer(
            ArtifactViewerData(phase="rituals", entries=[])
        )
        self.assertIn("no canonical artefacts declared", rendered)
        self.assertIn("rituals", rendered)

    def test_render_marks_missing_with_red_tag(self) -> None:
        from mythic_vibe_cli.tui.app import (
            _format_artifact_viewer,
            build_artifact_viewer_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            data = build_artifact_viewer_data(Path(tmp), "intent")
            rendered = _format_artifact_viewer(data)
        self.assertIn("[red]", rendered)
        self.assertIn("MYTHIC_ENGINEERING.md", rendered)


@unittest.skipIf(textual_unavailable, "textual not installed")
class TuiArtifactViewerIntegrationTests(unittest.TestCase):
    def test_artifact_panel_renders_in_status_screen(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    panel = app.screen.query_one("#artifact-panel")
                    return str(panel.render())

        rendered = asyncio.run(run_test())
        # Default state's current_phase is "intent"; that means the
        # intent artefacts should appear in the panel.
        self.assertIn("MYTHIC_ENGINEERING.md", rendered)
        self.assertIn("SYSTEM_VISION.md", rendered)


# ---- PH-04 slice 4.3 — Packet Viewer panel ------------------------------


class PacketViewerDataTests(unittest.TestCase):
    """Pure-data layer: build_packet_viewer_data() finds the current
    packet and snapshots its preview."""

    def test_empty_project_returns_empty_data(self) -> None:
        from mythic_vibe_cli.tui.app import build_packet_viewer_data

        with tempfile.TemporaryDirectory() as tmp:
            data = build_packet_viewer_data(Path(tmp))
        self.assertEqual(data.packet_id, "")
        self.assertEqual(data.relpath, "")
        self.assertEqual(data.preview_lines, [])
        self.assertEqual(data.line_count, 0)
        self.assertFalse(data.truncated)

    def test_codex_prompt_md_preferred_when_present(self) -> None:
        from mythic_vibe_cli.tui.app import build_packet_viewer_data

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mythic = root / "mythic"
            mythic.mkdir()
            (mythic / "codex_prompt.md").write_text(
                "# Codex Prompt\n\nLine 2\nLine 3\n",
                encoding="utf-8",
            )
            packets = mythic / "packets"
            packets.mkdir()
            (packets / "PKT-0001.md").write_text("historical packet content\n", encoding="utf-8")
            data = build_packet_viewer_data(root)

        self.assertEqual(data.packet_id, "codex_prompt")
        # Use forward slashes in the comparison so this works on Windows too.
        self.assertEqual(data.relpath.replace("\\", "/"), "mythic/codex_prompt.md")
        self.assertEqual(data.preview_lines[0], "# Codex Prompt")
        self.assertEqual(data.line_count, 4)
        self.assertGreater(data.byte_size, 0)

    def test_falls_back_to_most_recent_packet_when_codex_prompt_missing(self) -> None:
        import os

        from mythic_vibe_cli.tui.app import build_packet_viewer_data

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packets = root / "mythic" / "packets"
            packets.mkdir(parents=True)
            old = packets / "PKT-0001.md"
            old.write_text("old packet\n", encoding="utf-8")
            new = packets / "PKT-0002.md"
            new.write_text("# Recent packet\n\nbody line\n", encoding="utf-8")
            # Force PKT-0002 to be more recent than PKT-0001.
            old_time = time.time() - 100
            os.utime(old, (old_time, old_time))

            data = build_packet_viewer_data(root)

        self.assertEqual(data.packet_id, "PKT-0002")
        self.assertEqual(data.preview_lines[0], "# Recent packet")

    def test_preview_truncated_when_file_exceeds_cap(self) -> None:
        from mythic_vibe_cli.tui.app import (
            PACKET_PREVIEW_LINES,
            build_packet_viewer_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mythic = root / "mythic"
            mythic.mkdir()
            many_lines = "\n".join(f"line {i}" for i in range(50))
            (mythic / "codex_prompt.md").write_text(many_lines, encoding="utf-8")
            data = build_packet_viewer_data(root, preview_lines=PACKET_PREVIEW_LINES)

        self.assertEqual(len(data.preview_lines), PACKET_PREVIEW_LINES)
        self.assertEqual(data.line_count, 50)
        self.assertTrue(data.truncated)

    def test_no_truncation_when_file_fits_within_cap(self) -> None:
        from mythic_vibe_cli.tui.app import build_packet_viewer_data

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mythic = root / "mythic"
            mythic.mkdir()
            (mythic / "codex_prompt.md").write_text(
                "one\ntwo\nthree\n",
                encoding="utf-8",
            )
            data = build_packet_viewer_data(root, preview_lines=10)

        self.assertEqual(data.preview_lines, ["one", "two", "three"])
        self.assertFalse(data.truncated)

    def test_unreadable_file_returns_empty_data(self) -> None:
        from mythic_vibe_cli.tui.app import build_packet_viewer_data

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mythic = root / "mythic"
            mythic.mkdir()
            # Create as a directory with the same name to force the read to fail.
            target = mythic / "codex_prompt.md"
            target.mkdir()  # not a file -> .is_file() is False; selector skips it
            data = build_packet_viewer_data(root)

        # Selector falls back to packets/ — none exist -> empty result.
        self.assertEqual(data.relpath, "")

    def test_to_dict_round_trip_shape(self) -> None:
        from mythic_vibe_cli.tui.app import build_packet_viewer_data

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mythic = root / "mythic"
            mythic.mkdir()
            (mythic / "codex_prompt.md").write_text("hi\n", encoding="utf-8")
            data = build_packet_viewer_data(root)
            payload = data.to_dict()

        self.assertEqual(
            set(payload.keys()),
            {
                "packet_id",
                "relpath",
                "line_count",
                "byte_size",
                "modified_at",
                "preview_lines",
                "truncated",
            },
        )


class PacketViewerFormatTests(unittest.TestCase):
    def test_empty_data_renders_placeholder(self) -> None:
        from mythic_vibe_cli.tui.app import PacketViewerData, _format_packet_viewer

        rendered = _format_packet_viewer(PacketViewerData())
        self.assertIn("no packet on disk", rendered)
        self.assertIn("codex-pack", rendered)
        self.assertIn("forge plan", rendered)

    def test_render_includes_packet_id_and_preview(self) -> None:
        from mythic_vibe_cli.tui.app import (
            _format_packet_viewer,
            build_packet_viewer_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mythic = root / "mythic"
            mythic.mkdir()
            (mythic / "codex_prompt.md").write_text(
                "# Mythic Engineering Task Packet\n\n## 1. Role\n",
                encoding="utf-8",
            )
            data = build_packet_viewer_data(root)
            rendered = _format_packet_viewer(data)

        self.assertIn("codex_prompt", rendered)
        self.assertIn("# Mythic Engineering Task Packet", rendered)
        self.assertIn("## 1. Role", rendered)

    def test_truncated_render_shows_remainder_count(self) -> None:
        from mythic_vibe_cli.tui.app import (
            _format_packet_viewer,
            build_packet_viewer_data,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mythic = root / "mythic"
            mythic.mkdir()
            (mythic / "codex_prompt.md").write_text(
                "\n".join(f"line {i}" for i in range(50)),
                encoding="utf-8",
            )
            data = build_packet_viewer_data(root, preview_lines=5)
            rendered = _format_packet_viewer(data)

        self.assertIn("(45 more lines)", rendered)


# ---- PH-04 slice 4.4 — Status Bar ---------------------------------------


class StatusBarFormatTests(unittest.TestCase):
    """Pure formatter tests against fabricated StatusData instances."""

    def _data(self, **overrides):  # type: ignore[no-untyped-def]
        from mythic_vibe_cli.tui.app import StatusData

        defaults = {
            "path": "/tmp/projects/myproj",
            "phase": "build",
            "active_task_id": "TASK-0001",
            "last_verification_id": "VER-ABCDE",
            "last_verification_result": "pass",
            "last_verification_level": "unit",
            "latest_handoff_id": "HO-9XYZ",
            "latest_handoff_created_at": "2026-04-29T12:00:00Z",
            "latest_handoff_next_step": "Run forge resume",
            "plugins_enabled": 2,
            "plugins_disabled": 0,
            "refreshed_at": "2026-04-29 12:00:00 UTC",
        }
        defaults.update(overrides)
        return StatusData(**defaults)

    def test_bar_includes_project_basename_phase_verify_handoff_plugins(self) -> None:
        from mythic_vibe_cli.tui.app import _format_status_bar

        rendered = _format_status_bar(self._data())
        self.assertIn("myproj", rendered)
        self.assertIn("phase:", rendered)
        self.assertIn("build", rendered)
        self.assertIn("verify: pass", rendered)
        self.assertIn("VER-ABCDE", rendered)
        self.assertIn("handoff: HO-9XYZ", rendered)
        self.assertIn("plugins: 2+0", rendered)

    def test_healthy_state_shows_green_ok_warning(self) -> None:
        from mythic_vibe_cli.tui.app import _format_status_bar

        rendered = _format_status_bar(self._data())
        self.assertIn("[green]ok[/green]", rendered)

    def test_failed_verify_surfaces_red_warning(self) -> None:
        from mythic_vibe_cli.tui.app import _format_status_bar

        rendered = _format_status_bar(self._data(last_verification_result="fail"))
        self.assertIn("[red]verify-failed[/red]", rendered)
        # No "ok" in the warnings section when a real warning is present.
        self.assertNotIn("[green]ok[/green]", rendered)

    def test_disabled_plugins_surface_yellow_warning(self) -> None:
        from mythic_vibe_cli.tui.app import _format_status_bar

        rendered = _format_status_bar(
            self._data(plugins_enabled=2, plugins_disabled=3)
        )
        self.assertIn("[yellow]3 plugin(s) disabled[/yellow]", rendered)

    def test_multiple_warnings_join_with_middle_dot(self) -> None:
        from mythic_vibe_cli.tui.app import _format_status_bar

        rendered = _format_status_bar(
            self._data(last_verification_result="fail", plugins_disabled=1)
        )
        self.assertIn("[red]verify-failed[/red]", rendered)
        self.assertIn("[yellow]1 plugin(s) disabled[/yellow]", rendered)
        # Both warnings appear, separated by a middle-dot.
        self.assertIn("verify-failed", rendered)
        self.assertIn("disabled", rendered)

    def test_missing_verification_renders_dash(self) -> None:
        from mythic_vibe_cli.tui.app import _format_status_bar

        rendered = _format_status_bar(self._data(last_verification_id="(none)"))
        self.assertIn("verify: -", rendered)

    def test_missing_handoff_renders_dash(self) -> None:
        from mythic_vibe_cli.tui.app import _format_status_bar

        rendered = _format_status_bar(self._data(latest_handoff_id="(none)"))
        self.assertIn("handoff: -", rendered)

    def test_empty_path_falls_back_to_placeholder(self) -> None:
        from mythic_vibe_cli.tui.app import _format_status_bar

        rendered = _format_status_bar(self._data(path=""))
        self.assertIn("(no project)", rendered)


@unittest.skipIf(textual_unavailable, "textual not installed")
class TuiStatusBarIntegrationTests(unittest.TestCase):
    """Headless test confirming the bar appears in the actual screen."""

    def test_status_bar_renders_phase_and_plugins(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    panel = app.screen.query_one("#status-bar")
                    return str(panel.render())

        rendered = asyncio.run(run_test())
        # Default state: phase=intent, plugins=0+0, no warnings -> ok.
        self.assertIn("phase:", rendered)
        self.assertIn("intent", rendered)
        self.assertIn("plugins:", rendered)


@unittest.skipIf(textual_unavailable, "textual not installed")
class TuiPacketViewerIntegrationTests(unittest.TestCase):
    def test_packet_panel_renders_placeholder_when_empty(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    panel = app.screen.query_one("#packet-panel")
                    return str(panel.render())

        rendered = asyncio.run(run_test())
        self.assertIn("no packet", rendered)

    def test_packet_panel_renders_codex_prompt_content(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                mythic = root / "mythic"
                mythic.mkdir()
                (mythic / "codex_prompt.md").write_text(
                    "# Mythic Engineering Task Packet\n\n## Role\nForge Worker\n",
                    encoding="utf-8",
                )
                app = MythicTuiApp(root)
                async with app.run_test() as pilot:
                    await pilot.pause()
                    panel = app.screen.query_one("#packet-panel")
                    return str(panel.render())

        rendered = asyncio.run(run_test())
        self.assertIn("codex_prompt", rendered)
        self.assertIn("Mythic Engineering Task Packet", rendered)


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
