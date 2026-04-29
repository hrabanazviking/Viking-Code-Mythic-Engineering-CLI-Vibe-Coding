# TASK — Pi Plunder Slice 1: File Mutation Queue

**Opened:** 2026-04-29
**Owner:** Runa
**TODO source:** Item #15 in `TODO.md` — *"Consult the Pi plundering documents, and begin lawful code plundering of Pi."*
**Plundering guide:** `Pi_Coding_Agent_Plundering_Guide.md` (just landed at `1457b2a`)

---

## Why this primitive first

From the Pi guide's Clean Rule (section 13):

> *"Pi's runtime/services split + compaction branch summarization + tool mutation queue. That trio addresses the three problems that block any serious provider-driven `workflow run`: turn-loop discipline, context-window survival, and write-conflict safety."*

Of those three, the **file mutation queue** is:

- the smallest self-contained primitive (a single TS file)
- the lowest-risk plunder (no entanglement with our existing architecture)
- the most immediately useful (we have file-editing surfaces but zero serialization safety)
- the natural foundation for any future provider-driven `workflow run`

Starting with the queue establishes the legal/attribution discipline (NOTICE, THIRD_PARTY_NOTICES.md, per-file headers) for every subsequent Pi plunder slice.

## Goal

Land:

1. `mythic_vibe_cli/runtime/file_mutation_queue.py` — Python port of pi's `src/core/tools/file-mutation-queue.ts`
2. `mythic_vibe_cli/runtime/__init__.py` — new subpackage marker
3. `tests/test_file_mutation_queue.py` — Python port of pi's `test/file-mutation-queue.test.ts`
4. `THIRD_PARTY_NOTICES.md` — new file with the full upstream MIT text
5. Per-file plunder header on the new Python module
6. CHANGELOG Unreleased entry
7. DEVLOG entry with continuity thread
8. Pi guide checklist tick for the embedded-license duty

## Out of scope

- Wiring the queue into existing tools (`packet create`, `verify`, etc.) — that is a follow-on slice
- Porting any other Pi subsystem (agent-session trio, compaction, tools, RPC, etc.)
- Updating the root README to advertise Pi-derived material until the queue is wired into a real surface
- Modifying `NOTICE` beyond a brief addition — the THIRD_PARTY_NOTICES.md file carries the embedded MIT text

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/runtime/__init__.py` | NEW |
| `mythic_vibe_cli/runtime/file_mutation_queue.py` | NEW (Python port + Pi attribution header) |
| `tests/test_file_mutation_queue.py` | NEW (port of pi tests + a couple Mythic-flavored cases) |
| `THIRD_PARTY_NOTICES.md` | NEW (full upstream MIT text + Pi attribution stanza) |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New 2026-04-29 entry |
| `Pi_Coding_Agent_Plundering_Guide.md` | tick the relevant checklist boxes once landed |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Read pi `src/core/tools/file-mutation-queue.ts`
- [ ] Read pi `test/file-mutation-queue.test.ts`
- [ ] Port queue to Python
- [ ] Port tests to pytest
- [ ] `pytest -q` green
- [ ] `ruff check mythic_vibe_cli tests` green
- [ ] `mypy mythic_vibe_cli` green
- [ ] Create `THIRD_PARTY_NOTICES.md`
- [ ] Per-file Pi attribution header on the Python module
- [ ] CHANGELOG entry
- [ ] DEVLOG entry
- [ ] Pi guide checklist boxes ticked
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. Re-read `Pi_Coding_Agent_Plundering_Guide.md` sections 3 (MIT duties) and 11 (Do/Do-Not) before touching any code.
3. Use `gh api` (no auth issues) to pull pi source files; do NOT clone the repo.
4. Test-port-first per Pi guide section 8: read the `.test.ts` first, capture the spec in pytest skeletons, then implement the Python production code to satisfy that spec.
5. The Python module MUST carry the per-file attribution header from the Pi guide section 3.2.
