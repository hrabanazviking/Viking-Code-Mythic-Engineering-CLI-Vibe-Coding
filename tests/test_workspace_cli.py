"""Tests for `mythic-vibe workspace` commands."""

from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mythic_vibe_cli.app import build_parser
from mythic_vibe_cli.commands import COMMAND_HANDLERS
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.runtime.slash_commands import BUILTIN_SLASH_COMMANDS


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


class WorkspaceArgparseTests(unittest.TestCase):
    def test_subcommands_parse(self) -> None:
        parser = build_parser()
        status = parser.parse_args(["workspace", "status"])
        clone = parser.parse_args(["workspace", "clone", "https://github.com/acme/hermes", "--yes"])
        branch = parser.parse_args(["workspace", "branch", "feature/memory", "--yes"])
        plan = parser.parse_args(["workspace", "plan", "clone", "hermes"])
        self.assertEqual(status.workspace_command, "status")
        self.assertEqual(clone.workspace_command, "clone")
        self.assertTrue(clone.yes)
        self.assertEqual(branch.branch, "feature/memory")
        self.assertEqual(plan.request, ["clone", "hermes"])


class WorkspaceDispatchTests(unittest.TestCase):
    def test_handler_registered(self) -> None:
        from mythic_vibe_cli.commands import cmd_workspace_dispatch

        self.assertIs(COMMAND_HANDLERS["workspace"], cmd_workspace_dispatch)

    def test_unknown_subcommand_returns_user_input_error(self) -> None:
        from mythic_vibe_cli.commands import cmd_workspace_dispatch

        ns = argparse.Namespace(workspace_command="bogus")
        self.assertEqual(cmd_workspace_dispatch(ns), USER_INPUT_ERROR)

    def test_clone_dry_run_json(self) -> None:
        from mythic_vibe_cli.commands import cmd_workspace_clone

        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(
                repo_url="https://github.com/acme/hermes.git",
                name="",
                workspace_root=tmp,
                yes=False,
                json=True,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_workspace_clone(ns)
            payload = json.loads(buf.getvalue())

        self.assertEqual(exit_code, SUCCESS)
        self.assertFalse(payload["action"]["executed"])
        self.assertIn("pass --yes", payload["action"]["message"])

    @unittest.skipUnless(GIT_AVAILABLE, "git not available on PATH")
    def test_open_and_status_text(self) -> None:
        from mythic_vibe_cli.commands import cmd_workspace_open, cmd_workspace_status

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            workspace_root = Path(tmp) / "workspaces"
            root.mkdir()
            _init_repo(root)
            open_ns = argparse.Namespace(
                repo_path=str(root),
                name="",
                workspace_root=str(workspace_root),
                json=False,
            )
            status_ns = argparse.Namespace(
                path=str(root),
                workspace_root=str(workspace_root),
                json=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                open_code = cmd_workspace_open(open_ns)
                status_code = cmd_workspace_status(status_ns)
            rendered = buf.getvalue()

        self.assertEqual(open_code, SUCCESS)
        self.assertEqual(status_code, SUCCESS)
        self.assertIn("Workspace recorded", rendered)
        self.assertIn("Tracked workspaces", rendered)

    @unittest.skipUnless(GIT_AVAILABLE, "git not available on PATH")
    def test_branch_dry_run_text(self) -> None:
        from mythic_vibe_cli.commands import cmd_workspace_branch

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            workspace_root = Path(tmp) / "workspaces"
            root.mkdir()
            _init_repo(root)
            ns = argparse.Namespace(
                path=str(root),
                branch="feature/memory",
                workspace_root=str(workspace_root),
                yes=False,
                json=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_workspace_branch(ns)
            rendered = buf.getvalue()

        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("Dry run", rendered)

    @unittest.skipUnless(GIT_AVAILABLE, "git not available on PATH")
    def test_pr_json_prepares_draft(self) -> None:
        from mythic_vibe_cli.commands import cmd_workspace_pr

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            workspace_root = Path(tmp) / "workspaces"
            root.mkdir()
            _init_repo(root)
            ns = argparse.Namespace(
                path=str(root),
                title="Fix memory",
                body="Tests passed.",
                base="main",
                workspace_root=str(workspace_root),
                write=False,
                json=True,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_workspace_pr(ns)
            payload = json.loads(buf.getvalue())

        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("Pull Request Draft", payload["action"]["metadata"]["draft"])

    def test_workspace_slash_catalog_contains_workspace(self) -> None:
        names = {entry.name for entry in BUILTIN_SLASH_COMMANDS}
        self.assertIn("workspace", names)


if __name__ == "__main__":
    unittest.main()
