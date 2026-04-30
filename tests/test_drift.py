"""Tests for the drift detector (PH-13 slice 13.1).

Three layers:

1. Pure-data tests on `DriftFinding` round-trip.
2. Per-detector tests against synthetic project trees in tempdirs.
3. CLI integration: ``mythic-vibe drift`` text + JSON output;
   `/drift` slash entry; TUI runner allow-list.
"""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path


from mythic_vibe_cli.drift import (  # noqa: E402
    DriftFinding,
    detect_superseded_decisions,
    detect_undocumented_handlers,
    detect_undocumented_modules,
    render_findings_text,
    scan_for_drift,
    summarize_findings,
    to_payload,
)


# ---- Helpers -----------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


# ---- Layer 1: DriftFinding ---------------------------------------------


class DriftFindingTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        finding = DriftFinding(
            category="undocumented_handler",
            severity="warning",
            path="x/y.py:10",
            description="missing docstring",
        )
        payload = finding.to_dict()
        self.assertEqual(payload["category"], "undocumented_handler")
        self.assertEqual(payload["severity"], "warning")
        self.assertEqual(payload["path"], "x/y.py:10")
        self.assertEqual(payload["description"], "missing docstring")

    def test_finding_is_immutable(self) -> None:
        finding = DriftFinding(
            category="undocumented_module",
            severity="info",
            path="x.py",
            description="",
        )
        with self.assertRaises(Exception):
            finding.path = "y.py"  # type: ignore[misc]

    def test_summarize_counts_each_severity(self) -> None:
        findings = [
            DriftFinding("undocumented_handler", "warning", "a", ""),
            DriftFinding("undocumented_handler", "warning", "b", ""),
            DriftFinding("undocumented_module", "info", "c", ""),
        ]
        summary = summarize_findings(findings)
        self.assertEqual(summary["warning"], 2)
        self.assertEqual(summary["info"], 1)
        self.assertEqual(summary["error"], 0)


# ---- Layer 2: Per-detector --------------------------------------------


class DetectUndocumentedHandlerTests(unittest.TestCase):
    def test_handler_without_docstring_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "mythic_vibe_cli" / "commands.py",
                """
                def cmd_foo(args):
                    return 0

                def cmd_bar(args):
                    \"\"\"Has a docstring.\"\"\"
                    return 0
                """,
            )
            findings = detect_undocumented_handlers(root)

        names = [f.description for f in findings]
        self.assertEqual(len(findings), 1)
        self.assertIn("cmd_foo", names[0])
        self.assertEqual(findings[0].severity, "warning")
        self.assertIn("commands.py:", findings[0].path)

    def test_non_handler_function_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "mythic_vibe_cli" / "commands.py",
                """
                def helper():
                    return 0

                def cmd_bar(args):
                    \"\"\"Has docstring.\"\"\"
                    return 0
                """,
            )
            self.assertEqual(detect_undocumented_handlers(root), [])

    def test_missing_commands_file_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(detect_undocumented_handlers(Path(tmp)), [])

    def test_syntax_error_in_commands_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "mythic_vibe_cli" / "commands.py", "def cmd_broken(args:\n")
            self.assertEqual(detect_undocumented_handlers(root), [])


