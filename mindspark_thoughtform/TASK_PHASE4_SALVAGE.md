# TASK: Phase 4 — Fragment Salvage + Refinement

**Created:** 2026-03-31
**Status:** IN PROGRESS
**Branch:** development
**Project:** MindSpark: ThoughtForge

---

## Task Scope

Build the refinement layer: FragmentSalvage (multi-pass draft scoring + reassembly),
EnforcementGate (citation integrity + response validation), wire both into ThoughtForgeCore,
and deliver run_thoughtforge.py interactive CLI.

---

## What Is Done (Phase 3 baseline)

- [x] Phase 0–3 complete, 191 tests passing
- [x] ThoughtForgeCore.think() full pipeline working
- [x] Inline fragment scoring in core.py (to be replaced/augmented)
- [x] Inline citation check in core.py (to be replaced with EnforcementGate)
- [x] refinement/__init__.py stub only

---

## What Is Pending (Phase 4 Work)

- [x] Write this TASK file + commit
- [ ] `src/thoughtforge/refinement/salvage.py` — FragmentSalvage.forge()
- [ ] `src/thoughtforge/refinement/enforcement.py` — EnforcementGate
- [ ] `src/thoughtforge/refinement/__init__.py` — exports
- [ ] Update `src/thoughtforge/cognition/core.py` — wire salvage + enforcement
- [ ] `run_thoughtforge.py` — interactive CLI
- [ ] `tests/test_phase4_refinement.py` — test suite
- [ ] Git commit Phase 4

---

## Phase 4 Module Map

| Module | Class | Key Method |
|---|---|---|
| `refinement/salvage.py` | `FragmentSalvage` | `forge(candidates, bundle, engine, prompt_builder, sketch, scaffold) -> SalvageResult` |
| `refinement/enforcement.py` | `EnforcementGate` | `check(text, citations, bundle) -> EnforcementResult` |
| `run_thoughtforge.py` | — | Interactive REPL + single-query mode |

## FragmentSalvage.forge() Logic

1. Score each candidate: length_score (45%) + citation_score (55%) per BUILD_PLAN_v1
2. Extract top sentences from best-scoring candidates
3. Attempt refine pass via engine (if available) — max 2 passes
4. Return SalvageResult: text, citations, confidence, passes_used

## EnforcementGate.check() Logic

1. If no knowledge retrieved → pass (nothing to enforce against)
2. If Wikidata records present → check at least 1 QID cited
3. If text below min length → fail
4. Return EnforcementResult: passed, notes, text (may append forge note on soft fail)

---

## Key File Locations

| File | Path |
|---|---|
| Build Plan Phase 4 | `BUILD_PLAN_v1.md` lines 134–146 |
| Scoring spec | `docs/specs/Retrieval_and_Scoring_Spec.md` |
| ThoughtForgeCore | `src/thoughtforge/cognition/core.py` |
| Refinement package | `src/thoughtforge/refinement/` |
| CLI | `run_thoughtforge.py` |

---

## Resumption Instructions

Read this file + check git log. Continue from first unchecked item above.
