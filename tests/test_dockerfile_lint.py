"""Phase 21.1 — Dockerfile + release-oci.yml structural lint.

The Dockerfile defines the multi-arch container image distribution
channel published by ``.github/workflows/release-oci.yml``. We
cannot exercise the actual image build here (no Docker daemon in
the unit-test runner), but we can statically lint the Dockerfile
for the invariants we care about:

- Multi-stage build (builder + runtime) so the final image is small.
- Non-root final user so a compromised entrypoint can't trivially
  escape into the container's root namespace.
- Explicit ENTRYPOINT in exec form (not shell) so signal handling
  reaches the CLI directly.
- ``apt-get install`` always paired with ``rm -rf /var/lib/apt/
  lists/*`` in the same RUN so the apt cache doesn't bloat the
  builder layer.

The release workflow gets the same treatment as Homebrew + Scoop
templates: assert the workflow references the Dockerfile, sets up
multi-arch buildx, logs into GHCR, and runs a smoke test. Catches
the "renamed something but forgot to update the workflow"
regression at PR time.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE_PATH = REPO_ROOT / "Dockerfile"
DOCKERIGNORE_PATH = REPO_ROOT / ".dockerignore"
RELEASE_OCI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-oci.yml"


class DockerfileStructureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            DOCKERFILE_PATH.is_file(),
            f"Dockerfile missing at {DOCKERFILE_PATH}",
        )
        self.raw = DOCKERFILE_PATH.read_text(encoding="utf-8")

    def test_uses_multi_stage_build(self) -> None:
        """Two FROM statements minimum (builder + runtime) so the
        final image doesn't carry build-time tooling."""
        from_lines = [
            line for line in self.raw.splitlines()
            if re.match(r"^\s*FROM\s+", line)
        ]
        self.assertGreaterEqual(
            len(from_lines), 2,
            f"expected multi-stage build (>=2 FROM), got {len(from_lines)}",
        )
        # First stage must be aliased so the runtime stage can COPY --from=...
        self.assertRegex(
            from_lines[0],
            r"FROM\s+\S+\s+AS\s+\w+",
            "first FROM should be aliased (AS builder)",
        )

    def test_uses_explicit_dockerfile_syntax(self) -> None:
        """The buildkit syntax directive lets buildx use modern
        features (cache mounts, --link). Without it old daemons
        silently fall back to legacy syntax."""
        first_line = self.raw.splitlines()[0]
        self.assertTrue(
            first_line.startswith("# syntax=docker/dockerfile:"),
            f"first line must declare syntax directive, got {first_line!r}",
        )

    def test_runs_as_non_root(self) -> None:
        """USER directive must drop root before ENTRYPOINT. A
        compromised CLI shouldn't have container-root by default."""
        # Find USER directives at start of any line (not in comments).
        user_lines = [
            line.strip() for line in self.raw.splitlines()
            if re.match(r"^USER\s+", line)
        ]
        self.assertTrue(
            user_lines,
            "no USER directive found — image would run as root",
        )
        # No USER directive should resolve to root (the default).
        for line in user_lines:
            self.assertNotRegex(
                line, r"^USER\s+root\b",
                f"USER directive resolves to root: {line!r}",
            )

    def test_entrypoint_is_exec_form(self) -> None:
        """Exec form (JSON array) keeps PID 1 as the CLI so signals
        propagate. Shell form wraps in /bin/sh -c which traps
        SIGTERM and breaks docker stop."""
        self.assertRegex(
            self.raw,
            r'ENTRYPOINT\s+\[\s*"mythic-vibe"',
            "ENTRYPOINT must be exec form starting with mythic-vibe",
        )

    def test_apt_install_clears_cache_in_same_run(self) -> None:
        """Each apt-get install line must end with the apt cache
        cleanup. Without it the builder layer bloats by ~30-50 MB
        of cached package metadata that the runtime image never
        needs but inherits via COPY."""
        # Find every RUN block that mentions apt-get install.
        # Multi-line continuation handled via re.DOTALL on the
        # block bounded by next RUN / FROM / blank double-newline.
        run_blocks = re.findall(
            r"RUN\s+(.+?)(?=\n\s*\n|\nRUN\s|\nFROM\s|\Z)",
            self.raw,
            re.DOTALL,
        )
        offending = [
            block for block in run_blocks
            if "apt-get install" in block
            and "rm -rf /var/lib/apt/lists" not in block
        ]
        self.assertEqual(
            offending, [],
            f"apt-get install RUN block(s) missing apt-cache cleanup: {offending}",
        )

    def test_smoke_run_at_build_time(self) -> None:
        """The runtime stage runs ``mythic-vibe --version`` as a
        layer-time smoke. A broken venv copy fails the build
        before the image ever lands in a registry."""
        self.assertIn("RUN mythic-vibe --version", self.raw)

    def test_includes_oci_image_labels(self) -> None:
        """LABEL org.opencontainers.image.* surfaces project
        metadata in registry UIs (license, source, docs URL)."""
        for label in (
            "org.opencontainers.image.title",
            "org.opencontainers.image.description",
            "org.opencontainers.image.source",
            "org.opencontainers.image.licenses",
        ):
            self.assertIn(
                label, self.raw,
                f"missing OCI image label: {label}",
            )

    def test_apache_2_0_license_label(self) -> None:
        """The licenses label must reflect the project's actual
        Apache-2.0 license. Mismatch here breaks downstream tools
        that filter by license."""
        self.assertRegex(
            self.raw,
            r'org\.opencontainers\.image\.licenses\s*=\s*"Apache-2\.0"',
            "OCI license label must be Apache-2.0",
        )


class DockerignoreContentsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            DOCKERIGNORE_PATH.is_file(),
            f".dockerignore missing at {DOCKERIGNORE_PATH}",
        )
        self.raw = DOCKERIGNORE_PATH.read_text(encoding="utf-8")

    def test_excludes_git_and_ci(self) -> None:
        """The build context must not carry .git (huge) or
        .github (irrelevant to runtime) into buildx."""
        for pattern in (".git", ".github"):
            self.assertIn(pattern, self.raw)

    def test_excludes_tests_and_docs(self) -> None:
        """Tests + docs aren't shipped in the image. Excluding
        them shrinks the buildx context (faster multi-arch builds)."""
        for pattern in ("tests", "docs"):
            self.assertIn(pattern, self.raw)

    def test_excludes_python_caches(self) -> None:
        """Cache directories pollute the build context for no
        functional benefit."""
        for pattern in (
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
        ):
            self.assertIn(pattern, self.raw)

    def test_excludes_env_files(self) -> None:
        """Local .env files contain secrets and must never land
        in a published image."""
        self.assertIn(".env", self.raw)


class ReleaseOciWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            RELEASE_OCI_WORKFLOW.is_file(),
            f"release-oci.yml missing at {RELEASE_OCI_WORKFLOW}",
        )
        self.raw = RELEASE_OCI_WORKFLOW.read_text(encoding="utf-8")

    def test_triggers_on_version_tags(self) -> None:
        # Same trigger semantics as release.yml so OCI + PyPI
        # ship from the same git tag in lockstep.
        self.assertRegex(self.raw, r'tags:\s*\n\s+-\s+"v\*\.\*\.\*"')

    def test_supports_workflow_dispatch_for_rehearsal(self) -> None:
        # Manual trigger lets operators rehearse the build path
        # without consuming a version tag.
        self.assertIn("workflow_dispatch", self.raw)

    def test_uses_multiarch_buildx(self) -> None:
        # Both QEMU emulation and buildx are required for a
        # multi-arch (amd64 + arm64) build on a single x86 runner.
        self.assertIn("docker/setup-qemu-action", self.raw)
        self.assertIn("docker/setup-buildx-action", self.raw)

    def test_targets_amd64_and_arm64(self) -> None:
        # The platforms list must include both arches; checking
        # both substrings catches a half-broken edit that drops
        # one platform.
        self.assertIn("linux/amd64", self.raw)
        self.assertIn("linux/arm64", self.raw)

    def test_logs_into_ghcr(self) -> None:
        # GHCR auth uses the workflow's GITHUB_TOKEN — no extra
        # secret management required for any GitHub-owned repo.
        self.assertIn("registry: ghcr.io", self.raw)
        self.assertIn("password: ${{ secrets.GITHUB_TOKEN }}", self.raw)

    def test_docker_hub_login_is_optional(self) -> None:
        # Hub publish is gated by the DOCKERHUB_PUBLISH_ENABLED
        # repo variable — workflow stays useful before Volmarr
        # provisions Hub credentials.
        self.assertIn("DOCKERHUB_PUBLISH_ENABLED", self.raw)
        self.assertIn("vars.DOCKERHUB_PUBLISH_ENABLED == 'true'", self.raw)

    def test_emits_provenance_and_sbom(self) -> None:
        # SLSA provenance + SPDX SBOM piggyback on docker/build-
        # push-action. Sigstore signing lands in PH-21.5.
        self.assertIn("provenance: true", self.raw)
        self.assertIn("sbom: true", self.raw)

    def test_runs_smoke_after_push(self) -> None:
        # docker pull + docker run check that the pushed image
        # actually executes the CLI. Catches a botched entrypoint
        # before operators pull a broken release.
        self.assertIn("docker pull", self.raw)
        self.assertIn("docker run", self.raw)
        self.assertRegex(
            self.raw,
            r"docker run.*--version",
        )

    def test_resolves_version_from_pyproject(self) -> None:
        # Same version-resolution pattern as release.yml so the
        # OCI tag matches the wheel/sdist version exactly.
        self.assertIn("pyproject.toml", self.raw)
        self.assertIn("tomllib", self.raw)


if __name__ == "__main__":
    unittest.main()
