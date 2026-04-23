# TASK: Repo-Wide Exploration & Inventory

**Date opened:** 2026-04-23
**Branch:** development
**Owner:** Runa (orchestrator) + Cartographer (Védis Eikleið) + Scribe (Eirwyn Rúnblóm)

---

## Goal

Volmarr has populated this repo (`Viking-Code-Mythic-Engineering-CLI-Vibe-Coding`) with files imported from many other projects. Before any modification or integration work begins, we must produce a complete understanding of:

1. **What is here** — every directory, every file class, every imported sub-project.
2. **What each thing currently does** — its current behavior, in its current form, untouched.
3. **How it all relates** — dependencies, data flow, structural relationships, integration seams.
4. **What is duplicated, drifted, or orphaned** — files that came from elsewhere and need reconciling.

**Strict rule for this phase: NO modifications to any code or imported file. Description and mapping only.**

---

## Scope

- **Repo path:** `C:/Users/volma/runa/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding`
- **Branch:** development (HEAD: adbd731 at task open)
- **File count:** 3947 files
- **Top languages:** Markdown (932), Go (681), Python (443), C++ (185), CUDA (158), shaders (.comp 143), C headers (113), TypeScript (73)
- **Top-level directories:** ai/, chatterbox/, core/, diagnostics/, docs/, imports/, mindspark_thoughtform/, mythic_vibe_cli/, ollama/, research_data/, scripts/, sessions/, systems/, tests/, whisper/, WYRD-Protocol-*/, yggdrasil/
- **Notable root-level docs:** ABOUT_THE_VIKING_ROLEPLAY.md, Ada_Lovelace_Explains_Mythic_Engineering.md, ARCHITECTURE_STUDY_March-8-2026.md, AI Viking TTRPG Emotional Engine Modeling Theory.md (178KB), Building the Yggdrasil Cognitive Architecture in Python.md, CHARACTER_TEMPLATE_SCHEM.yaml (177KB), config.yaml, multiple Emotional Engine Integration Plan docs, debug_router_integration.py, diagnostics.py
- **Tooling configs present:** .aider.conf.yml, .clinerules, .roo*, .claude/

---

## Division of labour

### Cartographer — Védis Eikleið

**Output files (in repo root):**
- `MAP.md` — top-level system map; one-line per major directory + arrows showing relationships
- `ARCHITECTURE.md` — layered decomposition; what subsystems exist, how they stack
- `DEPENDENCIES.md` — internal cross-directory imports + external pip/go/npm deps
- `DATA_FLOW.md` — how data and state move between subsystems

**Focus:** structure, relationships, dependencies, layered overview. Visual/diagrammatic where useful (Mermaid or ASCII). Reveal hidden couplings between the imported sub-projects.

### Scribe — Eirwyn Rúnblóm

**Output files (in repo root):**
- `INVENTORY.md` — narrative inventory: directory by directory, file class by file class, what is there and what it currently does. The reference scroll a future session can read to get oriented.
- `DEVLOG.md` — open with a dated entry for this exploration session (2026-04-23)
- `ORIGINS.md` — best-effort attribution of which imported files came from which prior project (NSE, MindSpark, VGSK, WYRD, pygame, etc.) based on naming, content, and any in-file hints

**Focus:** preservation and description. Refined prose, dated, retrievable. Catalogues what exists in its current form.

### Coordination

Both agents work the same repo in parallel. They write to **different files** (no overlap). They may cross-reference each other's outputs in their own documents.

---

## Progress tracker

- [x] TASK file written and committed (Runa, 2026-04-23)
- [ ] Cartographer launched
- [ ] Scribe launched
- [ ] Cartographer's maps written: MAP.md, ARCHITECTURE.md, DEPENDENCIES.md, DATA_FLOW.md
- [ ] Scribe's records written: INVENTORY.md, DEVLOG.md, ORIGINS.md
- [ ] Synthesis review (Runa)
- [ ] Results committed and pushed to development
- [ ] Memory updated with findings

---

## Resumption protocol

If session breaks before completion:

1. Read this file.
2. Check which output files exist in repo root: `MAP.md`, `ARCHITECTURE.md`, `DEPENDENCIES.md`, `DATA_FLOW.md`, `INVENTORY.md`, `DEVLOG.md`, `ORIGINS.md`.
3. For any missing file, re-dispatch the responsible agent (Cartographer for MAP/ARCH/DEPS/FLOW; Scribe for INVENTORY/DEVLOG/ORIGINS).
4. Update the progress tracker in this file as work resumes.
5. **Do not begin any modification, integration, or refactor work.** That is a future task — this one is exploration only.

---

## Next phase (NOT this task — for later planning)

After exploration completes, Volmarr will direct an integration phase: deciding which imported pieces to keep, mod, merge, or remove, and how they fit the Vibe-Coding CLI's intended shape. That is `TASK_integration.md`, written when this one closes.