class DetectUndocumentedModuleTests(unittest.TestCase):
    def test_module_with_docstring_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "mythic_vibe_cli" / "subpkg" / "ok.py",
                '"""This is a documented module."""\n\ndef hello():\n    return "hi"\n',
            )
            self.assertEqual(detect_undocumented_modules(root), [])

    def test_module_without_docstring_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "mythic_vibe_cli" / "noisy.py",
                """
                from __future__ import annotations
                import os

                def f():
                    return 1
                """,
            )
            findings = detect_undocumented_modules(root)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].category, "undocumented_module")
            self.assertEqual(findings[0].severity, "info")
            self.assertEqual(findings[0].path, "mythic_vibe_cli/noisy.py")

    def test_init_files_are_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "mythic_vibe_cli" / "__init__.py", "from .sub import *\n")
            self.assertEqual(detect_undocumented_modules(root), [])

    def test_pure_imports_then_blank_is_clean(self) -> None:
        """A module whose entire body is imports has no real
        statements to anchor a docstring on; the detector treats it
        as clean."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "mythic_vibe_cli" / "reexport.py",
                "from __future__ import annotations\nimport sys\n",
            )
            self.assertEqual(detect_undocumented_modules(root), [])


class DetectSupersededDecisionTests(unittest.TestCase):
    def _build(self, root: Path) -> None:
        _write(
            root / "docs" / "decisions" / "0001-old-pattern.md",
            """
            ---
            status: superseded
            ---

            # 0001 — Old pattern

            Replaced by 0002.
            """,
        )
        _write(
            root / "docs" / "decisions" / "0002-new-pattern.md",
            """
            ---
            status: accepted
            ---

            # 0002 — New pattern

            Supersedes 0001-old-pattern.md.
            """,
        )

    def test_superseded_referenced_only_in_other_adr_is_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._build(root)
            findings = detect_superseded_decisions(root)
        # 0001 is referenced from 0002 inside docs/decisions/, which
        # is normal ADR cross-reference — not drift.
        self.assertEqual(findings, [])

    def test_superseded_referenced_from_other_md_is_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._build(root)
            _write(
                root / "README.md",
                "See 0001-old-pattern.md for the canonical approach.\n",
            )
            findings = detect_superseded_decisions(root)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].category, "superseded_decision_referenced")
            self.assertEqual(findings[0].severity, "warning")
            self.assertIn("0001-old-pattern.md", findings[0].path)
            self.assertIn("README.md", findings[0].description)

    def test_no_decisions_dir_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(detect_superseded_decisions(Path(tmp)), [])

    def test_status_deprecated_is_treated_like_superseded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "mythic" / "decisions" / "0010-old.md",
                "---\nstatus: deprecated\n---\n\n# 0010\n",
            )
            _write(root / "ROADMAP.md", "Old plan: see 0010-old.md.\n")
            findings = detect_superseded_decisions(root)
            self.assertEqual(len(findings), 1)


# ---- Aggregator -------------------------------------------------------


class ScanForDriftTests(unittest.TestCase):
    def test_aggregator_unions_detector_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "mythic_vibe_cli" / "commands.py",
                "def cmd_foo(args):\n    return 0\n",
            )
            _write(
                root / "mythic_vibe_cli" / "noisy.py",
                "from __future__ import annotations\n\ndef f():\n    return 1\n",
            )
            findings = scan_for_drift(root)

        categories = {f.category for f in findings}
        self.assertIn("undocumented_handler", categories)
        self.assertIn("undocumented_module", categories)

    def test_clean_project_returns_empty_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "mythic_vibe_cli" / "ok.py",
                '"""Clean module."""\n',
            )
            self.assertEqual(scan_for_drift(root), [])


# ---- Renderers ---------------------------------------------------------


class RendererTests(unittest.TestCase):
    def test_text_renderer_handles_empty(self) -> None:
        rendered = render_findings_text([])
        self.assertIn("no findings", rendered.lower())

    def test_text_renderer_lists_each_finding(self) -> None:
        findings = [
            DriftFinding("undocumented_handler", "warning", "a.py:1", "missing"),
        ]
        rendered = render_findings_text(findings)
        self.assertIn("undocumented_handler", rendered)
        self.assertIn("a.py:1", rendered)
        self.assertIn("missing", rendered)

    def test_payload_envelope(self) -> None:
        findings = [
            DriftFinding("undocumented_handler", "warning", "a", ""),
            DriftFinding("undocumented_module", "info", "b", ""),
        ]
        payload = to_payload(findings)
        self.assertEqual(payload["command"], "drift")
        self.assertEqual(len(payload["findings"]), 2)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["summary"]["warning"], 1)
        self.assertEqual(payload["summary"]["info"], 1)


# ---- CLI integration --------------------------------------------------


class CmdDriftTests(unittest.TestCase):
    def test_cmd_drift_text_output(self) -> None:
        from mythic_vibe_cli.commands import cmd_drift

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "mythic_vibe_cli" / "commands.py",
                "def cmd_foo(args):\n    return 0\n",
            )
            args = argparse.Namespace(path=str(root), json=False)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_drift(args)
        self.assertEqual(exit_code, 0)
        self.assertIn("undocumented_handler", buf.getvalue())

    def test_cmd_drift_json_output(self) -> None:
        from mythic_vibe_cli.commands import cmd_drift

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "mythic_vibe_cli" / "commands.py",
                # Module-level docstring keeps the module-detector quiet
                # so this test isolates the handler-detector path.
                '"""Synthetic commands module."""\n\n'
                "def cmd_bar(args):\n    return 0\n",
            )
            args = argparse.Namespace(path=str(root), json=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_drift(args)
        self.assertEqual(exit_code, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["command"], "drift")
        self.assertEqual(len(payload["findings"]), 1)
        self.assertEqual(
            payload["findings"][0]["category"], "undocumented_handler"
        )

    def test_drift_handler_is_registered(self) -> None:
        from mythic_vibe_cli.commands import COMMAND_HANDLERS, cmd_drift

        self.assertIs(COMMAND_HANDLERS["drift"], cmd_drift)

    def test_slash_catalog_contains_drift(self) -> None:
        from mythic_vibe_cli.runtime.slash_commands import BUILTIN_SLASH_COMMANDS

        names = {entry.name for entry in BUILTIN_SLASH_COMMANDS}
        self.assertIn("drift", names)

    def test_tui_runner_forwards_path_for_drift(self) -> None:
        from mythic_vibe_cli.tui.runner import command_for_builtin

        with tempfile.TemporaryDirectory() as tmp:
            spec = command_for_builtin("drift", project_root=Path(tmp))
        self.assertIn("--path", spec.argv)
        self.assertIn(str(Path(tmp)), spec.argv)
        self.assertEqual(spec.label, "/drift")

    def test_argparse_accepts_drift_subcommand(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["drift", "--json"])
        self.assertEqual(ns.command, "drift")
        self.assertTrue(ns.json)


# ---- Slice 13.2: doctor integration ----------------------------------


class DoctorDriftIntegrationTests(unittest.TestCase):
    """Slice 13.2: cmd_doctor calls scan_for_drift and surfaces the
    findings under a ``drift`` key in JSON output and a Drift-findings
    section in text output."""

    def _init_mythic_project(self, root: Path) -> None:
        """Bootstrap the minimum scaffold cmd_doctor expects.

        Touches just the few status / structure files MythicWorkflow's
        doctor_report sanity-checks, so the doctor pass itself
        doesn't dominate the test signal."""
        for relpath in (
            "mythic/status.json",
            "mythic/plan.md",
            "mythic/loop.md",
            "tasks/current_GOALS.md",
            "docs/DEVLOG.md",
            "SYSTEM_VISION.md",
        ):
            target = root / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            if relpath.endswith(".json"):
                target.write_text("{}\n", encoding="utf-8")
            else:
                target.write_text(f"# {target.name}\n", encoding="utf-8")

    def test_doctor_json_payload_includes_drift_section(self) -> None:
        from mythic_vibe_cli.commands import cmd_doctor

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_mythic_project(root)
            _write(
                root / "mythic_vibe_cli" / "commands.py",
                '"""Synthetic."""\n\ndef cmd_x(args):\n    return 0\n',
            )
            args = argparse.Namespace(
                path=str(root),
                json=True,
                repo_boundary=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_doctor(args)
        payload = json.loads(buf.getvalue())
        self.assertIn("drift", payload)
        self.assertEqual(len(payload["drift"]), 1)
        self.assertEqual(
            payload["drift"][0]["category"], "undocumented_handler"
        )

    def test_doctor_text_renders_drift_findings_count(self) -> None:
        from mythic_vibe_cli.commands import cmd_doctor

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_mythic_project(root)
            _write(
                root / "mythic_vibe_cli" / "commands.py",
                '"""Synthetic."""\n\ndef cmd_y(args):\n    return 0\n',
            )
            args = argparse.Namespace(
                path=str(root),
                json=False,
                repo_boundary=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_doctor(args)
        rendered = buf.getvalue()
        self.assertIn("Drift findings: 1", rendered)
        self.assertIn("undocumented_handler", rendered)

    def test_doctor_text_says_none_when_clean(self) -> None:
        from mythic_vibe_cli.commands import cmd_doctor

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_mythic_project(root)
            # Project has no mythic_vibe_cli/ subdir → drift detectors
            # find nothing → cmd_doctor reports the empty-case message.
            args = argparse.Namespace(
                path=str(root),
                json=False,
                repo_boundary=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_doctor(args)
        self.assertIn("Drift findings: none", buf.getvalue())


# ---- Slice 13.3: heal v2 reconciliation packet -----------------------


class HealReconciliationPacketTests(unittest.TestCase):
    """Slice 13.3: cmd_heal generates a Scribe-targeted markdown +
    JSON packet from current drift findings, additive-only and
    operator-gated (--dry-run honoured)."""

    def test_packet_contents_group_findings_by_category(self) -> None:
        from mythic_vibe_cli.commands import cmd_heal

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(
                root / "mythic_vibe_cli" / "commands.py",
                '"""Synthetic."""\n\n'
                "def cmd_a(args):\n    return 0\n\n"
                "def cmd_b(args):\n    return 0\n",
            )
            _write(
                root / "mythic_vibe_cli" / "noisy.py",
                "from __future__ import annotations\n\ndef f():\n    return 1\n",
            )
            args = argparse.Namespace(
                path=str(root),
                failing_test=None,
                json=True,
                dry_run=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_heal(args)
            payload = json.loads(buf.getvalue())

            self.assertEqual(payload["command"], "heal")
            self.assertTrue(payload["written"])
            # Two handler findings + one module finding => 3 in summary.
            self.assertEqual(payload["summary"]["warning"], 2)
            self.assertEqual(payload["summary"]["info"], 1)
            # Both files exist on disk.
            md_path = Path(payload["markdown_path"])
            json_path = Path(payload["json_path"])
            self.assertTrue(md_path.is_file())
            self.assertTrue(json_path.is_file())
            # Markdown content groups by category and includes a Proposal.
            text = md_path.read_text(encoding="utf-8")
            self.assertIn("undocumented_handler", text)
            self.assertIn("undocumented_module", text)
            self.assertIn("Proposal", text)
            self.assertIn("Additive only", text)

    def test_dry_run_does_not_write_files(self) -> None:
        from mythic_vibe_cli.commands import cmd_heal

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = argparse.Namespace(
                path=str(root),
                failing_test=None,
                json=True,
                dry_run=True,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_heal(args)
            payload = json.loads(buf.getvalue())

        self.assertTrue(payload.get("dry_run"))
        self.assertFalse(payload.get("written"))
        self.assertFalse((Path(tmp) / "mythic" / "heal").exists())

    def test_clean_project_still_writes_an_informational_packet(self) -> None:
        """A project with no drift findings should still produce a
        readable packet — useful as a baseline / heartbeat."""
        from mythic_vibe_cli.commands import cmd_heal

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "mythic_vibe_cli" / "ok.py", '"""Clean."""\n')
            args = argparse.Namespace(
                path=str(root),
                failing_test="",
                json=True,
                dry_run=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_heal(args)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["summary"]["warning"], 0)
            self.assertEqual(payload["summary"]["info"], 0)
            text = Path(payload["markdown_path"]).read_text(encoding="utf-8")
            self.assertIn("No drift detected", text)


# ---- Slice 13.4: TUI drift panel -------------------------------------


textual_unavailable = False
try:
    import textual  # noqa: F401
except ImportError:
    textual_unavailable = True


class DriftPanelFormatTests(unittest.TestCase):
    """Pure formatter — `_format_drift_panel` Rich-tag rendering with
    severity colour-codes alongside the severity word (slice 4.9
    accessibility discipline: never colour without text fallback)."""

    def test_empty_findings_render_no_drift_message(self) -> None:
        from mythic_vibe_cli.tui.drift_panel import _format_drift_panel

        rendered = _format_drift_panel([])
        self.assertIn("No drift detected", rendered)
        # The pulse counter still renders 0/0/0 in monochrome.
        self.assertIn("0 error", rendered)
        self.assertIn("0 warning", rendered)
        self.assertIn("0 info", rendered)

    def test_findings_render_with_severity_word_and_tag(self) -> None:
        from mythic_vibe_cli.tui.drift_panel import _format_drift_panel

        findings = [
            DriftFinding("undocumented_handler", "warning", "x.py:1", "missing"),
            DriftFinding("undocumented_module", "info", "y.py", "no docstring"),
        ]
        rendered = _format_drift_panel(findings)
        # Both severity words present in monochrome.
        self.assertIn("warning", rendered.lower())
        self.assertIn("info", rendered.lower())
        # Colour tags wrap the severity word.
        self.assertIn("[yellow]warning[/yellow]", rendered)
        self.assertIn("[cyan]info[/cyan]", rendered)


@unittest.skipIf(textual_unavailable, "textual not installed")
class DriftScreenIntegrationTests(unittest.TestCase):
    def test_drift_screen_mounts_and_shows_findings(self) -> None:
        import asyncio

        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.drift_panel import DriftScreen

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _write(
                    root / "mythic_vibe_cli" / "commands.py",
                    '"""Synthetic."""\n\n'
                    "def cmd_a(args):\n    return 0\n",
                )
                app = MythicTuiApp(root)
                async with app.run_test() as pilot:
                    await pilot.pause()
                    app.push_screen(DriftScreen(root))
                    await pilot.pause()
                    card = app.screen.query_one("#drift-card")
                    return str(card.render())

        rendered = asyncio.run(run_test())
        self.assertIn("undocumented_handler", rendered)
        self.assertIn("warning", rendered.lower())

    def test_status_screen_d_key_pushes_drift_screen(self) -> None:
        import asyncio

        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.drift_panel import DriftScreen

        async def run_test() -> bool:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    await pilot.press("d")
                    await pilot.pause()
                    return isinstance(app.screen, DriftScreen)

        self.assertTrue(asyncio.run(run_test()))

    def test_drift_screen_has_uniform_keymap(self) -> None:
        """DriftScreen must register the slice 4.7 / 4.8 uniform keys
        (`?` Help, `t` Theme, `r` Refresh, `escape`/`q` Back)."""
        from mythic_vibe_cli.tui.drift_panel import DriftScreen

        keys = {b.key for b in DriftScreen.BINDINGS}
        for required in {"question_mark", "t", "r", "q", "escape"}:
            self.assertIn(required, keys, f"DriftScreen missing `{required}`")


if __name__ == "__main__":
    unittest.main()
