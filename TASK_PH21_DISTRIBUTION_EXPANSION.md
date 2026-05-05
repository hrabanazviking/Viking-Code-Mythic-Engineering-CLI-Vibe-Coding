# TASK — PH-21 Distribution Expansion (kickoff)

**Opened:** 2026-05-05
**Branch:** `development`
**HEAD at kickoff:** `352b7d1` (post-Hermes H.5)
**Operator:** Volmarr Wyrd
**Author:** Runa Gridweaver Freyjasdottir, executing on Volmarr's behalf
**Status:** `CLOSED — ALL 9 SLICES SHIPPED — 2026-05-05`

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
| 1 | **21.7** | AUR `mythic-vibe-cli` package + maintainer-repo workflow | ~2h | [x] |
| 2 | **21.8** | winget manifest PR to `winget-pkgs` | ~2h | [x] |
| 3 | **21.9** | Android / Termux formal support (docs + platform detection) | ~3-4h | [x] |
| 4 | **21.1** | Container / OCI image (multi-arch buildx → GHCR + Docker Hub) | ~3-4h | [x] |
| 5 | **21.2** | Single-file executables via PyInstaller (Linux + Windows + macOS) | ~6-8h | [x] |
| 6 | **21.3** | Single-file executables via Nuitka (alternative; faster startup) | ~6-8h | [x] |
| 7 | **21.4** | macOS Gatekeeper override docs (rescoped — not full notarization) | ~30min | [x] |
| 8 | **21.5** | GPG / Sigstore signed artifacts (replaces 20.6 checksums-only) | ~6-8h | [x] |
| 9 | **21.6** | Reproducible build attestations + tag signing | ~4-6h | [x] |

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

### 2026-05-05 — Slice 21.7 closed (AUR maintainer-repo channel)
**Shipped:**
- `packaging/aur/PKGBUILD.template` — standard AUR Python source
  PKGBUILD; `arch=('any')`, builds from PyPI sdist, uses
  `python-build` + `python-installer`. Apache-2.0 license declared
  via SPDX (modern AUR convention).
- `packaging/aur/.SRCINFO.template` — line-based AUR machine
  summary; placeholders match the PKGBUILD so they stay in sync.
- `.github/workflows/release.yml` — new `update-aur` job mirrors
  the `update-homebrew` + `update-scoop` pattern: render templates,
  push branch, open PR against `hrabanazviking/aur-mythic` using
  `AUR_BUMP_TOKEN` secret. Human maintainer syncs PR to AUR proper
  via `git push aur master` (recipe lives in the maintainer-repo
  README).
- `tests/test_packaging_templates.py` — 9 new tests covering
  PKGBUILD render-time placeholder safety, required AUR fields
  (pkgname/pkgver/pkgrel/arch/license/depends/sha256sums/build()/
  package()), .SRCINFO render-time safety, and release-workflow
  references to both templates + AUR_BUMP_TOKEN secret.
- `docs/INSTALL.md` — new "Arch Linux (AUR)" section between Scoop
  and the offline install path. Covers `yay -S` and manual makepkg.
- `packaging/README.md` — channel table extended to include AUR;
  defer-section re-shaped (AUR removed; OCI / PyInstaller / Nuitka
  / winget / Termux now flagged as in-flight PH-21 slices);
  maintainer-repo sync recipes section added.

**Gates green:** 2301 passed / 1 skipped / 109 subtests; ruff clean;
mypy clean; contract audit clean.

**Did not change:** no production runtime code — this slice is
release-pipeline + docs only. Threat model unaffected. Compatibility
policy unaffected (new channel adds publication surface, doesn't
mutate any existing stable surface).

Beginning slice 21.8 (winget manifest) next.

### 2026-05-05 — Execution order revised (additive)
Realized while planning slice 21.8 that the winget manifest needs a
Windows binary URL to reference, and PyInstaller (slice 21.2) is the
producer of that binary. Moving 21.8 after 21.2 so the manifest can
point at a real artifact instead of a placeholder URL. New
dependency-respecting order:

  1. ✅ 21.7 AUR
  2. 21.9 Termux        (next — independent, small)
  3. 21.1 OCI image     (independent, own artifact pipeline)
  4. 21.2 PyInstaller   (produces Win/macOS/Linux binaries)
  5. 21.4 Gatekeeper    (references 21.2 macOS binary)
  6. 21.8 winget        (references 21.2 Windows binary)
  7. 21.3 Nuitka        (alternative binaries; can run after 21.2)
  8. 21.5 Sigstore      (signs all artifacts from 21.1 + 21.2 + 21.3)
  9. 21.6 Attestations  (final cap)

