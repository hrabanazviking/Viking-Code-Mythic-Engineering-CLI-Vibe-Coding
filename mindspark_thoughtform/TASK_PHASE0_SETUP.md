# TASK: Phase 0 — Forge the Foundation

**Created:** 2026-03-31
**Status:** READY TO START (plan confirmed, files committed, no code written yet)
**Branch:** development
**Project:** MindSpark: ThoughtForge

---

## Task Scope

Set up the full repo skeleton for MindSpark: ThoughtForge so every future module has a clean home. This is pure structure + config — no logic code yet.

---

## What Is Done

- [x] Repo cloned to `C:/Users/volma/runa/MindSpark_ThoughtForge`
- [x] Build Plan written: `BUILD_PLAN_v1.md`
- [x] All spec `.md` files exist in repo root (to be moved in this phase)
- [x] Task file written (this file)
- [x] Memory updated

---

## What Is Pending (Phase 0 Work)

- [ ] Create directory skeleton:
  - `src/thoughtforge/`
  - `src/thoughtforge/knowledge/`
  - `src/thoughtforge/inference/`
  - `src/thoughtforge/cognition/`
  - `src/thoughtforge/refinement/`
  - `src/thoughtforge/utils/`
  - `src/thoughtforge/etl/`
  - `docs/specs/`
  - `data/knowledge_reference/` (already exists under MindSpark_ThoughtForge/data/)
  - `tests/`
  - `configs/`
  - `hardware_profiles/`
- [ ] Move all `.md` spec files from root into `docs/specs/`
- [ ] Write `pyproject.toml`
- [ ] Write `requirements.txt`
- [ ] Write `setup.py`
- [ ] Write hardware profile JSON configs for all 6 tiers
- [ ] Write GitHub Actions CI workflow (`.github/workflows/ci.yml`)
- [ ] Write `CONTRIBUTING.md`
- [ ] Update `.gitignore`
- [ ] Write `src/thoughtforge/__init__.py`
- [ ] Verify `pip install -e .` works

---

## Next Task After This

**Phase 1 — Memory Forge + Sovereign RAG**
- All 14 data structure types
- Wikidata streaming ETL (full dump)
- Multi-source ingestion (DBpedia, YAGO, ConceptNet, GeoNames, Gutenberg)
- Hybrid SQL + vector retrieval
- Memory lifecycle + pruning system
- See `BUILD_PLAN_v1.md` Phase 1 section for full detail

---

## Key File Locations

| File | Path |
|---|---|
| Build Plan | `BUILD_PLAN_v1.md` |
| Specs (post-Phase 0) | `docs/specs/` |
| Source code | `src/thoughtforge/` |
| Hardware profiles | `hardware_profiles/` |
| Tests | `tests/` |
| Data / knowledge | `data/` |
| ETL entry point | `src/thoughtforge/etl/wikidata_etl.py` |
| Main CLI | `run_thoughtforge.py` |
| Memory forge CLI | `forge_memory.py` |

---

## Resumption Instructions

If session breaks, read this file first, then `BUILD_PLAN_v1.md`.
Check git log to see what was last committed.
Continue from the first unchecked item in "What Is Pending" above.
