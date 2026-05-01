"""Tests for PH-12 Slice 12.2 — docker scaffold."""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mythic_vibe_cli.cicd.docker_scaffold import (
    DOCKER_COMPOSE_PATH,
    DOCKERFILE_PATH,
    DOCKERIGNORE_PATH,
    scaffold_docker,
)
from mythic_vibe_cli.commands import cmd_docker_dispatch, cmd_docker_scaffold
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR


class ScaffoldDockerTests(unittest.TestCase):
    def test_python_stack_writes_three_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\n', encoding="utf-8"
            )
            result = scaffold_docker(root)
            dockerfile = (root / DOCKERFILE_PATH).read_text(encoding="utf-8")
            dockerignore_exists = (root / DOCKERIGNORE_PATH).is_file()
            compose = (root / DOCKER_COMPOSE_PATH).read_text(encoding="utf-8")
        self.assertEqual(result.written_count, 3)
        self.assertIn("python:3.12-slim", dockerfile)
        self.assertTrue(dockerignore_exists)
        self.assertIn("python-app", compose)

    def test_node_stack_uses_node_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text('{"name":"x"}', encoding="utf-8")
            result = scaffold_docker(root)
            dockerfile = (root / DOCKERFILE_PATH).read_text(encoding="utf-8")
            compose = (root / DOCKER_COMPOSE_PATH).read_text(encoding="utf-8")
        self.assertIn("node:20-alpine", dockerfile)
        self.assertIn("node-app", compose)
        self.assertEqual(result.stack.primary_language, "node")

    def test_rust_stack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Cargo.toml").write_text("[package]\n", encoding="utf-8")
            scaffold_docker(root)
            dockerfile = (root / DOCKERFILE_PATH).read_text(encoding="utf-8")
        self.assertIn("rust:", dockerfile)
        self.assertIn("cargo build --release", dockerfile)

    def test_go_stack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "go.mod").write_text("module x\n", encoding="utf-8")
            scaffold_docker(root)
            dockerfile = (root / DOCKERFILE_PATH).read_text(encoding="utf-8")
        self.assertIn("golang:", dockerfile)
        self.assertIn("go build", dockerfile)

    def test_unknown_stack_falls_back_to_todo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scaffold_docker(root)
            dockerfile = (root / DOCKERFILE_PATH).read_text(encoding="utf-8")
        self.assertIn("debian:bookworm-slim", dockerfile)
        self.assertIn("Configure mythic-vibe docker scaffold", dockerfile)

    def test_dockerignore_lists_security_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scaffold_docker(root)
            ignore = (root / DOCKERIGNORE_PATH).read_text(encoding="utf-8")
        for forbidden in (".env", "*.pem", "*.key", "mythic/"):
            self.assertIn(forbidden, ignore)

    def test_does_not_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / DOCKERFILE_PATH).write_text(
                "# pre-existing\n", encoding="utf-8"
            )
            result = scaffold_docker(root)
            content = (root / DOCKERFILE_PATH).read_text(encoding="utf-8")
        # Dockerfile skipped; the other two files still wrote.
        self.assertEqual(result.written_count, 2)
        self.assertIn("pre-existing", content)
        skipped = [f for f in result.files if f.skipped_reason]
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0].target.name, "Dockerfile")

    def test_force_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / DOCKERFILE_PATH).write_text(
                "# pre-existing\n", encoding="utf-8"
            )
            result = scaffold_docker(root, force=True)
            content = (root / DOCKERFILE_PATH).read_text(encoding="utf-8")
        self.assertEqual(result.written_count, 3)
        self.assertNotIn("pre-existing", content)

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = scaffold_docker(root, dry_run=True)
            files_present = [
                (root / DOCKERFILE_PATH).is_file(),
                (root / DOCKERIGNORE_PATH).is_file(),
                (root / DOCKER_COMPOSE_PATH).is_file(),
            ]
        self.assertEqual(result.written_count, 0)
        self.assertEqual(files_present, [False, False, False])
        # All three previews still rendered.
        self.assertEqual(len(result.files), 3)


# ---- cmd_docker_scaffold ---------------------------------------------


class CmdDockerScaffoldTests(unittest.TestCase):
    def _ns(self, path: str, **overrides: object) -> argparse.Namespace:
        base = dict(path=path, force=False, dry_run=False, json=True)
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_dry_run_returns_previews(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\n', encoding="utf-8"
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_docker_scaffold(self._ns(str(root), dry_run=True))
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("previews", payload)
        self.assertEqual(set(payload["previews"]),
                         {"Dockerfile", ".dockerignore", "docker-compose.yml"})

    def test_real_run_writes_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\n', encoding="utf-8"
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_docker_scaffold(self._ns(str(root)))
            payload = json.loads(buf.getvalue())
            files_present = (root / DOCKERFILE_PATH).is_file()
        self.assertEqual(exit_code, SUCCESS)
        self.assertTrue(files_present)
        self.assertEqual(payload["result"]["written_count"], 3)


class CmdDockerDispatchTests(unittest.TestCase):
    def test_unknown_subcommand(self) -> None:
        from contextlib import redirect_stderr

        ns = argparse.Namespace(docker_command="ghost")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = cmd_docker_dispatch(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)


class DockerArgparseTests(unittest.TestCase):
    def test_scaffold_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["docker", "scaffold", "--force"])
        self.assertEqual(ns.command, "docker")
        self.assertEqual(ns.docker_command, "scaffold")
        self.assertTrue(ns.force)


if __name__ == "__main__":
    unittest.main()