The original "Order" column in the slice table is preserved as the
plan-at-kickoff record; this dated entry documents the actual
execution path.

### 2026-05-05 — Slice 21.9 closed (Termux / WSL platform tags)
**Shipped:**
- `mythic_vibe_cli/hardware.py` — three new pure-stdlib detectors
  plus a composite:
  - `is_termux()` — checks `TERMUX_VERSION` env var or
    `/data/data/com.termux/files/usr` filesystem prefix.
  - `is_wsl()` — substring match on `platform.uname().release`
    against "microsoft" (handles WSL1 + WSL2).
  - `is_raspberry_pi()` — reads `/proc/device-tree/model` and
    matches "raspberry pi" (case-insensitive).
  - `detect_platform_tags()` — composite returning a deterministic
    ordered list (`termux`, `wsl`, `raspberry_pi`, `arm64`).
- `HardwareProfile` — additive `platform_tags: list[str]` field.
  `to_dict()` serializes it; `__all__` exports the new helpers.
- `render_profile_text()` — new "Platform tags:" line; empty case
  shows `(none)` so the field is always visible.
- `render_profile_markdown()` — new `| Platform tags |` row
  matching the existing table style.
- `tests/test_hardware.py` — 18 new tests across 5 classes:
  IsTermuxTests (3), IsWslTests (4), IsRaspberryPiTests (3),
  DetectPlatformTagsTests (3), HardwareProfileTagsIntegrationTests
  (5). Covers env-only, filesystem-only, mixed, and missing
  signals; arm64-via-aarch64 normalization; empty + populated tag
  rendering in both text + markdown.
- `docs/INSTALL.md` — new "Termux (Android)" section with the
  full install recipe (`pkg install python rust` + `pip install
  mythic-vibe-cli`), a note that Termux already exports
  XDG_CONFIG_HOME so no path tweaks are needed, and a pointer to
  the new platform_tags surface for operator-side gating. New
  "WSL (Windows Subsystem for Linux)" section that documents the
  `wsl` tag emission. Termux troubleshooting bullet added to the
  existing Troubleshooting list.

**Gates green:** 2319 passed / 1 skipped / 109 subtests; ruff clean;
mypy clean (156 source files); contract audit clean (no new
commands, only an additive field on the existing hardware command's
JSON envelope).

**Compatibility surface:** the hardware command's JSON output is
Stable per `docs/compatibility_policy.md` §1. Adding a new key
(`platform_tags`) is additive and does not break existing
consumers; the empty-list default means callers that ignore the
key see no behavior change. New consumers gating on tags should
treat absence-of-tag as "not detected" rather than "definitely
not that platform" (read-only signals, never raise).

Beginning slice 21.1 (OCI multi-arch image) next.

### 2026-05-05 — Slice 21.1 closed (OCI multi-arch container image)
**Shipped:**
- `Dockerfile` — multi-stage build at repo root. Stage 1 (builder)
  installs the project + `[ai,otel,ux,tui]` extras into `/opt/venv`
  with build deps available for any wheel that needs to compile
  from sdist on arm64; bytecode caches stripped before handoff.
  Stage 2 (runtime) on python:3.12-slim, copies the venv, runs as
  non-root `mythic` user (uid 1000) with workspace at `/work`,
  layer-time smoke (`mythic-vibe --version`) catches a broken
  venv copy before push. ENTRYPOINT in exec-form so signals
  reach the CLI directly. Standard `org.opencontainers.image.*`
  labels (title, description, source, documentation, licenses,
  vendor) so registry UIs surface project metadata.
- `.dockerignore` — keeps the buildx context minimal: excludes
  `.git`, `.github`, `tests/`, `docs/`, `research_data/`,
  `scripts/`, `tools/`, `packaging/`, all Python caches, `mythic/`
  operational data, `.env*`, and the `Users/` test-debris path.
