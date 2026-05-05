# TASK — PH-21 Distribution Expansion (kickoff)

**Opened:** 2026-05-05
**Branch:** `development`
**HEAD at kickoff:** `352b7d1` (post-Hermes H.5)
**Operator:** Volmarr Wyrd
**Author:** Runa Gridweaver Freyjasdottir, executing on Volmarr's behalf
**Status:** `OPEN — AUTONOMOUS RUN — slice 21.7 first`

---

## Why this file exists

Volmarr granted full-permission autonomous mode for PH-21 on 2026-05-05.
PH-21 is the v1.x Distribution Expansion phase already scoped in
`TASK_PH19_DISTRIBUTION.md` (the master plan tracker). All decisions
were locked in the 2026-05-02 update. This kickoff file pins the
execution order, records progress per-slice, and acts as the resume
anchor if a session breaks before completion.

The plan, scope, and rationale **already live in
`TASK_PH19_DISTRIBUTION.md`** under the "PH-21 — v1.x Distribution
Expansion" section. This file does not re-litigate those decisions;
it tracks execution.

---

## Operating rules (carry-over from prior phases)

1. **Additive only — never subtractive** (`feedback_additive_only.md`).
2. TASK file → commit + push → implement → ruff/mypy/pytest green →
   per-slice closeout addendum → memory update → push.
3. ruff + mypy + pytest gate every commit.
4. Stdlib-first; cross-platform; open-source-only; file-location-agnostic.
5. One cohesive slice per commit; no batching.
6. Push frequently, not just at the end.

---

## Execution order (dependency-respecting, momentum-first)

The order is **quick-win channels → new artifact pipelines → cross-cutting security**.
Rationale: small isolated channels (21.7, 21.8, 21.9) consume existing
wheel/sdist artifacts already produced by the v1.0 release pipeline,
so they ship value within hours each. New artifact pipelines (21.1,
21.2, 21.3) introduce new build outputs. Cross-cutting security
(21.4, 21.5, 21.6) lands last because it operates on artifacts the
earlier slices produce.

| Order | Slice | What | Est. effort | Status |
|---|---|---|---|---|
| 1 | **21.7** | AUR `mythic-vibe-cli-bin` package + maintainer scripts | ~2h | [ ] |
| 2 | **21.8** | winget manifest PR to `winget-pkgs` | ~2h | [ ] |
| 3 | **21.9** | Android / Termux formal support (docs + platform detection) | ~3-4h | [ ] |
| 4 | **21.1** | Container / OCI image (multi-arch buildx → GHCR + Docker Hub) | ~3-4h | [ ] |
| 5 | **21.2** | Single-file executables via PyInstaller (Linux + Windows + macOS) | ~6-8h | [ ] |
| 6 | **21.3** | Single-file executables via Nuitka (alternative; faster startup) | ~6-8h | [ ] |
| 7 | **21.4** | macOS Gatekeeper override docs (rescoped — not full notarization) | ~30min | [ ] |
| 8 | **21.5** | GPG / Sigstore signed artifacts (replaces 20.6 checksums-only) | ~6-8h | [ ] |
| 9 | **21.6** | Reproducible build attestations + tag signing | ~4-6h | [ ] |

**PH-21 cumulative effort:** ~32-43h (per locked plan in TASK_PH19_DISTRIBUTION.md).

---

## Per-slice deliverables (what "done" means)

### 21.7 — AUR package
- New: `packaging/aur/PKGBUILD.template`
- New: `packaging/aur/.SRCINFO.template`
- Workflow: extend `release.yml` with an `update-aur` job that opens
  an automated PR (or pushes via SSH key) to an AUR maintainer repo
  on tag push.
- Docs: `docs/INSTALL.md` adds an "Arch Linux (AUR)" section.
- Tests: a unit test that renders the PKGBUILD template against a
  fixed version + sha256 and asserts the expected output (catches
  template drift).
- License: AUR PKGBUILD references the project's Apache-2.0 license.

### 21.8 — winget manifest
- New: `packaging/winget/manifest/` directory with
  `mythic-vibe.installer.yaml.template`,
  `mythic-vibe.locale.en-US.yaml.template`,
  `mythic-vibe.yaml.template` (the three-file YAML format winget
  requires for v1.6+ manifests).
- Workflow: extend `release.yml` with an `update-winget` job that
  uses `wingetcreate` to submit a manifest PR to `microsoft/winget-pkgs`.
  Manual review on the winget side; we just open the PR.
- Docs: `docs/INSTALL.md` adds a "Windows (winget)" section.
- Tests: render-template unit test (same shape as 21.7).

### 21.9 — Termux formal support
- Docs: `docs/INSTALL.md` adds a "Termux (Android)" section with the
  three commands (`pkg install python rust`, then `pip install
  mythic-vibe-cli`, then `mythic-vibe doctor`).
- Platform detection: `runtime/platform.py` (or wherever platform
  tagging lives) gains an `is_termux()` helper that reads
  `TERMUX_VERSION` env var. Doctor exposes the tag in `--json`
  output so operators can verify the runtime sees Termux correctly.
- Path adjustments: any `~/.cache/mythic-vibe` path uses
  `XDG_CACHE_HOME` first, which Termux already sets. Verify nothing
  is hardcoded to `/home/...`.
- Tests: `test_platform_termux.py` — sets/unsets `TERMUX_VERSION`,
  asserts `is_termux()` returns the right boolean and doctor output
  includes the tag.

### 21.1 — OCI container image
- New: `Dockerfile` at repo root — multi-stage:
  - Builder stage: python:3.12-slim, installs the project + the
    `[ai,otel,ux,tui]` extras into a venv, then strips bytecode caches.
  - Runtime stage: distroless or python:3.12-slim, copies the venv,
    sets `ENTRYPOINT ["mythic-vibe"]`, defaults to `--help`.
