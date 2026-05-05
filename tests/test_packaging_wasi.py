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

    def test_pins_wasi_sdk_release_tag(self) -> None:
        # PH-23.7 — the wasi-sdk release tag (e.g. wasi-sdk-24.0)
        # is a separate constant from the major version number,
        # so the upstream URL template can construct asset names
        # consistently across major.minor bumps.
        self.assertTrue(hasattr(self.module, "WASI_SDK_RELEASE"))
        # Format: wasi-sdk-MAJOR.MINOR (matches upstream tags).
        self.assertRegex(
            self.module.WASI_SDK_RELEASE, r"^wasi-sdk-\d+\.\d+$",
        )

    def test_declares_url_templates(self) -> None:
        # Both download URLs must be pinned at module level so a
        # future session bumping CPython or wasi-sdk minor edits
        # one place.
        self.assertTrue(
            hasattr(self.module, "CPYTHON_SOURCE_URL_TEMPLATE"),
        )
        self.assertTrue(
            hasattr(self.module, "WASI_SDK_URL_TEMPLATE"),
        )

    def test_declares_buildstepfailed_exception(self) -> None:
        # PH-23.7 — typed exception lets the driver map step
        # failures to specific exit codes (10 / 11 / 12 / 13)
        # so the CI log shows where the build broke.
        self.assertTrue(hasattr(self.module, "BuildStepFailed"))
        self.assertTrue(
            issubclass(self.module.BuildStepFailed, RuntimeError),
        )

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
        # PH-23.7 — --really-build now drives the actual cross-
        # build. We can't run the real build here (needs
        # wasi-sdk + ~10-20 minutes), so the test just confirms
        # the flag is parsed without immediate error. With our
        # cache + ensure_wasi_sdk patched to short-circuit, the
        # full pipeline would be exercised; here we just check
        # the path takes off without crashing on argparse.
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "test.wasm"
            cache = Path(tmp) / "cache"
            buf = io.StringIO()
            with mock.patch.object(sys, "stdout", buf):
                # Patch the ensure_* helpers so the cross-build
                # short-circuits before any network IO. Returns
                # a stub path that won't be a real cpython tree;
                # we expect the orchestrator to fail with a
                # non-zero return, which is fine — the test is
                # about argv parsing reaching the build path.
                with mock.patch.object(
                    self.module, "_ensure_wasi_sdk",
                    return_value=Path(tmp) / "fake-sdk",
                ):
                    with mock.patch.object(
                        self.module, "_ensure_cpython_source",
                        return_value=Path(tmp) / "fake-cpython",
                    ):
                        with mock.patch.object(
                            self.module, "_run_wasi_orchestrator",
                            return_value=0,
                        ):
                            rc = self.module.main([
                                "--output", str(output),
                                "--really-build",
                                "--cache-dir", str(cache),
                            ])
            # Expected to fail at step 7 (artifact-not-found)
            # since our stubbed dirs don't actually contain the
            # produced .wasm. Exit code 13 confirms the path
            # ran the full pipeline up to that step.
            self.assertEqual(
                rc, 13,
                "expected exit 13 (artifact-not-found) when "
                "ensure_* stubs short-circuit but copy step "
                "finds no real artifact",
            )

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

    def test_run_full_wasi_build_function_exists(self) -> None:
        # PH-23.7 — the function that drives the real cross-build.
        self.assertTrue(hasattr(self.module, "_run_full_wasi_build"))

    def test_ensure_wasi_sdk_function_exists(self) -> None:
        self.assertTrue(hasattr(self.module, "_ensure_wasi_sdk"))

    def test_ensure_cpython_source_function_exists(self) -> None:
        self.assertTrue(hasattr(self.module, "_ensure_cpython_source"))

    def test_run_wasi_orchestrator_function_exists(self) -> None:
        # The orchestrator runs the four ./Tools/wasm/wasi.py
        # steps. Pulled out so a future session can extend with
        # additional pre/post steps without touching the higher-
        # level pipeline.
        self.assertTrue(hasattr(self.module, "_run_wasi_orchestrator"))

    def test_resolve_cache_dir_honors_override(self) -> None:
        # The --cache-dir flag must take priority over env vars.
        with tempfile.TemporaryDirectory() as tmp:
            override = Path(tmp) / "explicit-cache"
            resolved = self.module._resolve_cache_dir(override)
            self.assertEqual(resolved, override)
            self.assertTrue(override.is_dir())

    def test_resolve_cache_dir_default_lands_under_cache_subdir(self) -> None:
        # Without override, should land at <home>/.cache/<subdir>
        # or under XDG_CACHE_HOME / MYTHIC_WASI_CACHE.
        resolved = self.module._resolve_cache_dir(None)
        self.assertIn(self.module.CACHE_SUBDIR, str(resolved))

    def test_wasi_sdk_os_suffix_for_supported_platforms(self) -> None:
        # The function must return a known suffix for each
        # supported runner OS.
        with mock.patch.object(sys, "platform", "linux"):
            self.assertEqual(
                self.module._wasi_sdk_os_suffix(), "x86_64-linux",
            )
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertEqual(
                self.module._wasi_sdk_os_suffix(), "x86_64-macos",
            )

    def test_wasi_sdk_os_suffix_rejects_unsupported_platform(self) -> None:
        # Windows isn't a supported wasi-sdk host upstream — the
        # function must raise BuildStepFailed rather than return
        # a wrong suffix.
        with mock.patch.object(sys, "platform", "win32"):
            with self.assertRaises(self.module.BuildStepFailed):
                self.module._wasi_sdk_os_suffix()


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

    def test_caches_wasi_sdk_and_cpython_source(self) -> None:
        """PH-23.9 — actions/cache restores + saves the wasi-sdk
        + CPython source tree between tag-push runs. Without the
        cache, every release re-downloads ~275 MB and re-extracts
        from scratch (~15-20 min); with the cache, ~5-8 min."""
        self.assertIn("actions/cache@v4", self.text)
        # The cached path is the build driver's default cache
        # root; if a future session changes _resolve_cache_dir,
        # this assertion catches the workflow staying out of sync.
        self.assertIn("~/.cache/mythic-vibe-wasi-build", self.text)

    def test_cache_key_includes_sdk_and_cpython_pins(self) -> None:
        """The cache key must be invalidated when EITHER pinned
        constant (WASI_SDK_RELEASE or CPYTHON_VERSION) bumps,
        otherwise a stale toolchain could be reused against a
        new source tree."""
        # The cache_key step reads both constants directly from
        # packaging/wasi/build.py so the workflow stays in sync.
        self.assertIn("WASI_SDK_RELEASE", self.text)
        self.assertIn("CPYTHON_VERSION", self.text)
        # The composed key includes both versions.
        self.assertIn(
            "wasi-${SDK_RELEASE}-cpython-${CPYTHON}-v1", self.text,
        )

    def test_cache_has_restore_keys_fallback(self) -> None:
        """A CPython version bump shouldn't force re-downloading
        the (unchanged) wasi-sdk tree. The restore-keys fallback
        matches just the SDK release so the SDK portion of the
        cache survives a CPython-only bump."""
        self.assertIn("restore-keys:", self.text)
        # The fallback prefix must be SDK-release-keyed only —
        # i.e. not include the CPython version segment.
        self.assertRegex(
            self.text,
            r"restore-keys:\s*\|\s*\n\s*wasi-\$\{\{\s*steps\.cache_key\.outputs\.sdk_release",
        )


if __name__ == "__main__":
    unittest.main()
