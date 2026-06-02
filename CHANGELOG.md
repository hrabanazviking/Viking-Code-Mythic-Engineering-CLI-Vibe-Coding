# Changelog

All notable changes to this repository's active product documentation and runtime-facing records are documented in this file.

The format is inspired by Keep a Changelog and uses explicit dates for continuity.

## [Unreleased]

This unreleased band tracks work landed on `development` after the v1.0.0 stable launch on 2026-05-03. None of it changes any v1.0 documented contract; everything is strictly additive.

### Added — Reforge roadmap Phase 0

- Added `docs/PRODUCT_INTENT.md` as the active product-intent record for the reforge roadmap. It states that Mythic is being corrected into a terminal-based coding companion CLI, with `mythic` as the primary interactive entrypoint, natural language as the main interaction, slash commands as secondary controls, and existing command code preserved as internal/admin machinery where useful. Linked the record from `docs/INDEX.md` and `README.md`.

### Added — Hermes Agent control plane (post-v1.0)

- **Hermes Agent** — programmatic control plane for any external AI agent. Two access modes (TCL Python in-process + HTTP API) share one core (`mythic_vibe_cli/agent_api/`). 18 curated tools cover status, doctor, drift, packet creation/lint, verify, reflect, ai recommend, provenance verify, workflow lineage, persona, plugin doctor, artifact read/list, recent events. Every invocation audited via the existing event-log primitive. New `mythic-vibe surface hermes [--bind ADDR --port N --token TOKEN]` launches the token-protected HTTP API. New `mythic-vibe hermes tools|inspect|invoke` invokes the curated agent-tool surface from the CLI without HTTP. See `docs/HERMES_AGENT.md` (operator + author guide).

### Added — PH-21 v1.x distribution expansion

Six new install channels alongside the v1.0 PyPI / Homebrew / Scoop trio:

- **AUR (Arch User Repository)** — `packaging/aur/PKGBUILD.template` + `.SRCINFO.template`. Release workflow `update-aur` job opens a PR against the `aur-mythic` maintainer repo via the `AUR_BUMP_TOKEN` secret. Builds from PyPI sdist so AUR users get the exact bytes PyPI users get. Operators install via `yay -S mythic-vibe-cli` or `makepkg -si`.
- **winget (Windows)** — `packaging/winget/` three-file v1.6 manifest (installer + locale + version). Workflow `update-winget` job resolves the PH-21.2 Windows binary URL + sha256 from the GitHub Release, renders the manifests, opens a PR against `winget-mythic` via `WINGET_BUMP_TOKEN`. Operators install via `winget install hrabanazviking.MythicVibeCLI`.
- **OCI multi-arch container** — `Dockerfile` + `.dockerignore` at repo root. New `release-oci.yml` workflow builds linux/amd64 + linux/arm64 via QEMU + buildx, pushes to `ghcr.io/hrabanazviking/mythic-vibe-cli:<VERSION>` + `:latest`. Optional Docker Hub mirror gated by the `DOCKERHUB_PUBLISH_ENABLED` repo variable. Image runs as non-root `mythic` (uid 1000) with workspace at `/work`, ENTRYPOINT in exec-form, OCI image labels for license + source + docs URL.
- **PyInstaller standalone binaries** — `packaging/pyinstaller/mythic-vibe.spec` + `entrypoint.py`. New `release-binaries.yml` workflow runs a 4-row OS matrix (Linux x86_64, macOS arm64, macOS x86_64 via macos-13, Windows x86_64). Each binary embeds the stdlib-only base only — extras stay with pip.
- **Nuitka alternative binaries** — `packaging/nuitka/build.py` driver. Same 4-row matrix, parallel job in `release-binaries.yml`. Smaller binaries (~8-15 MB vs ~15-25 MB for PyInstaller) and faster cold start (~80-150 ms vs ~250-500 ms) at the cost of longer build (~3-8 min per OS vs ~30-90 s).
- **macOS Gatekeeper override docs** — explicit "Right-click → Open" + `xattr -d com.apple.quarantine` recipes in `docs/INSTALL.md` for first-launch override of un-notarized binaries. Project ships un-notarized by design (no Apple Developer account required).

Plus platform polish:

- **Termux + WSL + Pi + arm64 platform-tag detection** — new `is_termux()`, `is_wsl()`, `is_raspberry_pi()`, `detect_platform_tags()` helpers in `mythic_vibe_cli/hardware.py`. `HardwareProfile` gains a `platform_tags: list[str]` field. `mythic-vibe hardware --json` exposes the tag set so operators can gate scripts on host context.
- **Termux install recipe** in `docs/INSTALL.md` covering `pkg install python rust && pip install mythic-vibe-cli`.

### Added — PH-22 v2.0 strategic stretch (foundation level)

Three v2.0 channels shipped at foundation level — real working scaffolds with comprehensive READMEs, tests, and CI workflows:

