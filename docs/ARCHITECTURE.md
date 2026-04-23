# Architecture (Architect Invocation)

**Status:** Active architecture record  
**Last updated:** 2026-04-23  
**Owner:** Architecture / Docs

This document is the `docs/` companion to the root-level `ARCHITECTURE.md`.  
Use this version when you need a fast orientation and clear implementation boundaries.

---

## 1) System posture

The repository currently behaves as a **multi-project monorepo** with one primary executable product:

1. **Mythic Vibe CLI** (`mythic_vibe_cli/`) — live operational path.
2. **Norse Saga Engine runtime modules** (`ai/`, `core/`, `systems/`, `sessions/`, `yggdrasil/`) — present, mostly dormant/incomplete wiring.
3. **Embedded upstream/vendor trees** (`ollama/`, `whisper/`, `WYRD-.../`, and research/spec artifacts) — largely self-contained.

Architecturally, treat these as **separate islands** until explicit integration contracts are introduced.

---

## 2) Primary live architecture: Mythic Vibe CLI

```text
User
  -> CLI Router (mythic_vibe_cli/cli.py)
    -> Workflow Engine (workflow.py)
    -> Codex Packet Builder (codex_bridge.py)
    -> Config Resolution (config.py)
    -> Method Sync + Cache (mythic_data.py)
      -> Filesystem state (docs/, tasks/, mythic/, DEVLOG.md, weave.db)
      -> Optional GitHub method sync
```

### Layer responsibilities

- **Interface layer (`cli.py`)**
  - Parses commands and options.
  - Dispatches command handlers.
- **Orchestration layer (`workflow.py`)**
  - Maintains phased flow (intent → constraints → architecture → plan → build → verify → reflect).
  - Manages operational project artifacts.
- **Prompt/bridge layer (`codex_bridge.py`)**
  - Builds prompt packets and context excerpts.
  - Applies budget and compaction behavior.
- **Configuration layer (`config.py`)**
  - Resolves config precedence from local/user/env scopes.
- **Data/method layer (`mythic_data.py`)**
  - Pulls and caches method docs.

---

## 3) Architectural boundaries

### Hard boundaries (current)

- `mythic_vibe_cli/` should remain independently executable.
- Root runtime trees (`core/`, `systems/`, `yggdrasil/`, etc.) are not assumed load-bearing for CLI execution.
- Vendor/upstream folders should not be imported accidentally into CLI runtime paths.

### Soft boundaries (planned)

- Integration should occur via explicit adapters/interfaces rather than direct deep imports.
- Cross-island reuse should be documented first (contract + data-flow + dependency impact), then wired.

---

## 4) Dependency direction rules

For maintainability, enforce one-way architectural flow in the live path:

1. `cli.py` can depend on `workflow`, `codex_bridge`, `config`, `mythic_data`.
2. `workflow.py` can depend on `config` and file-system state.
3. `codex_bridge.py` can depend on `config` and prepared workflow artifacts.
4. `config.py` should remain low-level and side-effect light.
5. `mythic_data.py` can touch network/cache concerns but should not absorb CLI orchestration logic.

If a change requires reversing this direction, treat it as an architecture decision and record it before merging.

---

## 5) Operational risks to monitor

- **Monorepo ambiguity:** contributors may assume dormant modules are active runtime dependencies.
- **Import drift:** accidental imports from unrelated islands can silently increase coupling.
- **Docs drift:** root `ARCHITECTURE.md`, `DOMAIN_MAP.md`, and this file can diverge without regular refresh.

---

## 6) Architecture guardrails

- Keep primary executable behavior centered in `mythic_vibe_cli/`.
- Prefer composition/adapters over direct cross-tree imports.
- Update architecture docs when introducing:
  - a new runtime entrypoint,
  - a new persistence contract,
  - a new external dependency path,
  - or any cross-island integration.

---

## 7) Related records

- Root deep-dive: `ARCHITECTURE.md`
- Domain boundaries: `docs/DOMAIN_MAP.md`
- Data movement: `DATA_FLOW.md`
- Concrete dependencies: `DEPENDENCIES.md`
- Required-code matrix: `CODE_REQUIREMENTS_MATRIX.md`

