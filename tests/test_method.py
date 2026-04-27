from __future__ import annotations

from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mythic_vibe_cli import app
from mythic_vibe_cli.exit_codes import SUCCESS
from mythic_vibe_cli.mythic_data import DEFAULT_METHOD_NOTES, MethodStore


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class MethodCommandTests(unittest.TestCase):
    def test_method_status_reports_fallback_profile_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with patch.dict(os.environ, {"MYTHIC_HOME": tmp}), redirect_stdout(output):
                code = app.main(["method", "status", "--json"])

            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["command"], "method status")
            self.assertEqual(payload["method"]["source"], "fallback")
            self.assertEqual(payload["method"]["profile"], "fallback")
            self.assertFalse(payload["method"]["cached"])
            self.assertIn("workflow", payload["method"]["sections"])
            self.assertIn("verification method", payload["method"]["sections"])

    def test_fallback_method_profile_keeps_the_full_seven_phase_loop(self) -> None:
        expected = ["1) Intent", "2) Constraints", "3) Architecture", "4) Plan", "5) Build", "6) Verify", "7) Reflect"]

        for phase_heading in expected:
            with self.subTest(phase_heading=phase_heading):
                self.assertIn(phase_heading, DEFAULT_METHOD_NOTES)

    def test_method_status_uses_cached_corpus_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = Path(tmp) / "method_cache.json"
            cache_file.write_text(
                json.dumps({"source": "https://example.test/method", "content": "# Canonical Method\n\nUse the work loop."}),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"MYTHIC_HOME": tmp}):
                status = MethodStore().status()

            self.assertEqual(status.source, "https://example.test/method")
            self.assertEqual(status.profile, "canonical-cache")
            self.assertTrue(status.cached)
            self.assertEqual(status.freshness, "cached")

    def test_import_all_markdown_writes_manifest_with_file_hashes(self) -> None:
        tree_payload = {
            "sha": "abc123",
            "tree": [
                {"type": "blob", "path": "README.md"},
                {"type": "blob", "path": "docs/guide.md"},
                {"type": "blob", "path": "image.png"},
            ],
        }
        bodies = {
            "README.md": "# Method\n",
            "docs/guide.md": "Guide text\n",
        }

        def fake_urlopen(request: object, timeout: int = 20) -> FakeResponse:
            url = request.full_url  # type: ignore[attr-defined]
            if "git/trees" in url:
                return FakeResponse(json.dumps(tree_payload).encode("utf-8"))
            for rel_path, body in bodies.items():
                if url.endswith(rel_path):
                    return FakeResponse(body.encode("utf-8"))
            raise AssertionError(f"Unexpected URL: {url}")

        with tempfile.TemporaryDirectory() as tmp, patch("urllib.request.urlopen", side_effect=fake_urlopen):
            target = Path(tmp) / "method"
            manifest = MethodStore(app_home=Path(tmp) / "home").import_all_markdown(target)

            manifest_payload = json.loads((target / "method_manifest.json").read_text(encoding="utf-8"))
            index_payload = json.loads((target / "_import_index.json").read_text(encoding="utf-8"))

            self.assertEqual(manifest.ref, "abc123")
            self.assertEqual(manifest_payload["schema_version"], 1)
            self.assertEqual(manifest_payload["markdown_files"], 2)
            self.assertEqual(manifest_payload["paths"], ["README.md", "docs/guide.md"])
            self.assertEqual(index_payload, manifest_payload)
            self.assertEqual(manifest_payload["files"][0]["sha256"], hashlib.sha256(b"# Method\n").hexdigest())
            self.assertTrue((target / "README.md").exists())
            self.assertTrue((target / "docs" / "guide.md").exists())


if __name__ == "__main__":
    unittest.main()
