"""Tests for PH-14 Slice 14.1 — constraint store."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.policy.constraint_store import (
    CONSTRAINT_KIND_ADR,
    CONSTRAINT_KIND_OATH,
    CONSTRAINT_KIND_RULE,
    Constraint,
    DEFAULT_SEVERITY,
    SEVERITIES,
    SEVERITY_ADVISORY,
    SEVERITY_BLOCKING,
    SEVERITY_WARN,
    _slugify,
    _strip_severity_tag,
    filter_by_severity,
    load_constraints,
)


class SeveritiesTests(unittest.TestCase):
    def test_default_is_warn(self) -> None:
        self.assertEqual(DEFAULT_SEVERITY, SEVERITY_WARN)

    def test_severity_set(self) -> None:
        self.assertEqual(
            set(SEVERITIES),
            {SEVERITY_BLOCKING, SEVERITY_WARN, SEVERITY_ADVISORY},
        )


class SlugifyTests(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertEqual(_slugify("Never push to main"), "never-push-to-main")

    def test_empty_returns_unnamed(self) -> None:
        self.assertEqual(_slugify(""), "unnamed")
        self.assertEqual(_slugify("   "), "unnamed")

    def test_truncation(self) -> None:
        slug = _slugify("a" * 200, limit=10)
        self.assertLessEqual(len(slug), 10)


class StripSeverityTagTests(unittest.TestCase):
    def test_no_tag_returns_default(self) -> None:
        text, severity = _strip_severity_tag("rule body")
        self.assertEqual(text, "rule body")
        self.assertEqual(severity, DEFAULT_SEVERITY)

    def test_blocking_tag(self) -> None:
        text, severity = _strip_severity_tag("never break the law [blocking]")
        self.assertEqual(text, "never break the law")
        self.assertEqual(severity, SEVERITY_BLOCKING)

    def test_advisory_tag(self) -> None:
        text, severity = _strip_severity_tag("nice to have [advisory]")
        self.assertEqual(severity, SEVERITY_ADVISORY)

    def test_case_insensitive(self) -> None:
        _text, severity = _strip_severity_tag("rule [BLOCKING]")
        self.assertEqual(severity, SEVERITY_BLOCKING)


# ---- load_constraints --------------------------------------------------


class LoadConstraintsEmptyTests(unittest.TestCase):
    def test_no_sources_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = load_constraints(Path(tmp))
        self.assertEqual(result.constraints, [])
        self.assertEqual(result.notes, [])

    def test_empty_oaths_file_noted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "oaths.md").write_text("", encoding="utf-8")
            result = load_constraints(root)
        self.assertEqual(result.constraints, [])
        self.assertTrue(any("oaths file" in n for n in result.notes))


class LoadConstraintsFromOathsTests(unittest.TestCase):
    def test_one_oath_per_heading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "oaths.md").write_text(
                "# My Oaths\n\n"
                "## I will review AI output\n"
                "- always read diffs before merging\n\n"
                "## I will never push to main [blocking]\n"
                "- defense in depth\n",
                encoding="utf-8",
            )
            result = load_constraints(root)
        self.assertEqual(len(result.constraints), 2)
        kinds = {c.kind for c in result.constraints}
        self.assertEqual(kinds, {CONSTRAINT_KIND_OATH})
        # Severity tag stripped from text + applied to severity.
        push_oath = next(
            c for c in result.constraints if "push to main" in c.text
        )
        self.assertEqual(push_oath.severity, SEVERITY_BLOCKING)
        self.assertNotIn("[blocking]", push_oath.text)
        self.assertEqual(push_oath.source_path, "mythic/oaths.md")
        self.assertTrue(push_oath.id.startswith("oath:"))

    def test_oath_body_appended_to_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "oaths.md").write_text(
                "## Verify before commit\n"
                "- pytest tests/\n"
                "- ruff check .\n",
                encoding="utf-8",
            )
            result = load_constraints(root)
        self.assertEqual(len(result.constraints), 1)
        constraint = result.constraints[0]
        self.assertIn("pytest", constraint.text)
        self.assertIn("ruff check", constraint.text)


class LoadConstraintsFileTests(unittest.TestCase):
    def test_one_constraint_per_bullet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "constraints.md").write_text(
                "# Constraints\n\n"
                "- never commit secrets [blocking]\n"
                "- prefer stdlib over third-party deps\n"
                "- name new modules in snake_case [advisory]\n",
                encoding="utf-8",
            )
            result = load_constraints(root)
        self.assertEqual(len(result.constraints), 3)
        kinds = {c.kind for c in result.constraints}
        self.assertEqual(kinds, {CONSTRAINT_KIND_RULE})
        secrets = next(c for c in result.constraints if "secrets" in c.text)
        self.assertEqual(secrets.severity, SEVERITY_BLOCKING)

    def test_blank_bullets_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "constraints.md").write_text(
                "- \n- valid rule\n- \n",
                encoding="utf-8",
            )
            result = load_constraints(root)
        self.assertEqual(len(result.constraints), 1)


class LoadConstraintsFromAdrsTests(unittest.TestCase):
    def test_active_adr_becomes_constraint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adrs_dir = root / "docs" / "ADRS"
            adrs_dir.mkdir(parents=True)
            (adrs_dir / "ADR-9999-test.md").write_text(
                "# ADR-9999: Sample\n\n"
                "## Status\n\nAccepted\n\n"
                "## Decision\n\n"
                "Modules under mythic_vibe_cli/ must not import from\n"
                "yggdrasil/ or core/.\n",
                encoding="utf-8",
            )
            result = load_constraints(root)
        self.assertEqual(len(result.constraints), 1)
        constraint = result.constraints[0]
        self.assertEqual(constraint.kind, CONSTRAINT_KIND_ADR)
        self.assertIn("ADR-9999", constraint.text)
        self.assertIn("must not import", constraint.text)
        self.assertEqual(constraint.source_section, "Decision")

    def test_superseded_adr_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adrs_dir = root / "docs" / "ADRS"
            adrs_dir.mkdir(parents=True)
            (adrs_dir / "ADR-9000-old.md").write_text(
                "# ADR-9000: Old\n\n"
                "## Status\n\nSuperseded by ADR-9001\n\n"
                "## Decision\n\nold rule\n",
                encoding="utf-8",
            )
            result = load_constraints(root)
        self.assertEqual(result.constraints, [])
        self.assertTrue(
            any("not active" in n.lower() for n in result.notes)
        )

    def test_adr_without_title_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adrs_dir = root / "docs" / "ADRS"
            adrs_dir.mkdir(parents=True)
            (adrs_dir / "ADR-9001-bad.md").write_text(
                "## Decision\n\nthis adr has no title\n",
                encoding="utf-8",
            )
            result = load_constraints(root)
        self.assertEqual(result.constraints, [])

    def test_adr_without_decision_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adrs_dir = root / "docs" / "ADRS"
            adrs_dir.mkdir(parents=True)
            (adrs_dir / "ADR-9002-empty.md").write_text(
                "# ADR-9002: Empty\n\n## Status\n\nAccepted\n",
                encoding="utf-8",
            )
            result = load_constraints(root)
        self.assertEqual(result.constraints, [])


class LoadConstraintsAggregationTests(unittest.TestCase):
    def test_all_three_sources_aggregated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "oaths.md").write_text(
                "## Verify before commit\n", encoding="utf-8"
            )
            (root / "mythic" / "constraints.md").write_text(
                "- prefer stdlib over third-party deps\n",
                encoding="utf-8",
            )
            adrs_dir = root / "docs" / "ADRS"
            adrs_dir.mkdir(parents=True)
            (adrs_dir / "ADR-1-x.md").write_text(
                "# ADR-1: x\n\n## Status\n\nAccepted\n\n## Decision\n\nrule body\n",
                encoding="utf-8",
            )
            result = load_constraints(root)
        kinds = {c.kind for c in result.constraints}
        self.assertEqual(
            kinds,
            {CONSTRAINT_KIND_OATH, CONSTRAINT_KIND_RULE, CONSTRAINT_KIND_ADR},
        )

    def test_dedup_by_id(self) -> None:
        """Two oaths with the same heading slug → one survives."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic").mkdir()
            (root / "mythic" / "oaths.md").write_text(
                "## Verify before commit\n## Verify before commit\n",
                encoding="utf-8",
            )
            result = load_constraints(root)
        self.assertEqual(len(result.constraints), 1)


class FilterBySeverityTests(unittest.TestCase):
    def test_filters_correctly(self) -> None:
        items = [
            Constraint(id="a", kind="rule", text="x", severity=SEVERITY_BLOCKING),
            Constraint(id="b", kind="rule", text="y", severity=SEVERITY_WARN),
            Constraint(id="c", kind="rule", text="z", severity=SEVERITY_BLOCKING),
        ]
        result = filter_by_severity(items, severity=SEVERITY_BLOCKING)
        self.assertEqual({c.id for c in result}, {"a", "c"})


class ConstraintDataclassTests(unittest.TestCase):
    def test_to_dict(self) -> None:
        c = Constraint(
            id="x",
            kind="rule",
            text="be brave",
            severity=SEVERITY_WARN,
            source_path="mythic/constraints.md",
            source_section="line 3",
        )
        payload = c.to_dict()
        for key in {"id", "kind", "text", "severity", "source_path", "source_section"}:
            self.assertIn(key, payload)


if __name__ == "__main__":
    unittest.main()
