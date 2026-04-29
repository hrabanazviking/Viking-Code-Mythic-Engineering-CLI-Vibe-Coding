from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mythic_vibe_cli import app
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR, VERIFICATION_FAILURE
from mythic_vibe_cli.method_excerpt import (
    DEFAULT_EXCERPT_CHAR_LIMIT,
    PHASE_METHOD_SECTIONS,
    ROLE_METHOD_SECTIONS,
    select_method_excerpts,
    sections_for,
)
from mythic_vibe_cli.mythic_data import DEFAULT_METHOD_NOTES, MethodStore, resolve_method_source


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
    def _write_manifest_fixture(self, root: Path, *, changed: bool = False) -> Path:
        target = root / "docs" / "mythic_source"
        target.mkdir(parents=True)
        body = b"# Method\n"
        target.joinpath("README.md").write_bytes(b"# Changed\n" if changed else body)
        target.joinpath("method_manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "source": "test-source",
                    "ref": "abc123",
                    "generated_at": "2026-04-27T00:00:00+00:00",
                    "markdown_files": 1,
                    "files": [{"path": "README.md", "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}],
                    "paths": ["README.md"],
                }
            ),
            encoding="utf-8",
        )
        return target

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

    def test_method_status_reports_project_configured_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            root.joinpath(".mythic-vibe.json").write_text(
                '{"method": {"source": "https://github.com/example/custom-method"}}',
                encoding="utf-8",
            )

            output = io.StringIO()
            with patch.dict(os.environ, {"MYTHIC_HOME": str(root / "home")}), redirect_stdout(output):
                code = app.main(["method", "status", "--path", tmp, "--json"])

            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["method"]["configured_source"], "https://github.com/example/custom-method")
            self.assertEqual(payload["method"]["source"], "fallback")

    def test_resolve_method_source_builds_github_endpoints(self) -> None:
        source = resolve_method_source("https://github.com/example/custom-method")

        self.assertEqual(source.source, "https://github.com/example/custom-method")
        self.assertEqual(
            source.readme_raw,
            "https://raw.githubusercontent.com/example/custom-method/main/README.md",
        )
        self.assertEqual(
            source.tree_api,
            "https://api.github.com/repos/example/custom-method/git/trees/main?recursive=1",
        )

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

    def test_method_diff_reports_clean_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "docs" / "mythic_source"
            target.mkdir(parents=True)
            body = b"# Method\n"
            (target / "README.md").write_bytes(body)
            (target / "method_manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source": "test",
                        "ref": "abc123",
                        "generated_at": "2026-04-27T00:00:00+00:00",
                        "markdown_files": 1,
                        "files": [{"path": "README.md", "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}],
                        "paths": ["README.md"],
                    }
                ),
                encoding="utf-8",
            )

            diff = MethodStore(app_home=Path(tmp) / "home").diff_import_manifest(target)

            self.assertTrue(diff.clean)
            self.assertEqual(diff.missing, [])
            self.assertEqual(diff.changed, [])
            self.assertEqual(diff.untracked, [])

    def test_method_diff_reports_missing_changed_and_untracked_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "docs" / "mythic_source"
            target.mkdir(parents=True)
            (target / "README.md").write_bytes(b"# Changed\n")
            (target / "extra.md").write_bytes(b"Extra\n")
            original = b"# Method\n"
            missing = b"Missing\n"
            (target / "method_manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source": "test",
                        "ref": "abc123",
                        "generated_at": "2026-04-27T00:00:00+00:00",
                        "markdown_files": 2,
                        "files": [
                            {"path": "README.md", "bytes": len(original), "sha256": hashlib.sha256(original).hexdigest()},
                            {"path": "missing.md", "bytes": len(missing), "sha256": hashlib.sha256(missing).hexdigest()},
                        ],
                        "paths": ["README.md", "missing.md"],
                    }
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["method", "diff", "--path", tmp, "--json"])

            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertFalse(payload["diff"]["clean"])
            self.assertEqual(payload["diff"]["changed"], ["README.md"])
            self.assertEqual(payload["diff"]["missing"], ["missing.md"])
            self.assertEqual(payload["diff"]["untracked"], ["extra.md"])

    def test_method_diff_requires_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stderr(output):
                code = app.main(["method", "diff", "--path", tmp])

            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("No method manifest found", output.getvalue())

    def test_method_pin_writes_reproducibility_record_for_clean_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = self._write_manifest_fixture(root)

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["method", "pin", "--path", tmp, "--note", "release baseline", "--json"])

            payload = json.loads(output.getvalue())
            pin_payload = json.loads(target.joinpath("method_pin.json").read_text(encoding="utf-8"))
            manifest_hash = hashlib.sha256(target.joinpath("method_manifest.json").read_bytes()).hexdigest()

            self.assertEqual(code, SUCCESS)
            self.assertTrue(payload["pinned"])
            self.assertEqual(pin_payload["source"], "test-source")
            self.assertEqual(pin_payload["ref"], "abc123")
            self.assertEqual(pin_payload["manifest_sha256"], manifest_hash)
            self.assertEqual(pin_payload["note"], "release baseline")

    def test_method_pin_dry_run_does_not_write_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = self._write_manifest_fixture(root)

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["method", "pin", "--path", tmp, "--dry-run", "--json"])

            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertFalse(payload["pinned"])
            self.assertFalse(target.joinpath("method_pin.json").exists())

    def test_method_pin_refuses_dirty_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = self._write_manifest_fixture(root, changed=True)

            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(["method", "pin", "--path", tmp, "--json"])

            payload = json.loads(output.getvalue())

            self.assertEqual(code, VERIFICATION_FAILURE)
            self.assertFalse(payload["pinned"])
            self.assertEqual(payload["diff"]["changed"], ["README.md"])
            self.assertFalse(target.joinpath("method_pin.json").exists())