- `.github/workflows/release-oci.yml` — new workflow triggered on
  `v*.*.*` tag pushes (mirrors release.yml semantics) plus
  `workflow_dispatch` for build-only rehearsal. Sets up QEMU +
  buildx, logs into GHCR via `GITHUB_TOKEN`, optionally logs into
  Docker Hub when `DOCKERHUB_PUBLISH_ENABLED` repo variable is
  `true` and `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` secrets
  are present. Builds linux/amd64 + linux/arm64 in one pass.
  SLSA `provenance: true` + SPDX `sbom: true` attached to the
  manifest (Sigstore signing lands separately in PH-21.5).
  Smoke test pulls + runs the amd64 image post-push so a broken
  image fails the workflow before operators pull it.
- `tests/test_dockerfile_lint.py` — 21 new tests across 3 classes
  covering: multi-stage build invariants, syntax directive,
  non-root USER, exec-form ENTRYPOINT, apt cache cleanup in
  same RUN, layer-time smoke, OCI labels, Apache-2.0 license
  label, dockerignore exclusions (git/CI/tests/docs/caches/env),
  workflow trigger semantics, multi-arch buildx setup, GHCR
  login, optional Docker Hub gating, provenance + SBOM emission,
  post-push smoke test, version resolution from pyproject.
- `docs/INSTALL.md` — new "Container (Docker / Podman)" section
  with three example invocations: latest tag, pinned version,
  bind-mounted project dir. Documents the non-root user, /work
  mount, default extras, OCI labels, and Docker Hub mirror
  opt-in.
- `packaging/README.md` — channel table extended with the OCI
  row pointing at the Dockerfile + .dockerignore. Secret table
  documents the GHCR (free) and Docker Hub (opt-in) auth paths.
  Defer-section tightened: AUR + OCI + Termux removed (now
  shipped); winget + PyInstaller + Nuitka remain in flight.

**Gates green:** 2340 passed / 1 skipped / 109 subtests (+21 from
this slice); ruff clean; mypy clean (156 source files); contract
audit clean (no new commands).

**Compatibility surface:** new publication channel; existing
stable surfaces (CLI commands, JSON contracts, exit codes) are
unaffected. Image tagging follows v1.0 SemVer (`:VERSION` per tag,
`:latest` floats). Operators pinning by sha256 digest get
deterministic builds across replays.

Beginning slice 21.2 (PyInstaller binaries) next.

### 2026-05-05 — Slice 21.2 closed (PyInstaller standalone binaries)
**Shipped:**
- `packaging/pyinstaller/mythic-vibe.spec` — PyInstaller spec for
  the stdlib-only base CLI. Uses `collect_data_files` to bundle
  `resources/schemas/*.json`. Hidden imports cover three lazily-
  imported runtime modules (model_catalog, doctor_fix, ai.route)
  plus tomllib/tomli for cross-3.10/3.11+ compat. Excludes every
  optional extra (anthropic / openai / google-genai / textual /
  rich / opentelemetry-* / hypothesis / pytest / mypy / ruff /
  tkinter / matplotlib / numpy) so the binary stays small (~15-25
  MB target) and starts fast. `console=True` keeps stdio attached;
  `upx=False` because UPX corrupts macOS code signatures and trips
  Windows Defender false positives; `target_arch=None` lets the
  matrix runner's host arch dictate the output.
- `packaging/pyinstaller/entrypoint.py` — minimal shim that imports
  `mythic_vibe_cli.cli.main` and calls `sys.exit(main())`. Kept
  tiny on purpose so the binary's behavior matches a pip-installed
  CLI exactly.
- `.github/workflows/release-binaries.yml` — new workflow with a
  4-row matrix:
    ubuntu-latest  → mythic-vibe-${VERSION}-linux-x86_64
    macos-latest   → mythic-vibe-${VERSION}-macos-arm64
    macos-13       → mythic-vibe-${VERSION}-macos-x86_64 (Intel)
    windows-latest → mythic-vibe-${VERSION}-windows-x86_64.exe
  Each row installs the project + PyInstaller, runs `pyinstaller
  packaging/pyinstaller/mythic-vibe.spec --clean`, smoke-tests the
  binary (--version + --help + doctor --json), renames with the
  per-OS asset suffix, computes a SHA256 sidecar, uploads the
  artifact. A separate `github-release` job downloads every
  artifact, flattens them into one dir, and attaches all four
  binaries + four `.sha256` files to the release.yml-created
  GitHub Release for the tag (softprops idempotently appends to
  the existing release). `workflow_dispatch` runs the build-only
  rehearsal path.
