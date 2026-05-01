"""Tests for PH-18 Slice 18.1 — boundary audit."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.robustness.boundary_audit import (
    BoundaryAuditResult,
    BoundaryFinding,
    SUBPROCESS_ALLOWED_RELATIVE_PATHS,
    _scan_module,
    audit_boundary,
    filter_findings_by_kind,
)


def _runtime_tree(root: Path, files: dict[str, str]) -> None:
    """Materialise a synthetic mythic_vibe_cli runtime tree under
    ``root``. Tests use this to drive the auditor against
    deterministic input rather than the live repo."""
    runtime = root / "mythic_vibe_cli"
    runtime.mkdir(parents=True, exist_ok=True)
    for relative, body in files.items():
        target = runtime / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")


# ---- BoundaryFinding -------------------------------------------------


class BoundaryFindingTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        f = BoundaryFinding(
            kind="direct_subprocess",
            location="x.py",
            line=10,
            column=0,
            snippet="subprocess.run(...)",
            detail="...",
        )
        payload = f.to_dict()
        for key in {"kind", "location", "line", "column", "snippet", "detail"}:
            self.assertIn(key, payload)


# ---- BoundaryAuditResult ---------------------------------------------


class BoundaryAuditResultTests(unittest.TestCase):
    def test_ok_when_empty(self) -> None:
        self.assertTrue(BoundaryAuditResult().ok)

    def test_ok_false_with_findings(self) -> None:
        result = BoundaryAuditResult(
            findings=[
                BoundaryFinding(
                    kind="bare_except",
                    location="x.py",
                    line=1,
                    column=0,
                    snippet="except:",
                )
            ]
        )
        self.assertFalse(result.ok)


# ---- _scan_module ----------------------------------------------------


class ScanModuleTests(unittest.TestCase):
    def test_clean_module_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ok.py"
            path.write_text(
                "def hello():\n    return 1\n",
                encoding="utf-8",
            )
            findings = _scan_module(path, path.read_text(), relative="ok.py")
        self.assertEqual(findings, [])

    def test_subprocess_run_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text(
                "import subprocess\nsubprocess.run(['ls'])\n",
                encoding="utf-8",
            )
            findings = _scan_module(path, path.read_text(), relative="x.py")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "direct_subprocess")
        self.assertIn("runtime.exec", findings[0].detail)

    def test_subprocess_popen_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text(
                "import subprocess\nsubprocess.Popen(['ls'])\n",
                encoding="utf-8",
            )
            findings = _scan_module(path, path.read_text(), relative="x.py")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "direct_subprocess")

    def test_os_system_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text(
                "import os\nos.system('ls')\n",
                encoding="utf-8",
            )
            findings = _scan_module(path, path.read_text(), relative="x.py")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "os_system")

    def test_os_popen_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text(
                "import os\nos.popen('ls').read()\n",
                encoding="utf-8",
            )
            findings = _scan_module(path, path.read_text(), relative="x.py")
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "os_system")

    def test_bare_except_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text(
                "try:\n    1/0\nexcept:\n    pass\n",
                encoding="utf-8",
            )
            findings = _scan_module(path, path.read_text(), relative="x.py")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].kind, "bare_except")

    def test_typed_except_not_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text(
                "try:\n    1/0\nexcept ZeroDivisionError:\n    pass\n",
                encoding="utf-8",
            )
            findings = _scan_module(path, path.read_text(), relative="x.py")
        self.assertEqual(findings, [])

    def test_canonical_runtime_exec_path_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text(
                "import subprocess\nsubprocess.run(['ls'])\n",
                encoding="utf-8",
            )
            findings = _scan_module(
                path, path.read_text(), relative="runtime/exec.py"
            )
        # runtime/exec.py is on the allow-list; no finding.
        self.assertEqual(findings, [])

    def test_syntax_error_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            findings = _scan_module(path, "def broken(:\n", relative="x.py")
        self.assertEqual(findings, [])

    def test_snippet_truncation(self) -> None:
        long_line = "x = " + "a" * 200
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.py"
            path.write_text(long_line + "\ntry:\n    pass\nexcept:\n    pass\n", encoding="utf-8")
            findings = _scan_module(path, path.read_text(), relative="x.py")
        # bare_except finding should still come through.
        bare = [f for f in findings if f.kind == "bare_except"]
        self.assertEqual(len(bare), 1)


# ---- audit_boundary --------------------------------------------------


class AuditBoundaryTests(unittest.TestCase):
    def test_clean_tree_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _runtime_tree(
                root,
                {
                    "ok.py": "def hello():\n    return 1\n",
                    "nested/clean.py": "x = 1\n",
                },
            )
            result = audit_boundary(root)
        self.assertTrue(result.ok)
        self.assertEqual(result.files_scanned, 2)

    def test_findings_aggregated_across_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _runtime_tree(
                root,
                {
                    "a.py": "import subprocess\nsubprocess.run(['ls'])\n",
                    "b.py": "try:\n    1/0\nexcept:\n    pass\n",
                    "c.py": "x = 1\n",
                },
            )
            result = audit_boundary(root)
        self.assertFalse(result.ok)
        self.assertEqual(result.files_scanned, 3)
        self.assertEqual(len(result.findings), 2)
        kinds = {f.kind for f in result.findings}
        self.assertEqual(kinds, {"direct_subprocess", "bare_except"})

    def test_canonical_runtime_exec_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _runtime_tree(
                root,
                {
                    "runtime/exec.py": "import subprocess\nsubprocess.run(['ls'])\n",
                    "other.py": "import subprocess\nsubprocess.run(['ls'])\n",
                },
            )
            result = audit_boundary(root)
        # Only `other.py` is flagged.
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0].location, "other.py")

    def test_pycache_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _runtime_tree(
                root,
                {
                    "__pycache__/skip.cpython-310.pyc": "should not parse",
                    "ok.py": "x = 1\n",
                },
            )
            # .pyc files won't have .py suffix, but write a real
            # __pycache__/something.py to confirm the skip.
            (root / "mythic_vibe_cli" / "__pycache__").mkdir(
                parents=True, exist_ok=True
            )
            (root / "mythic_vibe_cli" / "__pycache__" / "skip.py").write_text(
                "import subprocess\nsubprocess.run(['ls'])\n",
                encoding="utf-8",
            )
            result = audit_boundary(root)
        # The __pycache__ file should be skipped, not flagged.
        self.assertEqual(result.findings, [])

    def test_missing_runtime_root_returns_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = audit_boundary(Path(tmp))
        self.assertEqual(result.findings, [])
        self.assertTrue(any("not found" in n for n in result.notes))


# ---- filter_findings_by_kind -----------------------------------------


class FilterFindingsTests(unittest.TestCase):
    def test_filter_by_kind(self) -> None:
        findings = [
            BoundaryFinding(
                kind="bare_except", location="a.py", line=1, column=0, snippet="x"
            ),
            BoundaryFinding(
                kind="direct_subprocess",
                location="b.py",
                line=2,
                column=0,
                snippet="y",
            ),
            BoundaryFinding(
                kind="bare_except", location="c.py", line=3, column=0, snippet="z"
            ),
        ]
        bare = filter_findings_by_kind(findings, kind="bare_except")
        self.assertEqual({f.location for f in bare}, {"a.py", "c.py"})


# ---- Allow-list invariant --------------------------------------------


class AllowListTests(unittest.TestCase):
    def test_runtime_exec_on_allow_list(self) -> None:
        self.assertIn("runtime/exec.py", SUBPROCESS_ALLOWED_RELATIVE_PATHS)


# ---- Self-audit smoke test -------------------------------------------


class SelfAuditTests(unittest.TestCase):
    """Run the auditor against the live repo to confirm it
    completes cleanly. The findings count is allowed to be > 0
    — Round 1 surfaces existing bypasses; remediation is
    incremental."""

    def test_live_repo_audit_completes(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        result = audit_boundary(repo_root)
        # Sanity: the auditor scanned a real number of files.
        self.assertGreater(result.files_scanned, 50)
        # Result is well-formed regardless of finding count.
        payload = result.to_dict()
        self.assertIn("findings", payload)
        self.assertIn("count", payload)


if __name__ == "__main__":
    unittest.main()
