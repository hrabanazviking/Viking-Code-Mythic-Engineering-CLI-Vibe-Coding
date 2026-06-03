"""Tests for the Reforge Phase 7 workspace manager."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.workspaces.manager import (
    clone_repo,
    create_branch,
    load_registry,
    open_workspace,
    prepare_pr_draft,
    propose_workspace_plan,
    repo_name_from_url,
    track_branch,
    workspace_status,
)


GIT_AVAILABLE = shutil.which("git") is not None


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Tester")
    _git(root, "config", "user.email", "tester@example.com")
    (root / "README.md").write_text("hello\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "initial")


class WorkspaceManagerTests(unittest.TestCase):
    def test_repo_name_from_url(self) -> None:
        self.assertEqual(repo_name_from_url("https://github.com/acme/hermes.git"), "hermes")
        self.assertEqual(repo_name_from_url("git@github.com:acme/hermes.git"), "hermes")

    def test_clone_repo_dry_run_does_not_create_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp)
            action = clone_repo(
                "https://github.com/acme/hermes.git",
                workspace_root=workspace_root,
                execute=False,
            )

        self.assertFalse(action.executed)
        self.assertIn("pass --yes", action.message)
        self.assertEqual(Path(action.target_path).name, "hermes")

    @unittest.skipUnless(GIT_AVAILABLE, "git not available on PATH")
    def test_open_workspace_records_existing_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            workspace_root = Path(tmp) / "workspaces"
            root.mkdir()
            _init_repo(root)

            action = open_workspace(root, workspace_root=workspace_root)
            records = load_registry(workspace_root)

        self.assertEqual(action.exit_code, 0)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].name, "repo")

    @unittest.skipUnless(GIT_AVAILABLE, "git not available on PATH")
    def test_create_branch_dry_run_and_track_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            workspace_root = Path(tmp) / "workspaces"
            root.mkdir()
            _init_repo(root)

            dry = create_branch(root, "feature/memory", workspace_root=workspace_root)
            tracked = track_branch(root, workspace_root=workspace_root)
            records = load_registry(workspace_root)

        self.assertFalse(dry.executed)
        self.assertIn("pass --yes", dry.message)
        self.assertEqual(tracked.exit_code, 0)
        self.assertTrue(records[0].tracked_branches)

    @unittest.skipUnless(GIT_AVAILABLE, "git not available on PATH")
    def test_prepare_pr_draft_writes_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            workspace_root = Path(tmp) / "workspaces"
            root.mkdir()
            _init_repo(root)

            action = prepare_pr_draft(
                root,
                workspace_root=workspace_root,
                title="Fix memory",
                body="Tests passed.",
                write=True,
            )
            draft_exists = Path(action.target_path).is_file()
            draft_text = Path(action.target_path).read_text(encoding="utf-8")

        self.assertTrue(action.executed)
        self.assertTrue(draft_exists)
        self.assertIn("Fix memory", draft_text)

    @unittest.skipUnless(GIT_AVAILABLE, "git not available on PATH")
    def test_workspace_status_detects_current_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            workspace_root = Path(tmp) / "workspaces"
            root.mkdir()
            _init_repo(root)
            status = workspace_status(root, workspace_root)

        self.assertTrue(status.current_repo.endswith("repo"))
        self.assertFalse(status.dirty)

    def test_propose_workspace_plan_does_not_execute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rendered = propose_workspace_plan(
                "Clone https://github.com/acme/hermes and make a branch for fixing memory",
                workspace_root=Path(tmp),
            )
        self.assertIn("Workspace proposal", rendered)
        self.assertIn("https://github.com/acme/hermes", rendered)
        self.assertIn("No changes were made", rendered)


if __name__ == "__main__":
    unittest.main()