- `tests/test_packaging_pyinstaller.py` — 19 new tests across 3
  classes:
    PyInstallerSpecTests (8) — entrypoint reference, schema data-
        file collection, optional-extra excludes, console mode,
        no-UPX, target_arch=None, hidden-imports covering the
        lazy-import runtime paths, tomli/tomllib fallback.
    EntrypointShimTests (3) — imports cli.main, calls sys.exit
        on its return, compiles cleanly.
    ReleaseBinariesWorkflowTests (8) — tag triggers, manual
        rehearsal, Linux/macOS/Windows matrix coverage, macos-13
        Intel row, spec invocation, smoke-test commands, per-
        binary sha256 emission, GitHub Release upload.
- `docs/INSTALL.md` — new "Standalone binaries (PyInstaller)"
  section between AUR/Termux/WSL and the Container section. Covers
  download via `gh release download`, sha256 verification,
  per-OS asset name table, and the explicit "no extras bundled"
  caveat directing extras-needers to the pip channels. New
  troubleshooting bullets for macOS Gatekeeper (forwarding to
  PH-21.4) and Windows SmartScreen (forwarding to PH-21.5).
- `packaging/README.md` — channel table extended with the
  PyInstaller row pointing at the spec + entrypoint. Defer-section
  tightened: Nuitka (PH-21.3) and winget (PH-21.8) remain.

**Gates green:** 2359 passed / 1 skipped / 109 subtests (+19 from
this slice); ruff clean; mypy clean (156 source files); contract
audit clean.

**Compatibility surface:** new publication channel; existing
stable surfaces unaffected. The standalone binary is intentionally
stdlib-only — operators who need extras must use the pip channels.
This is documented as a Stable property of the binary surface so
later additions of "ai-flavor" or "tui-flavor" binaries would land
as separate assets rather than mutating the base binary's
contract.

Beginning slice 21.4 (macOS Gatekeeper override docs) next.

### 2026-05-05 — Slice 21.4 closed (macOS Gatekeeper override docs)
**Shipped:**
- `docs/INSTALL.md` — new `#### macOS first-launch (Gatekeeper
  override)` subsection inside the "Standalone binaries
  (PyInstaller)" section. Covers:
  - The exact Gatekeeper dialog operators will see.
  - Option A: right-click → Open (the operator-friendly path).
  - Option B: `xattr -d com.apple.quarantine /path/to/binary`
    (the CLI path).
  - A "Why we ship un-notarized" rationale subsection covering
    operator sovereignty, no-upstream-gatekeeper, open-source
    philosophy alignment, and the explicit "one-time prompt"
    trade-off.
  - A reversibility note: adding notarization later doesn't
    break any existing binary; it just adds a new code path.

**Gates green:** 2359 passed / 1 skipped / 109 subtests; ruff clean.
Docs-only slice — no production runtime change, no new tests
required (the existing PH-21.2 troubleshooting bullets already
forward to this section).

**Compatibility surface:** unchanged. Distribution semantics
documented but not modified.

Beginning slice 21.8 (winget manifest) next. With PH-21.2's
Windows binary now in the release pipeline, the winget portable
manifest can reference the actual asset URL.