class MethodExcerptSelectorTests(unittest.TestCase):
    def _seed_corpus(self, root: Path) -> Path:
        corpus = root / "docs" / "mythic_source"
        corpus.mkdir(parents=True)
        (corpus / "principles.md").write_text(
            "# Principles\n\n"
            "Hold to the simplest design that solves the intent.\n\n"
            "## Sub note\n\nNested.\n\n"
            "# Workflow\n\n"
            "Intent -> Constraints -> Architecture.\n",
            encoding="utf-8",
        )
        (corpus / "verification.md").write_text(
            "# Verification Method\n\n"
            "Verify that result matches intent, not just that code ran.\n\n"
            "# Failure Modes\n\n"
            "Watch for silent test skips and stale snapshots.\n",
            encoding="utf-8",
        )
        return corpus

    def test_sections_for_role_takes_priority_over_phase(self) -> None:
        self.assertEqual(sections_for("Auditor", "intent"), ROLE_METHOD_SECTIONS["Auditor"])

    def test_sections_for_falls_back_to_phase_when_role_unknown(self) -> None:
        self.assertEqual(sections_for(None, "verify"), PHASE_METHOD_SECTIONS["verify"])

    def test_sections_for_returns_empty_when_neither_known(self) -> None:
        self.assertEqual(sections_for("Bystander", "loiter"), ())

    def test_select_method_excerpts_picks_matching_headings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corpus = self._seed_corpus(Path(tmp))

            excerpts = select_method_excerpts(corpus, ("principles", "verification method"))

            self.assertEqual([e.section for e in excerpts], ["principles", "verification method"])
            principles = excerpts[0]
            self.assertEqual(principles.heading, "Principles")
            self.assertIn("simplest design", principles.text)
            self.assertIn("Nested.", principles.text)
            self.assertEqual(principles.source_path, "principles.md")
            self.assertFalse(principles.truncated)
            verification = excerpts[1]
            self.assertEqual(verification.heading, "Verification Method")
            self.assertIn("matches intent", verification.text)
            self.assertEqual(verification.source_path, "verification.md")

    def test_select_method_excerpts_returns_empty_when_corpus_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                select_method_excerpts(Path(tmp) / "missing", ("principles",)),
                [],
            )

    def test_select_method_excerpts_truncates_long_bodies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp) / "corpus"
            corpus.mkdir()
            big_body = "lorem ipsum " * 200
            (corpus / "big.md").write_text(f"# Workflow\n\n{big_body}\n", encoding="utf-8")

            excerpts = select_method_excerpts(corpus, ("workflow",), char_limit=80)

            self.assertEqual(len(excerpts), 1)
            self.assertTrue(excerpts[0].truncated)
            self.assertLessEqual(len(excerpts[0].text), 81)
            self.assertTrue(excerpts[0].text.endswith("…"))

    def test_select_method_excerpts_skips_manifest_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp) / "corpus"
            corpus.mkdir()
            (corpus / "method_manifest.json").write_text(
                "# Workflow\n\nMethod content stored in manifest.\n",
                encoding="utf-8",
            )
            (corpus / "real.md").write_text(
                "# Workflow\n\nReal content here.\n",
                encoding="utf-8",
            )

            excerpts = select_method_excerpts(corpus, ("workflow",))

            self.assertEqual(len(excerpts), 1)
            self.assertEqual(excerpts[0].source_path, "real.md")
            self.assertIn("Real content", excerpts[0].text)

    def test_select_method_excerpts_default_char_limit_constant(self) -> None:
        self.assertGreater(DEFAULT_EXCERPT_CHAR_LIMIT, 0)


if __name__ == "__main__":
    unittest.main()
