"""Tests for PH-12 Slice 12.1 — CI/CD scaffolding."""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from mythic_vibe_cli.cicd.ci_scaffold import (
    CI_WORKFLOW_PATH,
    render_ci_workflow,
    scaffold_ci_workflow,
)
from mythic_vibe_cli.cicd.stack_detector import DetectedStack, detect_stack
from mythic_vibe_cli.commands import cmd_ci_dispatch, cmd_ci_scaffold
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR


# ---- DetectedStack ---------------------------------------------------


class DetectedStackTests(unittest.TestCase):
    def test_primary_language_python_first(self) -> None:
        stack = DetectedStack(has_python=True, has_node=True)
        self.assertEqual(stack.primary_language, "python")

    def test_primary_language_unknown_for_empty(self) -> None:
        self.assertEqual(DetectedStack().primary_language, "unknown")

    def test_detected_languages_listed(self) -> None:
        stack = DetectedStack(has_python=True, has_rust=True)
        self.assertEqual(stack.detected_languages, ("python", "rust"))

    def test_to_dict_round_trip(self) -> None:
        stack = DetectedStack(
            has_python=True,
            python_test_runner="pytest",
            python_linters=("ruff",),
        )
        payload = stack.to_dict()
        self.assertEqual(payload["primary_language"], "python")
        self.assertEqual(payload["python_linters"], ["ruff"])


# ---- detect_stack -----------------------------------------------------


class DetectStackTests(unittest.TestCase):
    def test_empty_repo_returns_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stack = detect_stack(Path(tmp))
        self.assertEqual(stack.primary_language, "unknown")
        self.assertEqual(stack.detected_languages, ())

    def test_pyproject_marks_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\nrequires-python = ">=3.10"\n',
                encoding="utf-8",
            )
            stack = detect_stack(root)
        self.assertTrue(stack.has_python)
        self.assertIn(">=3.10", stack.python_min_version)

    def test_pyproject_with_ruff_and_mypy_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\n'
                "[tool.ruff]\nline-length = 100\n"
                "[tool.mypy]\nstrict = true\n",
                encoding="utf-8",
            )
            stack = detect_stack(root)
        self.assertIn("ruff", stack.python_linters)
        self.assertIn("mypy", stack.python_linters)

    def test_requirements_txt_alone_marks_python(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements.txt").write_text("pytest\n", encoding="utf-8")
            stack = detect_stack(root)
        self.assertTrue(stack.has_python)

    def test_package_json_marks_node(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(
                '{"name":"x","scripts":{"test":"jest","lint":"eslint ."}}',
                encoding="utf-8",
            )
            stack = detect_stack(root)
        self.assertTrue(stack.has_node)
        self.assertEqual(stack.node_package_manager, "npm")
        self.assertEqual(stack.node_test_command, "npm test")
        self.assertEqual(stack.node_lint_command, "npm run lint")

    def test_yarn_lock_changes_package_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text('{"name":"x"}', encoding="utf-8")
            (root / "yarn.lock").write_text("", encoding="utf-8")
            stack = detect_stack(root)
        self.assertEqual(stack.node_package_manager, "yarn")

    def test_pnpm_lock_changes_package_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text('{"name":"x"}', encoding="utf-8")
            (root / "pnpm-lock.yaml").write_text("", encoding="utf-8")
            stack = detect_stack(root)
        self.assertEqual(stack.node_package_manager, "pnpm")

    def test_cargo_marks_rust(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Cargo.toml").write_text("[package]\nname = \"x\"\n", encoding="utf-8")
            stack = detect_stack(root)
        self.assertTrue(stack.has_rust)
        self.assertEqual(stack.primary_language, "python") if stack.has_python else self.assertEqual(stack.primary_language, "rust")

    def test_go_mod_marks_go(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "go.mod").write_text("module x\n", encoding="utf-8")
            stack = detect_stack(root)
        self.assertTrue(stack.has_go)

    def test_pom_marks_java(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pom.xml").write_text("<project></project>", encoding="utf-8")
            stack = detect_stack(root)
        self.assertTrue(stack.has_java)

    def test_gemfile_marks_ruby(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Gemfile").write_text("source 'rubygems'\n", encoding="utf-8")
            stack = detect_stack(root)
        self.assertTrue(stack.has_ruby)

    def test_invalid_pyproject_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text("not [valid] toml = =", encoding="utf-8")
            stack = detect_stack(root)
        self.assertTrue(stack.has_python)  # presence still detected
        self.assertTrue(any("unparseable" in n for n in stack.notes))


# ---- render_ci_workflow ----------------------------------------------


class RenderCiWorkflowTests(unittest.TestCase):
    def test_python_template_includes_setup_python(self) -> None:
        body = render_ci_workflow(
            DetectedStack(has_python=True, python_test_runner="pytest")
        )
        self.assertIn("actions/setup-python", body)
        self.assertIn("pytest", body)

    def test_python_includes_ruff_when_detected(self) -> None:
        body = render_ci_workflow(
            DetectedStack(has_python=True, python_linters=("ruff",))
        )
        self.assertIn("ruff check", body)

    def test_python_includes_mypy_when_detected(self) -> None:
        body = render_ci_workflow(
            DetectedStack(has_python=True, python_linters=("mypy",))
        )
        self.assertIn("mypy", body)

    def test_node_template_uses_package_manager(self) -> None:
        body = render_ci_workflow(
            DetectedStack(has_node=True, node_package_manager="pnpm")
        )
        self.assertIn("setup-node", body)
        self.assertIn("pnpm install", body)

    def test_rust_template(self) -> None:
        body = render_ci_workflow(DetectedStack(has_rust=True))
        self.assertIn("cargo test", body)
        self.assertIn("clippy", body)

    def test_go_template(self) -> None:
        body = render_ci_workflow(DetectedStack(has_go=True))
        self.assertIn("setup-go", body)
        self.assertIn("go test", body)

    def test_unknown_template_has_todos(self) -> None:
        body = render_ci_workflow(DetectedStack())
        self.assertIn("TODO", body)


# ---- scaffold_ci_workflow ---------------------------------------------


class ScaffoldCiWorkflowTests(unittest.TestCase):
    def test_writes_file_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\n', encoding="utf-8"
            )
            result = scaffold_ci_workflow(root)
            target = root / CI_WORKFLOW_PATH
            target_exists = target.is_file()
        self.assertTrue(result.written)
        self.assertEqual(result.skipped_reason, "")
        self.assertTrue(target_exists)

    def test_does_not_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\n', encoding="utf-8"
            )
            target = root / CI_WORKFLOW_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# pre-existing\n", encoding="utf-8")
            result = scaffold_ci_workflow(root)
            # Read inside the with-block — tempdir is deleted on exit.
            content = target.read_text(encoding="utf-8")
        self.assertFalse(result.written)
        self.assertIn("already exists", result.skipped_reason)
        self.assertIn("pre-existing", content)

    def test_force_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\n', encoding="utf-8"
            )
            target = root / CI_WORKFLOW_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# pre-existing\n", encoding="utf-8")
            result = scaffold_ci_workflow(root, force=True)
            content = target.read_text(encoding="utf-8")
        self.assertTrue(result.written)
        self.assertNotIn("pre-existing", content)

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\n', encoding="utf-8"
            )
            result = scaffold_ci_workflow(root, dry_run=True)
            target = Path(tmp) / CI_WORKFLOW_PATH
            target_exists = target.is_file()
        self.assertFalse(target_exists)
        self.assertFalse(result.written)
        self.assertGreater(len(result.body), 0)


