# Architecture

**Status:** Active architecture record (v1.0.0)
**Last updated:** 2026-05-03
**Owner:** Architecture + Documentation maintainers
**Scope:** Active product runtime (`mythic_vibe_cli/`) and its governance boundaries in this monorepo.

> **v1.0 note.** Compatibility-policy v1.0 (`docs/compatibility_policy.md`) is now binding. The "Stable" tier in §3 of that doc is the authoritative answer to which surfaces here may change without a major version bump.

This document is the architecture contract for contributors. It defines where runtime behavior lives, how dependencies may flow, and how to avoid accidental coupling to dormant islands.

---

## 1) Repository posture

Treat this repository as a **multi-project monorepo**.

### Active runtime product

- `mythic_vibe_cli/`

### Active support surfaces

- `tests/`
- `docs/`
- root governance records (`README.md`, `ARCHITECTURE.md`, `DATA_FLOW.md`, `DEVLOG.md`, `CHANGELOG.md`)

### Dormant/reference islands

- runtime fragments (`ai/`, `core/`, `systems/`, `sessions/`, `yggdrasil/`)
- large protocol/research islands (`WYRD-...`, `mindspark_thoughtform/`)
- vendor mirrors (`whisper/`, `chatterbox/`, `ollama/`)

Default rule: islands are independent unless explicit adapter contracts are documented.

---

## 2) Active system flow

```text
User
    -> CLI Entrypoints (mythic_vibe_cli/__main__.py, mythic_vibe_cli/cli.py)
    -> Parser + Dispatch Kernel (mythic_vibe_cli/app.py)
    -> Command Handlers (mythic_vibe_cli/commands.py)
    -> Terminal/Error Helpers (mythic_vibe_cli/output.py, mythic_vibe_cli/errors.py)
    -> Core State Model (mythic_vibe_cli/core/state.py)
    -> Persistence Layer (mythic_vibe_cli/persistence/*.py)
    -> Workflow Lifecycle (workflow.py)
    -> Role Orchestration Planner (workflow_engine.py)
    -> Prompt Bridge (codex_bridge.py)
    -> Config Resolver (config.py)
    -> Method Data Sync/Cache (mythic_data.py)
      -> Filesystem artifacts (docs/, tasks/, mythic/, DEVLOG.md)
      -> Optional external method sync sources
```

---

## 3) Component responsibilities

### `mythic_vibe_cli/__main__.py`

- Provides `python -m mythic_vibe_cli`.
- Delegates to `mythic_vibe_cli.cli.main`.
- Must stay thin and side-effect free.

### `mythic_vibe_cli/cli.py`

- Preserves the public `mythic_vibe_cli.cli:main` entrypoint.
- Re-exports the current CLI kernel for compatibility.

### `mythic_vibe_cli/app.py`

- Defines command surface and argument contracts.
- Dispatches parsed commands through `COMMAND_HANDLERS`.
- Maintains user-facing ergonomics and stability.

### `mythic_vibe_cli/commands.py`

- Owns command implementations and compatibility alias registry.
- Translates parsed arguments into workflow/config/bridge/method operations.
- Keeps command behavior isolated from parser construction.

### `mythic_vibe_cli/output.py`

- Owns shared plain-text terminal rendering helpers.
- Keeps command output formatting consistent without coupling commands to `print()`.
- Coordinates quiet/verbose behavior for command output.

### `mythic_vibe_cli/errors.py`

- Owns structured CLI error payloads and formatting.
- Keeps command error messages actionable and compatible with the exit-code policy.

### `mythic_vibe_cli/core/state.py`

- Owns the schema-versioned `ProjectState` contract.
- Defines phase names, check-in records, decision records, verification records, and state validation.
- Must not perform filesystem, network, or terminal output side effects.

### `mythic_vibe_cli/persistence/json_store.py`

- Owns JSON state read/write behavior for `mythic/status.json`.
- Provides backup, atomic write, and lock-file protection for state updates.
- Must not own command semantics or Mythic phase decisions.

