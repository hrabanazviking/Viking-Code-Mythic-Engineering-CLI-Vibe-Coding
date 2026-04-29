"""Tests for TUI theme support (PH-04 slice 4.8).

Four layers:

1. Pure helpers — `next_theme`, `validate_theme`, constants.
2. Audit — every Screen subclass under ``mythic_vibe_cli.tui``
   registers a `t` (cycle theme) binding.
3. Headless TUI — `MythicTuiApp(theme=...)` applies, `t` cycles,
   bogus theme is silently ignored.
4. CLI plumbing — `cmd_tui` forwards `args.theme` into `run_tui`;
   the argparse parser rejects unknown theme names.
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock


textual_unavailable = False
try:
    import textual  # noqa: F401
except ImportError:
    textual_unavailable = True


from mythic_vibe_cli.tui.themes import (  # noqa: E402
    DEFAULT_THEME,
    TEXTUAL_BUILTIN_THEMES,
    THEME_CYCLE,
    next_theme,
    validate_theme,
)


# ---- Pure helpers ------------------------------------------------------


class ThemeConstantsTests(unittest.TestCase):
    def test_default_theme_is_textual_dark(self) -> None:
        self.assertEqual(DEFAULT_THEME, "textual-dark")

    def test_cycle_is_a_subset_of_builtin_themes(self) -> None:
        for theme in THEME_CYCLE:
            self.assertIn(theme, TEXTUAL_BUILTIN_THEMES)

    def test_cycle_contains_at_least_dark_and_light(self) -> None:
        self.assertIn("textual-dark", THEME_CYCLE)
        self.assertIn("textual-light", THEME_CYCLE)

    def test_cycle_has_no_duplicates(self) -> None:
        self.assertEqual(len(THEME_CYCLE), len(set(THEME_CYCLE)))


class NextThemeTests(unittest.TestCase):
    def test_advances_through_cycle(self) -> None:
        # Walk the entire cycle; expect each step to land on the next entry.
        current = THEME_CYCLE[0]
        for expected in THEME_CYCLE[1:]:
            current = next_theme(current)
            self.assertEqual(current, expected)

    def test_wraps_at_end_of_cycle(self) -> None:
        last = THEME_CYCLE[-1]
        self.assertEqual(next_theme(last), THEME_CYCLE[0])

    def test_off_cycle_theme_jumps_to_first(self) -> None:
        # Operator launched with --theme dracula (not on the curated cycle):
        # pressing `t` should land them on the first cycle entry, not no-op.
        self.assertEqual(next_theme("dracula"), THEME_CYCLE[0])
        self.assertEqual(next_theme("definitely-not-a-theme"), THEME_CYCLE[0])


class ValidateThemeTests(unittest.TestCase):
    def test_accepts_every_builtin(self) -> None:
        for name in TEXTUAL_BUILTIN_THEMES:
            self.assertEqual(validate_theme(name), name)

    def test_rejects_unknown_with_listing(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            validate_theme("nope")
        message = str(ctx.exception)
        self.assertIn("nope", message)
        # Error must list at least one canonical theme so the operator
        # can recover without reading source.
        self.assertIn("textual-dark", message)


# ---- Audit -------------------------------------------------------------


@unittest.skipIf(textual_unavailable, "textual not installed")
class ThemeBindingAuditTests(unittest.TestCase):
    """Every Screen subclass in the TUI must register a `t` binding so
    the operator can theme-switch from anywhere — same uniform-keymap
    discipline as slice 4.7's `?` audit."""

    def _all_tui_screens(self) -> list[type]:
        from textual.screen import Screen

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
                    continue
                seen.add(obj)
                screens.append(obj)
        return screens

    def test_every_tui_screen_registers_t(self) -> None:
        for cls in self._all_tui_screens():
            keys = {b.key for b in getattr(cls, "BINDINGS", [])}
            self.assertIn(
                "t",
                keys,
                f"{cls.__name__} is missing a `t` (cycle theme) binding "
                "(slice 4.8)",
            )


# ---- Headless TUI ------------------------------------------------------


@unittest.skipIf(textual_unavailable, "textual not installed")
class MythicTuiAppThemeTests(unittest.TestCase):
    def test_default_construction_keeps_textual_dark(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    return str(app.theme)

        self.assertEqual(asyncio.run(run_test()), "textual-dark")

    def test_explicit_theme_is_applied_on_mount(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp), theme="textual-light")
                async with app.run_test() as pilot:
                    await pilot.pause()
                    return str(app.theme)

        self.assertEqual(asyncio.run(run_test()), "textual-light")

    def test_t_keypress_advances_theme(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> tuple[str, str]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    before = str(app.theme)
                    await pilot.press("t")
                    await pilot.pause()
                    after = str(app.theme)
                    return before, after

        before, after = asyncio.run(run_test())
        self.assertEqual(before, THEME_CYCLE[0])
        self.assertEqual(after, THEME_CYCLE[1])

    def test_bogus_theme_does_not_crash_mount(self) -> None:
        """A direct in-process caller could pass a string Textual
        doesn't recognise. The CLI guards with argparse choices, but
        the App should still survive — the swallowed exception is
        documented in MythicTuiApp.on_mount."""
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> bool:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp), theme="not-a-real-theme")
                async with app.run_test() as pilot:
                    await pilot.pause()
                    return True

        self.assertTrue(asyncio.run(run_test()))


# ---- CLI plumbing ------------------------------------------------------


class CmdTuiThemeForwardingTests(unittest.TestCase):
    def test_cmd_tui_forwards_theme_argument(self) -> None:
        from mythic_vibe_cli.commands import cmd_tui

        captured: dict[str, object] = {}

        def fake_run_tui(root: Path, *, theme: str | None = None) -> int:
            captured["root"] = root
            captured["theme"] = theme
            return 0

        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(path=tmp, theme="nord")
            with mock.patch("mythic_vibe_cli.tui.app.run_tui", fake_run_tui):
                exit_code = cmd_tui(args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(captured["theme"], "nord")
        self.assertEqual(captured["root"], Path(tmp).resolve())

    def test_cmd_tui_passes_none_when_no_theme_given(self) -> None:
        from mythic_vibe_cli.commands import cmd_tui

        captured: dict[str, object] = {}

        def fake_run_tui(root: Path, *, theme: str | None = None) -> int:
            captured["theme"] = theme
            return 0

        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(path=tmp)  # no theme attr at all
            with mock.patch("mythic_vibe_cli.tui.app.run_tui", fake_run_tui):
                cmd_tui(args)

        self.assertIsNone(captured["theme"])


class TuiArgparseThemeTests(unittest.TestCase):
    def _build_parser(self) -> argparse.ArgumentParser:
        from mythic_vibe_cli.app import build_parser

        return build_parser()

    def test_argparse_accepts_known_theme(self) -> None:
        parser = self._build_parser()
        ns = parser.parse_args(["tui", "--theme", "nord"])
        self.assertEqual(ns.theme, "nord")

    def test_argparse_rejects_unknown_theme(self) -> None:
        parser = self._build_parser()
        # argparse exits via SystemExit on choice mismatch — capture stderr
        # so the test output stays clean.
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            parser.parse_args(["tui", "--theme", "definitely-not-a-theme"])

    def test_argparse_default_theme_is_none(self) -> None:
        parser = self._build_parser()
        ns = parser.parse_args(["tui"])
        self.assertIsNone(ns.theme)


if __name__ == "__main__":
    unittest.main()
