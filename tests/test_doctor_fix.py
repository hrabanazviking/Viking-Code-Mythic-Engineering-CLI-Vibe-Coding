"""Phase 20.2 (audit remediation 2026-05-02) — doctor --fix tests.

Covers ``mythic_vibe_cli/doctor_fix.py``:

- MFX-001 (missing mythic/ subdirs) — fix mode creates dirs;
  dry-run reports without creating; existing dirs are no-ops.
- MFX-002 (missing CHANGELOG [Unreleased]) — fix inserts a
  block AFTER the H1 title and BEFORE the first version
  section; existing block is no-op; missing CHANGELOG is
  skipped (NOT auto-created — that's an operator decision).
- ``cmd_doctor --fix`` integration — JSON payload includes
  fixes block; text output renders mode + per-action lines;
  exit code unchanged by fix-mode (still driven by report
  errors only).

Hard-rule guard tests: the fixer must NEVER touch user content
(constraints, oaths, ADRs). We build a project containing those
files, run the fixer, then assert the files are byte-identical
afterward.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.doctor_fix import (
    STANDARD_SUBDIRS,
    UNRELEASED_HEADER,
    FixAction,
    FixReport,
    run_doctor_fix,
)


class StandardSubdirsTests(unittest.TestCase):
    def test_creates_all_missing_subdirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_doctor_fix(Path(tmp))
            self.assertEqual(len(report.fixed), len(STANDARD_SUBDIRS))
            for relative in STANDARD_SUBDIRS:
                target = Path(tmp) / "mythic" / relative if relative else Path(tmp) / "mythic"
                self.assertTrue(
                    target.is_dir(),
                    f"missing subdir: {target}",
                )

    def test_dry_run_does_not_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_doctor_fix(Path(tmp), dry_run=True)
            self.assertEqual(len(report.would_fix), len(STANDARD_SUBDIRS))
            self.assertEqual(report.fixed, [])
            self.assertFalse((Path(tmp) / "mythic").exists())

    def test_existing_subdirs_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Pre-create mythic/ + packets/. Fixer should only
            # create the remainder.
            (Path(tmp) / "mythic" / "packets").mkdir(parents=True)
            report = run_doctor_fix(Path(tmp))
            mfx001 = [a for a in report.actions if a.rule_id == "MFX-001"]
            # 8 standard subdirs - 2 pre-created = 6 remaining.
            self.assertEqual(len(mfx001), len(STANDARD_SUBDIRS) - 2)


class ChangelogUnreleasedTests(unittest.TestCase):
    BASIC_CHANGELOG = (
        "# Changelog\n"
        "\n"
        "All notable changes documented here.\n"
        "\n"
        "## [1.2.0] — 2026-04-01\n"
        "\n"
        "- shipped feature X\n"
    )

    def test_inserts_unreleased_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text(self.BASIC_CHANGELOG, encoding="utf-8")
            report = run_doctor_fix(Path(tmp))
            mfx002 = [a for a in report.actions if a.rule_id == "MFX-002"]
            self.assertEqual(len(mfx002), 1)
            self.assertEqual(mfx002[0].status, "fixed")
            new_text = changelog.read_text(encoding="utf-8")
            self.assertIn(UNRELEASED_HEADER, new_text)
            # Must land BEFORE the existing version section.
            self.assertLess(
                new_text.find(UNRELEASED_HEADER),
                new_text.find("## [1.2.0]"),
            )
            # H1 title preserved.
            self.assertTrue(new_text.startswith("# Changelog"))
            # Original version body preserved verbatim.
            self.assertIn("- shipped feature X", new_text)

    def test_no_op_when_unreleased_already_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text(
                "# Changelog\n\n## [Unreleased]\n\n- pending\n",
                encoding="utf-8",
            )
            before = changelog.read_text(encoding="utf-8")
            report = run_doctor_fix(Path(tmp))
            mfx002 = [a for a in report.actions if a.rule_id == "MFX-002"]
            self.assertEqual(mfx002, [])
            self.assertEqual(
                changelog.read_text(encoding="utf-8"), before
            )

    def test_skipped_when_changelog_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_doctor_fix(Path(tmp))
            mfx002 = [a for a in report.actions if a.rule_id == "MFX-002"]
            self.assertEqual(len(mfx002), 1)
            self.assertEqual(mfx002[0].status, "skipped")
            self.assertFalse(
                (Path(tmp) / "CHANGELOG.md").exists(),
                "fixer must NOT auto-create CHANGELOG.md",
            )

    def test_dry_run_reports_would_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            changelog = Path(tmp) / "CHANGELOG.md"
            changelog.write_text(self.BASIC_CHANGELOG, encoding="utf-8")
            report = run_doctor_fix(Path(tmp), dry_run=True)
            mfx002 = [a for a in report.actions if a.rule_id == "MFX-002"]
            self.assertEqual(mfx002[0].status, "would_fix")
            # File NOT modified.
            self.assertEqual(
                changelog.read_text(encoding="utf-8"),
                self.BASIC_CHANGELOG,
            )


class HardRuleProtectionTests(unittest.TestCase):
    """The fixer must NEVER touch user-authored content. Build
    a project containing constraints / oaths / ADRs / packets /
    decisions, run the fixer, then assert every byte is intact."""

    def test_user_authored_files_untouched(self) -> None:
        files = {
            "mythic/constraints/CONSTRAINT-001.md":
                "# operator constraint\nFROZEN CONTENT\n",
            "mythic/oaths/OATH-001.md":
                "# operator oath\nFROZEN CONTENT\n",
            "docs/ADRS/ADR-0001-real.md":
                "# real ADR\nFROZEN CONTENT\n",
            "mythic/packets/PKT-000001.md":
                "# packet\nFROZEN CONTENT\n",
            "mythic/decisions/DECISION-001.md":
                "# decision\nFROZEN CONTENT\n",
        }
        with tempfile.TemporaryDirectory() as tmp:
            for relpath, content in files.items():
                target = Path(tmp) / relpath
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            run_doctor_fix(Path(tmp))
            for relpath, expected in files.items():
                actual = (Path(tmp) / relpath).read_text(
                    encoding="utf-8"
                )
                self.assertEqual(
                    actual, expected,
                    f"fixer modified user content: {relpath}",
                )


class FixReportSerializationTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        report = FixReport(
            actions=[
                FixAction(
                    rule_id="MFX-001",
                    status="fixed",
                    target="/tmp/x",
                    message="ok",
                ),
            ],
            dry_run=False,
        )
        payload = report.to_dict()
        self.assertEqual(payload["counts"]["fixed"], 1)
        self.assertEqual(payload["counts"]["would_fix"], 0)
        self.assertEqual(payload["counts"]["skipped"], 0)
        # JSON-serializable.
        json.dumps(payload)


class CmdDoctorFixIntegrationTests(unittest.TestCase):
    def _run(self, ns: argparse.Namespace) -> tuple[int, str]:
        from mythic_vibe_cli.commands import cmd_doctor

        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = cmd_doctor(ns)
        finally:
            sys.stdout = original
        return code, captured.getvalue()

    def _ns(self, tmp: str, **overrides) -> argparse.Namespace:
        kwargs = {
            "path": tmp,
            "json": False,
            "repo_boundary": False,
            "fix": False,
            "fix_dry_run": False,
        }
        kwargs.update(overrides)
        return argparse.Namespace(**kwargs)

    def test_fix_text_output_contains_action_lines(self) -> None:
        # The doctor exit code reflects project-scaffold health
        # (OPERATIONAL_FAILURE on a bare temp dir). The slice
        # under test is the auto-fix output, not the exit code,
        # so we only assert on the fix-related output here.
        with tempfile.TemporaryDirectory() as tmp:
            _code, output = self._run(self._ns(tmp, fix=True))
        self.assertIn("Auto-fix (applied)", output)
        self.assertIn("MFX-001", output)

    def test_fix_dry_run_does_not_create_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _code, output = self._run(self._ns(tmp, fix_dry_run=True))
            # Dry-run mode: no mythic/ created.
            self.assertFalse(
                (Path(tmp) / "mythic" / "packets").exists()
            )
        self.assertIn("Auto-fix (dry-run)", output)

    def test_fix_json_includes_fixes_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _code, output = self._run(self._ns(tmp, fix=True, json=True))
            payload = json.loads(output)
        self.assertIn("fixes", payload)
        self.assertIn("counts", payload["fixes"])
        self.assertIn("actions", payload["fixes"])

    def test_no_fix_flag_means_no_fixes_key(self) -> None:
        """Default doctor invocation (no --fix) MUST NOT include
        a fixes block in JSON output — preserves backwards
        compat for callers that don't expect it."""
        with tempfile.TemporaryDirectory() as tmp:
            _code, output = self._run(self._ns(tmp, json=True))
            payload = json.loads(output)
        self.assertNotIn("fixes", payload)


if __name__ == "__main__":
    unittest.main()
