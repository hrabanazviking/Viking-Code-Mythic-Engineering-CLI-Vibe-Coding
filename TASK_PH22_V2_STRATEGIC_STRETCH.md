# TASK — PH-22 v2.0 Strategic Stretch (kickoff)

**Opened:** 2026-05-05
**Branch:** `development`
**HEAD at kickoff:** `875166f` (PH-21 final slice closed)
**Operator:** Volmarr Wyrd
**Author:** Runa Gridweaver Freyjasdottir, executing on Volmarr's behalf
**Status:** `OPEN — AUTONOMOUS RUN — slice 22.1 first`

---

## Why this file exists

Volmarr granted full-permission autonomous mode for PH-22 + any
follow-on work on 2026-05-05, immediately after PH-21 closed.
PH-22 is the v2.0 strategic stretch phase already scoped in
`TASK_PH19_DISTRIBUTION.md` (the master plan tracker). The
locked decisions confirm all three sub-items in scope (22.1 +
22.2 + 22.3) with cumulative effort estimated at ~9-14 weeks of
human attention.

This kickoff file pins the dependency-respecting execution order
and acts as the resume contract if a session breaks before
completion. **PH-22 is genuinely multi-week R&D per slice** —
the realistic deliverable per autonomous run is **substantive
foundation work** (real scaffolds with tests + CI + operator
docs) that future sessions can extend toward production-quality
implementations.

---

## Operating rules (carry-over from prior phases)

1. **Additive only — never subtractive** (`feedback_additive_only.md`).
2. TASK file → commit + push → implement → ruff/mypy/pytest green →
   per-slice closeout addendum → memory update → push.
3. ruff + mypy + pytest gate every Python commit.
4. Stdlib-first (Python); cross-platform; open-source-only;
   file-location-agnostic.
5. New languages welcome: Rust (22.1) + Kotlin/Java (22.2) + Rust
   or Python (22.3) all introduce new toolchains. Each must come
   with build infrastructure that survives operator hand-off.
6. One cohesive slice per commit; no batching.
7. Push frequently, not just at the end.

---

## Execution order (dependency-respecting)

PH-22 has no internal dependencies between slices — each is an
independent v2.0 surface. Order is by **highest distribution
leverage first** so the work that matters most (22.1) is done
even if the session doesn't make it through all three.

| Order | Slice | What | Effort (full impl) | Status |
|---|---|---|---|---|
| 1 | **22.1** | Rust launcher shim — single static binary with no Python dep | ~2-4 weeks | [x] foundation |
| 2 | **22.2** | Native Android wrapper app — Kotlin/Chaquopy CLI shell | ~3-6 weeks | [x] foundation |
| 3 | **22.3** | WASI experimental runtime — CLI compiled to WebAssembly | ~4+ weeks (speculative) | [ ] |

**PH-22 cumulative full-impl effort:** ~9-14 weeks per the locked
plan. **Foundation-level scope per autonomous run:** 4-8 hours
across all three slices, leaving the toolchain bones in place +
clear hand-off documentation for future sessions.

---

## Per-slice deliverables — foundation-level (this run)

Each slice's foundation scope is "the minimum that lets a future
session extend toward production without re-deriving design".
Production-quality completion is recorded as out-of-scope here
and tracked in the per-slice closeout entries.

