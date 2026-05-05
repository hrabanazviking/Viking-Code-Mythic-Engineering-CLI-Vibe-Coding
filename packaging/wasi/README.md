# mythic-vibe-cli — WASI experimental runtime

PH-22.3 — exploring whether `mythic-vibe-cli` can run as a WebAssembly module under any WASI-supporting host (Wasmtime, wasmer, Node-with-WASI, future browsers).

> **Status:** purely experimental. Many of the CLI's surfaces will not work in WASI today; this directory ships the research, the build infrastructure, and a minimal proof of concept covering JSON-emitting read-only commands. Production-quality completion is deferred indefinitely — gated on upstream Python + Wasmtime evolution.

---

## Why bother

Three motivating use cases:

1. **Browser playground.** Operators evaluating Mythic Engineering could run `mythic-vibe doctor --json` against a sample project entirely in-browser, without installing anything. Pyodide already enables this for general Python; the goal here is a single `.wasm` artifact + a tiny JS host page.
2. **Hardened sandbox.** WASI is a fully-sandboxed runtime — no syscalls, file access only via explicit pre-opened directories, no network unless the host opts in. For security-sensitive scenarios (kiosk terminals, untrusted plugin hosts, CI runners with extreme isolation), running the CLI as WASM gives stronger guarantees than the OCI image.
3. **Universal binary.** A single `.wasm` artifact runs everywhere a WASI host runs — no per-OS / per-arch matrix.

The trade-off: significantly reduced functionality. WASI today doesn't support most of the system surface a real CLI relies on.

---

## What works in WASI (as of 2026-05)

CPython main-branch + several alternative paths exist. The compatibility status of mythic-vibe-cli's stdlib usage:

| Stdlib module | WASI support | mythic-vibe usage | Verdict |
|---|---|---|---|
| `argparse` | ✅ | every command | works |
| `json` | ✅ | every `--json` command | works |
| `pathlib`, `os.path` | ✅ | every command (with limits — see below) | works |
| `dataclasses` | ✅ | many internal types | works |
| `tomllib` (3.11+) | ✅ | version reading | works |
| `re` | ✅ | parsers, validators | works |
| `urllib.request` | ⚠️ host-controlled | AI provider calls | works only if host opts in |
| `subprocess` | ❌ | `doctor` git-status checks, `forge resume`, plugin sandbox | breaks |
| `os.fork`, `multiprocessing` | ❌ | (none — already avoided) | n/a |
| `threading` | ⚠️ partial | `runtime/cross_process_lock.py` | partial |
| `fcntl` (POSIX file locks) | ❌ | `runtime/cross_process_lock.py` | breaks |
| `socket` (raw) | ⚠️ host-controlled | (none directly; transitively via urllib) | host-dependent |

### File access

WASI sandboxes file access via **pre-opened directories** — the host must explicitly grant access to a directory tree at module instantiation. The CLI's project-scoped operations (`mythic-vibe init`, `imbue`, `start`, `status`, `verify`) all assume access to the operator's project directory, which the WASI host must pre-open as `/work` (or similar).

### Subprocess-based commands

The CLI's git integration, plugin sandbox, and several other surfaces shell out via `subprocess`. These will exit non-zero with a `subprocess module not available` error on WASI. The v2.0-WASI scope is **read-only JSON-emitting commands only**:

- `mythic-vibe --version` ✅
- `mythic-vibe doctor --json` ⚠️ (subprocess-based git checks suppressed)
- `mythic-vibe status --json` ✅
- `mythic-vibe packet list --json` ✅
- `mythic-vibe ai models --provider X --json` ✅
- `mythic-vibe verify --json` ⚠️ (subprocess plugin sandbox unavailable)

Anything that writes to disk, runs git, or executes plugins is out of scope until WASI itself catches up.

---

## Build paths considered

Three paths for compiling Python+CLI to WASM:

### Path A — CPython upstream WASI target

CPython main has supported `wasm32-wasi` as an experimental target since 3.11. Build flow:

```bash
git clone https://github.com/python/cpython
cd cpython
git checkout v3.12.7
./Tools/wasm/wasi.py configure-build-python
./Tools/wasm/wasi.py make-build-python
./Tools/wasm/wasi.py configure-host
./Tools/wasm/wasi.py make-host
# Output: cross-build/wasi/python.wasm
```

