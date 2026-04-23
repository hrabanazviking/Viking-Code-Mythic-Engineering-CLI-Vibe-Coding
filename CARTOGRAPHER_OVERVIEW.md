# CARTOGRAPHER_OVERVIEW.md — Initial Repository Overview

**Date:** 2026-04-23  
**Cartographer:** Védis Eikleið  
**Repository:** `Viking-Code-Mythic-Engineering-CLI-Vibe-Coding`

## 1) Terrain at a glance

This repository is a **hybrid archive + active product repo**:

- A small, active product: `mythic_vibe_cli/` (the Mythic Vibe CLI).
- A large set of imported systems from earlier projects:
  - Norse Saga Engine-style modules at root (`systems/`, `yggdrasil/`, `core/`, `ai/`).
  - Full embedded subprojects (`mindspark_thoughtform/`, `WYRD-Protocol-.../`).
- Three major vendored upstream projects (`ollama/`, `whisper/`, `chatterbox/`).

## 2) Primary islands

| Island | Role | Integration status |
|---|---|---|
| `mythic_vibe_cli/` + root `tests/` | Main runnable product and packaged Python code | **Active and coherent** |
| `systems/`, `yggdrasil/`, `core/`, `ai/`, `sessions/` | Imported Norse Saga Engine components | **Partially connected, contains broken/ghost imports** |
| `mindspark_thoughtform/` | Full embedded ThoughtForge project | **Mostly self-contained** |
| `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/` | Full embedded WYRD project | **Mostly self-contained** |
| `ollama/`, `whisper/`, `chatterbox/` | Vendored upstream dependencies | **Present, not actively wired into CLI** |

## 3) Practical source of truth (today)

For contributors trying to ship product value quickly, treat these as canonical first:

1. `README.md` (user-facing CLI behavior)
2. `pyproject.toml` (what is actually packaged)
3. `mythic_vibe_cli/` (actual CLI code)
4. `tests/` (tests that currently guard shipped CLI behavior)

Then use map artifacts for deep orientation:

- `MAP.md`
- `ARCHITECTURE.md`
- `DEPENDENCIES.md`
- `DATA_FLOW.md`
- `INVENTORY.md`

## 4) Immediate integration risks to remember

- Ghost imports exist in imported NSE code (example: references to modules not present in repo).
- `wyrdforge` appears in multiple places with overlap/drift risk.
- Root-level code quantity is very large compared with the actively packaged CLI.
- Different subprojects assume different dependency stacks; one environment may not satisfy all simultaneously.

## 5) Suggested north-star framing

Treat this repository as:

- **Core product lane:** `mythic_vibe_cli/` + root tests (keep stable, testable, releasable).
- **Integration lane:** imported engines and subprojects (progressively reconciled behind clear boundaries).
- **Archive lane:** theory/research corpus and vendored source trees retained for reference and future extraction.

This framing reduces confusion, keeps shipping velocity in the CLI lane, and turns the rest of the terrain into deliberate integration work rather than accidental coupling.
