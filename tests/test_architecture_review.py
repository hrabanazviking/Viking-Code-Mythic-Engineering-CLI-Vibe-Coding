"""Phase 20.H (audit remediation 2026-05-03) — architecture
review tests.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.architecture_review import (
    GOVERNANCE_DOCS,
    build_review_report,
    render_review_markdown,
)
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR


def _seed_govdocs(root: Path, *, include: tuple[str, ...] = GOVERNANCE_DOCS) -> None:
    for rel in include:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# {rel}\n", encoding="utf-8")


def _seed_adr(root: Path, *, count: int = 1) -> None:
    adr_dir = root / "docs" / "ADRS"
    adr_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, count + 1):
        (adr_dir / f"ADR-{i:04d}-sample.md").write_text(
            f"# ADR-{i:04d}\n", encoding="utf-8"
        )


class GovernanceDocsTests(unittest.TestCase):
    def test_constant_lists_expected_docs(self) -> None:
        for required in (
            "docs/ARCHITECTURE.md",
            "docs/DOMAIN_MAP.md",
            "docs/DATA_FLOW.md",
        ):
            self.assertIn(required, GOVERNANCE_DOCS)


class BuildReviewReportTests(unittest.TestCase):
    def test_empty_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = build_review_report(Path(tmp))
        self.assertFalse(report.all_governance_files_present)
        self.assertEqual(report.adr_count, 0)
        # Open questions should flag missing ARCHITECTURE.md +
        # DOMAIN_MAP.md + zero ADRs.
        question_text = " ".join(report.open_questions)
        self.assertIn("ARCHITECTURE.md missing", question_text)
        self.assertIn("DOMAIN_MAP.md missing", question_text)
        self.assertIn("No ADRs present", question_text)

    def test_full_governance_with_adrs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_govdocs(Path(tmp))
            _seed_adr(Path(tmp), count=3)
            report = build_review_report(Path(tmp))
        self.assertTrue(report.all_governance_files_present)
        self.assertEqual(report.adr_count, 3)

    def test_adr_count_excludes_non_adr_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp) / "docs" / "ADRS"
            adr_dir.mkdir(parents=True)
            (adr_dir / "ADR-0001-real.md").write_text("x", encoding="utf-8")
            (adr_dir / "README.md").write_text("not an adr", encoding="utf-8")
            (adr_dir / "ADR-template.md").write_text("template", encoding="utf-8")
            report = build_review_report(Path(tmp))
        # ADR-template.md does start with "ADR-" so the glob counts it.
        # Two matches: ADR-0001-real.md + ADR-template.md. README.md
        # is excluded by the pattern.
        self.assertEqual(report.adr_count, 2)


class RenderReviewMarkdownTests(unittest.TestCase):
    def test_contains_required_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_govdocs(Path(tmp))
            report = build_review_report(Path(tmp))
            md = render_review_markdown(report)
        for section in (
            "# Architecture Review",
            "## Governance artefacts",
            "## ADRs",
            "## Drift",
            "## Open questions",
            "## Reviewer checklist",
        ):
            self.assertIn(section, md)

    def test_open_questions_renders_none_when_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_govdocs(Path(tmp))
            _seed_adr(Path(tmp), count=1)
            report = build_review_report(Path(tmp))
            md = render_review_markdown(report)
        self.assertIn("(none)", md)


class CmdReviewIntegrationTests(unittest.TestCase):
    def _run(self, ns: argparse.Namespace) -> tuple[int, str]:
        from mythic_vibe_cli.commands import cmd_review

        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = cmd_review(ns)
        finally:
            sys.stdout = original
        return code, captured.getvalue()

    def test_architecture_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_govdocs(Path(tmp))
            code, output = self._run(argparse.Namespace(
                review_command="architecture",
                path=tmp,
                json=False,
            ))
        self.assertEqual(code, SUCCESS)
        self.assertIn("# Architecture Review", output)

    def test_architecture_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_govdocs(Path(tmp))
            _seed_adr(Path(tmp), count=2)
            code, output = self._run(argparse.Namespace(
                review_command="architecture",
                path=tmp,
                json=True,
            ))
            payload = json.loads(output)
        self.assertEqual(code, SUCCESS)
        self.assertEqual(payload["command"], "review architecture")
        self.assertEqual(payload["adr_count"], 2)
        self.assertTrue(payload["all_governance_files_present"])

    def test_unknown_subcommand_returns_user_input_error(self) -> None:
        code, _ = self._run(argparse.Namespace(
            review_command="bogus",
            path=tempfile.gettempdir(),
            json=False,
        ))
        self.assertEqual(code, USER_INPUT_ERROR)


class CadenceDocPresenceTest(unittest.TestCase):
    """The cadence doc is part of the slice — assert it exists
    so future cleanups don't accidentally remove it."""

    def test_quarterly_review_doc_exists(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        target = repo_root / "docs" / "governance" / "quarterly_review.md"
        self.assertTrue(target.is_file(), f"missing: {target}")
        text = target.read_text(encoding="utf-8")
        self.assertIn("# Quarterly Architecture Review", text)
        self.assertIn("review architecture", text)


if __name__ == "__main__":
    unittest.main()
