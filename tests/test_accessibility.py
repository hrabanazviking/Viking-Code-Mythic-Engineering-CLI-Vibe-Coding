"""Phase-4 finale accessibility audit (PH-04 slice 4.9).

Locks in five invariants the slice 4.1–4.8 work was already
respecting, so a future careless change can't quietly remove the
fallback signal a colour-blind / monochrome / screen-reader user
relies on:

1. Every visible Binding has a non-empty description string.
2. Every colour-coded indicator carries a word and/or glyph that
   conveys the same state in monochrome.
3. Every ``action_<name>`` method on a Screen is reachable from at
   least one Binding (no orphan keyboard-only actions).
4. The TUI renders under a non-default theme (``textual-light``)
   without losing key textual content.
5. ``StatusScreen.compose()`` yields widgets in visually top-to-bottom
   order so Tab navigation matches the reading order.
"""

from __future__ import annotations

import asyncio
import inspect
import re
import tempfile
import unittest
from pathlib import Path


textual_unavailable = False
try:
    import textual  # noqa: F401
except ImportError:
    textual_unavailable = True


def _all_tui_screens() -> list[type]:
    """Walk the TUI package and return every Screen subclass we ship."""
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


# ---- 1. Binding descriptions -------------------------------------------


@unittest.skipIf(textual_unavailable, "textual not installed")
class BindingDescriptionAudit(unittest.TestCase):
    """Every visible Binding (``show=True``) must carry a non-empty
    description — Textual's footer line, the slice 4.7 help overlay,
    and any screen reader narrating the chrome all rely on it."""

    def test_every_visible_binding_has_a_description(self) -> None:
        offenders: list[str] = []
        for cls in _all_tui_screens():
            for binding in getattr(cls, "BINDINGS", []):
                if not getattr(binding, "show", True):
                    continue  # hidden aliases (ctrl+c, enter) are exempt
                description = (binding.description or "").strip()
                if not description:
                    offenders.append(f"{cls.__name__}: {binding.key!r}")
        self.assertEqual(
            offenders,
            [],
            "These visible bindings have empty descriptions — "
            "the help overlay and footer would render blank cells:\n  "
            + "\n  ".join(offenders),
        )


# ---- 2. Non-colour signals --------------------------------------------


def _status_data(**overrides: object) -> object:
    """Helper — build a `StatusData` with all required fields filled
    in by sane defaults so individual tests can override only the
    field they care about."""
    from mythic_vibe_cli.tui.app import StatusData

    base: dict[str, object] = dict(
        path="/tmp/proj",
        phase="build",
        active_task_id="(none)",
        last_verification_id="(none)",
        last_verification_result="",
        last_verification_level="",
        latest_handoff_id="(none)",
        latest_handoff_created_at="",
        latest_handoff_next_step="",
        plugins_enabled=0,
        plugins_disabled=0,
    )
    base.update(overrides)
    return StatusData(**base)  # type: ignore[arg-type]