### `mythic_vibe_cli/persistence/migrations.py`

- Owns migration from legacy status JSON to the current state schema.
- Creates backups under `mythic/backups/` before rewriting existing state.
- Recovers corrupt JSON by preserving the broken file as a backup before writing a valid default state.

### `mythic_vibe_cli/resources/schemas/`

- Stores packaged JSON schema files for state, check-ins, decisions, and verification records.
- Documents the file-level contract used by validation and future external integrations.

### `mythic_vibe_cli/exit_codes.py`

- Defines the shared CLI exit-code policy.
- Keeps command return meanings stable across handlers.

### `mythic_vibe_cli/workflow.py`

- Owns phase transitions and lifecycle orchestration.
- Creates/updates artifacts and state files.
- Enforces sequence coherence for method execution.

### `mythic_vibe_cli/workflow_engine.py`

- Owns deterministic role orchestration plans for the six-agent workflow.
- Builds Skald -> Architect -> Cartographer -> Forge Worker -> Auditor -> Scribe handoff order.
- Exports packet-ready step requests without invoking external AI providers by default.
- Writes durable orchestration artifacts such as `mythic/workflow_plan.json`.

### `mythic_vibe_cli/codex_bridge.py`

- Composes context packets for AI-assisted workflows.
- Applies excerpting/compaction/budget policies.
- Preserves explicit packet structure for reproducibility.

### `mythic_vibe_cli/config.py`

- Resolves layered configuration from defaults/files/environment.
- Should remain deterministic and low side-effect.

### `mythic_vibe_cli/mythic_data.py`

- Handles sync/import/cache concerns for method data.
- Encapsulates network/provider interactions.

---

## 4) Dependency direction law

Allowed primary direction:

1. `__main__.py` and `cli.py` -> `app`
2. `app.py` -> `commands` + `core.state` argument constants
3. `commands.py` -> `workflow`, `persistence`, `codex_bridge`, `config`, `mythic_data`, `output`, `errors`, `exit_codes`
4. `workflow.py` -> `core.state`, `persistence`, `config` + local artifact IO
5. `workflow_engine.py` -> `ai.prompts.roles`, `codex_bridge.CodexPacketRequest`, `core.state`
6. `persistence/*.py` -> `core.state` + filesystem primitives
7. `codex_bridge.py` -> `config` + prepared context
8. `config.py` -> minimal dependencies only
9. `mythic_data.py` -> provider/sync/cache concerns

Forbidden by default:

- Reverse-layer imports that create cycles.
- Imports from dormant runtime islands.
- Imports from vendor mirrors directly into active CLI runtime.

Any exception requires a documented architecture decision before merge.

---

## 5) Filesystem interface contract

Runtime behavior assumes stable interaction with:

- `docs/` for governance/architecture records
- `tasks/` for planning and execution tracking
- `mythic/` for loop status/plan artifacts
- `mythic/status.json` as schema-versioned project state
- `mythic/backups/` for migration/recovery backups
- root continuity records such as `DEVLOG.md` and `CHANGELOG.md`

Renaming or relocating these without migration strategy is considered a breaking change.

---

## 6) Boundary rules

### Hard boundaries

- Active CLI remains independently executable.
- Dormant islands are not implicit dependencies.
- Vendor mirrors are not product runtime import targets.

### Soft boundaries

- Cross-island reuse must be done through explicit adapters.
- Adapter contracts must be documented before broad integration.

---

## 7) Architecture risks

1. **Monorepo ambiguity:** contributors may patch a look-alike module outside active path.
2. **Import drift:** convenience imports can silently create coupling debt.
3. **Contract drift:** docs may diverge from actual CLI behavior.
4. **Overloaded bridge packets:** context packets can become noisy without budget discipline.
5. **Output-mode drift:** human, quiet, dry-run, and JSON modes can diverge if command output bypasses shared helpers.
6. **State corruption:** migration or check-in writes can damage continuity if they bypass backup, lock, and atomic-write paths.

Mitigations:

