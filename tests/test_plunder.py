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


# ---------------------------------------------------------------------------
# PH-24.2 coverage push — exercise the real ``GitHubClient`` HTTP shim
# (urllib mocked). Goal: take ``plunder/github.py`` from ~46% to 95%+.
# ---------------------------------------------------------------------------


from mythic_vibe_cli.plunder.github import GitHubClient  # noqa: E402


class _GitHubFakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_GitHubFakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class GitHubClientUnitTests(unittest.TestCase):
    """Direct coverage of the urllib-based shim that real users hit."""

    def test_repo_info_to_dict_round_trips(self) -> None:
        info = GitHubRepoInfo(
            repo="x/y",
            ref="main",
            sha="aaaa",
            license_spdx_id="MIT",
            license_name="MIT License",
            html_url="https://github.com/x/y",
        )
        as_dict = info.to_dict()
        self.assertEqual(as_dict["repo"], "x/y")
        self.assertEqual(as_dict["sha"], "aaaa")
        self.assertEqual(as_dict["license_spdx_id"], "MIT")

    def test_get_json_raises_on_non_dict_payload(self) -> None:
        client = GitHubClient(token="ghp_test")
        def fake_urlopen(req, timeout=0):  # noqa: ANN001
            return _GitHubFakeResponse(b'["not a dict"]')

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(ValueError):
                client.get_json("https://api.github.com/repos/x/y")

    def test_get_json_includes_authorization_header_when_token_present(self) -> None:
        client = GitHubClient(token="ghp_secret")
        captured = {}

        def fake_urlopen(req, timeout=0):  # noqa: ANN001
            captured["auth"] = req.headers.get("Authorization")
            return _GitHubFakeResponse(b'{"ok": true}')

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            payload = client.get_json("https://api.github.com/repos/x/y")
        self.assertEqual(payload, {"ok": True})
        self.assertEqual(captured["auth"], "token ghp_secret")

    def test_get_json_omits_authorization_header_when_no_token(self) -> None:
        client = GitHubClient()
        captured = {}

        def fake_urlopen(req, timeout=0):  # noqa: ANN001
            captured["auth"] = req.headers.get("Authorization")
            return _GitHubFakeResponse(b'{"ok": true}')

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.get_json("https://api.github.com/repos/x/y")
        self.assertIsNone(captured["auth"])

    def test_inspect_repo_extracts_license_and_sha(self) -> None:
        client = GitHubClient()
        repo_payload = {
            "html_url": "https://github.com/example/source",
            "license": {"spdx_id": "Apache-2.0", "name": "Apache License 2.0"},
        }
        ref_payload = {"sha": "deadbeef"}

        responses = [repo_payload, ref_payload]

        def fake_urlopen(req, timeout=0):  # noqa: ANN001
            return _GitHubFakeResponse(json.dumps(responses.pop(0)).encode("utf-8"))

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            info = client.inspect_repo("example/source", "main")
        self.assertEqual(info.sha, "deadbeef")
        self.assertEqual(info.license_spdx_id, "Apache-2.0")
        self.assertEqual(info.license_name, "Apache License 2.0")
        self.assertTrue(info.html_url.endswith("/example/source"))

    def test_inspect_repo_handles_missing_license_block(self) -> None:
        """When ``repo.license`` is null/missing, the result should fall
        back to ``Unknown`` strings without raising."""
        client = GitHubClient()
        repo_payload: dict = {"html_url": "https://github.com/x/y"}
        ref_payload = {"sha": "abc"}
        responses = [repo_payload, ref_payload]

        def fake_urlopen(req, timeout=0):  # noqa: ANN001
            return _GitHubFakeResponse(json.dumps(responses.pop(0)).encode("utf-8"))

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            info = client.inspect_repo("x/y", "main")
        self.assertEqual(info.license_spdx_id, "Unknown")
        self.assertEqual(info.license_name, "Unknown")

    def test_get_file_decodes_base64_content(self) -> None:
        import base64

        client = GitHubClient()
        body_text = "print('borrow')\n"
        encoded = base64.b64encode(body_text.encode("utf-8")).decode("ascii")
        file_payload = {
            "type": "file",
            "encoding": "base64",
            "content": encoded,
            "sha": "f1l3sha",
            "html_url": "https://github.com/x/y/blob/main/src/tool.py",
        }

        def fake_urlopen(req, timeout=0):  # noqa: ANN001
            return _GitHubFakeResponse(json.dumps(file_payload).encode("utf-8"))

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            github_file = client.get_file("x/y", "src/tool.py", "main")
        self.assertEqual(github_file.text, body_text)
        self.assertEqual(github_file.sha, "f1l3sha")
        self.assertEqual(github_file.path, "src/tool.py")

    def test_get_file_rejects_non_file_response(self) -> None:
        client = GitHubClient()

        def fake_urlopen(req, timeout=0):  # noqa: ANN001
            return _GitHubFakeResponse(json.dumps({"type": "dir"}).encode("utf-8"))

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(ValueError):
                client.get_file("x/y", "src/", "main")

    def test_get_file_rejects_unsupported_encoding(self) -> None:
        client = GitHubClient()

        def fake_urlopen(req, timeout=0):  # noqa: ANN001
            return _GitHubFakeResponse(
                json.dumps({"type": "file", "encoding": "utf-8"}).encode("utf-8")
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with self.assertRaises(ValueError):
                client.get_file("x/y", "src/tool.py", "main")

    def test_fetch_to_cache_writes_file_under_cache_root(self) -> None:
        import base64

        client = GitHubClient()
        body_text = "borrowed body\n"
        encoded = base64.b64encode(body_text.encode("utf-8")).decode("ascii")
        file_payload = {
            "type": "file",
            "encoding": "base64",
            "content": encoded,
            "sha": "abc",
            "html_url": "https://github.com/x/y/blob/main/src/t.py",
        }

        def fake_urlopen(req, timeout=0):  # noqa: ANN001
            return _GitHubFakeResponse(json.dumps(file_payload).encode("utf-8"))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                gh_file, cache_path = client.fetch_to_cache(
                    root, "x/y", "src/t.py", "main"
                )
            self.assertTrue(cache_path.exists())
            self.assertEqual(cache_path.read_text(encoding="utf-8"), body_text)
            self.assertEqual(gh_file.text, body_text)


if __name__ == "__main__":
    unittest.main()
