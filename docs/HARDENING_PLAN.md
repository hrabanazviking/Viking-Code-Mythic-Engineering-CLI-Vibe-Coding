# Massive Codebase Hardening Plan

Last updated: 2026-06-02

This plan is based on a local audit of the active Mythic Vibe CLI runtime, scripts,
tools, packaging helpers, documentation contracts, and test suite. It is a phased
repair plan, not a changelog. The goal is to make the program measurably harder
to break while preserving user work and avoiding broad rewrites that hide bugs.

## Audit Snapshot

Scope checked:

- Active runtime and support surface: `mythic_vibe_cli/`, `scripts/`, `tools/`,
  and `packaging/`.
- Scoped active file inventory: 189 files.
- WASI stdlib audit scan: 169 runtime files, 44 stdlib modules used, 16
  third-party imports, 2 dynamic import sites, 103 possible prune candidates.

Commands run:

- `python scripts/quality_gate.py`
  - Result: pass.
- `python tools/contract_audit.py --strict`
  - Result: pass.
- `python -m pytest -q`
  - Result: 2883 passed, 26 failed, 4 skipped, 11 warnings, 109 subtests passed.
- `python -m pytest -q tests/test_script_hardening.py tests/test_cli_startup.py`
  - Result: 7 passed.
- `python -m mythic_vibe_cli simulate --json`
  - Result: simulation passed 4 of 4 scenarios, but stdout emitted two JSON
    objects and is not valid single-object JSON.
- `python -m mythic_vibe_cli doctor --path . --json`
  - Result: valid JSON, exit code 1, `ok=false`, 5 errors, 1 warning, 146 drift
    findings.
- `python -m mythic_vibe_cli security audit --path . --json`
  - Result: valid JSON, exit code 1, 109 dangerous findings and 762 secret
    findings before scope filtering.
- Runtime robustness audits:
  - Boundary audit: 6 direct process-boundary findings.
  - Path audit: 82 path findings.
  - API audit: 4 internal API boundary findings.

## Current Known Bug Backlog

| Priority | Area | Evidence | Required outcome |
| --- | --- | --- | --- |
| P0 | Full test suite | `python -m pytest -q` has 26 failures. | Full test suite is green in the project venv. |
| P0 | JSON CLI output | `mythic-vibe simulate --json` emits an error JSON object before the command envelope. | Every `--json` command emits exactly one machine-readable JSON document on stdout. |
| P0 | TUI contract drift | Status/accessibility tests expect `StatusScreen` ids such as `#status-bar`, `#events-panel`, `#packet-panel`, `#artifact-panel`, and `#loop-nav-panel`, while runtime starts `CockpitScreen`. | Tests and runtime agree on one primary screen contract, ids, keybindings, and overlays. |
| P0 | Slash command registry drift | `patch` exists in `COMMAND_HANDLERS` but is missing from expected slash/catalog sets; slash builtins are not unique. | Argparse, slash commands, TUI picker, and docs all share one deduplicated command source. |
| P0 | Patch manager identity contract | `tests/test_patch_manager.py::test_propose_patch` shows `get_active()` returns an equal proposal object but not the same object identity. | Either preserve identity or intentionally update the test and contract to value semantics. |
| P1 | Doctor required artifacts | Doctor reports missing root/runtime files: `MYTHIC_ENGINEERING.md`, `SYSTEM_VISION.md`, `tasks/current_GOALS.md`, `mythic/plan.md`, and `mythic/loop.md`. | Doctor expectations match the current product layout, or the missing required artifacts are intentionally restored. |
| P1 | Direct subprocess usage | Boundary audit finds direct subprocess calls in `cicd/release.py`, `cicd/rollback.py`, `protocols/mcp_client.py`, `repl.py`, `tui/cockpit.py`, and `tui/runner.py`. | Runtime subprocesses go through a guarded process API with timeout, stderr capture, structured errors, and cancellation. |
| P1 | Path ownership drift | Path audit reports 82 findings, many in help text and side-effect descriptions. | Real path construction uses canonical path helpers; intentional literal docs/help paths are baselined. |
| P1 | Security scanner noise | Security audit flags `.venv`, tests, docs, vendored/archive content, and scanner pattern definitions. | Default audit scope separates active runtime risk from documentation, tests, vendored code, and baselined examples. |
| P1 | Potential SQL pattern finding | `mythic_vibe_cli/knowledge/reader.py` uses a quoted identifier in a `PRAGMA table_info(...)` f-string. | Verify safety, add focused tests, then refactor or suppress with justification. |
| P1 | Internal API boundary drift | API audit flags imports from `runtime.atomic_write` and `core.state`. | Add public API exports or update the architecture/audit rules where the import is intentional. |
| P2 | Deprecation warning | `mythic_vibe_cli/ai/providers/model_catalog.py` uses deprecated `datetime.utcnow()`. | Replace with timezone-aware UTC calls and add a regression test. |
| P2 | Build and script hardening coverage | New script guard covers active scripts, but CI does not yet prove installer and script behavior on all target OSes. | CI exercises Linux, Windows, and macOS installers plus key script failure paths. |