- explicit domain map checks,
- required docs updates for behavior changes,
- routine command-help and smoke tests,
- changelog/devlog continuity discipline.
- command output through `output.py` and structured errors through `errors.py`.
- all state writes through `JsonStateStore` and all legacy upgrades through `migrations.py`.

---

## 8) Change protocol

Update this architecture record when introducing any of:

- new runtime entrypoint,
- changed phase lifecycle model,
- new persisted state contract,
- cross-island integration,
- new external dependency route.

Companion updates usually required:

- `docs/DOMAIN_MAP.md`
- `docs/api.md`
- root `ARCHITECTURE.md` / `DATA_FLOW.md` (if repository-wide flow changed)
- root `CHANGELOG.md` and `DEVLOG.md`

---

## 9) Review checklist for architecture-affecting PRs

- [ ] Active runtime paths are unchanged or intentionally migrated.
- [ ] No forbidden cross-domain imports introduced.
- [ ] Command/API docs updated.
- [ ] Examples remain executable.
- [ ] Changelog + devlog entries added for meaningful changes.

---

## 10) Related records

- `docs/DOMAIN_MAP.md`
- `docs/api.md`
- `docs/SYSTEM_VISION.md`
- `docs/INDEX.md`
- root `ARCHITECTURE.md`
- root `DATA_FLOW.md`

---

## 11) v1.0 module additions (PH-19 + PH-20, 2026-05-03)

The v1.0 launch added the following modules under the active runtime path. Each is independently tested under `tests/` and re-exported through its parent package where appropriate. The dependency direction stays the same — these are additive at the leaf, not new boundary crossings.

### Runtime layer (`mythic_vibe_cli/runtime/`)

- `cross_process_lock.py` — POSIX `fcntl.flock` + Windows `msvcrt.locking` with auto-release on process death. Wired into `forge_ledger.py` and `json_store.py:FileLock` (opt-in `cross_process=True`).
- `atomic_write.py` — write-tmp + `os.replace` with Windows `PermissionError` retry; `BaseException`-cleanup so `KeyboardInterrupt`/`SystemExit` don't leave orphan tmp files.

### Plugin layer (`mythic_vibe_cli/plugins/`)

- `capabilities.py` — declared-capability vocabulary (`read` / `network` / `subprocess` / `file-write`) + `audit_capabilities`. Default-deny.
- `circuit_breaker.py` — thread-safe per-plugin failure tracker with configurable threshold (`MYTHIC_PLUGIN_BREAKER_THRESHOLD`).
- `sandbox.py` — `safe_call` gained an additive `breaker=` kwarg; `breaker=None` default preserves pre-20.3 behavior.

### Top-level command modules

- `init_wizard.py` — opt-in `init --interactive` Q&A wizard.
- `packet_lint.py` — 7-rule heuristic packet quality linter.
- `doctor_fix.py` — tightly-scoped auto-remediation (mythic/ subdirs + CHANGELOG `[Unreleased]`); hard-rule guarded.
- `personas.py` — opt-in operator presets (`solo` / `team-lead` / `auditor`).
- `architecture_review.py` — pure-read quarterly review walker.
- `tui_panels.py` — opt-in TUI heatmap + plugin-risk panel data builders.
- `workflow_lineage.py` — Mermaid + JSON workflow lineage viewer.
- `ai/recommend.py` — pure-policy DSL scoring static-catalog models.
- `plunder/verify.py` — SHA-256 provenance verification.
- `plunder/attestation.py` — per-line modification attestation.

### Tooling

- `tools/contract_audit.py` — docs↔code drift detector with baseline-ratchet allowlist. CI-gated.
- `scripts/regenerate_sbom.py` — reproducible CycloneDX SBOM rebuild from a clean isolated venv.

### Workflows

- `.github/workflows/release.yml` — tag-driven distribution pipeline (PyPI OIDC + Homebrew tap + Scoop bucket + offline wheelhouse + GitHub Release).
- `.github/workflows/ci.yml` — expanded matrix (3 OS × 3 Python + Linux aarch64) with cross-platform smoke step + contract-audit gate.
