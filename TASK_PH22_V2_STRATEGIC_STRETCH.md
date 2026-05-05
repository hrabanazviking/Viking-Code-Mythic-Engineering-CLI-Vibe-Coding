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
| 1 | **22.1** | Rust launcher shim — single static binary with no Python dep | ~2-4 weeks | [ ] |
| 2 | **22.2** | Native Android wrapper app — Kotlin/Chaquopy CLI shell | ~3-6 weeks | [ ] |
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