**Pros:** matches the reference Python that pip-installed users get. No third-party Python distribution to track.

**Cons:** the build is complex (cross-compile + freezing the stdlib). The output `.wasm` is ~30-40 MB. Most C extensions don't WASI-compile (numpy, anything-with-native-code).

### Path B — Pyodide

[Pyodide](https://pyodide.org/) is a Python distribution for the browser. It compiles CPython to WASM via emscripten (not WASI proper) and ships its own package index of WASI-compatible wheels.

**Pros:** mature, widely adopted, comprehensive C-extension story (numpy / pandas / matplotlib all work). Great browser story.

**Cons:** emscripten target, not WASI — runs in browsers + Node + emscripten host but NOT in Wasmtime / wasmer. Pyodide's package format diverges from PyPI's wheel format.

### Path C — py2wasm (Wasmer)

[py2wasm](https://wasmer.io/posts/py2wasm-a-python-to-wasm-compiler) compiles a Python program (not CPython) to a single `.wasm` binary using Wasmer's Nuitka-based AOT compiler. The output runs in any WASI host.

**Pros:** single-file output. Fast cold start (no interpreter boot). Output is genuinely WASI, not emscripten.

**Cons:** newer / less battle-tested than CPython-upstream. Pure-Python only — no C extensions.

### Decision (foundation level)

**Path A** is the chosen path for the v2.0 WASI runtime, because:

1. **Stays close to the reference Python.** Operators get the same Python semantics as pip-installed users, modulo the WASI compatibility limits documented above.
2. **WASI proper, not emscripten.** Runs in any WASI host — Wasmtime, wasmer, future browsers via the WASI-on-Web standard.
3. **Pure-Python is fine.** The CLI's stdlib-only base has zero C extensions; the optional extras (anthropic, openai, textual, rich, opentelemetry) are deliberately excluded from the WASI build to match the reduced functional scope.

Pyodide remains a parallel exploration for a future browser-playground slice; py2wasm remains a contingency if upstream CPython WASI evolution stalls.

---

## Foundation-level scope (PH-22.3)

What's shipped:

- ✅ This README documenting the research + decision.
- ✅ `build.py` — Python build script that wraps the CPython WASI cross-build (or accepts a pre-built `python.wasm` from a cache for fast iteration).
- ✅ `.github/workflows/release-wasi.yml` workflow scaffold that runs the build on tag push, applies Sigstore + SLSA attestation, attaches the `.wasm` to the GitHub Release.
- ✅ `tests/test_packaging_wasi.py` — Python-side structural tests for the build script + workflow shape.
- ✅ `docs/INSTALL.md` updated with a "WebAssembly (experimental)" section explicit about the reduced functional scope.

## What was shipped after the foundation level

- ✅ **CPython WASI cross-build wired up** (PH-23.7, 2026-05-05). The `--really-build` flag now actually runs the build pipeline:
  1. Resolves a per-user build cache (`~/.cache/mythic-vibe-wasi-build/`, override via `MYTHIC_WASI_CACHE` or `--cache-dir`).
  2. Downloads + unpacks `wasi-sdk-24.0` (~250 MB) into the cache; idempotent on re-run.
  3. Downloads + unpacks the CPython source tarball at `CPYTHON_VERSION` (~25 MB) into the cache.
  4. Runs the four `./Tools/wasm/wasi.py` orchestrator steps in sequence: `configure-build-python` → `make-build-python` → `configure-host` → `make-host`. `WASI_SDK_PATH` env var set so the orchestrator finds the cross-toolchain.
  5. Copies the produced `cross-build/wasi/python.wasm` to the requested output path.

  Each step has a distinct exit code (10 / 11 / 12 / 13 for SDK install / source resolution / orchestrator / artifact-copy) so the CI log shows where the build broke. The release workflow runs the real build on tag pushes only; PR rehearsals stay on the placeholder path so CI runs stay fast.

- ✅ **CI cross-build cache** (PH-23.9, 2026-05-05). The release workflow now uses `actions/cache@v4` to persist `~/.cache/mythic-vibe-wasi-build/` between tag-push runs. Cache key is `wasi-{WASI_SDK_RELEASE}-cpython-{CPYTHON_VERSION}-v1` — bumping either pinned constant invalidates the cache so a stale toolchain never gets reused against a new source tree. Restore-key fallback matches just the SDK release, so a CPython-only bump still benefits from the already-downloaded wasi-sdk tree (~250 MB savings). Cache-hot tag pushes complete in ~5-8 min vs ~15-20 min cold.

- ✅ **mythic-vibe-cli zipapp sidecar** (PH-23.11, 2026-05-05). The build now produces a `.pyz` zipapp containing the `mythic_vibe_cli/` source tree alongside the `.wasm`. The release attaches both files; operators run the CLI under WASI via:

  ```bash
  wasmtime --dir=. mythic-vibe-1.0.0-wasi-experimental.wasm \
      -- mythic-vibe-1.0.0-wasi-experimental.pyz doctor --json
  ```

  The zipapp is built via stdlib `zipapp.create_archive` with the source-tree-only path (no pip metadata), so it lands at ~50-150 KB vs ~1-2 MB for a pip-installed tree. Compression is on. The `--build-zipapp` flag is on by default; use `--no-build-zipapp` to skip when only the bare CPython .wasm is wanted. Placeholder builds (no `--really-build`) skip the zipapp automatically. Both artifacts are Sigstore-signed + SLSA-attested via the existing PH-21.5 / PH-21.6 pattern.

  Reduced-scope contract carries forward: only the stdlib-only base ships in the zipapp; subprocess-based commands still don't work under WASI.

What was shipped after the foundation level:

- ✅ **Stdlib usage audit** (PH-23.15, 2026-05-05). New `tools/wasi_stdlib_audit.py` walks the runtime AST + reports the stdlib modules the CLI actually uses (~44 of 213), which are always-prunable in WASI regardless of usage (~72), which are unused-and-prunable (~103), plus any dynamic `importlib.import_module` call sites flagged for operator review. Output is human-readable (default) or JSON (`--json`). Run `python tools/wasi_stdlib_audit.py` to regenerate the analysis on every runtime change. Pruning impact estimate: ~175 stdlib modules can be dropped from the CPython WASI freeze list, shrinking python.wasm by ~30-40%. The analysis is the contract; the actual freeze-list patch on the CPython source tree is a separate slice (requires CPython source modification, deferred to a focused future session that owns the upstream-build-patching workflow).

What's still deferred:

- ⚠️ **CPython freeze-list patch.** The audit identifies prunable modules; a future session writes the patch to CPython's `Tools/wasm/wasi.py` orchestrator (or `Modules/Setup` / `freeze.py` config) that drops the listed modules from the embedded stdlib. Estimated ~30-40% size reduction on python.wasm.
- ⚠️ **Browser playground.** A `<wasm-host>` HTML page that loads the `.wasm` and exposes `mythic-vibe doctor --json` as a JS API.
- ⚠️ **Subprocess fallback.** Commands that shell out to git could be rewritten to use `dulwich` (pure-Python git) for WASI compatibility — opens the door to `mythic-vibe doctor` working under WASI without functionality loss. Multi-week refactor; out of v2.0 scope.

---

## Running locally (when the build lands)

```bash
# Foundation note: the actual build step is not yet wired —
# `python build.py` today emits a placeholder informing
# operators that the WASI cross-build is foundation-deferred.

cd packaging/wasi
python build.py --output ./dist/mythic-vibe.wasm

# Run with Wasmtime once a real wasm is built:
wasmtime --dir=. ./dist/mythic-vibe.wasm -- --version
wasmtime --dir=. ./dist/mythic-vibe.wasm -- doctor --json
```

---

## Why this slice exists at foundation level vs full implementation

The locked plan acknowledges PH-22.3 as ~4+ weeks of speculative work, with the explicit "many Python deps don't WASI-compile yet" caveat. Producing a real working `.wasm` build at this stage would consume the entire week's autonomous-mode budget for one slice that may not yield a usable artifact.

Instead, the foundation establishes:

1. **Decision capture.** Path A (CPython upstream) chosen, with rationale + alternatives documented.
2. **Compatibility audit.** Every stdlib module the CLI uses, with its WASI status. Operators (and future contributors) know exactly what's safe to use vs avoid.
3. **Build infrastructure shape.** The build script + workflow exist with correct contracts; future sessions fill in the actual cross-build invocation.
4. **Tested scaffolding.** Structural tests catch drift before the eventual full build lands.

When upstream CPython WASI matures (broader stdlib support, smaller binaries, better C-extension story), this scaffolding turns into a real WASI release with minimal additional design work.
