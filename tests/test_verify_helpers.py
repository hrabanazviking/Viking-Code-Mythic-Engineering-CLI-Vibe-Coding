"""Coverage tests for the verify subsystem helpers.

Targets ``mythic_vibe_cli.verify.doc_checker``, ``invariant_checker``,
and ``git_diff``. The doctor and invariant paths are pure-Python and
testable directly; the git_diff path uses a real local git repo
created in a temp directory.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.verify.doc_checker import DocCheckResult, check_docs
from mythic_vibe_cli.verify.git_diff import (
    GitDiffResult,
    collect_changed_files,
    review_changed_files,
)
from mythic_vibe_cli.verify.invariant_checker import (
    InvariantCheckResult,
    check_invariants,
)


GIT_AVAILABLE = shutil.which("git") is not None


class DocCheckerTests(unittest.TestCase):
    def test_check_docs_reports_missing_when_directory_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = check_docs(Path(tmp))
            self.assertIsInstance(result, DocCheckResult)
            self.assertGreater(len(result.missing), 0)
            self.assertFalse(result.ok)
            self.assertIn("README.md", result.missing)
            self.assertIn("conservative", " ".join(result.warnings).lower())

    def test_check_docs_reports_ok_when_all_files_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            for path in [
                "README.md",
                "CHANGELOG.md",
                "DEVLOG.md",
                "docs/ARCHITECTURE.md",
                "docs/DOMAIN_MAP.md",
                "docs/DATA_FLOW.md",
                "docs/PHILOSOPHY.md",
                "docs/COMMAND_CONTRACTS.md",
                "docs/INDEX.md",
            ]:
                (root / path).write_text("ok\n", encoding="utf-8")

            result = check_docs(root)
            self.assertEqual(result.missing, [])
            self.assertTrue(result.ok)
            self.assertEqual(result.warnings, [])

    def test_doc_check_result_to_dict_round_trip(self) -> None:
        result = DocCheckResult(
            checked=["README.md"], missing=["CHANGELOG.md"], warnings=["conservative"]
        )
        payload = result.to_dict()
        self.assertEqual(payload["checked"], ["README.md"])
        self.assertEqual(payload["missing"], ["CHANGELOG.md"])
        self.assertEqual(payload["warnings"], ["conservative"])
        self.assertFalse(payload["ok"])


class InvariantCheckerTests(unittest.TestCase):
    def test_invariant_check_result_to_dict_round_trip(self) -> None:
        result = InvariantCheckResult(
            checked=["project state schema", "repo boundary docs"],
            errors=["state-corrupt"],
            warnings=["soft-warn"],
        )
        payload = result.to_dict()
        self.assertEqual(payload["checked"], result.checked)
        self.assertEqual(payload["errors"], ["state-corrupt"])
        self.assertEqual(payload["warnings"], ["soft-warn"])
        self.assertFalse(payload["ok"])

    def test_invariant_check_result_ok_when_no_errors(self) -> None:
        result = InvariantCheckResult(
            checked=["x"], errors=[], warnings=["just a warn"]
        )
        self.assertTrue(result.ok)
        self.assertTrue(result.to_dict()["ok"])

    def test_check_invariants_on_bare_directory_returns_errors_not_typeerror(self) -> None:
        """Regression test for F-022 (fixed): MythicWorkflow.doctor(repo_boundary=True)
        previously dropped its return tuple via a bare ``return`` on
        workflow.py:269 when the project lacked a ``mythic_vibe_cli/``
        package at its root, causing the caller to crash with
        ``TypeError: cannot unpack non-iterable NoneType object``.
        After the hot-fix the function returns the partial 3-tuple and
        callers receive a structured error instead of a crash.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = check_invariants(root)
            self.assertIsInstance(result, InvariantCheckResult)
            self.assertFalse(result.ok)
            joined_errors = " | ".join(result.errors)
            self.assertIn("Missing active runtime package", joined_errors)
            self.assertIn("project state schema", result.checked)


@unittest.skipUnless(GIT_AVAILABLE, "git not available on PATH")
class GitDiffTests(unittest.TestCase):
    def _init_repo(self, root: Path) -> None:
        env = {**os.environ, "GIT_AUTHOR_NAME": "x", "GIT_AUTHOR_EMAIL": "x@x",
               "GIT_COMMITTER_NAME": "x", "GIT_COMMITTER_EMAIL": "x@x"}
        subprocess.run(["git", "-C", str(root), "init", "-q", "-b", "main"], check=True, env=env)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "x@x"], check=True, env=env)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "x"], check=True, env=env)
        (root / "tracked.txt").write_text("hello\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "."], check=True, env=env)
        subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "initial"], check=True, env=env)

    def test_collect_changed_files_empty_for_clean_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_repo(root)
            self.assertEqual(collect_changed_files(root), [])

    def test_collect_changed_files_lists_modified_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_repo(root)
            (root / "tracked.txt").write_text("changed\n", encoding="utf-8")
            (root / "new.txt").write_text("brand new\n", encoding="utf-8")

            files = collect_changed_files(root)
            self.assertIn("tracked.txt", files)
            self.assertIn("new.txt", files)

    def test_review_changed_files_warns_when_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_repo(root)
            result = review_changed_files(root)
            self.assertIsInstance(result, GitDiffResult)
            self.assertEqual(result.changed_files, [])
            self.assertTrue(any("No changed files" in w for w in result.warnings))

    def test_review_changed_files_returns_diffs_for_modifications(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_repo(root)
            (root / "tracked.txt").write_text("changed!\n", encoding="utf-8")

            result = review_changed_files(root)
            self.assertIn("tracked.txt", result.changed_files)
            self.assertIn("tracked.txt", result.diffs)
            self.assertIn("changed!", result.diffs["tracked.txt"])

    def test_review_changed_files_truncates_at_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_repo(root)
            for i in range(10):
                (root / f"file_{i}.txt").write_text(f"content {i}\n", encoding="utf-8")

            result = review_changed_files(root, limit=3)
            self.assertEqual(len(result.changed_files), 3)
            self.assertTrue(any("truncated" in w for w in result.warnings))

    def test_git_diff_result_to_dict(self) -> None:
        result = GitDiffResult(
            changed_files=["a.py"],
            diffs={"a.py": "+ added"},
            warnings=["truncated"],
        )
        payload = result.to_dict()
        self.assertEqual(payload["changed_files"], ["a.py"])
        self.assertEqual(payload["diffs"], {"a.py": "+ added"})
        self.assertEqual(payload["warnings"], ["truncated"])


if __name__ == "__main__":
    unittest.main()
