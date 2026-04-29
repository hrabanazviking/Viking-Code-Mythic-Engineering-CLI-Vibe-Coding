"""Tests for the diff review screen (PH-04 slice 4.5).

Three layers:

1. Pure parser tests (no Textual needed) — `parse_unified_diff` corner cases.
2. Pure session tests — `DiffReviewSession` state transitions and round-trip.
3. Headless TUI tests via `App.run_test()` — keybinding flow on a real screen.
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


from mythic_vibe_cli.tui.diff_review import (  # noqa: E402
    DIFF_REVIEW_BINDINGS_TEXT,
    DiffHunk,
    DiffLine,
    DiffReviewSession,
    _format_hunk_for_review,
    _format_review_progress,
    parse_unified_diff,
)


# ---- Parser ------------------------------------------------------------


class ParseUnifiedDiffTests(unittest.TestCase):
    def test_empty_input_returns_empty_list(self) -> None:
        self.assertEqual(parse_unified_diff(""), [])
        self.assertEqual(parse_unified_diff("   \n\n"), [])

    def test_non_diff_text_returns_empty_list(self) -> None:
        self.assertEqual(parse_unified_diff("hello world\nfoo bar"), [])

    def test_single_hunk_parses_with_kinds(self) -> None:
        diff_text = (
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -1,3 +1,4 @@\n"
            " def hello():\n"
            "-    return 1\n"
            "+    return 2\n"
            "+    # added line\n"
            " print(hello())\n"
        )
        hunks = parse_unified_diff(diff_text)
        self.assertEqual(len(hunks), 1)
        hunk = hunks[0]
        self.assertEqual(hunk.file_path, "foo.py")
        self.assertEqual(hunk.old_start, 1)
        self.assertEqual(hunk.old_count, 3)
        self.assertEqual(hunk.new_start, 1)
        self.assertEqual(hunk.new_count, 4)
        kinds = [line.kind for line in hunk.lines]
        self.assertEqual(
            kinds,
            ["context", "deletion", "addition", "addition", "context"],
        )
        # The leading marker character is stripped from the body text.
        self.assertEqual(hunk.lines[1].text, "    return 1")
        self.assertEqual(hunk.lines[2].text, "    return 2")

    def test_multi_file_diff_resets_active_file(self) -> None:
        diff_text = (
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
            "--- a/bar.py\n"
            "+++ b/bar.py\n"
            "@@ -10 +10 @@\n"
            "-baz\n"
            "+qux\n"
        )
        hunks = parse_unified_diff(diff_text)
        self.assertEqual(len(hunks), 2)
        self.assertEqual(hunks[0].file_path, "foo.py")
        self.assertEqual(hunks[1].file_path, "bar.py")
        # Both hunks default to count=1 when the header omits the count.
        self.assertEqual(hunks[0].old_count, 1)
        self.assertEqual(hunks[0].new_count, 1)
        self.assertEqual(hunks[1].old_start, 10)

    def test_hunk_header_without_explicit_count_defaults_to_one(self) -> None:
        diff_text = "+++ b/x.py\n@@ -5 +5 @@\n-a\n+b\n"
        hunks = parse_unified_diff(diff_text)
        self.assertEqual(len(hunks), 1)
        self.assertEqual(hunks[0].old_count, 1)
        self.assertEqual(hunks[0].new_count, 1)

    def test_mode_change_and_diff_git_lines_are_skipped(self) -> None:
        diff_text = (
            "diff --git a/foo b/foo\n"
            "old mode 100644\n"
            "new mode 100755\n"
            "--- a/foo\n"
            "+++ b/foo\n"
            "@@ -1 +1 @@\n"
            "-x\n"
            "+y\n"
        )
        hunks = parse_unified_diff(diff_text)
        self.assertEqual(len(hunks), 1)
        self.assertEqual(hunks[0].file_path, "foo")

    def test_no_newline_marker_renders_as_context(self) -> None:
        diff_text = (
            "+++ b/foo\n"
            "@@ -1,2 +1,2 @@\n"
            " a\n"
            "-b\n"
            "+c\n"
            "\\ No newline at end of file\n"
        )
        hunks = parse_unified_diff(diff_text)
        self.assertEqual(len(hunks), 1)
        kinds = [line.kind for line in hunks[0].lines]
        self.assertEqual(kinds, ["context", "deletion", "addition", "context"])

    def test_path_without_b_prefix_is_accepted(self) -> None:
        diff_text = "+++ path/to/file.py\n@@ -1 +1 @@\n-a\n+b\n"
        hunks = parse_unified_diff(diff_text)
        self.assertEqual(len(hunks), 1)
        self.assertEqual(hunks[0].file_path, "path/to/file.py")

    def test_to_dict_round_trip(self) -> None:
        diff_text = "+++ b/x\n@@ -1 +1 @@\n-old\n+new\n"
        hunks = parse_unified_diff(diff_text)
        payload = hunks[0].to_dict()
        for key in {
            "file_path",
            "header",
            "old_start",
            "old_count",
            "new_start",
            "new_count",
            "lines",
        }:
            self.assertIn(key, payload)
        self.assertEqual(payload["lines"][0], {"kind": "deletion", "text": "old"})
        self.assertEqual(payload["lines"][1], {"kind": "addition", "text": "new"})


# ---- Session -----------------------------------------------------------


def _hunk(file_path: str = "foo.py") -> DiffHunk:
    return DiffHunk(
        file_path=file_path,
        header="@@ -1 +1 @@",
        old_start=1,
        old_count=1,
        new_start=1,
        new_count=1,
        lines=(DiffLine(kind="addition", text="x"),),
    )


class DiffReviewSessionTests(unittest.TestCase):
    def test_post_init_seeds_pending_decisions(self) -> None:
        session = DiffReviewSession(hunks=(_hunk("a"), _hunk("b")))
        self.assertEqual(session.decisions, ["pending", "pending"])
        self.assertEqual(session.total, 2)
        self.assertEqual(session.decided_count, 0)
        self.assertFalse(session.is_complete)
        self.assertEqual(session.current_hunk, session.hunks[0])

    def test_decisions_length_must_match_hunks(self) -> None:
        with self.assertRaises(ValueError):
            DiffReviewSession(hunks=(_hunk(),), decisions=["pending", "pending"])

    def test_record_decision_sets_current_index(self) -> None:
        session = DiffReviewSession(hunks=(_hunk("a"), _hunk("b")))
        session.record_decision("accepted")
        self.assertEqual(session.decisions, ["accepted", "pending"])
        self.assertEqual(session.decided_count, 1)

    def test_record_decision_rejects_unknown_value(self) -> None:
        session = DiffReviewSession(hunks=(_hunk(),))
        with self.assertRaises(ValueError):
            session.record_decision("bogus")  # type: ignore[arg-type]

    def test_record_decision_on_empty_session_is_noop(self) -> None:
        session = DiffReviewSession(hunks=())
        session.record_decision("accepted")  # must not raise
        self.assertEqual(session.decisions, [])

    def test_advance_and_retreat_clamp_at_ends(self) -> None:
        session = DiffReviewSession(hunks=(_hunk("a"), _hunk("b")))
        self.assertTrue(session.advance())
        self.assertEqual(session.current_index, 1)
        self.assertFalse(session.advance())  # already last
        self.assertEqual(session.current_index, 1)
        self.assertTrue(session.retreat())
        self.assertEqual(session.current_index, 0)
        self.assertFalse(session.retreat())  # already first

    def test_is_complete_when_all_decisions_made(self) -> None:
        session = DiffReviewSession(hunks=(_hunk("a"), _hunk("b")))
        session.record_decision("accepted")
        session.advance()
        session.record_decision("rejected")
        self.assertTrue(session.is_complete)

    def test_accepted_hunks_returns_only_accepted_in_order(self) -> None:
        session = DiffReviewSession(
            hunks=(_hunk("a"), _hunk("b"), _hunk("c")),
        )
        session.record_decision("accepted")
        session.advance()
        session.record_decision("rejected")
        session.advance()
        session.record_decision("accepted")
        accepted = session.accepted_hunks()
        self.assertEqual([h.file_path for h in accepted], ["a", "c"])

    def test_to_dict_round_trip(self) -> None:
        session = DiffReviewSession(hunks=(_hunk("a"), _hunk("b")))
        session.record_decision("accepted")
        session.advance()
        payload = session.to_dict()
        for key in {
            "hunks",
            "decisions",
            "current_index",
            "decided_count",
            "is_complete",
        }:
            self.assertIn(key, payload)
        self.assertEqual(payload["decisions"], ["accepted", "pending"])
        self.assertEqual(payload["current_index"], 1)
        self.assertEqual(payload["decided_count"], 1)
        self.assertFalse(payload["is_complete"])

    def test_current_hunk_is_none_when_no_hunks(self) -> None:
        session = DiffReviewSession(hunks=())
        self.assertIsNone(session.current_hunk)
        self.assertTrue(session.is_complete)  # empty trivially complete


# ---- Formatters --------------------------------------------------------


class FormatterTests(unittest.TestCase):
    def test_format_hunk_for_review_includes_path_and_colour_tags(self) -> None:
        hunk = DiffHunk(
            file_path="src/x.py",
            header="@@ -1,2 +1,3 @@",
            old_start=1,
            old_count=2,
            new_start=1,
            new_count=3,
            lines=(
                DiffLine(kind="context", text="ctx"),
                DiffLine(kind="deletion", text="old"),
                DiffLine(kind="addition", text="new"),
            ),
        )
        rendered = _format_hunk_for_review(hunk)
        self.assertIn("src/x.py", rendered)
        self.assertIn("@@ -1,2 +1,3 @@", rendered)
        self.assertIn("[green]+ new[/green]", rendered)
        self.assertIn("[red]- old[/red]", rendered)

    def test_format_review_progress_counts_each_decision(self) -> None:
        session = DiffReviewSession(
            hunks=(_hunk("a"), _hunk("b"), _hunk("c"), _hunk("d")),
        )
        session.record_decision("accepted")
        session.advance()
        session.record_decision("rejected")
        session.advance()
        session.record_decision("skipped")
        rendered = _format_review_progress(session)
        self.assertIn("1 accepted", rendered)
        self.assertIn("1 rejected", rendered)
        self.assertIn("1 skipped", rendered)
        self.assertIn("1 pending", rendered)

    def test_format_review_progress_empty_session(self) -> None:
        rendered = _format_review_progress(DiffReviewSession(hunks=()))
        self.assertIn("No hunks", rendered)


# ---- Headless TUI ------------------------------------------------------


@unittest.skipIf(textual_unavailable, "textual not installed")
class DiffReviewScreenTests(unittest.TestCase):
    def _make_session(self) -> DiffReviewSession:
        diff_text = (
            "+++ b/foo.py\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
            "--- a/bar.py\n"
            "+++ b/bar.py\n"
            "@@ -2 +2 @@\n"
            "-aa\n"
            "+bb\n"
        )
        return DiffReviewSession(hunks=tuple(parse_unified_diff(diff_text)))

    def test_screen_renders_first_hunk_on_mount(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.diff_review import DiffReviewScreen

        session = self._make_session()

        async def run_test() -> tuple[str, str]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    app.push_screen(DiffReviewScreen(session))
                    await pilot.pause()
                    header = app.screen.query_one("#diff-review-header")
                    body = app.screen.query_one("#diff-review-hunk")
                    return str(header.render()), str(body.render())

        header_render, body_render = asyncio.run(run_test())
        self.assertIn("Hunk 1 / 2", header_render)
        self.assertIn("foo.py", body_render)

    def test_accept_advances_and_records_decision(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.diff_review import DiffReviewScreen

        session = self._make_session()

        async def run_test() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    app.push_screen(DiffReviewScreen(session))
                    await pilot.pause()
                    await pilot.press("a")
                    await pilot.pause()

        asyncio.run(run_test())
        self.assertEqual(session.decisions[0], "accepted")
        self.assertEqual(session.current_index, 1)

    def test_reject_skip_and_navigation_keys(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.diff_review import DiffReviewScreen

        # Build a 4-hunk session so we can exercise r / s / j / k.
        diff_text = (
            "+++ b/a\n@@ -1 +1 @@\n-1\n+2\n"
            "--- a/b\n+++ b/b\n@@ -1 +1 @@\n-3\n+4\n"
            "--- a/c\n+++ b/c\n@@ -1 +1 @@\n-5\n+6\n"
            "--- a/d\n+++ b/d\n@@ -1 +1 @@\n-7\n+8\n"
        )
        session = DiffReviewSession(hunks=tuple(parse_unified_diff(diff_text)))

        async def run_test() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    app.push_screen(DiffReviewScreen(session))
                    await pilot.pause()
                    await pilot.press("r")  # reject hunk 0, advance to 1
                    await pilot.pause()
                    await pilot.press("s")  # skip hunk 1, advance to 2
                    await pilot.pause()
                    await pilot.press("j")  # advance to 3 without recording
                    await pilot.pause()
                    await pilot.press("k")  # back to 2
                    await pilot.pause()

        asyncio.run(run_test())
        self.assertEqual(session.decisions[0], "rejected")
        self.assertEqual(session.decisions[1], "skipped")
        self.assertEqual(session.decisions[2], "pending")
        self.assertEqual(session.current_index, 2)

    def test_help_toggle_shows_bindings_text(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.diff_review import DiffReviewScreen

        session = self._make_session()

        async def run_test() -> tuple[str, str]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    app.push_screen(DiffReviewScreen(session))
                    await pilot.pause()
                    before = str(app.screen.query_one("#diff-review-help").render())
                    await pilot.press("question_mark")
                    await pilot.pause()
                    after = str(app.screen.query_one("#diff-review-help").render())
                    return before, after

        before, after = asyncio.run(run_test())
        self.assertNotIn("accept", before.lower())
        # The help line uses the canonical bindings constant.
        self.assertIn("accept", after.lower())
        self.assertIn("a accept", DIFF_REVIEW_BINDINGS_TEXT)


if __name__ == "__main__":
    unittest.main()