## Hardening Principles

- Protect user worktree changes. Never use whole-tree resets as a repair tool.
- Active runtime first. Archived, vendored, generated, and research content must
  not block runtime release unless it ships in the executable path.
- JSON mode is a contract. Stdout is data; diagnostics belong in stderr or in
  the single JSON envelope.
- Process execution is a boundary. All runtime subprocess calls need timeouts,
  structured errors, cancellation behavior, and captured output.
- Broad exception handling is allowed only when it logs or reports the failure
  path and returns a defined degraded behavior.
- Configuration must be validated before use. Invalid config should produce a
  precise diagnostic and a fallback only when fallback is safe.
- Tests must prove contracts at user entry points, not only helper functions.
- Audit tools need scoped baselines so real bugs are visible.

## Phase 0 - Baseline and Guardrails

Objective: create a stable baseline so every later phase can prove progress.

Tasks:

- Add a small audit runner or documented command bundle for the standard gates:
  pytest, quality gate, contract audit, doctor, security audit, simulate JSON,
  and robustness audits.
- Add a test fixture that fails if CLI JSON commands emit more than one top-level
  JSON object on stdout.
- Add a test fixture that checks command runs do not modify tracked runtime
  artifacts such as `.mythic/memory.sqlite` and provider call logs unless a test
  explicitly opts in.
- Define security scanner default scopes: active runtime, scripts/tools, tests,
  docs/research, vendored/archive, and virtualenv. Only active runtime should
  determine release-blocking severity by default.
- Record a machine-readable baseline for known false positives with file, line,
  rule id, reason, and expiry date.

Exit criteria:

- One documented command sequence reproduces the current health state.
- False-positive baselines exist and are reviewed instead of ignored.
- Generated local state is not silently changed by normal tests.

## Phase 1 - Make the Test Suite Green

Objective: remove current regressions before deeper refactors.

Tasks:

- Resolve the `CockpitScreen` versus `StatusScreen` contract mismatch.
  Decide whether `CockpitScreen` is the canonical status surface or whether
  `StatusScreen` must return as a compatibility layer.
- Restore expected TUI ids, landmarks, panels, accessibility nodes, and overlay
  navigation contracts.
- Fix theme cycling and keybinding tests, especially the `t` theme key.
- Fix slash command catalog drift:
  - Include `patch` consistently.
  - Remove duplicate slash builtin ids.
  - Align CLI slash listing descriptions with TUI picker descriptions.
  - Ensure argparse handlers are covered by the slash/catalog contract.
- Fix `SlashPickerScreen` duplicate option ids such as duplicate `slash:test`.
- Fix the `PatchManager.get_active()` identity/value contract.
- Replace deprecated `datetime.utcnow()` with timezone-aware UTC usage.

Exit criteria:

