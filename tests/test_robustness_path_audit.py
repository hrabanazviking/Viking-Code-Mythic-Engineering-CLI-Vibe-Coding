"""Tests for PH-18 Slice 18.2 — path audit."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.robustness.path_audit import (
    HARDCODED_PATH_ALLOWED_RELATIVE_PATHS,
    PathAuditResult,
    PathFinding,
    _scan_module,
    audit_paths,
)


def _runtime_tree(root: Path, files: dict[str, str]) -> None:
    runtime = root / "mythic_vibe_cli"
    runtime.mkdir(parents=True, exist_ok=True)
    for relative, body in files.items():
        target = runtime / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")


# ---- _scan_module ----------------------------------------------------


class ScanModuleTests(unittest.TestCase):
    def test_clean_module_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text("x = 1\n", encoding="utf-8")
            findings = _scan_module(path, path.read_text(), relative="x.py")
        self.assertEqual(findings, [])

    def test_hardcoded_mythic_path_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text(
                'output = "mythic/checkins/foo.md"\n',
                encoding="utf-8",
            )
            findings = _scan_module(path, path.read_text(), relative="x.py")
        self.assertEqual(len(findings), 1)
        self.assertIn("mythic/checkins", findings[0].matched_literal)
        self.assertEqual(findings[0].kind, "runtime")
        self.assertIn("hardcoded", findings[0].detail)

    def test_help_text_classified_as_documentation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text(
                'parser.add_argument("--out", help="default: mythic/checkins/foo.md")\n',
                encoding="utf-8",
            )
            findings = _scan_module(path, path.read_text(), relative="x.py")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "documentation")

    def test_docstring_classified_as_documentation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text(
                '"""Reads mythic/status.json for display only."""\n',
                encoding="utf-8",
            )
            findings = _scan_module(path, path.read_text(), relative="x.py")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "documentation")

    def test_reviewed_metadata_classified_as_reviewed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text(
                'PHASE_ARTEFACTS = {"build": ["mythic/codex_prompt.md"]}\n',
                encoding="utf-8",
            )
            findings = _scan_module(path, path.read_text(), relative="x.py")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "reviewed")

    def test_allow_listed_module_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "core" / "state.py"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                'STATUS_PATH = "mythic/status.json"\n',
                encoding="utf-8",
            )
            findings = _scan_module(
                path, path.read_text(), relative="core/state.py"
            )
        self.assertEqual(findings, [])

    def test_url_with_mythic_substring_not_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text(
                'URL = "https://example.com/mythic/repo"\n',
                encoding="utf-8",
            )
            findings = _scan_module(path, path.read_text(), relative="x.py")
        self.assertEqual(findings, [])

    def test_long_string_skipped(self) -> None:
        """Very long strings (template / doc content) are skipped
        to avoid false positives on prose that happens to include
        the substring."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            content = (
                'TEMPLATE = """\n'
                + ("filler " * 100)
                + 'mythic/something.md\n'
                + ("more filler " * 50)
                + '"""\n'
            )
            path.write_text(content, encoding="utf-8")
            findings = _scan_module(path, path.read_text(), relative="x.py")
        self.assertEqual(findings, [])

    def test_syntax_error_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            findings = _scan_module(path, "def broken(:\n", relative="x.py")
        self.assertEqual(findings, [])


# ---- audit_paths -----------------------------------------------------


class AuditPathsTests(unittest.TestCase):
    def test_clean_tree_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _runtime_tree(root, {"ok.py": "x = 1\n"})
            result = audit_paths(root)
        self.assertTrue(result.ok)
        self.assertEqual(result.files_scanned, 1)

    def test_hardcoded_path_aggregated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _runtime_tree(
                root,
                {
                    "a.py": 'OUT = "mythic/foo.md"\n',
                    "b.py": 'OTHER = "mythic/bar/baz"\n',
                    "ok.py": "x = 1\n",
                },
            )
            result = audit_paths(root)
        self.assertEqual(len(result.findings), 2)
        kinds = {f.location for f in result.findings}
        self.assertEqual(kinds, {"a.py", "b.py"})

    def test_allow_listed_path_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _runtime_tree(
                root,
                {
                    "core/state.py": 'STATUS = "mythic/status.json"\n',
                },
            )
            result = audit_paths(root)
        self.assertEqual(result.findings, [])

    def test_missing_runtime_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = audit_paths(Path(tmp))
        self.assertEqual(result.findings, [])
        self.assertTrue(any("not found" in n for n in result.notes))


# ---- PathFinding / PathAuditResult -----------------------------------


class DataclassTests(unittest.TestCase):
    def test_finding_to_dict(self) -> None:
        f = PathFinding(
            location="a.py",
            line=1,
            column=0,
            snippet="x",
            matched_literal="mythic/x",
        )
        payload = f.to_dict()
        for key in {
            "location",
            "line",
            "column",
            "snippet",
            "matched_literal",
            "detail",
        }:
            self.assertIn(key, payload)

    def test_result_ok_when_empty(self) -> None:
        self.assertTrue(PathAuditResult().ok)

    def test_result_ok_ignores_documentation_findings(self) -> None:
        result = PathAuditResult(
            findings=[
                PathFinding(
                    location="a.py",
                    line=1,
                    column=0,
                    snippet="x",
                    matched_literal="mythic/status.json",
                    kind="documentation",
                )
            ]
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.runtime_findings, [])


# ---- Allow-list invariants -------------------------------------------


class AllowListTests(unittest.TestCase):
    def test_core_state_allowed(self) -> None:
        self.assertIn(
            "core/state.py", HARDCODED_PATH_ALLOWED_RELATIVE_PATHS
        )


# ---- Self-audit smoke test -------------------------------------------


class SelfAuditTests(unittest.TestCase):
    def test_live_repo_audit_completes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = audit_paths(repo_root)
        self.assertGreater(result.files_scanned, 50)
        # Result is well-formed regardless of finding count.
        payload = result.to_dict()
        self.assertIn("findings", payload)


if __name__ == "__main__":
    unittest.main()