### 22.1 — Rust launcher shim
**Goal:** a small static Rust binary that, on first run, fetches
[python-build-standalone](https://github.com/indygreg/python-build-standalone)
to a per-user cache, downloads the mythic-vibe-cli wheel from
PyPI, installs into the cached interpreter, and execs the CLI.
Subsequent runs reuse the cache. Operators get a single
~3-5 MB binary that requires no Python pre-installed.

**Foundation deliverables:**
- `packaging/launcher/Cargo.toml` — Rust crate manifest with the
  HTTP / archive / path dependencies pinned.
- `packaging/launcher/src/main.rs` — the launcher entry point
  with structured stages (locate cache, fetch interpreter,
  install wheel, exec CLI). Each stage is its own function so
  future tests can mock the network layer.
- `packaging/launcher/README.md` — design doc covering the
  download URLs, cache layout, version-pinning strategy, and
  the operator-visible UX (first-run vs cached-run output).
- `.github/workflows/release-launcher.yml` — workflow scaffold
  that runs `cargo build --release` per OS matrix, smokes the
  binary, applies Sigstore signing + SLSA attestations
  (carrying PH-21.5 + PH-21.6 patterns forward).
- `tests/test_launcher_scaffold.py` — Python-side structural
  tests asserting Cargo.toml shape, src/main.rs presence of
  the documented stages, and workflow shape.
- `docs/INSTALL.md` — new "Launcher binary (no Python required)"
  section explaining download + first-run UX + cache location.

**Out-of-scope (deferred to future session):**
- Polishing the first-run UX (progress bars, retries, mirror
  selection, offline-cache pre-population).
- Verifying the launcher's downloaded artifacts via the
  PH-21.5 Sigstore signatures.
- Plugin support — the launcher today execs the base CLI;
  plugin discovery from the cached venv works automatically
  but is not yet documented.

### 22.2 — Native Android wrapper app
**Goal:** an Android app (Kotlin) that embeds the Python runtime
via [Chaquopy](https://chaquo.com/chaquopy/) and presents the
CLI as a native Android UI (text input + scrollable output).
First-class Android distribution path complementing the existing
Termux-via-pip path.

**Foundation deliverables:**
- `packaging/android/` directory with a buildable Gradle project
  skeleton:
  - `build.gradle.kts` (Kotlin DSL, modern Gradle).
  - `app/build.gradle.kts` with the Chaquopy plugin + min-SDK
    + target-SDK + the project's Python version.
  - `app/src/main/kotlin/.../MainActivity.kt` — Compose-based
    activity that runs the CLI in a coroutine and streams
    output to a Text composable.
  - `app/src/main/AndroidManifest.xml` — minimal permissions
    (INTERNET only, for the AI provider extras when enabled).
- `packaging/android/README.md` — design doc covering the
  Gradle build flow, why Chaquopy over BeeWare, the SDK / NDK
  setup operators need, and the operator-visible UX.
- `.github/workflows/release-android.yml` — workflow scaffold
  that runs `./gradlew assembleRelease` to produce an APK,
  smoke-tests it via the Android emulator action, signs +
  attests, attaches to the GitHub Release.
- `tests/test_android_scaffold.py` — Python-side structural
  tests asserting the Gradle project shape + AndroidManifest
  declarations + workflow shape.
- `docs/INSTALL.md` — new "Android (native app)" section
  alongside the existing Termux section.

**Out-of-scope (deferred):**
- F-Droid + Play Store distribution (each their own multi-day
  paperwork item).
- Native Android UI for richer interactions (file picker,
  share-target, in-app provider config).
- Android-specific Mythic features (auto-record check-ins as
  voice memos via Android's transcription API).

### 22.3 — WASI experimental runtime
**Goal:** prove out compiling mythic-vibe-cli to WebAssembly
(WASI target) so it runs in any WASM-supporting host
(browsers via py2wasm/Pyodide, Wasmtime/wasmer servers, Node
with WASI shim). Pure exploration — many Python deps don't
WASI-compile yet, so the deliverable scope is "what works,
what doesn't, what's unblockable".

**Foundation deliverables:**
- `packaging/wasi/` directory with:
  - `README.md` — research doc covering: which CPython→WASM
    paths exist (CPython main-branch WASI target, Pyodide,
    py2wasm); compatibility status of mythic-vibe-cli's stdlib
    usage; which paths break (subprocess, fcntl, threading);
    proposed first-cut scope (read-only "doctor" + "status"
    JSON output, no subprocess-based commands).
  - `Cargo.toml` (if a Rust harness wraps the wasm) OR
  - `build.py` (if the build is purely Python tooling).
  - A minimal WASI build script that compiles the project's
    stdlib-only base + emits a `.wasm` artifact.
- `.github/workflows/release-wasi.yml` — workflow scaffold
  that produces the `.wasm` artifact on tag push, attests +
  signs, attaches to the Release.
- `tests/test_wasi_scaffold.py` — Python-side tests verifying
  the build infrastructure + workflow shape.
- `docs/INSTALL.md` — new "WebAssembly (experimental)" section
  with the explicit "many features not yet supported" caveat.

**Out-of-scope (deferred):**
- Actually shipping a fully-functional CLI in WASM. The
  immediate goal is `mythic-vibe doctor --json` working in
  WASI; full surface support waits on upstream Python WASI
  evolution.
- Browser playground (deferred to v2.x once the WASI base
  works in Wasmtime / wasmer).
- Pyodide-based browser path (parallel exploration; deferred).

---

## Status updates per slice (additive log)

Each slice gets a dated entry below as it lands. New entries
append; prior entries are never mutated.

### 2026-05-05 — Kickoff committed
TASK file written, plan locked. Beginning slice 22.1 (Rust
launcher) on commit `+1` from this kickoff commit.

### 2026-05-05 — Slice 22.1 closed at FOUNDATION level (Rust launcher shim)
**Shipped:**
- `packaging/launcher/Cargo.toml` — Rust crate manifest pinning
  Rust 1.74 MSRV, Apache-2.0 license, all 10 runtime deps (ureq
  for HTTP, flate2 + tar + zstd for archive extraction, dirs for
  per-user cache dir resolution, serde + serde_json for JSON,
  sha2 + hex for SHA256 verification, anyhow for error
  handling). Release profile pinned for size: `opt-level = "z"`,
  `lto = true`, `codegen-units = 1`, `strip = true`,
  `panic = "abort"` — produces ~3 MB binary.
- `packaging/launcher/src/main.rs` — 13 named pub fn lifecycle
  stages (run, resolve_cache_root, ensure_interpreter,
  pbs_download_url, host_target_triple, python_executable_in,
  download, extract_archive, ensure_venv_with_cli, venv_has_cli,
  create_venv, pip_install_cli, exec_cli) plus `#[cfg(test)]`
  unit tests covering env-override resolution, URL
  composition, host triple resolution, and Python exe path.
  Cross-platform: Unix `execv` for signal passthrough; Windows
  spawn+wait fallback. 5-arch host_target_triple match
  (x86_64+aarch64 Linux, x86_64+arm64 macOS, x86_64 Windows).
  Two archive extraction paths (.tar.gz + .tar.zst).
- `packaging/launcher/README.md` — design doc covering: what
  the launcher is, three-strategy comparison
  (PyInstaller/Nuitka/Launcher), per-platform cache layout,
  build instructions, "adding an extra to the cached venv"
  recipe, foundation-vs-deferred breakdown (5 deferred items
  enumerated for future sessions: SHA256 verification,
  first-run UX polish, wheel version pinning, Sigstore wheel
  verification, offline cache pre-population), Rust-vs-Go
  rationale, and three-operator-profile guidance.
- `.github/workflows/release-launcher.yml` — new workflow with
  5-row arch matrix (ubuntu-latest, ubuntu-24.04-arm,
  macos-latest, macos-13, windows-latest, each with explicit
  rustup target). Per row: install Rust toolchain, resolve
  version from pyproject, `cargo build --release --target X`,
  `cargo test --release --target X` for unit-level coverage,
  rename binary with asset suffix, compute SHA256 sidecar,
  apply PH-21.5 Sigstore signing + PH-21.6 SLSA attestation
  (workflow permissions extended with `attestations: write`),
  upload artifact. Separate `github-release` job flattens all
  5 rows + uploads to the existing GitHub Release.
- `tests/test_packaging_launcher.py` — 26 Python-side
  structural tests across 4 classes:
    LauncherCargoManifestTests (5) — crate name, license, MSRV,
        all 10 runtime deps present, size-optimized release
        profile flags.
    LauncherMainRsTests (8) — pinned PYTHON_VERSION constant,
        pinned PBS_RELEASE_TAG, all 13 lifecycle pub fn names
        present, MYTHIC_LAUNCHER_CACHE env var, all 5 host
        target triples covered, both .tar.gz + .tar.zst
        extraction paths, Unix execv usage, internal test mod
        present.
    LauncherReadmeTests (4) — cache layout documented,
        env-override documented, three-strategy comparison
        present, deferred-work subsection present.
    ReleaseLauncherWorkflowTests (9) — tag triggers, manual
        rehearsal, full 5-arch matrix coverage, cargo build +
        cargo test invocation, sha256 sidecar emission,
        Sigstore signing, SLSA attestation, GitHub Release
        upload.
- `docs/INSTALL.md` — new "Launcher binary (no Python required)"
  section between Standalone binaries and Container. Three-way
  comparison table; download + verify recipe; per-platform
  cache layout; "install extras into cached venv" recipe;
  forward-pointer to `packaging/launcher/README.md`.
- `packaging/README.md` — channel table extended with the
  launcher row.

**Gates green:** 2431 passed / 1 skipped / 109 subtests (+26
from this slice); ruff clean; mypy clean (156 source files);
contract audit clean.

**Foundation status:** the crate compiles, the CI workflow
shape is right, the design + cache layout + operator UX are
fully documented. **Production-quality completion
deferred** to future sessions and explicitly enumerated in
`packaging/launcher/README.md` (SHA256 verification, first-run
UX polish, wheel version pinning, Sigstore wheel verification,
offline cache pre-population). A future session has every
hook needed to extend this without rederiving design.

**Compatibility surface:** new publication channel.
Fundamentally different trade-off from the
PyInstaller/Nuitka binaries: smaller initial download, slower
first run, supports operator-installed extras post-first-run.
Does not affect any existing stable surface.

Beginning slice 22.2 (Native Android wrapper app) next.

### 2026-05-05 — Slice 22.2 closed at FOUNDATION level (Native Android wrapper app)
**Shipped:**
- `packaging/android/settings.gradle.kts` — Gradle settings with
  the chaquo.com/maven repo entry that lets the Chaquopy plugin
  resolve.
- `packaging/android/build.gradle.kts` — top-level plugin
  declarations (Android Gradle Plugin 8.5.2, Kotlin 2.0.20,
  Compose plugin, Chaquopy 16.0.0), all `apply false`.
- `packaging/android/gradle.properties` — JVM args, parallel
  builds, configuration cache, AndroidX-only stack, Kotlin
  official code style.
- `packaging/android/app/build.gradle.kts` — app module with:
  - Chaquopy plugin applied + `chaquopy { defaultConfig { pip {
    install("mythic-vibe-cli") } } }` so the wheel + transitive
    deps bake into the APK at build time.
  - Compose enabled via `buildFeatures.compose = true` + the
    Compose Compiler plugin.
  - min-SDK 26 (Android 8.0+, ~99% of in-use devices).
  - ABI filters covering armeabi-v7a + arm64-v8a + x86 + x86_64.
  - Java/Kotlin 17 source/target.
  - Compose BOM 2024.09.03 + Material 3 + Activity Compose +
    Lifecycle ViewModel.
- `packaging/android/app/src/main/AndroidManifest.xml` — single
  INTERNET permission only; rationale documented in a comment
  block listing what's intentionally NOT declared (RECORD_AUDIO,
  WRITE_EXTERNAL_STORAGE, etc.). Single MainActivity with the
  LAUNCHER intent filter.
- `packaging/android/app/src/main/kotlin/dev/mythicvibe/android/MainActivity.kt` —
  Compose-based single-activity UI. `Python.start(AndroidPlatform(this))`
  in `onCreate` so the first-command latency surfaces in startup.
  `MythicVibeApp` composable: text-input field for command,
  Run button, scrollable output panel. CLI invocations run on
  `Dispatchers.IO` via the runner module; errors caught + shown
  in output rather than crashing the activity.
- `packaging/android/app/src/main/python/mythic_vibe_cli_android_runner.py` —
  Chaquopy-side runner. Captures stdout + stderr from
  `mythic_vibe_cli.cli.main` via `contextlib.redirect_*`,
  handles SystemExit (argparse errors), returns a string with
  the captured output + exit code so the Compose UI gets a
  ready-to-display blob.
- `packaging/android/app/proguard-rules.pro` — advisory rules
  (R8 disabled today; Chaquopy + Compose reflection don't play
  with aggressive shrinking).
- `packaging/android/README.md` — design doc covering: what the
  app is, complementary-with-Termux positioning, why Chaquopy
  over BeeWare, build instructions, project layout, foundation-
  vs-deferred work breakdown (6 deferred items: APK signing
  config, streaming stdout, cancellation, persistent session
  log, native UI for richer flows, F-Droid + Play Store
  distribution), three-operator-profile guidance.
- `.github/workflows/release-android.yml` — workflow with JDK
  17 setup, Python 3.12 setup (Chaquopy needs it), version-
  resolve from pyproject, `gradle wrapper --gradle-version
  8.10` (foundation-level: gradle wrapper isn't checked in
  yet, generated at build time), `assembleRelease`, locate
  the APK + rename with `mythic-vibe-${VERSION}-android.apk`
  + sha256 sidecar. Applies PH-21.5 Sigstore signing + PH-21.6
  SLSA attestation. attestations: write permission added.
  Separate github-release job uploads the APK to the existing
  GitHub Release.
- `tests/test_packaging_android.py` — 31 Python-side
  structural tests across 7 classes:
    AndroidGradleProjectTests (4) — settings includes app
        module + Chaquopy repo, root build pins all 4 plugin
        versions, gradle.properties enables AndroidX.
    AppModuleTests (6) — Chaquopy plugin applied, Compose
        enabled, pip install("mythic-vibe-cli"), min-SDK 26,
        all 4 ABI filters, Python 3.12.
    AndroidManifestTests (2) — INTERNET permission only (with
        XML-comment-strip to avoid false positives on the
        rationale block), MainActivity declared with LAUNCHER
        intent.
    MainActivityTests (4) — Python.start, setContent, runner
        module reference, Dispatchers.IO usage.
    AndroidPythonRunnerTests (5) — imports cli.main, captures
        both stdout + stderr, handles SystemExit, returns
        str (not None), compiles cleanly.
    AndroidReadmeTests (3) — Chaquopy choice rationale present,
        min-SDK documented, deferred-work subsection present.
    ReleaseAndroidWorkflowTests (7) — tag triggers, manual
        rehearsal, JDK 17, assembleRelease invocation, Sigstore
        + SLSA attestation, GitHub Release upload.
- `docs/INSTALL.md` — new "Android (native app)" section
  immediately above the Termux section. Side-load via adb
  recipe + sha256 verification + complementary-with-Termux
  positioning. Forward-pointer to `packaging/android/README.md`.
- `packaging/README.md` — channel table extended with the
  Android APK row.

**Gates green:** 2462 passed / 1 skipped / 109 subtests (+31
from this slice); ruff clean; mypy clean (156 source files).

**Foundation status:** the Gradle project is buildable, the
Compose UI invokes the CLI via JNI, the Chaquopy runner module
captures and surfaces output. **Production-quality completion
deferred** to future sessions and explicitly enumerated in
`packaging/android/README.md` (APK signing config, streaming
stdout, cancellation, session log, richer UI, distribution
channel paperwork). A future session has every hook needed to
extend without rederiving design.

**Compatibility surface:** new publication channel. The Android
app + Termux are complementary — different operator profiles.
Does not affect any existing stable surface.

Beginning slice 22.3 (WASI experimental runtime) next — the
final PH-22 slice.

---

## Resume anchor

If a session breaks mid-run, the next session resumes by:
1. Reading this file.
2. Looking at the rightmost `[ ]` in the slice table to find the
   next unfinished slice.
3. Looking at the most recent dated status update to confirm
   last commit-pushed state.
4. Running `git log --oneline -10` to confirm HEAD matches the
   memory's recorded progress.
5. Continuing with the next slice in order.

After PH-22 closes, **post-PH-22 work is operator-driven** — the
master roadmap stops at PH-22. Future phases (PH-23+) would be
opened by Volmarr based on how the v2.0 stretch outcomes mature.
