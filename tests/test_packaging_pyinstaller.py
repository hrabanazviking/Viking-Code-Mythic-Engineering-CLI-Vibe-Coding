"""Phase 21.2 — PyInstaller spec + entrypoint + release-binaries
workflow structural sanity.

The actual freeze build needs the PyInstaller toolchain and runs in
the GitHub Actions matrix; here we lint the spec text + verify the
entrypoint shim imports cleanly + check the release workflow's
matrix shape. Catches the "renamed something but forgot to update
the spec" regression at PR time instead of release time.
"""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PYINSTALLER_DIR = REPO_ROOT / "packaging" / "pyinstaller"
SPEC_PATH = PYINSTALLER_DIR / "mythic-vibe.spec"
ENTRYPOINT_PATH = PYINSTALLER_DIR / "entrypoint.py"
RELEASE_BINARIES_WORKFLOW = (
    REPO_ROOT / ".github" / "workflows" / "release-binaries.yml"
)


class PyInstallerSpecTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            SPEC_PATH.is_file(),
            f"PyInstaller spec missing at {SPEC_PATH}",
        )
        self.raw = SPEC_PATH.read_text(encoding="utf-8")

    def test_uses_entrypoint_shim(self) -> None:
        """The Analysis() call must reference the entrypoint shim
        at packaging/pyinstaller/entrypoint.py — that's the
        importable script PyInstaller's static analyzer roots from."""
        # The spec uses a relative path because PyInstaller resolves
        # script paths relative to the spec file's directory.
        self.assertIn('Analysis(\n    ["entrypoint.py"]', self.raw)

    def test_collects_resource_data_files(self) -> None:
        """resources/schemas/*.json must end up bundled. PyInstaller
        won't grab them automatically; the spec's collect_data_files
        call is what gets them in."""
        self.assertIn("collect_data_files", self.raw)
        self.assertIn('includes=["resources/schemas/*.json"', self.raw)

    def test_excludes_optional_dependency_extras(self) -> None:
        """The standalone binary is the stdlib-only base. Every
        optional extra (ai / tui / ux / otel) and every test/lint/
        type-only dep must be in excludes so PyInstaller doesn't
        bundle them. Operators who need extras stick with the pip
        flow."""
        for excluded in (
            "anthropic",
            "openai",
            "google",
            "textual",
            "rich",
            "opentelemetry",
            "hypothesis",
            "pytest",
            "mypy",
            "ruff",
        ):
            self.assertIn(
                f'"{excluded}"', self.raw,
                f"missing exclude entry for {excluded}",
            )

    def test_console_application(self) -> None:
        """CLI tool — must keep stdio attached. windowed=True would
        suppress stdout/stderr on Windows, breaking the smoke
        commands."""
        self.assertIn("console=True", self.raw)

    def test_no_upx_compression(self) -> None:
        """UPX corrupts macOS code signatures and triggers Windows
        Defender false positives. The spec opts out so future
        signing slices (PH-21.5) work cleanly."""
        self.assertIn("upx=False", self.raw)

    def test_target_arch_inherits_from_runner(self) -> None:
        """PyInstaller picks up the runner's host arch when target_arch
        is None. The matrix delivers per-arch binaries by running
        on per-arch runners — explicit target_arch would override
        that and break the macos-arm64 row."""
        self.assertIn("target_arch=None", self.raw)

    def test_lists_runtime_hidden_imports(self) -> None:
        """Conditionally-imported modules need to be in
        hiddenimports; static analysis can miss imports inside
        function bodies. The spec covers the model_catalog freshness
        path, doctor_fix lazy import, and ai.route on-demand load."""
        for module in (
            "mythic_vibe_cli.ai.providers.model_catalog",
            "mythic_vibe_cli.doctor_fix",
            "mythic_vibe_cli.ai.route",
        ):
            self.assertIn(
                f'"{module}"', self.raw,
                f"missing hidden-import for {module}",
            )

    def test_tomli_fallback_in_hidden_imports(self) -> None:
        """tomllib is stdlib in 3.11+; tomli is the 3.10 fallback.
        Both must be hidden-imported so the binary works against
        either Python version when frozen."""
        self.assertIn('"tomllib"', self.raw)
        self.assertIn('"tomli"', self.raw)


class EntrypointShimTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            ENTRYPOINT_PATH.is_file(),
            f"PyInstaller entrypoint missing at {ENTRYPOINT_PATH}",
        )
        self.raw = ENTRYPOINT_PATH.read_text(encoding="utf-8")

    def test_imports_cli_main(self) -> None:
        """The shim must call mythic_vibe_cli.cli.main() so the
        binary's behavior matches a pip-installed CLI exactly."""
        self.assertRegex(
            self.raw,
            r"from\s+mythic_vibe_cli\.cli\s+import\s+main",
        )

    def test_propagates_exit_code(self) -> None:
        """sys.exit(main()) — anything else (bare main(), no exit)
        breaks the doctor-non-zero-on-errors contract."""
        self.assertIn("sys.exit(main())", self.raw)

    def test_shim_imports_cleanly(self) -> None:
        """The shim is short enough that any import error here
        means the spec or entrypoint diverged. Compile it as a
        sanity check."""
        compile(self.raw, str(ENTRYPOINT_PATH), "exec")


class ReleaseBinariesWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            RELEASE_BINARIES_WORKFLOW.is_file(),
            f"release-binaries.yml missing at {RELEASE_BINARIES_WORKFLOW}",
        )
        self.raw = RELEASE_BINARIES_WORKFLOW.read_text(encoding="utf-8")

    def test_triggers_on_version_tags(self) -> None:
        # Same trigger semantics as release.yml + release-oci.yml.
        self.assertRegex(self.raw, r'tags:\s*\n\s+-\s+"v\*\.\*\.\*"')

    def test_supports_workflow_dispatch_for_rehearsal(self) -> None:
        # Manual trigger lets operators verify the spec compiles
        # before spending a release tag.
        self.assertIn("workflow_dispatch", self.raw)

    def test_matrix_covers_linux_macos_windows(self) -> None:
        # Per-OS matrix must include all three platforms. The
        # binary surface is meaningless without coverage of every
        # OS the CI matrix already tests.
        for runner in (
            "ubuntu-latest",
            "macos-latest",
            "windows-latest",
        ):
            self.assertIn(
                runner, self.raw,
                f"missing matrix runner: {runner}",
            )

    def test_includes_macos_intel_row(self) -> None:
        # Apple Silicon runners produce arm64 binaries; macos-13
        # is the last image with the x86_64 toolchain alongside
        # arm64. Without this row Intel-Mac operators get nothing.
        self.assertIn("macos-13", self.raw)

    def test_invokes_pyinstaller_with_spec(self) -> None:
        # The spec file is the contract; passing arbitrary CLI
        # args to pyinstaller would bypass the curated excludes /
        # hiddenimports / datas configuration.
        self.assertIn(
            "pyinstaller packaging/pyinstaller/mythic-vibe.spec",
            self.raw,
        )

    def test_runs_smoke_after_build(self) -> None:
        # Each matrix row must verify the binary actually runs.
        # Catches a botched freeze before the binary ever lands
        # in a GitHub Release.
        self.assertIn("--version", self.raw)
        self.assertIn("--help", self.raw)
        self.assertIn("doctor --json", self.raw)

    def test_emits_per_binary_sha256(self) -> None:
        # Out-of-band verification path: operators download the
        # binary + the .sha256 sidecar, run sha256sum to verify.
        self.assertIn(".sha256", self.raw)
        self.assertRegex(
            self.raw,
            r"sha256sum|shasum -a 256",
            "no per-binary sha256 emission step",
        )

    def test_uploads_to_github_release(self) -> None:
        # softprops/action-gh-release attaches binaries to the
        # release.yml-created GitHub Release for the tag.
        self.assertIn("softprops/action-gh-release", self.raw)

    def test_signs_pyinstaller_binary_with_sigstore(self) -> None:
        # Phase 21.5 — keyless signing over each per-OS PyInstaller
        # binary. The signing step must reference the dist/ path
        # the build step writes to.
        self.assertIn("sigstore/gh-action-sigstore-python", self.raw)
        self.assertIn("inputs: dist/mythic-vibe-*", self.raw)

    def test_signs_nuitka_binary_with_sigstore(self) -> None:
        # Phase 21.5 — same pattern for the Nuitka binary path.
        # Nuitka writes to dist-nuitka/ to keep the two builders'
        # outputs distinct.
        self.assertIn("inputs: dist-nuitka/mythic-vibe-nuitka-*", self.raw)


if __name__ == "__main__":
    unittest.main()
