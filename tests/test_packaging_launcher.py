"""Phase 22.1 — Rust launcher scaffold structural sanity.

The actual cargo build runs in CI (cargo not always present in
the unit-test runner). Here we lint the Cargo.toml + src/main.rs
+ release-launcher.yml shape so renaming a public function or
dropping a workflow step gets caught at PR time instead of release
time.

Foundation-level: these tests check the scaffold's contract, not
the launcher's runtime behavior. Runtime tests live in the Rust
crate itself (`cargo test`).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER_DIR = REPO_ROOT / "packaging" / "launcher"
CARGO_TOML = LAUNCHER_DIR / "Cargo.toml"
MAIN_RS = LAUNCHER_DIR / "src" / "main.rs"
LAUNCHER_README = LAUNCHER_DIR / "README.md"
RELEASE_LAUNCHER_WORKFLOW = (
    REPO_ROOT / ".github" / "workflows" / "release-launcher.yml"
)


class LauncherCargoManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            CARGO_TOML.is_file(),
            f"Cargo.toml missing at {CARGO_TOML}",
        )
        self.raw = CARGO_TOML.read_text(encoding="utf-8")

    def test_declares_crate_name(self) -> None:
        # The binary name is the operator-visible identity — must
        # be stable across releases.
        self.assertRegex(
            self.raw, r'name\s*=\s*"mythic-vibe-launcher"',
        )

    def test_declares_apache_2_0_license(self) -> None:
        # Same SPDX license as the rest of the project.
        self.assertRegex(self.raw, r'license\s*=\s*"Apache-2\.0"')

    def test_pins_minimum_rust_version(self) -> None:
        # rust-version pins the MSRV so a future toolchain bump is
        # an explicit Cargo.toml edit, not a silent CI break.
        self.assertRegex(self.raw, r'rust-version\s*=\s*"\d+\.\d+"')

    def test_declares_required_runtime_deps(self) -> None:
        # The launcher's MVP needs HTTP + archive extraction +
        # cache-dir + JSON + sha256 + error handling. Each must
        # appear at top level of [dependencies].
        for dep in ("ureq", "flate2", "tar", "zstd", "dirs",
                    "serde", "serde_json", "sha2", "hex", "anyhow"):
            self.assertTrue(
                re.search(rf'^\s*{dep}\s*=', self.raw, re.MULTILINE),
                f"missing runtime dep: {dep}",
            )

    def test_release_profile_optimizes_for_size(self) -> None:
        # Operators care about download size more than compile
        # time for a launcher shim. The release profile pins
        # size-optimized flags.
        self.assertIn('opt-level = "z"', self.raw)
        self.assertIn("lto = true", self.raw)
        self.assertIn("strip = true", self.raw)
        self.assertIn('panic = "abort"', self.raw)


class LauncherMainRsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            MAIN_RS.is_file(),
            f"main.rs missing at {MAIN_RS}",
        )
        self.raw = MAIN_RS.read_text(encoding="utf-8")

    def test_declares_pinned_python_version(self) -> None:
        # PYTHON_VERSION is the contract operators see in the
        # cache-layout doc — bumping it is a deliberate edit.
        self.assertRegex(
            self.raw, r'pub const PYTHON_VERSION:\s*&str\s*=\s*"\d+\.\d+\.\d+"',
        )

    def test_declares_pinned_pbs_release_tag(self) -> None:
        # Bumping the python-build-standalone release tag
        # invalidates the per-arch SHA256 table the future
        # session adds — the constant exists today so the
        # change site is obvious.
        self.assertRegex(
            self.raw, r'pub const PBS_RELEASE_TAG:\s*&str\s*=\s*"\d{8}"',
        )

    def test_declares_lifecycle_functions(self) -> None:
        # The lifecycle stages must each be a named pub fn so
        # tests + future extensions can call them in isolation.
        for name in (
            "fn run(",
            "fn resolve_cache_root(",
            "fn ensure_interpreter(",
            "fn pbs_download_url(",
            "fn host_target_triple(",
            "fn python_executable_in(",
            "fn download(",
            "fn extract_archive(",
            "fn ensure_venv_with_cli(",
            "fn venv_has_cli(",
            "fn create_venv(",
            "fn pip_install_cli(",
            "fn exec_cli(",
        ):
            self.assertIn(
                name, self.raw,
                f"lifecycle function missing: {name}",
            )

    def test_supports_cache_env_override(self) -> None:
        # Operators redirect the cache via MYTHIC_LAUNCHER_CACHE
        # — used by CI runners + sandboxed environments where
        # the platform default isn't writable.
        self.assertIn("MYTHIC_LAUNCHER_CACHE", self.raw)

    def test_handles_per_arch_targets(self) -> None:
        # The host_target_triple match must cover every arch the
        # release-launcher.yml matrix builds. Missing one row
        # silently ships a launcher that errors with "unsupported
        # host" on first run.
        for triple in (
            "x86_64-unknown-linux-gnu",
            "aarch64-unknown-linux-gnu",
            "x86_64-apple-darwin",
            "aarch64-apple-darwin",
            "x86_64-pc-windows-msvc",
        ):
            self.assertIn(
                triple, self.raw,
                f"host triple missing: {triple}",
            )

    def test_supports_tarball_decompression_paths(self) -> None:
        # python-build-standalone publishes both .tar.gz + .tar.zst.
        # Both must extract cleanly.
        self.assertIn(".tar.gz", self.raw)
        self.assertIn(".tar.zst", self.raw)

    def test_uses_unix_execv_for_signal_passthrough(self) -> None:
        # On Unix execv replaces the launcher process so the CLI
        # gets PID 1 semantics (signals, exit codes, ttys all
        # pass through cleanly). Windows falls back to spawn+wait
        # because Windows lacks execv.
        self.assertIn("os::unix::process::CommandExt", self.raw)

    def test_includes_unit_tests(self) -> None:
        # The crate has its own #[cfg(test)] mod for runtime
        # behavior. Smoke-check that the test mod exists.
        self.assertIn("#[cfg(test)]", self.raw)
        self.assertIn("mod tests", self.raw)


class LauncherReadmeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            LAUNCHER_README.is_file(),
            f"launcher README missing at {LAUNCHER_README}",
        )
        self.raw = LAUNCHER_README.read_text(encoding="utf-8")

    def test_documents_cache_layout(self) -> None:
        # Operators redirecting MYTHIC_LAUNCHER_CACHE need the
        # documented expected structure. Smoke-check the doc
        # mentions the two top-level subdirs.
        self.assertIn("py-3.12.7", self.raw)
        self.assertIn("venv", self.raw)

    def test_documents_env_override(self) -> None:
        self.assertIn("MYTHIC_LAUNCHER_CACHE", self.raw)

    def test_compares_against_pyinstaller_nuitka(self) -> None:
        # The launcher is one of three strategies — the README
        # must explain when each fits to avoid operator confusion.
        self.assertIn("PyInstaller", self.raw)
        self.assertIn("Nuitka", self.raw)

    def test_lists_deferred_work(self) -> None:
        # Future sessions need to know exactly what's in scope
        # vs deferred. Smoke-check the "deferred to a future
        # session" subsection exists.
        self.assertRegex(
            self.raw, r"deferred to a future session", re.IGNORECASE,
        )


class ReleaseLauncherWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            RELEASE_LAUNCHER_WORKFLOW.is_file(),
            f"release-launcher.yml missing at {RELEASE_LAUNCHER_WORKFLOW}",
        )
        self.raw = RELEASE_LAUNCHER_WORKFLOW.read_text(encoding="utf-8")

    def test_triggers_on_version_tags(self) -> None:
        self.assertRegex(self.raw, r'tags:\s*\n\s+-\s+"v\*\.\*\.\*"')

    def test_supports_workflow_dispatch_for_rehearsal(self) -> None:
        self.assertIn("workflow_dispatch", self.raw)

    def test_matrix_covers_full_arch_grid(self) -> None:
        # The 5-row matrix must produce every binary the README
        # promises operators. Missing rows ship a launcher that's
        # advertised but not deliverable.
        for runner in (
            "ubuntu-latest",
            "ubuntu-24.04-arm",
            "macos-latest",
            "macos-13",
            "windows-latest",
        ):
            self.assertIn(
                runner, self.raw,
                f"matrix missing runner: {runner}",
            )

    def test_invokes_cargo_build_release(self) -> None:
        self.assertIn("cargo build --release", self.raw)

    def test_runs_cargo_unit_tests(self) -> None:
        # The Rust unit tests are the runtime-behavior surface;
        # the workflow must run them per matrix row.
        self.assertIn("cargo test", self.raw)

    def test_emits_per_binary_sha256(self) -> None:
        self.assertIn(".sha256", self.raw)
        self.assertRegex(
            self.raw, r"sha256sum|shasum -a 256",
        )

    def test_signs_with_sigstore(self) -> None:
        # Same Sigstore pattern as PH-21.5 — keyless signing
        # over the launcher binary.
        self.assertIn("sigstore/gh-action-sigstore-python", self.raw)

    def test_emits_slsa_build_provenance(self) -> None:
        # Same SLSA L3 pattern as PH-21.6.
        self.assertIn("actions/attest-build-provenance", self.raw)
        self.assertIn("attestations: write", self.raw)

    def test_uploads_to_github_release(self) -> None:
        self.assertIn("softprops/action-gh-release", self.raw)


if __name__ == "__main__":
    unittest.main()