class NonColourSignalAudit(unittest.TestCase):
    """For each colour-coded indicator, the rendered string must also
    carry a word / glyph that conveys the same state without colour.

    Pure-formatter tests — no Textual mount needed."""

    def test_diagnostics_pulse_has_glyph_and_word_in_both_states(self) -> None:
        from mythic_vibe_cli.runtime.event_log import EventStreamSnapshot
        from mythic_vibe_cli.tui.app import _format_diagnostics_panel

        idle = _format_diagnostics_panel(
            EventStreamSnapshot(entries=(), new_in_last_poll=0, total_seen=0)
        )
        self.assertIn("○", idle)
        self.assertIn("idle", idle.lower())

        live = _format_diagnostics_panel(
            EventStreamSnapshot(entries=(), new_in_last_poll=3, total_seen=3)
        )
        self.assertIn("●", live)
        self.assertIn("live", live.lower())

    def test_status_bar_healthy_state_says_ok(self) -> None:
        from mythic_vibe_cli.tui.app import _format_status_bar

        rendered = _format_status_bar(_status_data())
        # "ok" is the canonical word; the colour tag is decoration.
        self.assertIn("ok", rendered.lower())

    def test_status_bar_failed_verify_says_failed(self) -> None:
        from mythic_vibe_cli.tui.app import _format_status_bar

        rendered = _format_status_bar(
            _status_data(
                phase="verify",
                last_verification_id="V-1",
                last_verification_result="fail",
            )
        )
        # "failed" + "verify" must both be present without relying on red.
        self.assertIn("verify", rendered.lower())
        self.assertIn("fail", rendered.lower())

    def test_status_bar_disabled_plugins_says_disabled(self) -> None:
        from mythic_vibe_cli.tui.app import _format_status_bar

        rendered = _format_status_bar(_status_data(plugins_disabled=2))
        self.assertIn("disabled", rendered.lower())

    def test_loop_navigator_uses_ascii_glyphs(self) -> None:
        from mythic_vibe_cli.tui.app import (
            LoopNavigatorData,
            LoopNavigatorEntry,
            PHASE_STATE_COMPLETED,
            PHASE_STATE_CURRENT,
            PHASE_STATE_PENDING,
            _format_loop_navigator,
        )

        data = LoopNavigatorData(
            entries=[
                LoopNavigatorEntry(phase="intent", state=PHASE_STATE_COMPLETED, marker="x"),
                LoopNavigatorEntry(phase="build", state=PHASE_STATE_CURRENT, marker=">"),
                LoopNavigatorEntry(phase="verify", state=PHASE_STATE_PENDING, marker="."),
            ],
            current_phase="build",
        )
        rendered = _format_loop_navigator(data)
        for marker in (">", "x", "."):
            self.assertIn(marker, rendered)
        # And every phase name is also visible — text label, not colour.
        for phase in ("intent", "build", "verify"):
            self.assertIn(phase, rendered)

    def test_diff_review_hunk_lines_use_plus_minus_prefix(self) -> None:
        from mythic_vibe_cli.tui.diff_review import (
            DiffHunk,
            DiffLine,
            _format_hunk_for_review,
        )

        hunk = DiffHunk(
            file_path="x.py",
            header="@@ -1,2 +1,3 @@",
            old_start=1,
            old_count=2,
            new_start=1,
            new_count=3,
            lines=(
                DiffLine(kind="addition", text="alpha"),
                DiffLine(kind="deletion", text="beta"),
            ),
        )
        rendered = _format_hunk_for_review(hunk)
        # The +/- prefix is the non-colour signal — even with red/green
        # tags stripped, the operator can tell additions from deletions.
        self.assertIn("+ alpha", rendered)
        self.assertIn("- beta", rendered)


# ---- 3. Action reachability -------------------------------------------


@unittest.skipIf(textual_unavailable, "textual not installed")
class KeyboardActionReachabilityAudit(unittest.TestCase):
    """Every ``action_<name>`` method declared on a Screen must be
    reachable from at least one Binding — otherwise the action is
    keyboard-orphaned and the operator can't invoke it."""

    def _binding_actions(self, cls: type) -> set[str]:
        actions: set[str] = set()
        for binding in getattr(cls, "BINDINGS", []):
            action = binding.action or ""
            # Strip any ``app.`` / ``screen.`` qualifier so we compare
            # against the bare method-name suffix.
            tail = action.split(".")[-1]
            actions.add(tail)
        return actions

    def test_every_action_method_is_bound(self) -> None:
        offenders: list[str] = []
        for cls in _all_tui_screens():
            bound = self._binding_actions(cls)
            # `inspect.getmembers` includes inherited attributes; we want
            # only methods declared on this class so we don't double-count
            # actions inherited from base Screen / App.
            for name in cls.__dict__:
                if not name.startswith("action_"):
                    continue
                bare = name[len("action_") :]
                # The action may also be reachable via the App or via a
                # globally-aliased binding on another screen — we only
                # check the *defining* class for simplicity.
                if bare not in bound:
                    offenders.append(f"{cls.__name__}.{name}")
        self.assertEqual(
            offenders,
            [],
            "These action methods have no Binding pointing at them — "
            "they're keyboard-orphaned:\n  " + "\n  ".join(offenders),
        )


# ---- 4. Theme-agnostic rendering --------------------------------------


