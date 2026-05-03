# `docs/specs/` — Research Corpus (out of v1.0 active-product scope)

**This directory holds research, design exploration, and conceptual specifications.** It is **not** part of the active Mythic Vibe CLI v1.0.0 product surface.

---

## What lives here

A 29-file corpus of design specifications, algorithm sketches, knowledge-graph blueprints, and conceptual essays. Topics range across:

- Sovereign RAG architecture exploration (`Sovereign_RAG_*`).
- ThoughtForge cognition system specifications (`ThoughtForge_*`).
- TurboQuant guided-memory cognition (`TurboQuant_*`).
- Wikidata ETL pipeline design (`Wikidata_ETL_Pipeline.md`).
- Skald and Galdrabok narrative design (`Skald_*`, `GALDRABOK_*`).
- Memory lifecycle, retrieval, and prompt-template specifications.
- Norse-pagan world-modelling and character-design references.

These documents informed adjacent projects (NorseSagaEngine, MindSpark ThoughtForge, WYRD Protocol — see [`docs/DORMANT_ISLANDS.md`](../DORMANT_ISLANDS.md)) and remain useful reference material. They were **not** consumed by the v1.0.0 launch.

---

## Why this README exists

Without an explicit scope note, a new contributor browsing the docs/ directory might assume `docs/specs/` documents the active CLI behavior. It does not. The active product is documented in:

- [`README.md`](../../README.md) — front door.
- [`docs/INDEX.md`](../INDEX.md) — canonical navigation.
- [`docs/api.md`](../api.md), [`docs/COMMAND_CONTRACTS.md`](../COMMAND_CONTRACTS.md) — command surface.
- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md), [`docs/DOMAIN_MAP.md`](../DOMAIN_MAP.md), [`docs/DATA_FLOW.md`](../DATA_FLOW.md) — runtime architecture.
- [`docs/ACTIVE_PRODUCT_BOUNDARY.md`](../ACTIVE_PRODUCT_BOUNDARY.md) — exact runtime contract.
- [`docs/compatibility_policy.md`](../compatibility_policy.md) — v1.0 binding contract.

Treat anything in `docs/specs/` as **reference material** unless an ADR explicitly draws it into the active product path.

---

## Status

- **Audit cadence:** these specs are NOT included in the routine doc-audit cycle (the v1.0.0 audit refreshed 22 active-product docs across four passes; the specs corpus was deliberately out of scope).
- **Contribution policy:** PRs that touch these files should explain *why* the change matters to active product behavior, OR clearly mark the change as research / exploration.
- **Future direction:** if any spec here matures into product behavior, an ADR (see [`docs/ADRS/`](../ADRS/)) records the decision and the corresponding code lives in `mythic_vibe_cli/`.

---

## File index

The corpus shifts as research evolves. Run `ls docs/specs/` for the current file list.

For the v1.0.0 launch (2026-05-03), the corpus covered:

- `Algorithms_and_Pseudocode_Spec.md`
- `Alternative_Knowledge_Graphs.md`
- `Data_Structures_Spec.md`
- `GALDRABOK_PREFACE.md`
- `Master_Game_Plan_Roadmap.md`
- `Memory_Guided_Cognition_Resources.md`
- `Memory_Lifecycle_and_Pruning_Spec.md`
- `Production_Ready_Implementation_Package.md`
- `Prompt_Templates_Spec.md`
- `Retrieval_and_Scoring_Spec.md`
- `Skald_Code_Assembly_Blueprint.md`
- `Skald_Project_Vision_Atlas.md`
- `Sovereign_RAG_Brainstorming.md`
- `Sovereign_RAG_Technical_Overview.md`
- `SQL_RAG_Memory_Enforced_Cognition.md`
- `The_Heathen_Third_Path_Essay.md`
- `ThoughtForge_Complete_System_Library_v2.md`
- `ThoughtForge_Full_Expanded_Implementation.md`
- `ThoughtForge_Full_Implementation_Package.md`
- `ThoughtForge_Implementation_Game_Plan_Draft1.md`
- `TurboQuant_Cognition_Blueprint.md`
- `TurboQuant_Guided_Memory_Cognition.md`
- `Various_Astrid_Freyjasdottir_Outfits.md`
- `Warding_of_Huginns_Well.md`
- `Wikidata_ETL_Pipeline.md`
- plus the `runhild/` subdirectory.
