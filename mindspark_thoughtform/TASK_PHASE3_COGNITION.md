# TASK: Phase 3 — Cognition Scaffolds + Orchestration

**Created:** 2026-03-31
**Status:** COMPLETE — commit 7fb8a60
**Branch:** development
**Project:** MindSpark: ThoughtForge

---

## Task Scope

Build the full cognition layer: input routing → scaffold assembly → prompt construction → `ThoughtForgeCore.think()` main loop. This connects Phase 1 (knowledge retrieval) and Phase 2 (TurboQuant inference) into a complete end-to-end pipeline.

---

## What Is Done (Phase 2 baseline)

- [x] Phase 0–2 complete, 116 tests passing
- [x] All 14 data structure types defined in `models.py`
- [x] `KnowledgeForge.retrieve()` API working (SQL + vector + hybrid)
- [x] `MemoryStore` full read/write API working
- [x] `TurboQuantEngine` with `generate()` and `generate_drafts()` working
- [x] `configs/default.yaml` has cognition config block
- [x] `cognition/` and `refinement/` packages are empty stubs

---

## What Is Pending (Phase 3 Work)

- [x] Write this TASK file + commit
- [ ] `configs/personality_core.yaml` — Skald persona
- [ ] `src/thoughtforge/cognition/router.py` — InputRouter → InputSketch
- [ ] `src/thoughtforge/cognition/scaffold.py` — ScaffoldBuilder → CognitionScaffold
- [ ] `src/thoughtforge/cognition/prompt_builder.py` — candidate/refine/repair prompt assembly
- [ ] `src/thoughtforge/cognition/core.py` — ThoughtForgeCore.think() full loop
- [ ] `src/thoughtforge/cognition/__init__.py` — exports
- [ ] `tests/test_phase3_cognition.py` — test suite
- [ ] Git commit Phase 3

---

## Phase 3 Module Map

| Module | Class | Key Method |
|---|---|---|
| `router.py` | `InputRouter` | `route(raw_text, thread_state) -> InputSketch` |
| `scaffold.py` | `ScaffoldBuilder` | `build(sketch, bundle, personality) -> CognitionScaffold` |
| `prompt_builder.py` | `PromptBuilder` | `build_candidate_prompt()`, `build_refine_prompt()`, `build_repair_prompt()` |
| `core.py` | `ThoughtForgeCore` | `think(user_text) -> FinalResponseRecord` |

## ThoughtForgeCore.think() Pipeline

1. `InputRouter.route()` → InputSketch
2. `KnowledgeForge.retrieve()` → MemoryActivationBundle
3. `ScaffoldBuilder.build()` → CognitionScaffold
4. `TurboQuantEngine.generate_drafts()` → list[CandidateRecord]
5. score fragments from candidates → list[FragmentRecord]
6. compose refine prompt → second-pass generation → FinalResponseRecord
7. quality gate: if weak/reject → repair pass
8. return FinalResponseRecord

---

## Key File Locations

| File | Path |
|---|---|
| Algorithms spec | `docs/specs/Algorithms_and_Pseudocode_Spec.md` |
| Prompt templates spec | `docs/specs/Prompt_Templates_Spec.md` |
| Data structures | `src/thoughtforge/knowledge/models.py` |
| KnowledgeForge | `src/thoughtforge/knowledge/forge.py` |
| TurboQuantEngine | `src/thoughtforge/inference/turboquant.py` |
| Cognition package | `src/thoughtforge/cognition/` |
| Config | `configs/default.yaml` |
| Personality YAML | `configs/personality_core.yaml` |

---

## Resumption Instructions

Read this file, then check `git log --oneline`. Continue from the first unchecked item above.