# ---- cmd_ci_scaffold ---------------------------------------------------


class CmdCiScaffoldTests(unittest.TestCase):
    def _ns(self, path: str, **overrides: object) -> argparse.Namespace:
        base = dict(
            path=path,
            force=False,
            dry_run=False,
            json=True,
        )
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_dry_run_returns_preview_in_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\n', encoding="utf-8"
            )
            ns = self._ns(str(root), dry_run=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_ci_scaffold(ns)
            payload = json.loads(buf.getvalue())
            target_exists = (root / CI_WORKFLOW_PATH).is_file()
        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("preview", payload)
        self.assertGreater(len(payload["preview"]), 0)
        self.assertFalse(target_exists)

    def test_real_run_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\n', encoding="utf-8"
            )
            ns = self._ns(str(root))
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_ci_scaffold(ns)
            payload = json.loads(buf.getvalue())
            target_exists = (root / CI_WORKFLOW_PATH).is_file()
        self.assertEqual(exit_code, SUCCESS)
        self.assertTrue(target_exists)
        self.assertTrue(payload["result"]["written"])

    def test_existing_file_blocks_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\n', encoding="utf-8"
            )
            target = root / CI_WORKFLOW_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# existing\n", encoding="utf-8")
            ns = self._ns(str(root), json=False)  # text path triggers write_error
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                with redirect_stdout(io.StringIO()):
                    exit_code = cmd_ci_scaffold(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)
        self.assertIn("already exists", stderr.getvalue())


class CmdCiDispatchTests(unittest.TestCase):
    def test_unknown_subcommand_returns_user_input_error(self) -> None:
        ns = argparse.Namespace(ci_command="ghost")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = cmd_ci_dispatch(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)
        self.assertIn("Unknown ci subcommand", stderr.getvalue())


class CiArgparseTests(unittest.TestCase):
    def test_scaffold_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["ci", "scaffold", "--path", ".", "--force"])
        self.assertEqual(ns.command, "ci")
        self.assertEqual(ns.ci_command, "scaffold")
        self.assertTrue(ns.force)


if __name__ == "__main__":
    unittest.main()
