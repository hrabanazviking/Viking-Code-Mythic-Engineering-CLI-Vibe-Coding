"""Tests for PH-12 Slice 12.3 — release helper."""

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

from mythic_vibe_cli.cicd.release import (
    Version,
    create_git_tag,
    prepare_release,
    read_pyproject_version,
    render_changelog_entry,
    write_pyproject_version,
)
from mythic_vibe_cli.commands import cmd_release
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR


# ---- Version --------------------------------------------------------


class VersionTests(unittest.TestCase):
    def test_parse_simple(self) -> None:
        v = Version.parse("1.2.3")
        self.assertEqual((v.major, v.minor, v.patch), (1, 2, 3))
        self.assertEqual(str(v), "1.2.3")

    def test_parse_with_suffix(self) -> None:
        v = Version.parse("1.2.3rc1")
        self.assertEqual(v.suffix, "rc1")
        self.assertEqual(str(v), "1.2.3rc1")

    def test_parse_invalid_raises(self) -> None:
        with self.assertRaises(ValueError):
            Version.parse("not-a-version")
        with self.assertRaises(ValueError):
            Version.parse("")

    def test_bump_patch(self) -> None:
        v = Version(1, 2, 3, "rc1")
        self.assertEqual(str(v.bump("patch")), "1.2.4")

    def test_bump_minor_resets_patch(self) -> None:
        self.assertEqual(str(Version(1, 2, 3).bump("minor")), "1.3.0")

    def test_bump_major_resets_minor_and_patch(self) -> None:
        self.assertEqual(str(Version(1, 2, 3).bump("major")), "2.0.0")

    def test_bump_unknown_kind_raises(self) -> None:
        with self.assertRaises(ValueError):
            Version(1, 0, 0).bump("magic")  # type: ignore[arg-type]


# ---- read_pyproject_version ------------------------------------------


class ReadPyprojectVersionTests(unittest.TestCase):
    def test_missing_file_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(read_pyproject_version(Path(tmp)))

    def test_pyproject_without_version_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\n', encoding="utf-8"
            )
            self.assertIsNone(read_pyproject_version(root))

    def test_pyproject_with_version_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\nversion = "1.2.3"\n',
                encoding="utf-8",
            )
            v = read_pyproject_version(root)
        self.assertIsNotNone(v)
        assert v is not None
        self.assertEqual(str(v), "1.2.3")


# ---- write_pyproject_version -----------------------------------------


class WritePyprojectVersionTests(unittest.TestCase):
    def test_replaces_version_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "pyproject.toml"
            path.write_text(
                '[project]\nname = "x"\nversion = "1.0.0"\n',
                encoding="utf-8",
            )
            ok = write_pyproject_version(root, Version(1, 1, 0))
            content = path.read_text(encoding="utf-8")
        self.assertTrue(ok)
        self.assertIn('version = "1.1.0"', content)
        self.assertNotIn('"1.0.0"', content)

    def test_missing_pyproject_returns_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(
                write_pyproject_version(Path(tmp), Version(1, 0, 0))
            )

    def test_no_version_line_returns_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\n', encoding="utf-8"
            )
            self.assertFalse(write_pyproject_version(root, Version(1, 0, 0)))


# ---- render_changelog_entry ------------------------------------------


class RenderChangelogTests(unittest.TestCase):
    def test_default_stub(self) -> None:
        body = render_changelog_entry(new_version=Version(1, 2, 3))
        self.assertIn("## v1.2.3", body)
        self.assertIn("TODO", body)

    def test_summary_substituted(self) -> None:
        body = render_changelog_entry(
            new_version=Version(1, 2, 3),
            summary="Hot fix for x",
            bullets=["fixed crash on startup", "tightened auth path"],
        )
        self.assertIn("Hot fix for x", body)
        self.assertIn("fixed crash on startup", body)
        self.assertIn("tightened auth path", body)


# ---- create_git_tag --------------------------------------------------


class CreateGitTagTests(unittest.TestCase):
    def test_real_tag_creation_in_temp_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Initialise a real git repo.
            subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(root),
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Tester"],
                cwd=str(root),
                check=True,
            )
            (root / "README.md").write_text("# x\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=str(root), check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "init"],
                cwd=str(root),
                check=True,
            )
            result = create_git_tag(root, "v1.0.0", message="release v1.0.0")
        self.assertTrue(result.created)
        self.assertEqual(result.tag, "v1.0.0")

    def test_missing_git_returns_clean_error(self) -> None:
        with mock.patch("subprocess.run", side_effect=FileNotFoundError("git")):
            with tempfile.TemporaryDirectory() as tmp:
                result = create_git_tag(Path(tmp), "v1.0.0")
        self.assertFalse(result.created)
        self.assertIn("git binary not found", result.error)


# ---- prepare_release -------------------------------------------------


class PrepareReleaseTests(unittest.TestCase):
    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\nversion = "1.0.0"\n',
                encoding="utf-8",
            )
            result = prepare_release(root, bump="minor")
            content = (root / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual(str(result.new_version), "1.1.0")
        self.assertFalse(result.pyproject_updated)
        self.assertIn('"1.0.0"', content)
        self.assertTrue(result.dry_run)

    def test_apply_writes_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\nversion = "1.0.0"\n',
                encoding="utf-8",
            )
            result = prepare_release(root, bump="major", apply=True)
            content = (root / "pyproject.toml").read_text(encoding="utf-8")
        self.assertEqual(str(result.new_version), "2.0.0")
        self.assertTrue(result.pyproject_updated)
        self.assertIn('"2.0.0"', content)

    def test_create_tag_invokes_git_tag(self) -> None:
        from mythic_vibe_cli.cicd.release import GitTagResult

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\nversion = "1.0.0"\n',
                encoding="utf-8",
            )
            with mock.patch(
                "mythic_vibe_cli.cicd.release.create_git_tag",
                return_value=GitTagResult(tag="v1.0.1", created=True),
            ) as mock_tag:
                result = prepare_release(
                    root, bump="patch", apply=True, create_tag=True
                )
            mock_tag.assert_called_once()
        self.assertIsNotNone(result.tag)
        assert result.tag is not None
        self.assertTrue(result.tag.created)

    def test_missing_pyproject_returns_clean_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = prepare_release(Path(tmp), bump="patch")
        self.assertIsNone(result.current_version)
        self.assertIsNone(result.new_version)
        self.assertTrue(any("missing" in n for n in result.notes))


# ---- cmd_release ------------------------------------------------------


class CmdReleaseTests(unittest.TestCase):
    def _ns(self, path: str, **overrides: object) -> argparse.Namespace:
        base = dict(
            path=path,
            bump="patch",
            apply=False,
            tag=False,
            summary="",
            json=True,
        )
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_dry_run_returns_success_with_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "x"\nversion = "1.0.0"\n',
                encoding="utf-8",
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_release(self._ns(str(root), bump="minor"))
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertEqual(payload["result"]["new_version"], "1.1.0")
        self.assertTrue(payload["result"]["dry_run"])

    def test_invalid_bump_returns_user_input_error(self) -> None:
        ns = argparse.Namespace(
            path=".", bump="huge", apply=False, tag=False, summary="", json=False
        )
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = cmd_release(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)
        self.assertIn("--bump", stderr.getvalue())

    def test_missing_pyproject_returns_user_input_error_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stderr = io.StringIO()
            ns = self._ns(str(tmp), json=False)
            with redirect_stderr(stderr):
                with redirect_stdout(io.StringIO()):
                    exit_code = cmd_release(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)
        self.assertIn("pyproject.toml", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
