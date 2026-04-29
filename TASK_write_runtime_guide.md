# TASK — Operator-Facing Runtime Guide

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `dcd9986` — sixth runtime primitive (source-info closeout).

---

## Why this slice

The runtime subpackage is six primitives deep and stable enough to document. Mirrors the slot left by `docs/plugins.md`: a single operator-facing page that explains what each primitive does, when to reach for it, and how the primitives compose. Without this page, the runtime surface exists in code but not in a reader's mental model.

## Goal

Land `docs/runtime.md` modelled on `docs/plugins.md` — concise, anchored sections, runnable code where useful, cross-links to canonical sources.

## Sections

1. **Overview** — what `mythic_vibe_cli.runtime` is, what it isn't
2. **The six primitives at a glance** — one-line summary table
3. **`file_mutation_queue`** — per-path mutation safety, usage, when to reach
4. **`output_guard`** — stdout cleanliness, when active, idempotent contract
5. **`event_bus`** — sync publish/subscribe, usage, exception isolation
6. **`timings`** — `MYTHIC_TIMING=1` profiling, sample output, no-op when disabled
7. **`slash_commands`** — typed catalog, what's in `BUILTIN_SLASH_COMMANDS`, when consumers will appear
8. **`source_info`** — provenance for contributed artifacts, scope/origin semantics
9. **Composition patterns** — examples of combining primitives (queue inside a guarded JSON command, bus emitting timed events, etc.)
10. **Constraints and contracts** — sync-only, no monkey-patching, payload immutability
11. **See also** — cross-links

## Out of scope

- New code
- New primitives
- Wiring suggestions for unwired primitives (slash-commands, source-info)

## Files to Touch

| File | Change |
|---|---|
| `docs/runtime.md` | NEW |
| `docs/INDEX.md` | Add link under Operator Docs |
| `docs/plugins.md` | Cross-link to `docs/runtime.md` from §6 (constraints) and §9 (see also) where the bus / dispatcher are mentioned |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Draft `docs/runtime.md`
- [ ] Add INDEX.md link
- [ ] Cross-link from `docs/plugins.md`
- [ ] Validate code snippets compile (paste-and-run sanity)
- [ ] CHANGELOG entry
- [ ] DEVLOG entry
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. Voice and shape mirror `docs/plugins.md` — prose concise, sections short, examples runnable.
3. Don't reproduce the canonical interface contracts that already live in the docstrings; link to source files.
4. Length target: ~300 lines.