- `python -m pytest -q` passes.
- No pytest run changes tracked runtime artifacts.
- The failure count is zero without marking current tests as skipped.

## Phase 2 - Machine-Readable Output Integrity

Objective: make command output reliable for scripts, tests, and agents.

Tasks:

- Fix `simulate --json` so nested diagnostics are captured inside the command
  envelope instead of printed as a separate JSON object.
- Audit all `--json` entry points for stray `print()`, logging-to-stdout, nested
  command calls, and unguarded traceback output.
- Add golden tests for JSON commands:
  - stdout parses as exactly one JSON document.
  - stderr may contain human diagnostics but never corrupts stdout.
  - command failure returns structured `ok=false` or `error` data.
- Add a CLI output helper that owns JSON serialization and refuses accidental
  second writes in JSON mode.

Exit criteria:

- `python -m mythic_vibe_cli simulate --json | python -m json.tool` succeeds.
- Every JSON command has a parser test.
- Crash reports and warnings never precede JSON envelopes on stdout.

## Phase 3 - Single Command and Slash Catalog

Objective: end drift between argparse commands, slash commands, TUI pickers, and
documentation.

Tasks:

- Define one command catalog object containing id, aliases, description,
  handler, JSON support, TUI visibility, slash visibility, and docs category.
- Generate or validate `docs/COMMAND_CONTRACTS.md` and `docs/SLASH_COMMANDS.md`
  from that catalog.
- Make `COMMAND_HANDLERS`, argparse registration, slash command registration,
  and TUI picker options consume the same catalog.
- Enforce unique ids and aliases at import time with a clear startup diagnostic.
- Add contract tests for catalog completeness and duplicate prevention.

Exit criteria:

- Adding a command in one place updates argparse, slash picker, and docs checks.
- No duplicate slash ids can be registered.
- Contract audit remains clean.

## Phase 4 - TUI Resilience and Accessibility

Objective: make the Textual interface stable under missing data, resized
terminals, failed background checks, and repeated screen transitions.

Tasks:

- Normalize the primary screen lifecycle and startup route.
- Add compatibility tests for expected widget ids and accessibility landmarks.
- Ensure all background tasks are cancellable and cannot crash the app after a
  screen is closed.
- Route git status, model status, memory status, and provider health checks
  through guarded services instead of direct calls from widgets.
- Add tests for small terminal sizes, missing config, corrupt status files, and
  repeated mount/unmount cycles.
- Ensure keybindings are declared once and validated against help overlays.

Exit criteria:

- TUI tests pass in headless CI.
- Missing optional tools or corrupt local state show degraded status, not
  uncaught exceptions.
- Keybinding help matches actual key behavior.

## Phase 5 - Process Boundary Hardening

Objective: remove unguarded subprocess usage from runtime paths.

Tasks:

- Introduce or extend a process runner API with:
  - command allowlist policy for runtime commands,
  - explicit timeout,
  - working directory control,
  - environment filtering,
  - output size caps,
  - structured result objects,
  - cancellation,
  - platform-aware executable lookup.
- Migrate runtime findings:
  - `mythic_vibe_cli/cicd/release.py`
  - `mythic_vibe_cli/cicd/rollback.py`
  - `mythic_vibe_cli/protocols/mcp_client.py`
  - `mythic_vibe_cli/repl.py`
  - `mythic_vibe_cli/tui/cockpit.py`
  - `mythic_vibe_cli/tui/runner.py`
- Decide whether build scripts in `packaging/` and maintenance scripts in
  `scripts/` must use the same API or can stay under `script_guard` with an
  explicit audit exception.
- Add timeout and missing-executable tests for every migrated runtime command.

Exit criteria:

- Boundary audit reports zero unapproved runtime subprocess findings.
- Runtime command failures return structured diagnostics.
- Long-running child processes are killed or cancelled predictably.

## Phase 6 - Path, State, and Data Ownership

Objective: make filesystem access predictable, portable, and recoverable.

Tasks:

- Separate actual path construction findings from literal documentation/help
  strings in the path audit.