- **Rust launcher shim** — `packaging/launcher/` with `Cargo.toml` (10 runtime deps, MSRV 1.74) + `src/main.rs` (13 named pub fn lifecycle stages: cache resolve / interpreter download / archive extract / venv create / pip install / exec). Static native binary (~3-5 MB) that fetches python-build-standalone + the wheel into `~/.cache/mythic-vibe-launcher/` on first run. Subsequent runs short-circuit to the cached venv. New `release-launcher.yml` workflow runs a 5-arch matrix (Linux x86_64 + Linux aarch64 + macOS arm64 + macOS x86_64 + Windows x86_64), `cargo build --release`, `cargo test`, Sigstore signing + SLSA attestation. Operator env vars: `MYTHIC_LAUNCHER_CACHE`, `MYTHIC_LAUNCHER_REQUIRE_SHA`, `MYTHIC_LAUNCHER_MIRRORS`.
- **Native Android wrapper app** — `packaging/android/` Gradle/Kotlin project. AGP 8.5.2 + Kotlin 2.0.20 + Compose 2024.09.03 + Chaquopy 16.0.0. App embeds CPython 3.12 + the wheel via Chaquopy's pip install at APK build time. Compose-based single-activity UI invokes the CLI via JNI on Dispatchers.IO. Min-SDK 26 (Android 8.0+). Four ABIs covered (armeabi-v7a + arm64-v8a + x86 + x86_64). New `release-android.yml` workflow runs `./gradlew assembleRelease` + Sigstore signing + SLSA attestation. Single INTERNET permission — privacy-by-default. Maintainer keystore setup recipe at `packaging/android/SIGNING.md`.
- **WASI experimental runtime** — `packaging/wasi/` with `build.py` driver + `release-wasi.yml` workflow + comprehensive research README. CPython compiled to WebAssembly via the upstream `wasm32-wasi` target. Reduced functional scope: read-only JSON-emitting commands only (subprocess-based commands don't work in WASI today).

### Added — PH-23 cross-cutting polish (16 slices)

- **PH-23.1 — mkdocs-material documentation site.** New `mkdocs.yml` at repo root + `.github/workflows/docs.yml` (strict-build PR gate + GitHub Pages deploy on main pushes). Comprehensive nav: Getting Started → Operator Guides → Reference → Architecture → Security → Governance → Decision Records (10 ADRs explicitly listed). New operator-facing `docs/INDEX.md` landing; legacy contributor hub preserved at `docs/contributor_index.md`. `[docs]` extra extends with `mkdocs-material>=9.5` + `pymdown-extensions>=10.0`.
- **PH-23.2 — absolute-path-leak guard fixture.** New `tests/conftest.py` with two session-scope autouse fixtures: `remove_stale_test_debris` cleans up the May-2026 audit-cycle debris pattern at session start; `detect_absolute_path_leaks` snapshots leak-pattern dirs at start, fails the session if any test introduces new debris (Users / private / var / tmp / AppData / ProgramData top-level dirs). `MYTHIC_LEAK_GUARD_DISABLED` env disables for intentional regression tests.
- **PH-23.3 — historical wire-in TASK file commit.** Stale `TASK_wirein_cleanup.md` from 2026-05-01 (predated PH-18) committed as historical record with a closeout header verifying every listed item has a real implementation in the live codebase.
- **PH-23.4 — launcher SHA256 verification.** `verify_archive_sha256()` in `packaging/launcher/src/main.rs` with three branches (matched / mismatched / missing). New `tools/fetch_pbs_checksums.py` Python helper fetches upstream SHA256SUMS + renders a populated `PBS_EXPECTED_SHA256` const for paste-in. `MYTHIC_LAUNCHER_REQUIRE_SHA=1` env enables strict mode.
- **PH-23.5 — Android APK signing config.** `app/build.gradle.kts` declares a release `signingConfig` reading from project properties or env vars. `release-android.yml` decodes the `ANDROID_KEYSTORE_BASE64` secret to a temp file before `assembleRelease`. Falls back to unsigned APK with `::warning::` when secrets absent. New `packaging/android/SIGNING.md` maintainer guide.
- **PH-23.6 — launcher first-run UX polish.** indicatif progress bar streaming the python-build-standalone download (~30-60 s on first run no longer looks like a hang). Retry with exponential backoff (1 → 2 → 4 s, 4 attempts). Mirror failover via `MYTHIC_LAUNCHER_MIRRORS` env var with `__VERSION__` / `__TAG__` / `__TRIPLE__` placeholder substitution.
- **PH-23.7 — WASI real cross-build pipeline.** `_run_full_wasi_build()` in `packaging/wasi/build.py` now actually drives the CPython WASI cross-build: downloads wasi-sdk-24.0 + CPython source, runs the four `./Tools/wasm/wasi.py` orchestrator steps (configure-build-python → make-build-python → configure-host → make-host), copies the produced `python.wasm` to the output. Per-step exit codes (10 / 11 / 12 / 13) so the CI log shows exactly where the build broke.
- **PH-23.8 — output_guard property accessors coverage.** 7 new tests for `_ProxyStream`'s `encoding` / `name` / `closed` / `isatty` / `fileno` accessors. Module 88% → ~98%.
- **PH-23.9 — WASI cross-build CI cache.** `actions/cache@v4` keyed on `wasi-{WASI_SDK_RELEASE}-cpython-{CPYTHON_VERSION}-v1`. Cache-hot tag pushes complete in ~5-8 min vs ~15-20 min cold. Restore-key fallback matches just the SDK release for partial-hit on CPython-only bumps.
- **PH-23.10 — event_log + voice/transcribe coverage push.** 19 new tests covering OSError swallow paths, parse-line edge cases, EventTailReader poll branches, StubTranscriber edge cases, `_write_wav_temp` cleanup. event_log 84% → 97%; voice/transcribe 84% → 88%.
- **PH-23.11 — WASI zipapp sidecar.** `_build_zipapp_sidecar()` in `build.py` produces a `.pyz` zipapp containing the `mythic_vibe_cli/` source tree alongside the `.wasm`. Operators run `wasmtime --dir=. mythic-vibe.wasm -- mythic-vibe.pyz doctor --json`. The CLI now actually runs under WASI (the `.wasm` alone was bare CPython).
- **PH-23.12 — chat_bridge.py coverage push 78% → 96%.** 25 targeted tests covering parse_command shlex/empty-token edges, handle_message exception + SystemExit branches, _render_chat_block formatting modes, MatrixConfig + TelegramConfig from_file/from_env/from_sources full paths, _matrix_request + _telegram_request JSON edges, allowlist semantics.
- **PH-23.13 — workflow.py coverage push 82% → 93%.** 14 tests covering check_in invalid-phase rejection, reflect-blocked-without-verification + invalid-record + non-pass paths, status_summary handoff line composition, _load_status fallbacks, _next_phase all-complete branch, doctor edge branches.
- **PH-23.14 — web_terminal.py coverage push 80% → 97%.** 11 tests covering live HTTP routing edges (static JS path, 404 GET/POST), _read_json_body error branches (empty / invalid JSON / non-dict), handle_run_request SystemExit + Exception swallow paths, server.stop() idempotence.
- **PH-23.15 — WASI stdlib usage audit.** New `tools/wasi_stdlib_audit.py` walks the runtime AST + reports which stdlib modules are used (~44 of 213), which are always-prunable in WASI regardless of usage (~72), which are unused-and-prunable (~103). Pruning impact estimate: ~30-40% reduction on python.wasm size. Output formats: human-readable text (default) or JSON (`--json`).
- **PH-23.16 — WASI browser playground foundation.** New `packaging/wasi/playground/` directory with `index.html` (page shell + CSS) + `playground.js` (UI wiring + stub command runner) + `README.md`. Covers the v2.0 WASI command surface with quick-pick buttons + free-form text input. JS stub runner produces realistic JSON output today; future slice replaces with `@bjorn3/browser_wasi_shim` for real WASI execution.

### Added — cryptographic provenance (Sigstore + SLSA L3 + tag signing)

- **Sigstore keyless signing** over every release artifact via GitHub Actions OIDC + Fulcio. Wired into `release.yml` (PyPI wheel + sdist + SBOM), `release-oci.yml` (cosign sign --yes against the manifest digest of both `:VERSION` and `:latest`), `release-binaries.yml` (PyInstaller + Nuitka per-binary), `release-launcher.yml` (Rust launcher per-arch), `release-android.yml` (APK), `release-wasi.yml` (.wasm + .pyz). All `.sigstore` bundles ship to operators alongside the artifacts they sign.
- **SLSA Level 3 build provenance attestations** via `actions/attest-build-provenance@v2`. Bound to artifact digest + workflow run. Verifiable via `gh attestation verify` (or `gh attestation verify-image` for the OCI image).
- **gitsign-based signed release tags** — Sigstore's keyless equivalent of GPG-signed tags. Maintainer-side workflow recipe in `docs/security/tag_signing.md`.
- **`docs/security/verifying_artifacts.md`** — comprehensive end-user verification guide. Quick-reference table mapping channel → tool → expected cert identity. Per-channel recipes for PyPI / OCI / standalone binaries. Forward-pointer to PH-21.6's SLSA attestations. Troubleshooting: tag mismatch, old tooling, asset/bundle mismatch.

### Added — PH-26 continued autonomous polish (post-launch slice family)

Volmarr's 2026-05-06 directive after the PH-25 closing report: keep advancing autonomously while respecting the credential boundary. Three slices closed:

- **PH-26.0 — Housekeeping.** `coverage.json` + `htmlcov/` added to `.gitignore` so generated coverage artifacts don't drift into the repo.
- **PH-26.1 — Coverage push (+36 tests).** `context/scanner.py` 83% → 93% (os.walk fallback + `_is_doc_path` / `_is_test_path` / `_is_binary` / `_test_command_for` / `_dedupe_entries` edge cases). `protocols/mcp_client.py` 78% → 89% (initialize / list_tools / call_tool happy + non-dict / non-list error branches; close() lifecycle including stdin/stdout swallow + process-wait timeout + OSError; context-manager exit). `surfaces/chat_bridge_loop.py` 79% → 84% (transient-error classifier across all branches; matrix-loop retry + terminal propagation; telegram-loop sender exception swallow + dispatch-None skip).
- **PH-26.2 — Documentation polish.** New `SECURITY.md` (vulnerability disclosure policy with supported-versions table, response timeline by severity, in-scope vs out-of-scope, hardening posture summary) and new `docs/TROUBLESHOOTING.md` (10 sections, organised by symptom: install / doctor / AI provider / plugins / TUI / chat-bridge / Hermes / cross-platform / tests / release verification). Both wired into `docs/INDEX.md`; `TROUBLESHOOTING` added to `mkdocs.yml` nav under Operator Guides.
- **PH-26.3 — Property-based tests (+9 tests).** First hypothesis suite under `tests/property/` for the PH-24 hardening helpers. `test_url_guard_properties.py` (5 tests) covers allow-list closure across case permutations + reject-list closure across 18+ disallowed schemes + error-message structure invariants + stability-under-fuzz (no exceptions other than ValueError). `test_atomic_write_properties.py` (4 tests) covers byte-exact round-trip across arbitrary BMP text up to 4 KB + newline-preservation under EOL-heavy fuzz (regression guard for the PH-24.4 defect) + no-orphan-tmp invariant + non-utf-8 encoding round-trips.

Cumulative across PH-24 + PH-25 + PH-26: tests **2658 → 2843** (+185), aggregate (line + branch) coverage **84% → 86%** (statement-only **84% → 88.2%**), modules at ≥95% **5 → 75**, modules at ≥90% **n/a → 111 of 157** (~71%). 2 real defects fixed (Windows newline translation + URL scheme open-default); 1 new defensive module (`runtime/url_guard.py`); 2 new operator-facing documents. ruff + mypy clean throughout. Live HEAD on `development`: `878cc43`. Plan + per-slice closeouts: `PH26_CLOSING_REPORT_2026-05-06.md`.

### Added — PH-24 pre-release hardening (post-launch slice family)

Volmarr's directive 2026-05-05: defer the v1.0.1 release tag, instead spend an extended autonomous run **finding and fixing every bug, gap, and hardening opportunity** so the eventual release is genuinely stable. Strictly additive — no breaking changes, no removed features. Six slices closed:

- **PH-24.1 — Comprehensive pre-release audit.** `AUDIT_PRE_RELEASE_HARDENING_2026-05-05.md` documents 14 findings across 5 sweeps (static analysis + pseudocode + bare-except + dead-code + resource-leak). Result: 0 Critical, 0 High, 1 Medium, 4 justified Low, 6 Cosmetic. 0 TODOs in production paths. 0 resource leaks.
- **PH-24.1.fix-1 — Audit follow-through.** `ClassVar[list[Binding]]` annotations on 8 Textual screens (RUF012); `strict=False` on 4 `zip()` calls (B905); `setattr(args, "json", True)` → `args.json = True` (B010). All behaviour-preserving.
- **PH-24.2 — Coverage push (84% → 85% aggregate, +53 tests across 4 files).** `ai/providers/anthropic.py` 57% → 94%; `ai/providers/gemini.py` 28% → 95%; `plunder/github.py` 46% → 100%; `agent_api/tcl.py` 57% → 89%; `agent_api/http_api.py` 73% → 83%.
- **PH-24.3 — Cleanup-path hardening (+4 tests).** `runtime/atomic_write.py` 94% → 100% (unlink-failure mask + orphan-tmp prevention); `runtime/cross_process_lock.py` 75% → 78% (close-failure swallow + re-acquire).
- **PH-24.4 — Cross-platform regression sweep.** Found a real defect: `Path.write_text` defaulted to system newline translation, so on Windows every `\n` in a JSON / JSONL artifact became `\r\n` — producing byte-different artifacts than POSIX for the same content (would break Sigstore + SLSA hashing across release machines). Fix: pass `newline=""` to every text-mode write that produces a persistent on-disk artifact (`runtime/atomic_write.py`, `runtime/event_log.py`, `persistence/json_store.py`, `forge_ledger.py`). New `tests/test_cross_platform_invariants.py` (10 tests) guards this invariant on every CI run.
- **PH-24.5 — URL scheme guard.** New `mythic_vibe_cli/runtime/url_guard.py` exposes `assert_safe_url(url)` — rejects any scheme outside `http` / `https` before `urllib.request.urlopen` is reached. Wired into 12 urlopen sites: AI providers (anthropic / gemini / openai / openrouter / ollama / model_catalog), Ollama health probe, Mythic Engineering method-source sync + import, GitHub plunder client, Matrix homeserver request, Telegram bot API. Closes the S310 class of findings. New `tests/test_url_guard.py` (20 tests) covers happy paths + 8 reject scenarios + case-insensitive scheme + integration tests through `post_json` and `GitHubClient.get_json`.
- **PH-24.6 — Documentation completeness.** Audit found 26 env vars used in code but absent from README's reference. README now enumerates `MYTHIC_HOME`, `MYTHIC_HOOKS`, `MYTHIC_DAILY_COST_CAP_USD`, `MYTHIC_PATH_RE`, `MYTHIC_TUI_NARROW`, `MYTHIC_MCP_READ_TIMEOUT`, `MYTHIC_MCP_MAX_DISCARD`, plus the per-backend chat-bridge config (12 vars across Matrix + Telegram), plus per-island enable gates (4 vars).

Cumulative across PH-24.1 through PH-24.6: tests **2658 → 2751** (+93), aggregate coverage **84% → 85%**, modules at ≥95% **5 → 9**, ruff + mypy clean throughout. Live HEAD on `development` advanced from `bf01cfb` (v1.0.0) through six successive cohesive commits. Plan + per-slice closeouts in `TASK_PH24_PRE_RELEASE_HARDENING.md`.

### Cross-project housekeeping

- **MindSpark ThoughtForge** (`C:/Users/volma/runa/MindSpark_ThoughtForge`) — committed previously-untracked `src/thoughtforge/utils/errors.py` (typed exception hierarchy with `context` / `recoverable` / `suggested_fix` fields) and `validators.py` (input validation + sanitisation). Both files were already imported by 6 modules; landing them in git closes the working-tree drift.
- **NorseSagaEngine** (`C:/Users/volma/runa/NorseSagaEngine`) — reverted runtime drift (timestamp + cache_key noise on auto-generated quest yaml + rag_meta.json), gitignored `data/character_memory/` runtime tree.
- **pygame Viking Edition** (`C:/Users/volma/runa/pygame`) — Phase 1E thread-safety audit (no bugs found across event.c + surface.c + display.c) + Phase 1F self-healing audit (2 real C defects fixed: `scrap_sdl2.c:53` discarded SDL_Init return; `base.c:352-356` silently swallowed top-level SDL_Init failure) + Phase 2A platform-guard audit (~150-guard taxonomy + new `src_c/include/pgplatform.h` additive header with `PG_PLATFORM_*` / `PG_ARCH_*` / `PG_HAVE_*` / `PG_BUILD_*` macros).

## [1.0.0] — 2026-05-03

The first stable release of Mythic Vibe CLI. Closes the v1.0 launch gate (PH-19 + PH-20). All 26 slices from the audit-remediation cycle (PH-19.0 → 19.8 + PH-20.0 → 20.7) are shipped:

- **PH-19 (Distribution + Hardening)** — pre-launch bug sweep (10 fixes inc. cross-process locking + atomic write helper); JSON snapshot tests; docs↔code contract auditor; CI matrix expansion (3 OS × 3 Python + arm64 Linux); hypothesis property tests for state migrations; threat model + CycloneDX SBOM; compatibility policy v1.0; tag-driven release pipeline (PyPI OIDC + Homebrew tap + Scoop bucket + offline wheelhouse); stale-catalog watchdog.
- **PH-20 (Polish + v1.0.0 Launch)** — opt-in init wizard; packet lint; doctor --fix (hard-rule guarded); plugin capability model + plugin doctor + circuit breaker; `ai recommend`; provider conformance suite; `provenance verify` + `provenance attest`; persona presets; verify --replay shortcut; workflow lineage viewer; per-role packet budget optimizer; drift dashboard rollup; conventional-commit changelog classification; quarterly architecture review command + cadence doc; opt-in TUI heatmap + plugin risk panels.

Aggregate test count grew from 1665 (pre-PH-19) to **2224** passing (+109 subtests across providers). Coverage steady ≥ 82%. Compatibility policy is now binding: SemVer rules apply from this release onward.

See `RELEASE_v1_0_0_2026-05-03.md` in the repo root for the full closeout memo.

### Added

- Added the command-runner screen to the Textual TUI, closing the picker → preview → runner trio. Pressing `r` (or Enter) on `CommandPreviewScreen` for a *builtin* slash command pushes a new `RunningCommandScreen` that spawns `sys.executable -m mythic_vibe_cli <name>` via `subprocess.Popen` (cross-platform stdlib only — no Unix-specific signal handlers, no platform branches), polls every 0.2s on a Textual `set_interval`, and renders live elapsed time. When the process exits, the screen drains stdout/stderr and shows the final exit code plus a 4 KB tail; Esc returns. Path-aware commands (`status`, `scan`, `verify`, `reflect`, `resume`, `method`, `handoff`, `workflow`, `plugin`, `grimoire`) automatically receive `--path <project_root>`. Plugin/extension/skill/prompt entries display "(plugin dispatch not yet implemented)" instead — that contract belongs to a future slice. The screen registers an `on_unmount` cleanup that terminates and reaps the child process, so callers using a temporary cwd (e.g., headless tests with `tempfile.TemporaryDirectory`) can clean up safely on Windows. New `mythic_vibe_cli/tui/runner.py` with `RunSpec`, `command_for_builtin(name, *, project_root=None)`, and `RunningCommandScreen`; lazy `__getattr__` re-export keeps the missing-textual fallback intact.
- Added the slash-commands picker screen to the Textual TUI. Pressing `/` from the main `StatusScreen` opens `SlashPickerScreen` with an `Input` filter and an `OptionList` populated from `BUILTIN_SLASH_COMMANDS` plus plugin-contributed entries (via `PluginHookDispatcher.discover_slash_commands()`). Substring filtering is case-insensitive and matches name or description. Selecting an option pushes a `CommandPreviewScreen` showing the entry's source, source-info path, and full description; Esc returns. This slice does not dispatch the selected command — that is the next slice. New `mythic_vibe_cli/tui/picker.py` with the two screens plus `PickerEntry`, `gather_picker_entries(root)`, and `filter_entries(entries, query)` helpers; lazy `__getattr__` re-export keeps the missing-textual fallback intact.
- Added `mythic_vibe_cli.runtime.event_log` — bounded JSONL append-and-tail at `mythic/events.jsonl`. Caps at 200 entries (rotates by rewriting with the tail). `PluginHookDispatcher.emit()` now writes one line per emit (best-effort; IO errors swallowed). The Textual TUI gains a "Recent Events" panel below the 2×2 status grid that auto-refreshes every 2 seconds and shows the most recent 12 entries newest-first. Cross-platform via stdlib `pathlib`/`json`/`tempfile`. The pre-existing `tests/test_context_scan.py::test_scan_changed_only_limits_recommended_context` was relaxed to acknowledge that scan now writes both `mythic/project_index.json` and `mythic/events.jsonl` as side-effects (the test now asserts the source file appears among changed files rather than being the only entry).
- Added `mythic-vibe tui` — a Textual-based status TUI showing project phase, last verification, latest handoff, and plugin counts in a four-panel grid with auto-refresh every 2 seconds. Keybindings: `q` quit, `r` manual refresh. Requires the new optional `[tui]` extra (`textual>=0.80`); when Textual is not installed the command surfaces a helpful install message and returns `OPERATIONAL_FAILURE` rather than raising. Cross-platform via Textual (pure Python, MIT) — no per-OS branches. Added `tui` to the `dev` group so test runs can exercise the TUI via Textual's built-in `App.run_test()` headless driver.
- Added `mythic-vibe shell` — a minimal interactive REPL. Reads command lines from stdin via `input()`, dispatches each to `app.main(argv)` so the full argparse + handler stack runs per command. Handles `/help` (prints the slash catalog inline including plugin-contributed entries), `/quit` / `/exit`, EOF (Ctrl+D), and Ctrl+C (returns to prompt). Bare commands without a leading `/` work too. Bad shlex-quotes emit a parse error and the loop continues; non-zero exit codes are surfaced and the loop continues. The REPL has no readline/history yet (deferred follow-on); no Textual dependency. First slice of the V2 Phase 3 (TUI) arc — establishes the REPL contract a future TUI will wrap or replace.
- Added `mythic-vibe slash list` for inspecting the slash-command catalog. Prints `BUILTIN_SLASH_COMMANDS` and any entries contributed by enabled plugins via an optional `slash_commands()` callable on the plugin class. Supports `--source builtin|extension|prompt|skill|plugin` to restrict output to a single source; `--source builtin` skips plugin loading entirely. JSON output exposes `{command, path, source_filter, builtin: [...], contributed: [...]}` with each entry as the dataclass `to_dict()` form.
- Added `PluginHookDispatcher.discover_slash_commands()` — a one-shot discovery method (separate from `PLUGIN_HOOKS`) that aggregates `SlashCommandInfo` instances from any loaded plugin exposing a callable `slash_commands` attribute. Plugin exceptions follow the bus log-and-continue contract; non-`SlashCommandInfo` items are silently skipped.
- Wired `exec_command` through every existing subprocess call site in production code: `verify/test_runner.py`, `verify/git_diff.py`, `handoff.py`, and `context/scanner.py`. Direct `subprocess.run` usage is now confined to `runtime/exec.py` itself. Behavior preserved (all 219 tests green); side benefit is graceful missing-binary handling — e.g., a missing `pytest` now becomes a verification failure (`code=127`) instead of an unhandled `FileNotFoundError`.
- Added `mythic_vibe_cli.runtime.exec` — subprocess execution primitive ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. `exec_command(command, args, cwd, *, timeout, cancel_event)` returns an `ExecResult` (`stdout`, `stderr`, `code`, `killed`, plus `to_dict`). `shell=False` is hard-coded; missing commands return `code=127` rather than raising. `timeout` uses `threading.Timer`; `cancel_event` (the Python equivalent of pi's `AbortSignal`) uses a watcher thread; both kill via `SIGTERM` then `SIGKILL` after a 5-second grace period. Pi's `waitForChildProcess` Node-stdio quirk handler is not needed — Python's `Popen.communicate()` handles the underlying issue natively.
- Updated `docs/runtime.md` to add §8 covering `exec`, renumbered the trailing sections, updated the at-a-glance table to show seven primitives, and updated the index in `docs/INDEX.md` accordingly.
- Added `docs/runtime.md` — operator-facing guide for the seven runtime primitives in `mythic_vibe_cli/runtime/`. Sections cover what each primitive does, public surface, usage examples, when to reach for it, common composition patterns, and cross-links. Mirrors the shape of `docs/plugins.md`. Cross-linked from `docs/INDEX.md` (Operator Docs) and `docs/plugins.md` (See also).
- Added `mythic_vibe_cli.runtime.source_info` — provenance type for contributed artifacts ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. Exports `SourceInfo` frozen dataclass (path, source, scope, origin, optional base_dir), `SourceScope` Literal (`"user" | "project" | "temporary"`), `SourceOrigin` Literal (`"package" | "top-level"`), and `synthetic_source_info(path, source, scope=..., origin=..., base_dir=None)` factory mirroring pi's `createSyntheticSourceInfo`. Pi's `PathMetadata`-dependent factory is intentionally not ported (out of scope; pi's package-manager subsystem is not being plundered).
- Upgraded `SlashCommandInfo.source_info` from `str` to `SourceInfo`, closing the deferred detail noted in the slash-commands catalog slice. Extension/skill/prompt/plugin-contributed commands now carry structured provenance with scope, origin, and an optional `base_dir`.
- Added `mythic_vibe_cli.runtime.slash_commands` — typed catalog of slash commands ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. Exports `BUILTIN_SLASH_COMMANDS` (Mythic-relevant defaults: `help`, `status`, `scan`, `packet`, `verify`, `reflect`, `resume`, `method`, `handoff`, `workflow`, `plugin`, `grimoire`, `reload`, `quit`), `BuiltinSlashCommand` and `SlashCommandInfo` frozen dataclasses, and the `SlashCommandSource` Literal (`"extension" | "prompt" | "skill" | "plugin"` — adds `"plugin"` to pi's three because Mythic has a first-class plugin layer). Catalog only — runtime dispatch belongs to whichever future surface (REPL/TUI/SDK) consumes the catalog.
- Wired the timings primitive into `app.main()` so `MYTHIC_TIMING=1 mythic-vibe ...` produces a startup-and-command profile to stderr (`argparse`, `configure_output`, `handler:<command>`, `TOTAL`). `print_timings()` runs in a `finally` block so even argparse-driven `SystemExit` (e.g., `--help`) prints the partial profile. With the env var unset, every call is a no-op and the function behaves identically to before.
- Added `mythic_vibe_cli.runtime.timings` — lightweight elapsed-time instrumentation primitive ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. Three functions: `reset_timings()`, `record(label)`, `print_timings()`. Gated by the `MYTHIC_TIMING` env var (accepts `1` / `true` / `yes` / `on`); when unset, all three functions are inexpensive no-ops so call sites can sprinkle `record(...)` without conditional gating. Output formatted in pi-style with a TOTAL footer to stderr. Re-exported from `mythic_vibe_cli.runtime`.
- Added `docs/plugins.md` — operator-facing guide for writing and registering Mythic plugins. Covers the eight hook signatures, payload shapes, complete worked example (`AuditPlugin` recording every life-cycle event to an append-only log), registration via `grimoire add` / inspection via `plugin inspect` / pause via `plugin disable`, the synchronous-only / exception-isolated / read-only-payload contract, and the per-invocation lifecycle. Cross-linked from `docs/INDEX.md` (Operator Docs) and `docs/api.md` (plugin command surface).
- Wired `before_reflect` / `after_reflect` emission into `cmd_reflect` real-work path; dry-run skips emission. `before_reflect` carries the user-supplied `summary` / `next_step` / `note`; `after_reflect` adds `handoff_id`, `json_path`, `markdown_path`, and `next_recommended_action`. **With this slice, all eight declared hooks in `PLUGIN_HOOKS` (scan/packet/verify/reflect, before+after each) now have real emitters; the plugin dispatch layer is fully load-bearing.**
- Wired `before_verify` / `after_verify` emission into `cmd_verify`. `before_verify` fires at the top with `{path, selected: {commands, changed_files, docs, invariants}}`. `after_verify` fires after the verification artifact is written with `{path, result, level, verification_id, artifact_path, errors_count, warnings_count, blocked_count}` — scalar summary only; full warning/error/command lists stay in the artifact.
- Wired `before_packet` / `after_packet` emission across three packet-write call sites: `packet create` (and the `codex-pack` / `evoke` aliases via the shared `cmd_packet_create`), `packet ingest`, and the `workflow plan --packets` step loop. Each emission is bracketed by `PluginHookDispatcher.emit("before_packet", ...)` / `emit("after_packet", ...)` with a small stable-key payload (`source`, `path`, `phase`, `role`, `task`, `audience`, `format`; `after_packet` adds `packet_id` + `packet_path`). The workflow path additionally surfaces `workflow_id` and `workflow_step_id`. Dry-run paths and `workflow plan` without `--packets` skip emission entirely.
- Added `mythic_vibe_cli.plugins.PluginHookDispatcher` — per-invocation dispatcher that loads enabled plugins from the project's `PluginRegistry`, resolves each plugin's `before_*` / `after_*` hook methods, and subscribes them to a fresh `EventBusController`. Plugins that fail to import are skipped silently; plugin handler exceptions are contained by the bus contract. Re-exported from `mythic_vibe_cli.plugins`.
- Wired `cmd_scan` to emit `before_scan` and `after_scan` through `PluginHookDispatcher` on the real-work path. Dry-run scans skip both hooks. The remaining declared hooks (`before_verify`, `after_verify`, `before_reflect`, `after_reflect`) stay wired through the dispatcher contract and will be emitted from their matching commands in subsequent slices.
- Added `mythic_vibe_cli.runtime.event_bus` — synchronous publish/subscribe coordination layer ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. `create_event_bus()` returns an `EventBusController` exposing `emit(channel, data)` / `on(channel, handler) -> unsubscribe` / `clear()`. Handler exceptions are logged to stderr (channel + traceback) and never crash the bus, matching pi's "log and continue" contract. Snapshots handlers before iterating so a handler can unsubscribe itself during dispatch. Re-exported from `mythic_vibe_cli.runtime`. The bus is unwired plumbing in this slice; future slices will connect it to the existing `before_*` / `after_*` plugin hook declarations.
- Wired `take_over_stdout()` into `app.main()` so every `--json` command runs under the stdout guard. Accidental `print()` and any third-party stdout writes route to stderr; only deliberate `write_json()` payloads reach real stdout (via `write_raw_stdout()`).
- Wired `file_mutation_queue` into `PacketBuilder` writer sites so `packet create`, `packet ingest`, and the underlying `_write_record` / `_write_ingested_record` / `_write_context_manifest` paths serialize per resolved path. Wrapped `create_packet` and `ingest_packet` with a packet-directory-level queue so concurrent calls cannot collide on `_next_packet_id` allocation. Verified by a new packet-writer concurrency test that issues 8 simultaneous `create_packet` calls and asserts 8 distinct PKT-IDs land on disk.
- Added `json_output_guard` context manager to `mythic_vibe_cli.runtime.output_guard` — `with json_output_guard(active=True):` installs the guard for the block and restores on exit (including on exceptions). `active=False` makes the block a transparent no-op.
- Added `mythic_vibe_cli.runtime.output_guard` — stdout cleanliness primitive ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. `take_over_stdout()` installs a proxy stream that routes all `sys.stdout` writes to `sys.stderr`; `write_raw_stdout()` and `flush_raw_stdout()` keep the protocol-output path usable while the guard is active; `restore_stdout()` undoes the takeover; `is_stdout_taken_over()` reports state. Idempotent takeover and no-op restore are both covered. Re-exported from `mythic_vibe_cli.runtime`.
- Added `mythic_vibe_cli.runtime.file_mutation_queue` — per-resolved-path serialization primitive ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. Symlink aliases share the same queue via `os.path.realpath`; entries are reference-counted so the lock map cleans up after the last waiter. Public surface: `file_mutation_queue` context manager and `with_file_mutation_queue` functional form. Companion test ported from pi's Vitest suite under `tests/test_file_mutation_queue.py`.
- Added `THIRD_PARTY_NOTICES.md` recording the Pi attribution stanza, the plunder map, and the full upstream MIT permission text. First entry in the file; future plundered material lands here.
- Added `mythic_vibe_cli.method_excerpt` (Stage 15 final box) — `select_method_excerpts(corpus_dir, sections, char_limit)`, `sections_for(role, phase)`, and `ROLE_METHOD_SECTIONS` / `PHASE_METHOD_SECTIONS` maps. Scans the imported method corpus for headings matching role-relevant section keywords and returns capped excerpts.
- Added method excerpt embedding to `packet create`. Markdown packets gain a `## 12. Method Excerpts` section between Check-in Summary and SAFETY; JSON packets gain a `method_excerpts` array. Sections are chosen by packet role with phase fall-back. When the corpus is missing or no headings match, the method section is omitted (graceful degradation, no error).
- Added `packet show --previous-workflow --step <step_id>` for resolving the workflow id from the second-most-recent entry in `mythic/workflow_history.json`. Same exclusivity rules as `--latest-workflow`; cannot be combined with it; errors when the ledger has fewer than two entries.
- Added `LATEST:<step_id>` and `PREVIOUS:<step_id>` self-describing sentinels to `packet diff --left` and `--right`. Mixing them in one call (e.g., `--left LATEST:step-01 --right PREVIOUS:step-01`) is the canonical cross-run regression diff pattern. The sentinels work without flag toggles and compose with the existing `WF-<id>:<step_id>` shorthand and `--latest-workflow` bare-step form.
- Added `_resolve_previous_workflow_id` helper for callers that need the second-most-recent workflow id from the ledger.
- Added `mythic/workflow_history.json` as an append-only ledger of workflow plan saves (workflow_id, task, created_at, plan_path, role_sequence). `workflow plan` (without `--dry-run`) appends an entry on every successful save; the ledger is capped at 50 entries.
- Added `mythic-vibe workflow history` for inspecting the ledger. Supports `--limit N` to cap the returned entries and `--json` for structured output that exposes `count`, `total`, and the resolved `history_path`.
- Added `WorkflowEngine.append_history`, `WorkflowEngine.load_history`, and `WorkflowEngine.history_path` plus `WORKFLOW_HISTORY_FILENAME` and `WORKFLOW_HISTORY_LIMIT` constants for callers that need to read or write history programmatically.
- Added `packet list --latest-workflow` so packet listings can scope to the saved `mythic/workflow_plan.json` without restating the workflow id. Cannot be combined with `--workflow`. Errors when the saved plan is missing or has no `workflow_id`. JSON output exposes the resolved `latest_workflow_id` for symmetry with `packet show` and `packet diff`.
- Added `packet show --latest-workflow --step <step_id>` and `packet diff --latest-workflow` so packet refs can resolve against the saved `mythic/workflow_plan.json` without restating the workflow id. With `packet diff --latest-workflow`, `--left` and `--right` additionally accept a bare `step-NN` form. Errors when the saved plan is missing or has no `workflow_id`. JSON output reports the resolved `latest_workflow_id` for `packet diff`.
- Added `packet show --workflow <id> --step <step_id>` for resolving a packet by its workflow stamp instead of by `PKT-` ID. Both flags are required together and cannot be combined with `--packet-id`; missing matches return `USER_INPUT_ERROR`.
- Added `WF-<id>:<step_id>` shorthand to `packet diff --left` and `--right`, resolving the shorthand to a stored packet at run time. JSON output reports both the original references (`left_ref`, `right_ref`) and the resolved packet IDs.
- Added `PacketBuilder.find_packet_by_workflow_step` helper that returns the latest packet stamped with a given `workflow_id` and `workflow_step_id`.
- Added `packet list --workflow <id>` and `packet list --workflow <id> --step <step_id>` filters for showing only the packets belonging to one workflow run; `--step` requires `--workflow` and returns `USER_INPUT_ERROR` otherwise. Legacy packets without IDs are excluded when a workflow filter is set, and JSON output exposes a `filters` object reporting the applied scope.
- Added deterministic `workflow_id` (form `WF-<UTC compact>-<sha8(task+created_at)>`) to every freshly built workflow plan, persisted in `mythic/workflow_plan.json` and surfaced in `workflow plan`, `workflow packets`, and `workflow run` JSON output.
- Added `workflow_id` and `workflow_step_id` stamping on packets generated via `workflow plan --packets`, written to each packet's `.meta.json`.
- Added ID-first packet matching to `workflow packets` and `workflow run --dry-run --packets-only`, with the existing `(role, phase, task, audience, output_format)` text match preserved as a legacy fallback. Each `packet_status` entry now reports `match_strategy` (`"id"`, `"text"`, or `null`).
- Added `mythic-vibe workflow packets` for read-only packet readiness listings, including `--missing-only` filtering.
- Added `workflow run --dry-run --packets-only` to validate that every workflow step has a matching packet artifact before provider execution is introduced.
- Added `mythic-vibe workflow run --dry-run` for safe ordered role-execution previews from saved or generated workflow plans.
- Added `workflow plan --packets`, `--audience`, and `--format` so workflow plans can generate one packet artifact per role step without provider execution.
- Added `mythic-vibe workflow plan` for writing and previewing role orchestration plans from the CLI.
- Added `mythic_vibe_cli.workflow_engine` for deterministic six-role orchestration plans, handoff order, packet request export, and durable `mythic/workflow_plan.json` writing.
- Added `mythic_vibe_cli.ai.prompts.roles` as the first real packet-role catalog, including first-class `Skald` support.
- Added Stage 15 method profile visibility with `mythic-vibe method status`, `method show`, and `method sync`.
- Added `method_manifest.json` generation for `import-md`, including source ref, file count, relative paths, byte sizes, and SHA-256 hashes.
- Added `mythic-vibe method diff` to compare an imported method corpus against its manifest.
- Added `mythic-vibe method pin` to write a reproducibility pin for clean imported method corpora.
- Added configurable `method.source` support, including `MYTHIC_METHOD_SOURCE`, project config loading, and `config` reporting.
- Added method version detection, fallback profile reporting, method section labels, and freshness warnings for uncached method corpora.
- Added argparse help examples for high-traffic commands: `init`, `next`, `verify`, `packet create`, `reflect`, `resume`, and `doctor`.
- Added Stage 14 UX commands: `examples`, `guide`, `next`, `explain phase`, `explain artifact`, `tutorial`, and `completion`.
- Added optional rich output support behind `MYTHIC_RICH=1` and the `ux` optional dependency group.
- Added shell completion generation for bash, zsh, and Windows PowerShell.
- Added Stage 13 packaging and release-quality configuration, including optional dependency groups for `dev`, `ai`, `docs`, `test`, `lint`, `type`, and `build`.
- Added GitHub Actions CI for tests, coverage, ruff, mypy, changelog checks, package builds, and distribution checks.
- Added `docs/INSTALL.md`, `docs/RELEASE_CHECKLIST.md`, and `scripts/check_changelog.py`.
- Added `mythic-vibe plugin list|inspect|disable` for visible plugin health and control.
- Added `mythic_vibe_cli.plugins` helpers for plugin API contracts, versioned registry records, and entrypoint inspection.
- Added hook declarations for `before_scan`, `after_scan`, `before_packet`, `after_packet`, `before_verify`, `after_verify`, `before_reflect`, and `after_reflect`.
- Added `plugin_manifest.schema.json` for the plugin registry contract.
- Added `mythic-vibe plunder inspect|plan|fetch|apply|record` for staged, lawful single-file reuse.
- Added `mythic_vibe_cli.plunder` helpers for GitHub fetches, license posture, provenance manifests, and NOTICE updates.
- Added `mythic/imports/plunder_plan.json`, `mythic/imports/plunder_manifest.json`, and local plunder cache support.
- Added Apache/MIT/BSD compatibility notes and "Do not plunder" warnings for unknown or incompatible licenses.
- Added `mythic-vibe reflect`, `mythic-vibe handoff create|show|latest`, and `mythic-vibe resume` for durable session continuity.
- Added timestamped handoff artifacts under `mythic/handoffs/` plus `docs/SESSION_HANDOFF.md` generation.
- Added latest-handoff linkage in `status` output so the current session handoff is easy to recover.
- Added canonical `docs/INDEX.md` and `docs/COMMAND_CONTRACTS.md` scaffolding during project initialization.
- Added `docs/ADRS/ADR-0003-verification-gates.md` and `docs/ADRS/ADR-0004-doctor-diagnostics.md`.
- Added structured `doctor` reporting with required-artifact, state-coherence, docs-drift, and boundary sections.
- Added `mythic-vibe verify` with command execution, changed-file review, docs checks, invariant checks, and durable verification records.
- Added `mythic/verifications/` artifacts with a `latest.json` pointer.
- Added a reflect gate so `mythic-vibe checkin --phase reflect` refuses to proceed until a successful verification exists.
- Added `mythic_vibe_cli.verify` helpers for test running, git diff review, doc checks, and invariant checks.
- Added provider usage and metadata fields to response objects and JSON command output.
- Added provider-side pricing heuristics so estimated costs are no longer zero for real adapters.
- Added real provider execution for `openai`, `anthropic`, `gemini`, and `openrouter` behind explicit API keys.
- Added provider request and response logging under `mythic/ai/provider_calls.jsonl` with secret redaction.
- Added packet resolution for `mythic-vibe ai test` and `mythic-vibe ai run`, including stored packet IDs and on-disk packet files.
- Added `mythic-vibe ai providers`, `mythic-vibe ai test`, `mythic-vibe ai run`, and `mythic-vibe ai ingest-response`.
- Added an isolated provider registry with `copy-paste`, `local`, `openai`, `anthropic`, `gemini`, and `openrouter` adapters.
- Added explicit API-key validation and dry-run-first provider behavior.
- Added weighted packet budget allocation so high-priority sections retain more context under truncation.
- Added budget-allocation coverage to verify packet compaction keeps priority sections larger than low-signal ones.
- Added role presets, output formats, safety sections, and context manifest support to packet generation.
- Added JSON packet rendering as a first-class packet output format.
- Added packet context manifest writing to `mythic/context_sources.json`.
- Added `mythic-vibe packet ingest` to import packet artifacts into the local packet store.
- Added `mythic-vibe packet diff` to compare stored packet artifacts.
- Packet ingestion now preserves source path and provenance metadata.
- Added `mythic-vibe packet create`, `mythic-vibe packet show`, and `mythic-vibe packet list`.
- Added packet IDs and metadata files under `mythic/packets/`.
- Renamed the internal packet concept to `PacketBuilder` while keeping `CodexBridge` compatibility.
- Added project-index context into Codex prompt packet generation.
- Added automatic `mythic/project_index.json` writing during packet creation.
- Added `mythic-vibe scan` with project indexing, changed-file mode, docs mode, and JSON output.
- Added `mythic_vibe_cli.context` scanner and indexer modules for local project context mapping.
- Added `.mythicignore` to define local context-scan exclusions.
- Added `python -m mythic_vibe_cli` package execution via `mythic_vibe_cli/__main__.py`.
- Added `mythic_vibe_cli.commands` for command implementations and registry ownership.
- Added `mythic_vibe_cli.output` and `mythic_vibe_cli.errors` as shared command rendering/error helpers.
- Added `mythic_vibe_cli.exit_codes` to name the CLI return-code policy.
- Added shared command controls for JSON output, quiet/verbose output, and dry-run previews where commands can support them safely.
- Added `docs/COMMAND_CONTRACTS.md` for entrypoints, dispatch aliases, and exit-code contracts.
- Added CLI kernel tests for module execution, registry aliases, and exit-code policy.
- Added Stage 0 repository boundary records: `REPO_BOUNDARY.md`, `docs/ACTIVE_PRODUCT_BOUNDARY.md`, `docs/DORMANT_ISLANDS.md`, and two ADRs under `docs/ADRS/`.
- Added `mythic-vibe doctor --repo-boundary` to validate active runtime boundary records and forbidden dormant-island imports.
- Added active product repo-boundary tests.
- Added `docs/INDEX.md` as a canonical documentation navigation map and upkeep protocol.
- Added first formal `CHANGELOG.md` to establish release-facing history discipline.
- Added `docs/DOCUMENTATION_STANDARDS.md` as the durability, drift-control, and update-obligation charter for active docs.
- Added `docs/SESSION_HANDOFF_TEMPLATE.md` for consistent end-of-session continuity capture.

### Changed

- Packet role presets now live outside `codex_bridge.py`, keeping packet building separate from role identity and prompt definitions.
- `next` human output now shows failed verification commands, verification errors, and blocked reasons as separate sections when the latest verification is not passing.
- `next` now prioritizes failed or blocked verification records before normal phase guidance, and uses the latest handoff next step when verification is already passing.
- Expanded operator docs with Stage 14 guidance, shell completion setup, and optional rich-output notes.
- Expanded `pyproject.toml` metadata, Python classifiers, package URLs, ruff config, mypy config, and coverage config.
- `grimoire add|list` now writes a versioned plugin registry while preserving the legacy `plugins` list for compatibility.
- Legacy `plunder --repo --source --dest` now refuses silent overwrites unless `--force` is supplied.
- `status` now includes the latest handoff path, ID, and next recommended action when a handoff exists.
- `doctor --repo-boundary` now stays focused on runtime boundary checks, while the normal doctor path handles docs drift and ADR checks.
- Project scaffolding now creates the canonical docs index and command contract files by default.
- Successful verification now updates `last_verification_id` in project state.
- Verification artifacts are now durable, and blocked reflection emits a clear reason instead of pretending the gate passed.
- Real provider responses now include request IDs, usage, estimated cost, and observed cost metadata when available.
- `mythic-vibe ai test` now stays dry-run-only, and `mythic-vibe ai run` now honors `--dry-run` explicitly.
- `copy-paste` and `local` provider modes keep their always-available bridge behavior for inline packet input.
- Moved the real CLI kernel into `mythic_vibe_cli/app.py` while preserving `mythic_vibe_cli.cli:main` as the public compatibility entrypoint.
- Extracted command behavior out of `mythic_vibe_cli/app.py` so `app.py` now owns parsing/dispatch while `commands.py` owns command execution.
- Replaced the long command dispatch chain with a `COMMAND_HANDLERS` registry while preserving existing commands and ritual aliases.
- Updated architecture, domain, and API docs for the Stage 1 CLI kernel contract.
- Updated command contract docs to define shared runtime options and machine-readable output behavior.
- Configured pytest to collect only active product tests from `tests/`, preventing dormant islands and vendor mirrors from polluting the active verification gate.
- Fixed config home-directory resolution so `HOME` overrides are honored consistently in tests and nonstandard environments.
- Expanded root `README.md` with explicit documentation governance and continuity obligations.
- Reworked `docs/index.md` into a compatibility redirect to remove duplicated navigation authority.
- Expanded `docs/quickstart.md` with first-loop workflow, bridge usage, and troubleshooting.
- Expanded `docs/ARCHITECTURE.md` with detailed component contracts, risk model, and review checklist.
- Expanded `docs/DOMAIN_MAP.md` with stricter ownership/dependency boundaries and exception protocol.
- Expanded `docs/api.md` with module contracts, compatibility policy, and integration examples.
- Expanded `docs/SYSTEM_VISION.md` with mission detail, UX outcomes, and evolution horizons.
- Expanded `docs/INDEX.md` into a canonical map with update matrices, maintenance cadence, and quality gates.
- Updated `DEVLOG.md` with an additional continuity entry for this scribe-level documentation expansion.

## [2026-04-23]

### Added

- Documentation continuity framework upgrades for active product records.

### Changed

- Multiple core docs were rewritten and expanded for clarity, durability, and contributor onboarding.
