"""Phase 21.3 — Nuitka build driver + workflow structural sanity.

We can't run the actual Nuitka build here (3-8 minutes per
platform, requires the Nuitka toolchain). Instead we lint the
build driver (importable, callable, builds the right argv list)
and the workflow's Nuitka matrix shape. Catches "renamed something
but forgot to update X" regressions at PR time.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
NUITKA_BUILD_PATH = REPO_ROOT / "packaging" / "nuitka" / "build.py"
RELEASE_BINARIES_WORKFLOW = (
    REPO_ROOT / ".github" / "workflows" / "release-binaries.yml"
)


def _load_build_module():
    """Import packaging/nuitka/build.py without polluting sys.path.

    The packaging/ directory isn't a Python package; we load the
    build script via importlib so tests don't depend on the test
    runner's working directory.
    """
    spec = importlib.util.spec_from_file_location(
        "_nuitka_build", str(NUITKA_BUILD_PATH)
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"failed to load spec for {NUITKA_BUILD_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class NuitkaBuildDriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            NUITKA_BUILD_PATH.is_file(),
            f"Nuitka build driver missing at {NUITKA_BUILD_PATH}",
        )
        self.module = _load_build_module()

    def test_build_command_returns_argv_list(self) -> None:
        """build_command must return a list of strings — subprocess
        invocations require argv lists, and shell=True is forbidden
        in the workflow path."""
        cmd = self.module.build_command(Path("/tmp/dist-nuitka"))
        self.assertIsInstance(cmd, list)
        for token in cmd:
            self.assertIsInstance(token, str)

    def test_build_command_invokes_nuitka_module(self) -> None:
        """The driver must call ``python -m nuitka`` so the same
        Python that imports the project resolves Nuitka — avoids
        version mismatches between a global Nuitka and the
        runner's Python."""
        cmd = self.module.build_command(Path("/tmp/dist-nuitka"))
        self.assertIn("-m", cmd)
        self.assertIn("nuitka", cmd)

    def test_build_command_uses_standalone_onefile(self) -> None:
        """Standalone + onefile is the contract — operators
        download a single executable. Anything else breaks the
        PH-21.3 deliverable."""
        cmd = self.module.build_command(Path("/tmp/dist-nuitka"))
        self.assertIn("--standalone", cmd)
        self.assertIn("--onefile", cmd)

    def test_build_command_includes_project_package(self) -> None:
        """Nuitka's static analyzer otherwise tracks only direct
        imports from the entrypoint; the entrypoint shim only
        imports cli.main, so the rest of mythic_vibe_cli would
        be missed without explicit --include-package."""
        cmd = self.module.build_command(Path("/tmp/dist-nuitka"))
        self.assertIn(
            "--include-package=mythic_vibe_cli", cmd,
            "missing --include-package flag for the project package",
        )

    def test_build_command_includes_package_data(self) -> None:
        """Resources (schemas/*.json) ship with the package and
        must be bundled into the binary — operators running
        offline can't pull them from PyPI."""
        cmd = self.module.build_command(Path("/tmp/dist-nuitka"))
        self.assertIn(
            "--include-package-data=mythic_vibe_cli", cmd,
            "missing --include-package-data flag",
        )

    def test_build_command_excludes_optional_extras(self) -> None:
        """Optional extras must be in --nofollow-import-to so
        Nuitka doesn't try to compile them. Same exclusions as the
        PyInstaller spec — both binaries match the stdlib-only
        contract."""
        cmd = self.module.build_command(Path("/tmp/dist-nuitka"))
        excluded = [
            "anthropic", "openai", "google", "textual",
            "rich", "opentelemetry", "hypothesis", "pytest",
        ]
        for module_name in excluded:
            self.assertIn(
                f"--nofollow-import-to={module_name}", cmd,
                f"missing nofollow flag for {module_name}",
            )

    def test_build_command_uses_shared_pyinstaller_entrypoint(self) -> None:
        """Both Nuitka and PyInstaller compile from the same
        entrypoint shim so the two binaries' runtime behavior
        matches exactly. Diverging entrypoints would create subtle
        per-builder behavioral drift."""
        cmd = self.module.build_command(Path("/tmp/dist-nuitka"))
        self.assertIn("packaging/pyinstaller/entrypoint.py", cmd)

    def test_build_command_passes_output_dir(self) -> None:
        """The --output-dir flag must reflect the argument. Path
        rendering is platform-specific (Windows uses backslashes),
        so we just assert the flag is present and references the
        sentinel basename."""
        cmd = self.module.build_command(Path("output-sentinel"))
        output_flags = [
            tok for tok in cmd if tok.startswith("--output-dir=")
        ]
        self.assertEqual(
            len(output_flags), 1,
            f"expected exactly one --output-dir flag, got {output_flags}",
        )
        self.assertIn("output-sentinel", output_flags[0])

    def test_build_command_assumes_yes_for_downloads(self) -> None:
        """CI runners have no operator at the keyboard. Without
        --assume-yes-for-downloads, Nuitka may hang on a dependency
        prompt."""
        cmd = self.module.build_command(Path("/tmp/dist-nuitka"))
        self.assertIn("--assume-yes-for-downloads", cmd)

    def test_main_dry_run_returns_zero(self) -> None:
        """--dry-run prints the command and exits cleanly without
        running Nuitka. Lets operators verify the flag set on a
        local checkout without paying the build cost."""
        # Run from a temp dir to avoid triggering the rmtree path
        # against the real dist-nuitka/.
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "dry-run-out"
            rc = self.module.main([
                "--output-dir", str(output_dir),
                "--dry-run",
            ])
        self.assertEqual(rc, 0)


class ReleaseBinariesNuitkaJobTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = RELEASE_BINARIES_WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_has_build_nuitka_job(self) -> None:
        """The release-binaries workflow must include a
        build-nuitka job parallel to the PyInstaller build job."""
        self.assertIn("build-nuitka:", self.raw)

    def test_nuitka_job_invokes_build_driver(self) -> None:
        # The driver script lives at packaging/nuitka/build.py;
        # the workflow runs `python packaging/nuitka/build.py`.
        self.assertIn(
            "python packaging/nuitka/build.py",
            self.raw,
        )

    def test_nuitka_job_covers_full_os_matrix(self) -> None:
        """Same 4-row matrix as the PyInstaller job: Linux x86_64,
        macOS arm64, macOS x86_64 (macos-13), Windows x86_64."""
        # The Nuitka job uses the same matrix shape so we look for
        # the macos-13 Intel runner inside the build-nuitka section.
        nuitka_section = self.raw.split("build-nuitka:", 1)[1]
        self.assertIn("ubuntu-latest", nuitka_section)
        self.assertIn("macos-latest", nuitka_section)
        self.assertIn("macos-13", nuitka_section)
        self.assertIn("windows-latest", nuitka_section)

    def test_nuitka_assets_named_with_nuitka_suffix(self) -> None:
        """Asset names embed 'nuitka' so operators distinguish
        the two binaries on the GitHub Release page."""
        nuitka_section = self.raw.split("build-nuitka:", 1)[1]
        self.assertIn("mythic-vibe-nuitka-", nuitka_section)

    def test_nuitka_job_runs_smoke_after_build(self) -> None:
        """Same smoke as PyInstaller: --version + --help +
        doctor --json. Catches a botched compile before the
        binary ships."""
        nuitka_section = self.raw.split("build-nuitka:", 1)[1]
        self.assertIn("--version", nuitka_section)
        self.assertIn("--help", nuitka_section)
        self.assertIn("doctor --json", nuitka_section)

    def test_github_release_job_waits_for_both_builds(self) -> None:
        """The github-release job must wait for both the
        PyInstaller and Nuitka matrices before flattening +
        uploading. Otherwise it might attach only the PyInstaller
        binaries to the release."""
        self.assertIn("needs: [build, build-nuitka]", self.raw)


if __name__ == "__main__":
    unittest.main()