- New: `.dockerignore` so the build context is small.
- Workflow: new `release-oci.yml` triggered on tag push. Uses
  `docker/setup-qemu-action`, `docker/setup-buildx-action`,
  `docker/login-action` (GHCR), `docker/build-push-action` for
  multi-arch (amd64 + arm64) buildx + push to
  `ghcr.io/hrabanazviking/mythic-vibe-cli:$VERSION` and `:latest`.
- Docs: `docs/INSTALL.md` adds a "Container (Docker / Podman)" section.
- Tests: `test_dockerfile_lint.py` — opens `Dockerfile`, asserts:
  - multi-stage build (>=2 `FROM`),
  - non-root final user,
  - explicit `ENTRYPOINT`,
  - no `apt-get install` without `&& rm -rf /var/lib/apt/lists/*`.

### 21.2 — PyInstaller binaries
- New: `packaging/pyinstaller/mythic-vibe.spec` — handles entry-point,
  hidden imports (the dynamic `pkg_resources` paths in plugin loader),
  data files (resources/schemas/*).
- Workflow: new `release-binaries.yml` triggered on tag push. Matrix:
  ubuntu-latest × macos-latest × windows-latest. Each job:
  - installs the project + `[ai,otel,ux,tui]`,
  - runs `pyinstaller packaging/pyinstaller/mythic-vibe.spec`,
  - produces a single-file binary,
  - smoke-tests it (`./dist/mythic-vibe --help` + `doctor --json`),
  - uploads to the GitHub Release as a workflow artifact.
- Naming: `mythic-vibe-${VERSION}-${OS}-${ARCH}` (consistent across OSes).
- Docs: `docs/INSTALL.md` adds "Standalone binaries (PyInstaller)" section.
- Tests: `test_packaging_pyinstaller_spec.py` — parses the spec file
  and asserts the entry-point + hidden imports are correctly listed.

### 21.3 — Nuitka binaries
- New: `packaging/nuitka/build.py` — invokes Nuitka with the right
  flags: `--standalone --onefile --include-package=mythic_vibe_cli
  --include-data-dir=mythic_vibe_cli/resources=mythic_vibe_cli/resources`.
- Workflow: extend `release-binaries.yml` with a parallel matrix of
  Nuitka jobs (same OS × arch matrix as PyInstaller). Operator picks
  which binary they prefer per release notes.
- Naming: `mythic-vibe-nuitka-${VERSION}-${OS}-${ARCH}`.
- Docs: same INSTALL.md section adds a Nuitka subsection comparing
  startup time + binary size vs PyInstaller (operator chooses).
- Tests: `test_packaging_nuitka_build_spec.py` — imports
  `packaging/nuitka/build.py`, asserts the flag list is correct.

### 21.4 — macOS Gatekeeper override docs
- Docs: `docs/INSTALL.md` "Standalone binaries" section gains a
  "macOS first-launch (Gatekeeper override)" subsection. Covers:
  - Right-click → Open (operator-friendly path),
  - `xattr -d com.apple.quarantine /path/to/mythic-vibe` (CLI path),
  - Why we ship un-notarized (operator-sovereignty + open-source +
    no $99/yr Apple tax).
- Per the locked decision in TASK_PH19_DISTRIBUTION.md (Volmarr
  chose to skip notarization).

### 21.5 — Sigstore signed artifacts
- Workflow: extend `release.yml` and `release-oci.yml` and
  `release-binaries.yml` with Sigstore signing steps using
  `sigstore/gh-action-sigstore-python` (PyPI artifacts) and
  `sigstore/cosign-installer` + `cosign sign --yes` (OCI image
  + binaries). Keyless OIDC; no key management.
- Verification docs: `docs/security/verifying_artifacts.md` —
  per-channel verification commands.
- Tests: a release-rehearsal smoke test that signs a fixture
  artifact locally (skipped in CI without OIDC) and asserts the
  signature bundle has the expected structure.
- Replaces the 20.6 "checksums-only" provenance verify approach
  with stronger keyless cryptographic provenance.

### 21.6 — Reproducible build attestations + tag signing
- SLSA Level 3 build provenance via
  `actions/attest-build-provenance@v2` for every release artifact.
- Tag signing: release workflow signs git tags using
  `gpg --batch --sign-tag` with a project-rotated key (or via
  GitHub's tag signature path with `gpg-key-id` secret). Decision
  point: keyless tag signing with Sigstore is preferred if Sigstore
  supports it for git tags by 2026-05; otherwise fall back to
  GPG with key recorded in `docs/security/`.
- Docs: `docs/security/verifying_artifacts.md` extends with
  attestation verification using `gh attestation verify`.
- Tests: a contract-level test that asserts the release workflow
  contains the expected attestation steps (drift-prevention).

---

## Status updates per slice (additive log)

Each slice gets a dated entry below as it lands. New entries append;
prior entries are never mutated.

### 2026-05-05 — Kickoff committed
TASK file written, plan locked, gitignore amended for the stray
`Users/` test-debris path. Beginning slice 21.7 (AUR) on commit `+1`
from this kickoff commit.

---

## Resume anchor

If a session breaks mid-run, the next session resumes by:
1. Reading this file.
2. Looking at the rightmost `[ ]` in the slice table to find the
   next unfinished slice.
3. Looking at the most recent dated status update to confirm last
   commit-pushed state.
4. Running `git log --oneline -10` to confirm HEAD matches the
   memory's recorded progress.
5. Continuing with the next slice in order.

This file is the durable resume contract.
