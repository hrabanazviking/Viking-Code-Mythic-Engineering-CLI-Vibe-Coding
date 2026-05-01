"""Tests for PH-12 Slice 12.4 — rollback summariser."""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from mythic_vibe_cli.cicd.rollback import (
    CommitSummary,
    RollbackReport,
    summarise_rollback,
)
from mythic_vibe_cli.commands import cmd_rollback
from mythic_vibe_cli.exit_codes import OPERATIONAL_FAILURE, SUCCESS


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True)


def _write_repo(root: Path, *, with_tag: str | None = "v1.0.0") -> None:
    """Initialise a tiny real git repo + tag for end-to-end tests."""
    _git(["init", "-q"], cwd=root)
    _git(["config", "user.email", "test@example.com"], cwd=root)
    _git(["config", "user.name", "Tester"], cwd=root)
    (root / "README.md").write_text("# x\n", encoding="utf-8")
    _git(["add", "."], cwd=root)
    _git(["commit", "-q", "-m", "init"], cwd=root)
    if with_tag:
        _git(["tag", with_tag], cwd=root)
    # Add two more commits to create a non-empty rollback range.
    (root / "main.py").write_text("print('hi')\n", encoding="utf-8")
    _git(["add", "."], cwd=root)
    _git(["commit", "-q", "-m", "feat: add main"], cwd=root)
    (root / "README.md").write_text("# x\nupdated\n", encoding="utf-8")
    _git(["add", "."], cwd=root)
    _git(["commit", "-q", "-m", "docs: update readme"], cwd=root)


# ---- RollbackReport / CommitSummary ----------------------------------


class DataclassTests(unittest.TestCase):
    def test_commit_summary_to_dict(self) -> None:
        c = CommitSummary(
            sha="abc", short_sha="abc", author="x", subject="y"
        )
        self.assertEqual(c.to_dict()["sha"], "abc")

    def test_rollback_report_ok_when_no_error(self) -> None:
        r = RollbackReport(since_ref="v1.0.0", head="HEAD")
        self.assertTrue(r.ok)

    def test_rollback_report_to_dict_round_trip(self) -> None:
        r = RollbackReport(
            since_ref="v1.0.0",
            head="abcdef",
            commits=[CommitSummary("a", "a", "x", "y")],
            files=["a.py"],
        )
        payload = r.to_dict()
        self.assertEqual(payload["commit_count"], 1)
        self.assertEqual(payload["file_count"], 1)


# ---- summarise_rollback (end-to-end) ---------------------------------


class SummariseRollbackTests(unittest.TestCase):
    def test_real_repo_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_repo(root)
            report = summarise_rollback(root, since_ref="v1.0.0")
        self.assertTrue(report.ok)
        self.assertEqual(len(report.commits), 2)
        # Newest first via git log default ordering.
        subjects = [c.subject for c in report.commits]
        self.assertIn("feat: add main", subjects)
        self.assertIn("docs: update readme", subjects)
        # Files-touched include both main.py and the README change.
        self.assertIn("main.py", report.files)
        self.assertIn("README.md", report.files)

    def test_blank_since_ref_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = summarise_rollback(Path(tmp), since_ref="")
        self.assertFalse(report.ok)
        self.assertIn("non-empty", report.error)

    def test_unknown_ref_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_repo(root, with_tag=None)
            report = summarise_rollback(root, since_ref="vGHOST")
        self.assertFalse(report.ok)

    def test_non_git_directory_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = summarise_rollback(Path(tmp), since_ref="v1.0.0")
        self.assertFalse(report.ok)
        self.assertIn("HEAD", report.error)

    def test_missing_git_binary_returns_error(self) -> None:
        """When git is unavailable, _resolve_head returns "" and the
        caller surfaces the "HEAD could not be resolved" message
        rather than the raw FileNotFoundError. Both shapes are
        equivalent for operators — the helper signals failure
        cleanly without raising."""
        with mock.patch("subprocess.run", side_effect=FileNotFoundError("git")):
            with tempfile.TemporaryDirectory() as tmp:
                report = summarise_rollback(Path(tmp), since_ref="v1.0.0")
        self.assertFalse(report.ok)
        self.assertIn("HEAD could not be resolved", report.error)

    def test_no_commits_in_range_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_repo(root)
            # Tag HEAD with a fresh ref that has nothing after it.
            _git(["tag", "v2.0.0"], cwd=root)
            report = summarise_rollback(root, since_ref="v2.0.0")
        self.assertTrue(report.ok)
        self.assertEqual(report.commits, [])
        self.assertTrue(any("Nothing" in n or "nothing" in n for n in report.notes))


# ---- cmd_rollback ----------------------------------------------------


class CmdRollbackTests(unittest.TestCase):
    def test_real_repo_returns_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_repo(root)
            ns = argparse.Namespace(
                path=str(root), since="v1.0.0", json=True
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_rollback(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertGreaterEqual(payload["report"]["commit_count"], 2)
        self.assertGreaterEqual(payload["report"]["file_count"], 1)

    def test_blank_since_returns_failure(self) -> None:
        ns = argparse.Namespace(path=".", since="", json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_rollback(ns)
        self.assertEqual(exit_code, OPERATIONAL_FAILURE)
        payload = json.loads(buf.getvalue())
        self.assertFalse(payload["report"]["ok"])

    def test_text_path_emits_helpful_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_repo(root)
            ns = argparse.Namespace(
                path=str(root), since="v1.0.0", json=False
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_rollback(ns)
        self.assertEqual(exit_code, SUCCESS)
        # Output should explicitly remind operators it's read-only.
        self.assertIn("does NOT revert", buf.getvalue())


class RollbackArgparseTests(unittest.TestCase):
    def test_rollback_requires_since(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                parser.parse_args(["rollback"])

    def test_rollback_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["rollback", "--since", "v1.2.3"])
        self.assertEqual(ns.command, "rollback")
        self.assertEqual(ns.since, "v1.2.3")


if __name__ == "__main__":
    unittest.main()
