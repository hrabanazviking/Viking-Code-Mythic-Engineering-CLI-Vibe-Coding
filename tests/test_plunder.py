from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mythic_vibe_cli import app
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.plunder.github import GitHubFile, GitHubRepoInfo
from mythic_vibe_cli.plunder.license import classify_license
from mythic_vibe_cli.plunder.provenance import cache_path_for


class FakeGitHubClient:
    def __init__(self, token: str = ""):
        self.token = token

    def inspect_repo(self, repo: str, ref: str) -> GitHubRepoInfo:
        return GitHubRepoInfo(
            repo=repo,
            ref=ref,
            sha="abc123",
            license_spdx_id="MIT",
            license_name="MIT License",
            html_url=f"https://github.com/{repo}",
        )

    def get_file(self, repo: str, source_path: str, ref: str) -> GitHubFile:
        return GitHubFile(
            repo=repo,
            path=source_path,
            ref=ref,
            sha="file456",
            text="print('borrowed carefully')\n",
            html_url=f"https://github.com/{repo}/blob/{ref}/{source_path}",
        )

    def fetch_to_cache(self, root: Path, repo: str, source_path: str, ref: str) -> tuple[GitHubFile, Path]:
        github_file = self.get_file(repo, source_path, ref)
        cache_path = cache_path_for(root, repo, source_path, ref)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(github_file.text, encoding="utf-8")
        return github_file, cache_path


class PlunderWorkflowTests(unittest.TestCase):
    def test_license_classifier_blocks_unknown_and_copyleft(self) -> None:
        self.assertTrue(classify_license("Apache-2.0").compatible)
        self.assertTrue(classify_license("MIT").compatible)
        self.assertTrue(classify_license("BSD-3-Clause").compatible)
        self.assertFalse(classify_license("GPL-3.0").compatible)
        self.assertIn("Do not plunder", classify_license("NOASSERTION").warning)

    def test_plan_fetch_apply_records_manifest_and_notice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {"GITHUB_TOKEN": "fake-token"}

            with patch.dict(os.environ, env, clear=False), patch("mythic_vibe_cli.commands.GitHubClient", FakeGitHubClient):
                plan_output = io.StringIO()
                with redirect_stdout(plan_output):
                    plan_code = app.main(
                        [
                            "plunder",
                            "plan",
                            "--path",
                            str(root),
                            "--repo",
                            "example/source",
                            "--source",
                            "src/tool.py",
                            "--dest",
                            "vendor/tool.py",
                            "--json",
                        ]
                    )

                fetch_output = io.StringIO()
                with redirect_stdout(fetch_output):
                    fetch_code = app.main(
                        [
                            "plunder",
                            "fetch",
                            "--path",
                            str(root),
                            "--repo",
                            "example/source",
                            "--source",
                            "src/tool.py",
                            "--ref",
                            "abc123",
                            "--json",
                        ]
                    )

            apply_output = io.StringIO()
            with redirect_stdout(apply_output):
                apply_code = app.main(["plunder", "apply", "--path", str(root), "--notice", "--json"])

            plan_payload = json.loads(plan_output.getvalue())
            fetch_payload = json.loads(fetch_output.getvalue())
            apply_payload = json.loads(apply_output.getvalue())
            manifest = json.loads((root / "mythic" / "imports" / "plunder_manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(plan_code, SUCCESS)
            self.assertEqual(fetch_code, SUCCESS)
            self.assertEqual(apply_code, SUCCESS)
            self.assertEqual(plan_payload["plan"]["license"]["spdx_id"], "MIT")
            self.assertEqual(fetch_payload["source"]["sha"], "file456")
            self.assertTrue((root / "vendor" / "tool.py").exists())
            self.assertEqual(manifest["imports"][0]["repo"], "example/source")
            self.assertEqual(manifest["imports"][0]["license"], "MIT")
            self.assertTrue((root / "NOTICE").exists())
            self.assertEqual(apply_payload["record"]["source_sha"], "file456")

    def test_apply_refuses_incompatible_plan_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic" / "imports").mkdir(parents=True)
            (root / "mythic" / "imports" / "plunder_plan.json").write_text(
                json.dumps(
                    {
                        "repo": "example/source",
                        "source_file": "src/tool.py",
                        "destination": str(root / "vendor" / "tool.py"),
                        "ref": "abc123",
                        "source_sha": "file456",
                        "license": {
                            "spdx_id": "GPL-3.0",
                            "name": "GNU General Public License v3.0",
                            "compatible": False,
                            "warning": "Do not plunder: copyleft license requires explicit review.",
                            "notes": [],
                        },
                        "modifications": "Unmodified import planned.",
                    }
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                code = app.main(["plunder", "apply", "--path", str(root)])

            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("Do not plunder", output.getvalue())


if __name__ == "__main__":
    unittest.main()
