"""Phase 20.F (audit remediation 2026-05-03) — changelog
classification tests.

Covers ``scripts/check_changelog.py`` additions:

- The original release-gate behaviour is preserved.
- ``--classify`` parses the ``[Unreleased]`` block, recognises
  conventional-commit-style prefixes, and reports per-bucket
  counts.
- ``--json`` emits the report as parseable JSON.

Pure stdlib; no network.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


# Load scripts/check_changelog.py without polluting sys.path —
# same loader pattern as tests/test_contract_audit.py.
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
_SPEC = importlib.util.spec_from_file_location(
    "check_changelog", _SCRIPTS_DIR / "check_changelog.py"
)
check_changelog = importlib.util.module_from_spec(_SPEC)  # type: ignore[arg-type]
sys.modules["check_changelog"] = check_changelog
_SPEC.loader.exec_module(check_changelog)  # type: ignore[union-attr]


SAMPLE_CHANGELOG = """\
# Changelog

## [Unreleased]

### Added

- feat: shipped the Foo handler
- feat(scope): added Bar
- chore: bump deps
- whatever — entry without a recognised prefix
- fix: closed the Baz race condition

### Changed

- refactor: split the Quux module

## [1.0.0] — 2026-05-03

- initial release
"""


class ExtractUnreleasedBlockTests(unittest.TestCase):
    def test_returns_block_until_next_release(self) -> None:
        block = check_changelog.extract_unreleased_block(SAMPLE_CHANGELOG)
        self.assertIn("feat: shipped the Foo handler", block)
        self.assertNotIn("initial release", block)

    def test_returns_empty_when_marker_missing(self) -> None:
        text = "# Changelog\n\n## [1.0.0]\n\n- entry\n"
        self.assertEqual(check_changelog.extract_unreleased_block(text), "")


class ParseUnreleasedEntriesTests(unittest.TestCase):
    def test_extracts_bullet_entries(self) -> None:
        block = check_changelog.extract_unreleased_block(SAMPLE_CHANGELOG)
        entries = check_changelog.parse_unreleased_entries(block)
        # 5 in Added + 1 in Changed = 6 entries.
        self.assertEqual(len(entries), 6)
        self.assertIn("feat: shipped the Foo handler", entries)
        self.assertIn("refactor: split the Quux module", entries)


class ClassifyEntryTests(unittest.TestCase):
    def test_known_label_buckets_correctly(self) -> None:
        label, bucket = check_changelog.classify_entry("feat: foo")
        self.assertEqual(label, "feat")
        self.assertEqual(bucket, "Added")

    def test_label_with_scope(self) -> None:
        label, bucket = check_changelog.classify_entry("fix(api): bar")
        self.assertEqual(label, "fix")
        self.assertEqual(bucket, "Fixed")

    def test_unknown_prefix_label_surfaced_bucket_unclassified(self) -> None:
        """Unknown labels are surfaced in `label` (operator signal
        — they can see what they typed) but bucket falls through
        to Unclassified."""
        label, bucket = check_changelog.classify_entry("magic: nope")
        self.assertEqual(label, "magic")
        self.assertEqual(bucket, check_changelog.UNCLASSIFIED_BUCKET)

    def test_no_prefix_unclassified(self) -> None:
        label, bucket = check_changelog.classify_entry("just a description")
        self.assertEqual(label, "")
        self.assertEqual(bucket, check_changelog.UNCLASSIFIED_BUCKET)


class ClassifyUnreleasedTests(unittest.TestCase):
    def test_full_report_shape(self) -> None:
        report = check_changelog.classify_unreleased(SAMPLE_CHANGELOG)
        self.assertEqual(report["total_entries"], 6)
        # 2 feat + 1 chore + 1 fix + 1 refactor + 1 unclassified = 6
        # buckets: Added(2 feat) + Chore(1) + Fixed(1) + Changed(1 refactor) + Unclassified(1)
        buckets = report["by_bucket"]
        self.assertEqual(buckets.get("Added"), 2)
        self.assertEqual(buckets.get("Fixed"), 1)
        self.assertEqual(buckets.get("Changed"), 1)
        self.assertEqual(buckets.get("Chore"), 1)
        self.assertEqual(buckets.get("Unclassified"), 1)
        self.assertEqual(report["unclassified_count"], 1)

    def test_label_counts(self) -> None:
        report = check_changelog.classify_unreleased(SAMPLE_CHANGELOG)
        labels = report["by_label"]
        self.assertEqual(labels.get("feat"), 2)
        self.assertEqual(labels.get("fix"), 1)
        self.assertEqual(labels.get("refactor"), 1)
        self.assertEqual(labels.get("chore"), 1)


class CliMainTests(unittest.TestCase):
    def _run_main(self, argv: list[str], cwd: Path) -> tuple[int, str]:
        captured = io.StringIO()
        original = sys.stdout
        original_cwd = Path.cwd()
        sys.stdout = captured
        try:
            import os
            os.chdir(cwd)
            code = check_changelog.main(argv)
        finally:
            sys.stdout = original
            os.chdir(original_cwd)
        return code, captured.getvalue()

    def test_classify_text_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "CHANGELOG.md").write_text(
                SAMPLE_CHANGELOG, encoding="utf-8"
            )
            code, output = self._run_main(["--classify"], Path(tmp))
        self.assertEqual(code, 0)
        self.assertIn("[Unreleased] classification", output)
        self.assertIn("By bucket", output)
        self.assertIn("By label", output)

    def test_classify_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "CHANGELOG.md").write_text(
                SAMPLE_CHANGELOG, encoding="utf-8"
            )
            code, output = self._run_main(
                ["--classify", "--json"], Path(tmp)
            )
            payload = json.loads(output)
        self.assertEqual(code, 0)
        self.assertEqual(payload["total_entries"], 6)
        self.assertIn("by_bucket", payload)

    def test_release_gate_unchanged_with_no_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Minimal CHANGELOG that passes the original gate.
            (Path(tmp) / "CHANGELOG.md").write_text(
                "# Changelog\n\n"
                "## [Unreleased]\n\n"
                "### Added\n\n- Packaging entry\n\n"
                "### Changed\n\n- something\n",
                encoding="utf-8",
            )
            code, output = self._run_main([], Path(tmp))
        self.assertEqual(code, 0)
        self.assertIn("release gate passed", output)

    def test_missing_changelog_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run_main([], Path(tmp))
        self.assertEqual(code, 1)
        self.assertIn("Missing CHANGELOG.md", output)


if __name__ == "__main__":
    unittest.main()