### 2026-05-05 — Slice 21.8 closed (winget manifest channel)
**Shipped:**
- `packaging/winget/mythic-vibe.installer.yaml.template` — winget
  v1.6 Installer manifest. `InstallerType: portable` matches
  PH-21.2's PyInstaller single-file binary (winget extracts to
  `%LOCALAPPDATA%\Microsoft\WinGet\Packages\<id>\` and adds to
  `PATH`; `winget uninstall` cleans up by removing the binary).
  Declares both `mythic-vibe` and `mythic` console-script
  aliases in the `Commands` array. `Architecture: x64` matches
  the windows-x86_64 asset.
- `packaging/winget/mythic-vibe.locale.en-US.yaml.template` —
  default-locale manifest with publisher / homepage / support
  URLs (winget-pkgs review checks all three), Apache-2.0 license,
  short and long descriptions, tags, and a release-notes URL
  pointing at the GitHub Release page for the tag.
- `packaging/winget/mythic-vibe.yaml.template` — top-level version
  manifest pointing at the en-US default locale.
- `.github/workflows/release.yml` — new `update-winget` job
  parallel to `update-aur`/`update-homebrew`/`update-scoop`.
  Pipeline:
  1. Probes the Windows binary asset on the GitHub Release with
     up to 5 retries x 30s sleep — handles the race where
     release-binaries.yml's Windows row finishes after the
     wheel/sdist release goes live.
  2. Resolves URL + computes SHA256 by downloading the asset
     and hashing it locally (avoids relying on the .sha256
     sidecar's presence/format).
  3. Renders all three templates into the maintainer-repo's
     `manifests/h/hrabanazviking/MythicVibeCLI/<VERSION>/`
     subdirectory (the layout winget-pkgs requires).
  4. Opens a PR against `hrabanazviking/winget-mythic` using
     `WINGET_BUMP_TOKEN`. A human syncs to `microsoft/winget-pkgs`
     via wingetcreate or a manual fork PR (recipe lives in the
     maintainer-repo README).
- `tests/test_packaging_templates.py` — 18 new tests across 3
  classes (WingetInstallerTemplateTests, WingetLocaleTemplateTests,
  WingetVersionTemplateTests) plus 3 extensions to
  ReleaseWorkflowTests. Catches every "renamed something but
  forgot to update X" regression for the winget channel:
  required placeholders, full substitution removes all markers,
  portable installer type, x64 architecture, Commands array
  with both aliases, modern (v1.6) manifest version, license +
  publisher metadata, default locale match between version and
  locale templates, workflow references all three templates,
  workflow uses the WINGET_BUMP_TOKEN secret, workflow resolves
  the Windows binary by name (not hardcoded URL).
- `docs/INSTALL.md` — new "winget (Windows)" section between
  Scoop and AUR. One-line install (`winget install
  hrabanazviking.MythicVibeCLI`) plus a SmartScreen note
  forwarding to PH-21.5's keyless-signing slice.
- `packaging/README.md` — channel table extended with the winget
  row pointing at all three template files. Secret table
  includes WINGET_BUMP_TOKEN. Defer-section tightened: only
  Nuitka (PH-21.3) remains. New entry in the maintainer-repo
  sync recipes section explains the Microsoft-side review
  expectation (1-3 day turnaround per release).

**Gates green:** 2377 passed / 1 skipped / 109 subtests (+18 from
this slice); ruff clean; mypy clean (156 source files); contract
audit clean.

**Compatibility surface:** new publication channel; existing
stable surfaces unaffected. The winget manifest references the
PH-21.2 binary by URL pattern (mythic-vibe-${VERSION}-windows-
x86_64.exe), so any future renaming of PH-21.2's asset suffix
must update both PH-21.2 and PH-21.8 in lockstep — caught by
the test_winget_resolves_windows_binary_from_release_assets test.

Beginning slice 21.3 (Nuitka alternative binaries) next.

### 2026-05-05 — Slice 21.3 closed (Nuitka alternative binaries)
**Shipped:**
- `packaging/nuitka/build.py` — Python build driver wrapping the
  Nuitka invocation. Pure function `build_command(output_dir,
  binary_name)` returns the argv list (testable without invoking
  Nuitka). Flags: `--standalone --onefile`, explicit
  `--include-package=mythic_vibe_cli` so Nuitka's static analyzer
  picks up modules beyond the entrypoint shim's direct imports,
  `--include-package-data=mythic_vibe_cli` for resources/schemas/*.json,
  `--remove-output` for clean rebuilds, `--show-progress` for
  informative CI logs, `--assume-yes-for-downloads` for
  unattended runs, eight `--nofollow-import-to=` excludes
  matching PyInstaller's exclusion set (anthropic / openai /
  google / textual / rich / opentelemetry / hypothesis / pytest).
  Compiles from the **same** entrypoint shim as PyInstaller
  (`packaging/pyinstaller/entrypoint.py`) so both binaries'
  runtime behavior matches exactly. `--dry-run` flag for
  local rehearsal without the build cost.
- `.github/workflows/release-binaries.yml` — new `build-nuitka`
  job parallel to the existing `build` (PyInstaller) job. Same
  4-row OS matrix (ubuntu-latest, macos-latest, macos-13,
  windows-latest). Invokes `python packaging/nuitka/build.py`
  for each row, smoke-tests the binary, renames with the nuitka
  suffix (`mythic-vibe-nuitka-${VERSION}-${OS}-${ARCH}`), uploads
  per-row sha256 sidecar. The `github-release` job now waits on
  both `build` and `build-nuitka` (`needs: [build, build-nuitka]`),
  flattens both artifact sets, and uploads all 8 binaries + 8
  sha256 files to the GitHub Release for the tag.
- `tests/test_packaging_nuitka.py` — 16 new tests across 2
  classes:
    NuitkaBuildDriverTests (10) — driver imports cleanly, returns
    argv list of strings, invokes `python -m nuitka`, uses
    `--standalone --onefile`, includes the project package, bundles
    package data, excludes optional extras with the right
    nofollow flags, points at the shared PyInstaller entrypoint
    shim, propagates `--output-dir` correctly across platforms,
    accepts `--dry-run` cleanly.
    ReleaseBinariesNuitkaJobTests (6) — workflow has the
    build-nuitka job, invokes the build driver, covers the full
    OS matrix including macos-13, asset names embed `nuitka`,
    smoke commands present, github-release waits for both
    matrices.
- `docs/INSTALL.md` — new `#### Nuitka alternative` subsection
  inside the standalone-binaries section. Comparison table
  (asset name, binary size, cold start, build time, behavior)
  contrasts the two binary flavors. Operator-facing guidance:
  pick by preference, Nuitka wins when binary size or cold-start
  latency matters (e.g. CI runners invoking the CLI hundreds of
  times per pipeline). Same download + verify recipe shape as
  the PyInstaller subsection.
