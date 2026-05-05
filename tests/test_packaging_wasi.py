"""Phase 22.3 — WASI build script + workflow structural sanity.

The actual CPython WASI cross-build lives behind --really-build
on packaging/wasi/build.py and is foundation-deferred. These
tests verify the build script's contract + the workflow shape
so a future session implementing the real build only has to
flip flags, not redesign the contract.
"""

from __future__ import annotations

import importlib.util
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parent.parent
WASI_DIR = REPO_ROOT / "packaging" / "wasi"
WASI_BUILD = WASI_DIR / "build.py"
WASI_README = WASI_DIR / "README.md"
RELEASE_WASI_WORKFLOW = (
    REPO_ROOT / ".github" / "workflows" / "release-wasi.yml"
)


def _load_wasi_build_module():
    """Import packaging/wasi/build.py via importlib so tests
    don't rely on the test-runner working directory."""
    spec = importlib.util.spec_from_file_location(
        "_wasi_build", str(WASI_BUILD)
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"failed to load spec for {WASI_BUILD}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WasiBuildScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            WASI_BUILD.is_file(),
            f"WASI build script missing at {WASI_BUILD}",
        )
        self.module = _load_wasi_build_module()

    def test_module_imports_cleanly(self) -> None:
        # If the module imports without raising, its top-level
        # structure is at minimum syntax-valid.
        self.assertTrue(hasattr(self.module, "main"))

    def test_pins_cpython_version(self) -> None:
        # CPython version must be pinned at module level so a
        # future session bumping it is an explicit edit.
        self.assertTrue(hasattr(self.module, "CPYTHON_VERSION"))
        self.assertRegex(
            self.module.CPYTHON_VERSION, r"^\d+\.\d+\.\d+$",
        )

    def test_pins_wasi_sdk_version(self) -> None:
        self.assertTrue(hasattr(self.module, "WASI_SDK_VERSION"))

    def test_main_supports_output_flag(self) -> None:
        # The build script must let the workflow specify the
        # output path so renaming is the workflow's responsibility,
        # not the script's.
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "test.wasm"
            buf = io.StringIO()
            with mock.patch.object(sys, "stdout", buf):
                rc = self.module.main(["--output", str(output)])
            self.assertEqual(rc, 0)
            self.assertTrue(output.is_file())

    def test_main_supports_really_build_flag(self) -> None:
        # --really-build is the foundation-deferred path; today
        # it returns 0 with a clear log message. A future session
        # implements the real cross-build behind this flag.
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "test.wasm"
            buf = io.StringIO()
            with mock.patch.object(sys, "stdout", buf):
                rc = self.module.main([
                    "--output", str(output),
                    "--really-build",
                ])
            self.assertEqual(rc, 0)

    def test_emits_placeholder_when_not_really_building(self) -> None:
        # Without --really-build the script writes a non-wasm
        # placeholder so future-session implementers know the
        # contract: the workflow path stays green, but the
        # output isn't a real wasm yet.
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "test.wasm"
            buf = io.StringIO()
            with mock.patch.object(sys, "stdout", buf):
                self.module.main(["--output", str(output)])
            content = output.read_bytes()
        self.assertIn(b"placeholder", content.lower())
        self.assertIn(b"foundation", content.lower())

    def test_shell_helper_exists(self) -> None:
        # The shell() helper is the future-session hook for the
        # real cross-build's subprocess invocations. Its existence
        # documents the contract.
        self.assertTrue(hasattr(self.module, "shell"))
        self.assertTrue(callable(self.module.shell))


class WasiReadmeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            WASI_README.is_file(),
            f"WASI README missing at {WASI_README}",
        )
        self.text = WASI_README.read_text(encoding="utf-8")

    def test_documents_compatibility_audit(self) -> None:
        # The "what works in WASI" section must enumerate stdlib
        # modules so future operators / contributors know the
        # supported surface.
        self.assertIn("argparse", self.text)
        self.assertIn("subprocess", self.text)

    def test_documents_three_build_paths(self) -> None:
        # Path A (CPython upstream) / Path B (Pyodide) / Path C
        # (py2wasm) are the three considered approaches; future
        # sessions revisiting the path choice need the rationale.
        self.assertIn("CPython upstream", self.text)
        self.assertIn("Pyodide", self.text)
        self.assertIn("py2wasm", self.text)

    def test_records_chosen_path(self) -> None:
        # Decision capture — Path A chosen with rationale.
        self.assertTrue(
            re.search(r"Path A.*chosen", self.text, re.IGNORECASE),
            "README must record Path A as the chosen build path",
        )

    def test_lists_deferred_work(self) -> None:
        self.assertTrue(
            re.search(r"deferred", self.text, re.IGNORECASE),
            "README must enumerate deferred work for future sessions",
        )

    def test_documents_foundation_status(self) -> None:
        # The foundation-vs-real-build status must be explicit
        # so future sessions know exactly what to wire next.
        self.assertIn("foundation", self.text.lower())


class ReleaseWasiWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            RELEASE_WASI_WORKFLOW.is_file(),
            f"release-wasi.yml missing at {RELEASE_WASI_WORKFLOW}",
        )
        self.text = RELEASE_WASI_WORKFLOW.read_text(encoding="utf-8")

    def test_triggers_on_version_tags(self) -> None:
        self.assertRegex(self.text, r'tags:\s*\n\s+-\s+"v\*\.\*\.\*"')

    def test_supports_workflow_dispatch_for_rehearsal(self) -> None:
        self.assertIn("workflow_dispatch", self.text)

    def test_invokes_build_script(self) -> None:
        # The workflow must call packaging/wasi/build.py — not
        # an arbitrary inline build command — so the build
        # contract stays version-controlled in build.py.
        self.assertIn("python packaging/wasi/build.py", self.text)

    def test_renames_artifact_with_version_suffix(self) -> None:
        # Asset name follows the project convention:
        #   mythic-vibe-${VERSION}-wasi-experimental.wasm
        # The "experimental" suffix flags the v2.0 reduced-
        # functionality status to operators.
        self.assertIn("wasi-experimental.wasm", self.text)

    def test_signs_with_sigstore(self) -> None:
        # PH-21.5 pattern over the .wasm file.
        self.assertIn("sigstore/gh-action-sigstore-python", self.text)

    def test_emits_slsa_attestation(self) -> None:
        self.assertIn("actions/attest-build-provenance", self.text)
        self.assertIn("attestations: write", self.text)

    def test_uploads_to_github_release(self) -> None:
        self.assertIn("softprops/action-gh-release", self.text)


if __name__ == "__main__":
    unittest.main()
