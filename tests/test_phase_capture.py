"""Tests for PH-02 slice 2.3 workflow-phase capture commands.

Five new top-level argparse parents (``intent`` / ``constraints`` /
``architecture`` / ``plan`` / ``build``) each with a single
``capture`` subcommand that writes a Mythic Phase Record to
``mythic/checkins/<timestamp>-<phase>.md``.

The tests cover:
- happy path for each phase (file written, template fields populated)
- dry-run path (no file written)
- JSON output payload shape
- repeatable --note bullets
- confidence / risk / next-step propagation
- unknown-subcommand fall-through (parity with cmd_ai_dispatch /
  cmd_slash_dispatch error messages)
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli import app, commands
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR


CAPTURE_PHASES = ("intent", "constraints", "architecture", "plan", "build")


class PhaseCaptureHappyPathTests(unittest.TestCase):
    """Each of the five phases writes a markdown record with the
    canonical Mythic Phase Record template."""

    def test_each_phase_writes_record_with_template_fields(self) -> None:
        for phase in CAPTURE_PHASES:
            with tempfile.TemporaryDirectory() as tmp:
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    code = app.main(
                        [
                            phase,
                            "capture",
                            "--task",
                            f"Slice work — {phase}",
                            "--summary",
                            f"Captured {phase} for tests",
                            "--path",
                            tmp,
                            "--operator",
                            "runa",
                        ]
                    )
                self.assertEqual(code, SUCCESS, msg=f"{phase} capture returned non-success")
                checkins = list((Path(tmp) / "mythic" / "checkins").glob(f"*-{phase}.md"))
                self.assertEqual(len(checkins), 1, msg=f"Expected exactly one {phase} record")
                content = checkins[0].read_text(encoding="utf-8")
                self.assertIn("# Mythic Phase Record", content)
                self.assertIn(f"- Phase: {phase}", content)
                self.assertIn(f"- Task: Slice work — {phase}", content)
                self.assertIn("- Operator: runa", content)
                self.assertIn(f"Captured {phase} for tests", content)


class PhaseCaptureFilenameShapeTests(unittest.TestCase):
    def test_filename_uses_iso_timestamp_with_safe_separators(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                code = app.main(
                    [
                        "intent",
                        "capture",
                        "--task",
                        "filename-shape",
                        "--summary",
                        "verify timestamp shape",
                        "--path",
                        tmp,
                    ]
                )
            self.assertEqual(code, SUCCESS)
            checkins = list((Path(tmp) / "mythic" / "checkins").glob("*-intent.md"))
            self.assertEqual(len(checkins), 1)
            name = checkins[0].name
            # Pattern: 2026-04-29T18-30-00Z-intent.md (ISO date with T
            # separator, hyphenated time so Windows can write it).
            self.assertRegex(
                name,
                r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z-intent\.md$",
                msg=f"Filename {name!r} does not match the documented shape",
            )

    def test_filename_has_no_colons(self) -> None:
        """Colons are illegal in Windows file paths; the helper must strip them."""
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "plan",
                        "capture",
                        "--task",
                        "no-colons",
                        "--summary",
                        "x",
                        "--path",
                        tmp,
                    ]
                )
            checkins = list((Path(tmp) / "mythic" / "checkins").glob("*-plan.md"))
            self.assertEqual(len(checkins), 1)
            self.assertNotIn(":", checkins[0].name)


class PhaseCaptureDryRunTests(unittest.TestCase):
    def test_dry_run_writes_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    [
                        "constraints",
                        "capture",
                        "--task",
                        "dry-run-only",
                        "--summary",
                        "would write",
                        "--dry-run",
                        "--path",
                        tmp,
                    ]
                )
            self.assertEqual(code, SUCCESS)
            self.assertIn("Dry run", stdout.getvalue())
            checkins_dir = Path(tmp) / "mythic" / "checkins"
            self.assertFalse(checkins_dir.exists() and any(checkins_dir.iterdir()))

    def test_dry_run_json_payload_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = app.main(
                    [
                        "architecture",
                        "capture",
                        "--task",
                        "dry-run-json",
                        "--summary",
                        "shape",
                        "--dry-run",
                        "--json",
                        "--path",
                        tmp,
                    ]
                )
            self.assertEqual(code, SUCCESS)
            payload = json.loads(stdout.getvalue())
            self.assertTrue(payload["dry_run"])
            self.assertEqual(payload["command"], "architecture capture")
            self.assertEqual(payload["phase"], "architecture")
            self.assertEqual(payload["task"], "dry-run-json")
            self.assertIn("target", payload)
            self.assertIn("timestamp", payload)


class PhaseCaptureFieldRenderingTests(unittest.TestCase):
    def test_repeated_note_flags_render_as_bullet_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "intent",
                        "capture",
                        "--task",
                        "many-notes",
                        "--summary",
                        "multiple notes",
                        "--note",
                        "Keep alias compatibility",
                        "--note",
                        "No new dependencies",
                        "--note",
                        "Tests must stay green",
                        "--path",
                        tmp,
                    ]
                )
            content = (Path(tmp) / "mythic" / "checkins").glob("*-intent.md")
            text = next(iter(content)).read_text(encoding="utf-8")
            self.assertIn("- Keep alias compatibility", text)
            self.assertIn("- No new dependencies", text)
            self.assertIn("- Tests must stay green", text)

    def test_no_notes_renders_none_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "build",
                        "capture",
                        "--task",
                        "no-notes",
                        "--summary",
                        "naked",
                        "--path",
                        tmp,
                    ]
                )
            checkins = list((Path(tmp) / "mythic" / "checkins").glob("*-build.md"))
            text = checkins[0].read_text(encoding="utf-8")
            self.assertRegex(text, r"## Notes\n\n\(none\)")

    def test_confidence_risk_and_next_step_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                app.main(
                    [
                        "plan",
                        "capture",
                        "--task",
                        "metadata",
                        "--summary",
                        "carry through",
                        "--confidence",
                        "high",
                        "--risk",
                        "schema-migration",
                        "--next-step",
                        "open the build packet",
                        "--path",
                        tmp,
                    ]
                )
            text = next(iter((Path(tmp) / "mythic" / "checkins").glob("*-plan.md"))).read_text(
                encoding="utf-8"
            )
            self.assertIn("- Confidence: high", text)
            self.assertIn("- Risk: schema-migration", text)
            self.assertIn("open the build packet", text)


class PhaseCaptureMissingFieldTests(unittest.TestCase):
    def test_missing_task_argparse_blocks(self) -> None:
        # argparse enforces required=True before our handler runs, so a
        # missing --task exits with code 2.
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as cm, redirect_stderr(io.StringIO()):
                app.main(["intent", "capture", "--summary", "x", "--path", tmp])
            self.assertEqual(cm.exception.code, 2)

    def test_missing_summary_argparse_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as cm, redirect_stderr(io.StringIO()):
                app.main(["plan", "capture", "--task", "x", "--path", tmp])
            self.assertEqual(cm.exception.code, 2)

    def test_blank_task_after_strip_returns_user_error(self) -> None:
        """argparse accepts an empty string; the handler must reject it
        with a clear message instead of writing a record with a blank
        Task field."""
        ns = argparse.Namespace(
            path=".",
            intent_command="capture",
            task="   ",
            summary="non-empty",
            note=[],
            confidence="unspecified",
            risk="",
            next_step="",
            operator="",
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = commands.cmd_intent_dispatch(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        self.assertIn("requires --task", stderr.getvalue())


class PhaseCaptureDispatcherFallthroughTests(unittest.TestCase):
    """Each phase parent uses a per-phase dispatcher with a single
    `capture` subcommand today. Unknown subcommands must surface a
    visible error instead of silently exiting with code 2."""

    def test_intent_dispatcher_unknown_subcommand_emits_error(self) -> None:
        ns = argparse.Namespace(intent_command="bogus")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = commands.cmd_intent_dispatch(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        self.assertIn("Unknown intent subcommand", stderr.getvalue())

    def test_build_dispatcher_unknown_subcommand_emits_error(self) -> None:
        ns = argparse.Namespace(build_command="bogus")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = commands.cmd_build_dispatch(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        self.assertIn("Unknown build subcommand", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