- `packaging/README.md` — channel table extended with the Nuitka
  binaries row. Defer-section finalized: all v1.x distribution
  channels have shipped; only PH-21.5 (Sigstore) and PH-21.6
  (reproducible attestations + tag signing) remain in PH-21
  scope, both cross-cutting cryptographic provenance work that
  applies on top of the channels rather than adding new ones.

**Gates green:** 2393 passed / 1 skipped / 109 subtests (+16 from
this slice); ruff clean; mypy clean (156 source files); contract
audit clean.

**Compatibility surface:** new publication channel; existing
stable surfaces unaffected. Both Nuitka and PyInstaller binaries
ship the same stdlib-only contract — the only operator-visible
differences are file size and cold-start latency. Operators who
script CI pipelines around the binary's exit codes / argv
parsing get identical behavior either way.

Beginning slice 21.5 (Sigstore signed artifacts) next.

### 2026-05-05 — Slice 21.5 closed (Sigstore keyless signing)
**Shipped:**
- `.github/workflows/release.yml` — new `Sign artifacts with
  Sigstore (keyless)` step uses
  `sigstore/gh-action-sigstore-python@v3.0.0` to sign the wheel
  + sdist + SBOM. The action requests a short-lived Fulcio cert
  via the workflow's OIDC `id-token`, signs each input, and
  emits `.sigstore` bundle files (signature + cert + Rekor entry)
  next to the artifacts. The github-release step now uploads
  `dist/*.sigstore` alongside the existing checksums + SBOM so
  operators can fetch a single bundle and verify offline-friendly.
- `.github/workflows/release-oci.yml` — new `Install cosign` +
  `Sign image with cosign (keyless)` steps. Uses
  `sigstore/cosign-installer@v3` (cosign v2.4.0) and
  `cosign sign --yes` against the manifest digest of both the
  versioned (`:VERSION`) and floating (`:latest`) tags. Signing
  the digest (not the tag) keeps the signature valid even if
  `:latest` is later repointed.
- `.github/workflows/release-binaries.yml` — new Sigstore signing
  steps in both the `build` (PyInstaller) and `build-nuitka`
  jobs. Same `sigstore/gh-action-sigstore-python@v3.0.0` pattern
  as release.yml, scoped to each row's binary path
  (`dist/mythic-vibe-*` for PyInstaller; `dist-nuitka/mythic-
  vibe-nuitka-*` for Nuitka). Bundles ship as workflow artifacts
  alongside the binaries; the github-release flatten step
  picks them up automatically.