- Build a canonical path service for repo root, config root, runtime state,
  cache, logs, crash reports, and user workspace paths.
- Replace ad hoc path literals in runtime code with the path service.
- Add path traversal tests for user-provided file names and config paths.
- Make runtime state writes atomic by default and preserve backups for important
  state files.
- Ensure every runtime write target is documented and can be redirected in tests.

Exit criteria:

- Path audit has zero unreviewed runtime findings.
- Tests can run with isolated temp roots and leave no tracked state changes.
- Corrupt state files are quarantined or repaired with clear diagnostics.

## Phase 7 - Public API Boundary Cleanup

Objective: make module boundaries match the architecture.

Tasks:

- Review API audit findings:
  - `init_wizard.py` importing `runtime.atomic_write`.
  - `persistence/json_store.py` importing `core.state`.
  - `persistence/migrations.py` importing `core.state`.
- Add public exports for stable utility APIs where cross-domain use is valid.
- Move persistence-owned state contracts into persistence APIs where direct
  `core.state` imports are not valid.
- Update API audit rules only after the architecture decision is documented.

Exit criteria:

- API audit reports zero unexplained findings.
- Persistence, runtime, core, and init wizard dependencies flow in one direction.

## Phase 8 - Security Audit Signal and Real Findings

Objective: turn the security audit from a noisy scanner into a release gate.

Tasks:

- Exclude `.venv`, generated artifacts, archived research, vendored code, and
  tests from release-blocking default scans.
- Keep separate scan modes for active runtime, tests, docs/research, vendored
  code, and full repository for forensic sweeps.
- Improve secret detection so variable names like `token` do not count as leaked
  secrets unless they contain literal secret-like values.
- Baseline examples inside `mythic_vibe_cli/security/dangerous_patterns.py`
  as rule definitions, not findings.
- Verify `mythic_vibe_cli/knowledge/reader.py` table identifier handling with
  injection-focused tests. Refactor or annotate the PRAGMA query after proof.
- Add SARIF or JSON report output suitable for CI artifacts.

Exit criteria:

- Active runtime security scan has no unreviewed critical or high findings.
- False positives require an explicit baseline entry with a reason.
- Known safe pattern definitions no longer bury real security findings.

## Phase 9 - Configuration and Provider Routing Hardening

Objective: make `config.yaml` rich, validated, portable, and safe.

Tasks:

- Add schema validation for routing profiles, provider lists, model ids, retry
  settings, token budgets, prompt templates, logging, and crash behavior.
- Validate router model lists by task type and provider, including fallback
  order, disabled providers, and unavailable API keys.
- Add tests for missing config, corrupt config, partial config, old config, and
  invalid provider/model combinations.
- Ensure max context, max output tokens, timeouts, retries, and budget policies
  are enforced at the routing boundary.
- Add a config migration path for future schema versions.
- Keep prompts editable in config while protecting required placeholder syntax.

Exit criteria:

- Invalid config produces exact diagnostics and a safe fallback when possible.
- Provider routing tests cover model order, provider failure, disabled services,
  and token/context limits.
- `config.yaml` remains human-editable and machine-validatable.

## Phase 10 - Persistence, Recovery, and Concurrency

Objective: prevent state corruption and recover cleanly when corruption happens.

Tasks:

- Add cross-process locking for state files that can be written by concurrent
  CLI/TUI sessions.
- Wrap important state writes in atomic write plus backup rotation.
- Add corruption recovery for JSON, YAML, SQLite, provider logs, status files,
  and memory files.
- Add startup checks that quarantine unreadable state files instead of crashing.
- Add tests for interrupted writes, partial files, invalid encodings, locked
  files, permission errors, and disk-full style failures where practical.
- Ensure crash reports never contain secrets or full provider payloads unless
  explicitly enabled.

Exit criteria:

- Simulated corrupt state never prevents `mythic` from starting.
- Recovery behavior is documented and covered by tests.
- Concurrent sessions do not corrupt shared state.

