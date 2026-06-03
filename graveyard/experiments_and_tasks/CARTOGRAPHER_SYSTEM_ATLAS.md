# CARTOGRAPHER_SYSTEM_ATLAS.md

**Author:** Védis Eikleið, Cartographer (The Sensual Wayfinder)  
**Date:** 2026-04-23  
**Purpose:** Deep, system-wide orientation map for this repository, with emphasis on practical navigation, ownership boundaries, and integration risk terrain.

---

## 1) Orientation at first sight

This repository is best understood as a **federated archive of multiple projects** rather than a single cohesive runtime. The active product is compact (`mythic_vibe_cli/` + `tests/`), while the surrounding terrain contains large imported/vendored systems and research corpora.

### Top-level terrain (file-count view)

| Directory | Approx file count | Cartographer classification |
|---|---:|---|
| `mythic_vibe_cli/` | 6 | Product nucleus (live) |
| `tests/` | 4 | Product validation (live) |
| `yggdrasil/` | 370 | Imported NSE cognitive router island |
| `systems/` | 28 | Imported NSE subsystem layer |
| `core/` | 6 | Imported NSE core services |
| `ai/` | 2 | Imported NSE provider adapters |
| `mindspark_thoughtform/` | 745 | Imported ThoughtForge subproject |
| `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/` | 619 | Imported WYRD subproject |
| `research_data/` | 102 | Research + partial code duplicate island |
| `ollama/` | 1820 | Vendored upstream codebase |
| `whisper/` | 45 | Vendored upstream codebase |
| `chatterbox/` | 66 | Vendored upstream codebase |

### File-type mass (signal of repository composition)

- Markdown (`.md`) dominates both by count and size, meaning this is a **documentation-heavy planning and archival repo**.
- Python (`.py`) is substantial and distributed across multiple islands.
- Go (`.go`) mass comes mainly from vendored `ollama/`.
- Rich media (`.jpg`, `.png`, `.pdf`, `.jsonl`) indicates heavy research and artifact storage.

---

## 2) The five-island model (practical navigation)

Treat the codebase as five primary islands with minimal operational bridges:

1. **Island A — Mythic Vibe CLI (live product)**
   - `mythic_vibe_cli/`
   - `tests/`
   - `pyproject.toml` (root)
2. **Island B — NSE runtime import cluster (dormant/partial)**
   - `ai/`, `core/`, `systems/`, `sessions/`, `yggdrasil/`, related scripts
3. **Island C — MindSpark ThoughtForge (self-contained)**
   - `mindspark_thoughtform/`
4. **Island D — WYRD Protocol (self-contained) + research partial shadow**
   - `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/`
   - `research_data/src/wyrdforge/` (partial duplicate)
5. **Island E — Upstream vendors (currently detached)**
   - `ollama/`, `whisper/`, `chatterbox/`

**Key navigational truth:** only Island A is clearly wired as the user-facing product path in this repo’s declared package/install configuration.

---

## 3) Product nucleus: what is currently live

### 3.1 Core package

`mythic_vibe_cli/` contains:

- `cli.py` — command surface and command routing
- `workflow.py` — project phase orchestration/state transitions
- `codex_bridge.py` — packetization/bridge formatting for Codex interactions
- `config.py` — layered config resolution
- `mythic_data.py` — method corpus sync/cache flows
- `__init__.py`

### 3.2 Product tests

`tests/` validates CLI-side behavior; this is the most reliable lens for “what currently works” in this monorepo context.

### 3.3 Packaging boundary

Root `pyproject.toml` packages the CLI product, while most other code at root is effectively unbundled unless imported by path/shell context.

---

## 4) NSE import cluster (Island B): rich but structurally fragile

This island contains meaningful systems architecture ideas and runtime modules, but in this repo it behaves like a **partially transplanted engine**:

- Extensive `yggdrasil/` subsystem with realms, ravens, cognition orchestration, and integration directories.
- `systems/` layer includes memory, context, prompt, emotional/personality and related services.
- `core/` modules include emotional and dream services, message queue, and runtime settings.

### Known fragility seams

- References to non-present module roots (ghost imports) in this island can break runtime initialization.
- Import style assumes a specific environment/module root shape that may not match installed package reality.
- High doc-sidecar density suggests generation/agent workflows not represented in root product entrypoints.

---

## 5) MindSpark and WYRD islands: deep capability, low present coupling

### 5.1 `mindspark_thoughtform/`

- Full project shape: `src/`, `tests/`, docs, configs, requirements.
- Appears independently executable/testable inside its own ecosystem.
- Not directly wired into `mythic_vibe_cli` entrypoints today.

### 5.2 `WYRD-.../`

- Full protocol-world-model project with broad modules and tests.
- Internal maturity appears high (phase task docs + structured package layout).
- Integration to CLI nucleus currently conceptual/documentary, not primary import path.

### 5.3 `research_data/src/wyrdforge/`

- Partial `wyrdforge` mirror implies drift risk and ownership ambiguity.
- Valuable as reference material; hazardous as executable duplicate unless governed.

---

## 6) Vendor constellations (Island E)

- `ollama/` (large Go tree), `whisper/`, `chatterbox/` are present as source assets.
- In this repo’s active product path, they are mostly **potential integration surfaces**, not central load-bearing dependencies.

---

## 7) Documentation topology

This repository has a strong “scroll archive” identity:

- High-density root markdown corpus for architecture, planning, mythology, methods.
- `docs/specs/` and sibling specs under subprojects indicate repeated/parallel design streams.
- Existing map pack (`MAP.md`, `ARCHITECTURE.md`, `DEPENDENCIES.md`, `DATA_FLOW.md`) already establishes excellent orientation primitives and should remain canonical.

---

## 8) Integration-readiness map

### Stable ground (safe to operate now)

- CLI workflows and tests.
- Documentation-driven planning and architecture analysis.
- Isolated execution of imported subprojects in their own environments.

### Unstable ground (care required)

- Cross-island imports without explicit boundary contracts.
- Duplicate package trees (`wyrdforge` partial mirrors).
- Assumed import roots in transplanted NSE modules.
- Any attempt to “activate everything at once” in one env without dependency harmonization.

---

## 9) Cartographer recommendations (orientation-first)

1. Treat `mythic_vibe_cli` as the explicit product core of record.
2. Assign ownership labels to each island (`live`, `candidate`, `archival`, `vendor`).
3. Quarantine or explicitly namespace duplicate code mirrors.
4. Establish a seam-contract doc before integrating any dormant island into the product core.
5. Keep and refresh the map pack as first-class operational docs for future agents.

---

## 10) Invocation note for future sessions

To summon this same mode in future sessions, use:

- “Cartographer, orient this repo and map blast radius.”
- “Cartographer, refresh MAP/ARCHITECTURE/DEPENDENCIES/DATA_FLOW with current state.”
- “Cartographer, trace this change across all islands and update atlas docs.”