- `docs/security/verifying_artifacts.md` — new comprehensive
  verification guide (~250 lines) covering:
  - Quick reference table mapping channel → tool → expected
    cert identity.
  - PyPI artifact verification recipe with explicit
    `python -m sigstore verify identity` invocations for both
    wheel + sdist.
  - Standalone binary verification (PyInstaller + Nuitka) with
    the per-channel cert identity (different workflow file →
    different identity URL).
  - OCI image verification via `cosign verify`, including the
    pin-to-digest pattern for operators who want to anchor
    against a specific manifest.
  - "Why keyless?" rationale section: no long-lived signing key,
    public Rekor transparency log, no registration required.
  - Forward-pointer to PH-21.6 reproducible build attestations
    that close the "from what" supply-chain gap (signatures
    prove who; attestations prove from what).
  - Troubleshooting: tag mismatch, old tooling, asset/bundle
    mismatch.
- `tests/test_packaging_templates.py` — 2 new tests on
  ReleaseWorkflowTests (test_signs_artifacts_with_sigstore +
  test_uploads_sigstore_bundles_to_release).
- `tests/test_dockerfile_lint.py` — 1 new test on
  ReleaseOciWorkflowTests (test_signs_image_with_cosign_keyless).
- `tests/test_packaging_pyinstaller.py` — 2 new tests on
  ReleaseBinariesWorkflowTests (test_signs_pyinstaller_binary +
  test_signs_nuitka_binary).

**Gates green:** 2398 passed / 1 skipped / 109 subtests (+5 from
this slice); ruff clean; mypy clean (156 source files); contract
audit clean.

**Compatibility surface:** new cryptographic provenance over
existing publication channels. Operators who don't verify see
no behavior change (signatures are additive); operators who
adopt verification get an offline-friendly verify path with a
public-good trust root. Replaces (does not remove) the PH-20.6
checksums-only approach — checksums still ship as the fast-path
pre-flight check, but the cryptographic root of trust now sits
with Sigstore.

Beginning slice 21.6 (reproducible build attestations + tag
signing) next — the final PH-21 slice.

### 2026-05-05 — Slice 21.6 closed (SLSA build provenance + tag signing)
**Shipped:**
- `.github/workflows/release.yml` — new `Attest wheel + sdist +
  SBOM build provenance` step uses
  `actions/attest-build-provenance@v2` to emit SLSA Level 3
  attestations binding artifact subject digest to the workflow
  invocation that produced it (commit, workflow file, inputs).
  Workflow permissions extended with `attestations: write`.
- `.github/workflows/release-oci.yml` — two new steps after the
  cosign signing: `Resolve image digest for attestation` (uses
  `docker buildx imagetools inspect` to get the manifest digest)
  + `Attest OCI image build provenance` with
  `subject-digest` + `subject-name` + `push-to-registry: true`
  so the attestation is queryable via `gh attestation
  verify-image`. Workflow permissions extended with
  `attestations: write`.
- `.github/workflows/release-binaries.yml` — new attestation
  steps in both `build` (PyInstaller) and `build-nuitka` jobs,
  each scoped to the matching subject-path. Workflow permissions
  extended with `attestations: write`.
- `docs/security/tag_signing.md` — new ~150-line maintainer
  guide for `gitsign` (Sigstore's keyless equivalent of
  GPG-signed tags). Covers:
  - One-time setup (install gitsign, configure git locally to
    use it for tags).
  - Cutting a signed tag (`git tag -s`, OIDC browser flow,
    Rekor logging, push to trigger pipeline).
  - Verifying a tag (both end-user `git verify-tag` and
    richer `gitsign verify` paths).
  - The supply-chain trust chain (tag → build attestation →
    artifact signature → operator verification).
  - GPG fallback for air-gapped maintainers.
  - The "tags via GitHub web UI are not signed" caveat plus
    recovery recipe (delete unsigned tag, re-create signed,
    re-push).
- `docs/security/verifying_artifacts.md` — extended with two new
  sections:
  - "Build provenance attestations (PH-21.6)" — covers
    `gh attestation verify` for wheel/sdist/SBOM/binaries and
    `gh attestation verify-image` for the OCI image. Includes
    a `--predicate-type "https://slsa.dev/provenance/v1"` filter
    recipe for operators with strict SLSA L3 enforcement.
  - "Tag signatures (PH-21.6)" — points operators at
    `git verify-tag` and `gitsign verify` recipes; references
    the maintainer guide for cutting signed tags.
