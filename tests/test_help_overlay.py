"""Tests for the shared help overlay (PH-04 slice 4.7).

Three layers:

1. Pure helpers — `binding_help_pairs` and `format_help_table`.
2. Audit — every Screen subclass under ``mythic_vibe_cli.tui``
   exposes a `?` (question_mark) binding.
3. Headless TUI — pressing `?` on each screen pushes a real
   `HelpOverlayScreen`; pressing `escape` pops it back.
"""

from __future__ import annotations

import asyncio
import inspect
import tempfile
import unittest
from pathlib import Path


textual_unavailable = False
try:
    import textual  # noqa: F401
except ImportError:
    textual_unavailable = True


from mythic_vibe_cli.tui.help_overlay import (  # noqa: E402
    binding_help_pairs,
    format_help_table,
)


# ---- Pure helpers ------------------------------------------------------


@unittest.skipIf(textual_unavailable, "textual not installed")
class BindingHelpPairsTests(unittest.TestCase):
    def test_visible_bindings_pass_through(self) -> None:
        from textual.binding import Binding

        bindings = [
            Binding("q", "quit", "Quit"),
            Binding("r", "refresh_now", "Refresh"),
        ]
        pairs = binding_help_pairs(bindings)
        self.assertEqual(pairs, [("q", "Quit"), ("r", "Refresh")])

    def test_hidden_bindings_are_filtered(self) -> None:
        from textual.binding import Binding

        bindings = [
            Binding("q", "quit", "Quit"),
            Binding("ctrl+c", "quit", "Quit", show=False),
        ]
        pairs = binding_help_pairs(bindings)
        self.assertEqual(pairs, [("q", "Quit")])

    def test_missing_description_renders_empty_string(self) -> None:
        from textual.binding import Binding

        bindings = [Binding("k", "noop", "")]
        self.assertEqual(binding_help_pairs(bindings), [("k", "")])


class FormatHelpTableTests(unittest.TestCase):
    def test_empty_pairs_render_placeholder(self) -> None:
        rendered = format_help_table("Status — keys", [])
        self.assertIn("Status — keys", rendered)
        self.assertIn("no bindings", rendered)

    def test_pairs_render_with_aligned_keys(self) -> None:
        rendered = format_help_table("X — keys", [("a", "Accept"), ("question_mark", "Help")])
        # The longer key sets the padding width — the cyan span around
        # `a` therefore contains trailing whitespace.
        self.assertIn("[cyan]a            [/cyan]", rendered)
        self.assertIn("[cyan]question_mark[/cyan]", rendered)
        self.assertIn("Accept", rendered)
        self.assertIn("Help", rendered)


# ---- Audit -------------------------------------------------------------


@unittest.skipIf(textual_unavailable, "textual not installed")
class HelpBindingAuditTests(unittest.TestCase):
    """Walk every Screen subclass shipped under ``mythic_vibe_cli.tui``
    and assert that each one registers a `?` binding so the operator
    has a uniform muscle-memory across the whole TUI."""

    def _all_tui_screens(self) -> list[type]:
        from textual.screen import Screen

        # Import the modules so subclasses are registered.
        from mythic_vibe_cli.tui import app, diff_review, help_overlay, picker, runner

        modules = [app, diff_review, help_overlay, picker, runner]
        seen: set[type] = set()
        screens: list[type] = []
        for module in modules:
            for _, obj in inspect.getmembers(module, inspect.isclass):
                if obj in seen:
                    continue
                if obj is Screen:
                    continue
                if not issubclass(obj, Screen):
                    continue
                if obj.__module__ != module.__name__:
                    continue  # imported from elsewhere; counted once
                seen.add(obj)
                screens.append(obj)
        return screens

    def test_every_tui_screen_registers_question_mark(self) -> None:
        screens = self._all_tui_screens()
        # Sanity floor: we know at minimum these classes exist.
        names = {cls.__name__ for cls in screens}
        for required in {
            "StatusScreen",
            "SlashPickerScreen",
            "CommandPreviewScreen",
            "RunningCommandScreen",
            "DiffReviewScreen",
            "HelpOverlayScreen",
        }:
            self.assertIn(required, names, f"{required} missing from audit set")

        for cls in screens:
            keys = {b.key for b in getattr(cls, "BINDINGS", [])}
            self.assertIn(
                "question_mark",
                keys,
                f"{cls.__name__} is missing a `?` binding (slice 4.7)",
            )


