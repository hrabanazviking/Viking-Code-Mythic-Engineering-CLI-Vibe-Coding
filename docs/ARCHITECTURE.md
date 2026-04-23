# Architecture

**Status:** Active architecture record  
**Last updated:** 2026-04-23  
**Owner:** Architecture / Docs

This document defines the active runtime architecture for this monorepo and the rules that prevent accidental coupling.

---

## 1) Repository posture

Treat this repository as a **multi-project monorepo** with one primary live product path:

1. **Mythic Vibe CLI** (`mythic_vibe_cli/`) — active runtime and operational entrypoint.
2. **Legacy/runtime islands** (`ai/`, `core/`, `systems/`, `sessions/`, `yggdrasil/`) — mostly dormant/fragmented.
3. **Vendor/research islands** (`ollama/`, `whisper/`, `WYRD-.../`, specs/research corpora) — reference only unless explicitly integrated.

Default assumption: islands are independent unless a documented adapter contract exists.

---

## 2) Active system flow (Mythic Vibe CLI)

```text
User
  -> CLI Router (mythic_vibe_cli/cli.py)
    -> Workflow Orchestrator (workflow.py)
    -> Prompt/Bridge Composer (codex_bridge.py)
    -> Config Resolution (config.py)
    -> Method Sync + Cache (mythic_data.py)
      -> Project artifacts (docs/, tasks/, mythic/, DEVLOG.md, weave.db)
      -> Optional external sync providers
```

### Layer responsibilities

- **`cli.py` (interface layer)**
  - Defines commands/options and dispatches handlers.
  - Keeps user-facing behavior coherent and predictable.

- **`workflow.py` (orchestration layer)**
  - Runs phase lifecycle and state transitions.
  - Writes/updates durable artifacts.

- **`codex_bridge.py` (prompt/packet layer)**
  - Builds high-signal context packets.
  - Applies compaction and budget constraints.

- **`config.py` (configuration layer)**
  - Resolves env/file/default precedence.
  - Stays low-side-effect and stable.

- **`mythic_data.py` (data/sync layer)**
  - Handles method source sync/import/caching.
  - Avoids owning orchestration logic.

---

## 3) Dependency direction law

To keep architecture legible, dependency direction should remain one-way:

1. `cli.py` -> `workflow`, `codex_bridge`, `config`, `mythic_data`
2. `workflow.py` -> `config` + local artifact IO
3. `codex_bridge.py` -> `config` + prepared workflow context
4. `config.py` -> minimal dependencies
5. `mythic_data.py` -> sync/cache concerns only

Any reversal requires an architecture decision record (ADR-style note in docs) before merge.

---

## 4) Boundary rules

### Hard boundaries

- `mythic_vibe_cli/` remains independently executable.
- Dormant islands are not implicit runtime dependencies.
- Vendor mirrors are not direct product import targets.

### Soft boundaries

- Cross-island reuse must enter via explicit adapters/interfaces.
- Document contracts and data flow before adding wiring.

---

## 5) Architecture risks

- **Monorepo ambiguity:** contributors may edit the wrong island for active product behavior.
- **Import drift:** accidental imports increase coupling and maintenance cost.
- **Docs drift:** architecture/governance docs can diverge from runtime reality.

Mitigation: require boundary verification commands in every meaningful PR.

---

## 6) Change protocol

When a change introduces any of the following, update this file in the same PR:

- new runtime entrypoint,
- new persistence/state contract,
- new external dependency path,
- new cross-island integration,
- significant command lifecycle change.

Also update related records:

- `docs/DOMAIN_MAP.md`
- root `ARCHITECTURE.md`
- `DATA_FLOW.md` (if data movement changed)

---

## 7) Related records

- Root deep-dive: `ARCHITECTURE.md`
- Ownership boundaries: `docs/DOMAIN_MAP.md`
- System direction: `docs/SYSTEM_VISION.md`
- Operational flow details: `DATA_FLOW.md`