- `tests/test_packaging_templates.py` — 2 new tests
  (test_emits_slsa_build_provenance_attestation +
  test_attestations_write_permission_present).
- `tests/test_dockerfile_lint.py` — 2 new tests
  (test_emits_slsa_build_provenance_attestation +
  test_attestations_write_permission_present), the OCI variant
  also asserting `subject-digest:` + `push-to-registry: true`.
- `tests/test_packaging_pyinstaller.py` — 3 new tests
  (test_emits_pyinstaller_build_provenance_attestation +
  test_emits_nuitka_build_provenance_attestation +
  test_attestations_write_permission_present).

**Gates green:** 2405 passed / 1 skipped / 109 subtests (+7 from
this slice); ruff clean; mypy clean (156 source files); contract
audit clean.

**Compatibility surface:** new cryptographic provenance layer.
Existing operators see no behavior change unless they opt into
verification. Operators who do verify get a complete supply-
chain proof: tag signature (which commit was the release) +
build provenance attestation (which artifact came from which
commit + workflow) + Sigstore artifact signature (who signed it).

---

## PH-21 — phase closeout

**All 9 slices shipped, 2026-05-05.**

| Slice | Title | Status | Commit |
|---|---|---|---|
| 21.7 | AUR maintainer-repo channel | ✅ | `723e256` |
| 21.9 | Termux + WSL + Pi platform tags | ✅ | `7342d13` |
| 21.1 | Multi-arch OCI container image | ✅ | `06c1d81` |
| 21.2 | PyInstaller standalone binaries | ✅ | `2d2ae6c` |
| 21.4 | macOS Gatekeeper override docs | ✅ | `3797b63` |
| 21.8 | winget v1.6 manifest channel | ✅ | `563c1cb` |
| 21.3 | Nuitka alternative binaries | ✅ | `84b415b` |
| 21.5 | Sigstore keyless signing | ✅ | `b6887bb` |
| 21.6 | SLSA build provenance + tag signing | ✅ | (this commit) |

**Test count change across PH-21:** 1925 → 2405 (+480 tests over 9 slices).

**New surfaces shipped:**

Distribution channels added in v1.x:
- AUR (Arch User Repository) — source from PyPI sdist
- OCI multi-arch image (GHCR + optional Docker Hub mirror)
- PyInstaller standalone binaries (Linux × Windows × macOS arm64 × macOS x86_64)
- Nuitka alternative binaries (same matrix)
- winget portable manifest (via maintainer repo + microsoft/winget-pkgs)

Platform polish:
- Termux / WSL / Raspberry Pi / arm64 platform-tag detection on the hardware command JSON surface

Cryptographic provenance:
- Sigstore keyless signatures over PyPI artifacts + OCI image + 8 standalone binaries
- SLSA Level 3 build provenance attestations across all release artifacts
- gitsign-based tag signing maintainer workflow

Documentation added:
- `docs/security/verifying_artifacts.md` — comprehensive end-user verification guide
- `docs/security/tag_signing.md` — maintainer guide for signed releases
- `docs/INSTALL.md` — sections for AUR, Termux, WSL, Container, Standalone binaries (PyInstaller + Nuitka with Gatekeeper override), winget
- `packaging/README.md` — channel matrix + secret table + maintainer-repo sync recipes

**Operator decisions remaining for first PH-21-era release:**
1. Provision the four maintainer repos: `aur-mythic`, `winget-mythic`, `homebrew-mythic` (already exists), `scoop-mythic` (already exists).
2. Configure repo PATs as secrets: `AUR_BUMP_TOKEN`, `WINGET_BUMP_TOKEN`, `TAP_BUMP_TOKEN` (existing), `BUCKET_BUMP_TOKEN` (existing).
3. Decide whether to enable Docker Hub publishing — sets `DOCKERHUB_PUBLISH_ENABLED` repo variable to `true` and provisions `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` secrets if yes; default-skip if no.
4. Install gitsign on the release-cutting machine and configure repo-local git for signed tags (one-time setup; recipe in `docs/security/tag_signing.md`).
5. (Optional) Configure PyPI trusted publishing for the project on pypi.org.

PH-21 leaves the project ready to ship its first v1.x distribution-expansion release once the operator items above are in place. PH-22 (v2.0 strategic stretch — Rust/Go launcher, Android wrapper, WASI runtime) remains in the backlog as multi-week work.

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