# ---- Headless integration ---------------------------------------------


@unittest.skipIf(textual_unavailable, "textual not installed")
class HelpOverlayIntegrationTests(unittest.TestCase):
    def test_status_screen_question_mark_pushes_overlay(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.help_overlay import HelpOverlayScreen

        async def run_test() -> tuple[bool, str]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    await pilot.press("question_mark")
                    await pilot.pause()
                    on_overlay = isinstance(app.screen, HelpOverlayScreen)
                    card = app.screen.query_one("#help-overlay-card")
                    return on_overlay, str(card.render())

        on_overlay, rendered = asyncio.run(run_test())
        self.assertTrue(on_overlay)
        self.assertIn("Status", rendered)
        self.assertIn("Refresh", rendered)
        self.assertIn("Quit", rendered)

    def test_overlay_dismisses_back_to_caller_on_escape(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp, StatusScreen

        async def run_test() -> bool:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    await pilot.press("question_mark")
                    await pilot.pause()
                    await pilot.press("escape")
                    await pilot.pause()
                    return isinstance(app.screen, StatusScreen)

        self.assertTrue(asyncio.run(run_test()))

    def test_slash_picker_question_mark_pushes_overlay(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.help_overlay import HelpOverlayScreen
        from mythic_vibe_cli.tui.picker import SlashPickerScreen

        async def run_test() -> tuple[bool, str]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    app.push_screen(SlashPickerScreen(Path(tmp)))
                    await pilot.pause()
                    # The picker focuses its Input on mount; defocus
                    # so the `?` reaches the screen-level binding.
                    app.screen.set_focus(None)
                    await pilot.pause()
                    await pilot.press("question_mark")
                    await pilot.pause()
                    on_overlay = isinstance(app.screen, HelpOverlayScreen)
                    card = app.screen.query_one("#help-overlay-card")
                    return on_overlay, str(card.render())

        on_overlay, rendered = asyncio.run(run_test())
        self.assertTrue(on_overlay)
        self.assertIn("Slash picker", rendered)
        self.assertIn("Cancel", rendered)

    def test_command_preview_question_mark_pushes_overlay(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.help_overlay import HelpOverlayScreen
        from mythic_vibe_cli.tui.picker import CommandPreviewScreen, PickerEntry

        async def run_test() -> tuple[bool, str]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    entry = PickerEntry(name="status", description="Status", source="builtin")
                    app.push_screen(CommandPreviewScreen(entry))
                    await pilot.pause()
                    await pilot.press("question_mark")
                    await pilot.pause()
                    on_overlay = isinstance(app.screen, HelpOverlayScreen)
                    card = app.screen.query_one("#help-overlay-card")
                    return on_overlay, str(card.render())

        on_overlay, rendered = asyncio.run(run_test())
        self.assertTrue(on_overlay)
        self.assertIn("Command preview", rendered)
        self.assertIn("Run", rendered)
        self.assertIn("Back", rendered)

    def test_running_command_screen_question_mark_pushes_overlay(self) -> None:
        import sys as _sys

        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.help_overlay import HelpOverlayScreen
        from mythic_vibe_cli.tui.runner import RunningCommandScreen, RunSpec

        async def run_test() -> tuple[bool, str]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    spec = RunSpec(
                        label="/echo-help",
                        argv=[_sys.executable, "-c", "import sys; sys.exit(0)"],
                    )
                    app.push_screen(RunningCommandScreen(spec, cwd=Path(tmp)))
                    for _ in range(5):
                        await pilot.pause()
                    await pilot.press("question_mark")
                    await pilot.pause()
                    on_overlay = isinstance(app.screen, HelpOverlayScreen)
                    card = app.screen.query_one("#help-overlay-card")
                    return on_overlay, str(card.render())

        on_overlay, rendered = asyncio.run(run_test())
        self.assertTrue(on_overlay)
        self.assertIn("Running command", rendered)
        self.assertIn("Back", rendered)


if __name__ == "__main__":
    unittest.main()
