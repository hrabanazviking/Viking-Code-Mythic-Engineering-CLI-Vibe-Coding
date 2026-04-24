# Architecture

**Status:** Active architecture record  
**Last updated:** 2026-04-24
**Owner:** Architecture + Documentation maintainers  
**Scope:** Active product runtime (`mythic_vibe_cli/`) and its governance boundaries in this monorepo.

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
    -> Workflow Orchestrator (workflow.py)
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

### `mythic_vibe_cli/exit_codes.py`

- Defines the shared CLI exit-code policy.
- Keeps command return meanings stable across handlers.

### `mythic_vibe_cli/workflow.py`

- Owns phase transitions and lifecycle orchestration.
- Creates/updates artifacts and state files.
- Enforces sequence coherence for method execution.

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
2. `app.py` -> `commands` + argument contract constants
3. `commands.py` -> `workflow`, `codex_bridge`, `config`, `mythic_data`, `output`, `errors`, `exit_codes`
4. `workflow.py` -> `config` + local artifact IO
5. `codex_bridge.py` -> `config` + prepared context
6. `config.py` -> minimal dependencies only
7. `mythic_data.py` -> provider/sync/cache concerns

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

Mitigations:

- explicit domain map checks,
- required docs updates for behavior changes,
- routine command-help and smoke tests,
- changelog/devlog continuity discipline.
- command output through `output.py` and structured errors through `errors.py`.

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
