# TASK: Phase 6 — Testing, Benchmarking, Personality Layer + Release

**Created:** 2026-03-31
**Phase:** 6 of 6 (FINAL)
**Branch:** development
**Status:** IN PROGRESS

---

## Goal

Full integration + adversarial test suite. Profile benchmarks. Viking/Skald
persona consistency scoring. MkDocs documentation site. v1.0.0 release with
CHANGELOG, updated README, and Hugging Face model card.

---

## Deliverables

| File | Status |
|---|---|
| `TASK_PHASE6_RELEASE.md` | ✅ (this file) |
| `benchmarks/__init__.py` | ✅ |
| `benchmarks/benchmark_profiles.py` | ✅ |
| `benchmarks/persona_consistency.py` | ✅ |
| `locustfile.py` | ✅ |
| `mkdocs.yml` | ✅ |
| `docs/index.md` | ✅ |
| `docs/quickstart.md` | ✅ |
| `docs/hardware_profiles.md` | ✅ |
| `docs/api.md` | ✅ |
| `CHANGELOG.md` | ✅ |
| `MODEL_CARD.md` | ✅ |
| `pyproject.toml` — version 0.1.0 → 1.0.0 | ✅ |
| `tests/test_phase6_integration.py` | ✅ |
| `tests/test_phase6_adversarial.py` | ✅ |
| `tests/test_phase6_release.py` | ✅ |

---

## Module Descriptions

### `benchmarks/benchmark_profiles.py`
- `BenchmarkQuery` — query text + expected topic + min word count
- `BenchmarkResult` — per-profile metrics: citation_accuracy, avg_response_words,
  avg_latency_ms, token_efficiency, enforcement_pass_rate, quality_summary
- `ProfileBenchmark` — `run(profile_id, queries=None, core=None) -> BenchmarkResult`
  Uses ThoughtForgeCore in no-model mode; records latency, citation hits,
  enforcement status per query

### `benchmarks/persona_consistency.py`
- `ConsistencyResult` — consistency_score, total_turns, flagged_turns,
  generic_phrase_hits, norse_tone_hits, citation_turns, summary
- `PersonaConsistencyScorer` — `score(responses: list[str]) -> ConsistencyResult`
  Checks for hard generic AI phrases (penalty), Norse/Skald tone markers (bonus),
  citation presence (bonus). Designed to validate the Skald persona across 100+ turns.
- `GENERIC_PHRASES` — list of phrases that break character (as an AI, I cannot, etc.)
- `NORSE_TONE_MARKERS` — tone words that reinforce persona

### `locustfile.py`
- `ThoughtForgeUser(HttpUser)` — Locust load test user
  Simulates concurrent `think()` calls via HTTP interface
  Tasks: single query, multi-turn conversation, knowledge-only mode

### MkDocs site
- `mkdocs.yml` — Material theme, nav structure, plugins
- `docs/index.md` — Project vision, pillars, quick start command
- `docs/quickstart.md` — Step-by-step 5-minute setup
- `docs/hardware_profiles.md` — All 6 profiles with specs
- `docs/api.md` — API reference for key classes

---

## Test Strategy

### `tests/test_phase6_integration.py`
- Full `think()` pipeline end-to-end (no DB fallback)
- FinalResponseRecord completeness (all fields present)
- Multi-call stability (same core, 3 consecutive calls)
- Knowledge-only mode returns valid text
- `enforcement_passed` always bool, `enforcement_notes` always str

### `tests/test_phase6_adversarial.py`
- Empty string input → no crash, valid FinalResponseRecord
- All-whitespace input → handled gracefully
- Very long query (2000+ chars) → no crash
- SQL injection string → treated as plain text (no crash)
- Unicode + emoji query → no crash
- Repeated identical query → stable output
- Query with hallucinated QIDs → enforcement gate catches
- Genericness phrases in synthetic response → EnforcementGate flags

### `tests/test_phase6_release.py`
- mkdocs.yml valid YAML + required keys
- CHANGELOG.md mentions v1.0.0
- pyproject.toml version == 1.0.0
- MODEL_CARD.md exists and non-empty
- BenchmarkResult dataclass fields + score ranges
- ConsistencyResult dataclass fields + score range
- PersonaConsistencyScorer returns valid result on sample data
- locustfile.py exists and importable structure check

---

## Next

v1.0 is the milestone — public demo + benchmark report.
After Phase 6: tag v1.0.0, push to main, create GitHub release.