## Phase 11 - Installers, Scripts, and Build Drivers

Objective: make setup and maintenance scripts dependable across Linux, Windows,
and macOS.

Tasks:

- Add installer smoke tests for:
  - Linux shell installer,
  - Windows batch installer,
  - macOS shell installer,
  - existing venv repair,
  - missing Python,
  - broken console script,
  - PATH update behavior.
- Add script guard coverage for all active scripts and tools that are intended
  to be user runnable.
- Convert brittle script argument parsing to `argparse` where scripts have
  multiple modes or destructive effects.
- Make build drivers emit structured logs and clear artifact paths.
- Validate shell scripts with `shellcheck` where available and batch scripts
  with a Windows CI smoke path.

Exit criteria:

- Fresh install produces a working `mythic` command on Linux, Windows, and macOS.
- Re-running installers is idempotent.
- Script failures produce actionable messages and nonzero exit codes.

## Phase 12 - Dormant Islands and Borrowed Code

Objective: prevent imported or borrowed code from leaking stale contracts into
the active product.

Tasks:

- Inventory dormant islands, borrowed modules, research prototypes, and archived
  code paths.
- Mark each item as active, adapter-only, archived, vendored, generated, or
  removal-candidate.
- For active borrowed code, update names, command references, config paths,
  product text, and tests to Mythic Vibe CLI.
- For archived code, keep it out of runtime imports, release-blocking scans, and
  packaging unless intentionally included.
- Add import-boundary tests so dormant modules cannot be accidentally imported by
  startup, CLI command discovery, or TUI startup.

Exit criteria:

- No stale borrowed-code product names appear in active runtime commands,
  installers, or startup errors.
- Dormant code is isolated and cannot break normal startup.

## Phase 13 - CI and Release Gates

Objective: make hardening durable after the repair work lands.

Tasks:

- Define required gates for every pull request:
  - unit and integration tests,
  - quality gate,
  - strict contract audit,
  - JSON output audit,
  - active runtime security audit,
  - boundary/path/API audits,
  - installer smoke tests by platform.
- Save JSON/SARIF audit artifacts in CI.
- Add a release checklist that includes installer verification, config schema
  migration, crash-boundary checks, and security baseline review.
- Add nightly full-repository scans that report but do not block on docs,
  research, archived, or vendored findings unless a new active import appears.

Exit criteria:

- CI blocks regressions in the contracts fixed by this plan.
- Release artifacts are built only from a green audited state.
- Audit baselines are reviewed and cannot silently grow.

## Definition of Done

The hardening effort is complete when all of these are true:

- `python -m pytest -q` passes.
- `python scripts/quality_gate.py` passes.
- `python tools/contract_audit.py --strict` passes.
- `python -m mythic_vibe_cli simulate --json | python -m json.tool` succeeds.
- `python -m mythic_vibe_cli doctor --path . --json` reports no unexpected
  missing required artifacts or drift.
- `python -m mythic_vibe_cli security audit --path . --json` has no unreviewed
  active-runtime critical or high findings.
- Boundary, path, and API audits report zero unreviewed active-runtime findings.
- Linux, Windows, and macOS installers create or repair a working `mythic`
  command.
- Startup failures produce structured diagnostics and never corrupt state.
- Normal test runs do not modify tracked runtime artifacts.

## Recommended Execution Order

1. Phase 0: baseline and guardrails.
2. Phase 1: green test suite.
3. Phase 2: JSON output integrity.
4. Phase 3: command catalog unification.
5. Phase 4: TUI hardening.
6. Phase 5: subprocess boundary hardening.
7. Phase 6: path and state ownership.
8. Phase 7: public API boundary cleanup.
9. Phase 8: security audit signal.
10. Phase 9: configuration and provider routing hardening.
11. Phase 10: persistence and recovery.
12. Phase 11: installers, scripts, and build drivers.
13. Phase 12: dormant islands and borrowed code cleanup.
14. Phase 13: CI and release gates.