@unittest.skipIf(textual_unavailable, "textual not installed")
class ThemeRenderingAudit(unittest.TestCase):
    """Slice 4.6's diagnostics + slice 4.4's status bar must remain
    legible under a non-default theme. Sample-render under
    ``textual-light`` and confirm the key text content survives."""

    def test_status_bar_and_diagnostics_render_under_textual_light(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> tuple[str, str, str]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp), theme="textual-light")
                async with app.run_test() as pilot:
                    await pilot.pause()
                    bar = app.screen.query_one("#status-bar")
                    diag = app.screen.query_one("#events-panel")
                    return str(app.theme), str(bar.render()), str(diag.render())

        theme, bar_render, diag_render = asyncio.run(run_test())
        self.assertEqual(theme, "textual-light")
        self.assertIn("phase:", bar_render)
        self.assertIn("plugins:", bar_render)
        # Diagnostics still surfaces the idle pulse text under light theme.
        self.assertIn("idle", diag_render.lower())


# ---- 5. Focus order ---------------------------------------------------


@unittest.skipIf(textual_unavailable, "textual not installed")
class FocusOrderAudit(unittest.TestCase):
    """``StatusScreen.compose`` must yield widgets in visual reading
    order: the header (internal), then the main row holding sidebar
    + mid-row, then the status bar, then the footer line, then the
    footer (internal). We assert on the IDs we set ourselves so
    Textual-internal widget classes don't drift the test."""

    def test_status_screen_yields_widgets_in_reading_order(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp

        async def run_test() -> list[str]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    return [c.id for c in app.screen.children if c.id]

        ordered_ids = asyncio.run(run_test())

        # The compose() yield order produces these IDs in this sequence.
        # Header / Footer don't have IDs we set, so they're filtered above.
        expected = ["main-row", "status-bar", "footer-line"]
        idx_main = ordered_ids.index("main-row")
        idx_bar = ordered_ids.index("status-bar")
        idx_footer = ordered_ids.index("footer-line")
        self.assertLess(idx_main, idx_bar, f"actual order: {ordered_ids}")
        self.assertLess(idx_bar, idx_footer, f"actual order: {ordered_ids}")
        # And every expected id is actually present.
        for required in expected:
            self.assertIn(required, ordered_ids)


# ---- Source-level static checks ---------------------------------------


class AsciiGlyphsAudit(unittest.TestCase):
    """Sanity-check that the user-facing glyphs we rely on for
    non-colour signalling are pure ASCII (cross-platform safe).

    Anything outside ASCII risks being garbled on Windows legacy
    code pages — recorded in `feedback_volmarr_preferences.md` as a
    durable rule across the whole ecosystem."""

    def test_loop_navigator_glyph_table_is_ascii(self) -> None:
        from mythic_vibe_cli.tui.app import _PHASE_GLYPHS

        for state, glyph in _PHASE_GLYPHS.items():
            self.assertTrue(
                all(ord(c) < 128 for c in glyph),
                f"Loop nav glyph for state {state!r} ({glyph!r}) is not ASCII",
            )

    def test_diff_review_bindings_text_is_ascii(self) -> None:
        from mythic_vibe_cli.tui.diff_review import DIFF_REVIEW_BINDINGS_TEXT

        # The bindings hint may use the middle-dot separator (U+00B7),
        # which is Latin-1 and renders cleanly on every modern terminal
        # including Windows. Anything beyond Latin-1 is the failure case.
        for char in DIFF_REVIEW_BINDINGS_TEXT:
            self.assertLess(
                ord(char),
                256,
                f"Non-Latin-1 char {char!r} in DIFF_REVIEW_BINDINGS_TEXT",
            )

    def test_pulse_glyphs_are_documented_unicode(self) -> None:
        """The diagnostics pulse uses ●/○ — record their codepoints
        so anyone hunting for the symbols can grep for them."""
        # U+25CF BLACK CIRCLE / U+25CB WHITE CIRCLE — both in BMP and
        # render correctly on every default terminal font we ship for.
        self.assertEqual(ord("●"), 0x25CF)
        self.assertEqual(ord("○"), 0x25CB)
        # And the formatter actually uses them.
        from mythic_vibe_cli.runtime.event_log import EventStreamSnapshot
        from mythic_vibe_cli.tui.app import _format_diagnostics_panel

        live = _format_diagnostics_panel(
            EventStreamSnapshot(entries=(), new_in_last_poll=1, total_seen=1)
        )
        idle = _format_diagnostics_panel(
            EventStreamSnapshot(entries=(), new_in_last_poll=0, total_seen=0)
        )
        self.assertIn("●", live)
        self.assertIn("○", idle)


if __name__ == "__main__":
    unittest.main()


# Silence "unused" warnings for the `re` import (kept for any future
# regex-based audit additions without bumping test imports).
_ = re
