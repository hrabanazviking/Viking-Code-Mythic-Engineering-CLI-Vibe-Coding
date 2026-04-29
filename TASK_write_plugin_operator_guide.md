# TASK — Operator-Facing Plugin Guide

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `3e6cf52` — closeout of all eight plugin hook emitters.

---

## Why this slice

The wiring is mechanical now: `PluginHookDispatcher` routes events from eight emitter sites to subscribed plugins. What's missing is the operator-facing page that says "here is how you write a plugin" — hook signatures, payload shapes, registration, inspection, the worked example. Without it, the extensibility surface exists in the code but not in the operator's mental model.

## Goal

Land `docs/plugins.md` — a concise operator guide. Style matches the existing operator docs (`docs/quickstart.md`, `docs/INSTALL.md`): bulleted, anchored, runnable examples. Length target: 200-400 lines.

## Sections

1. **Overview** — what a Mythic plugin is, what it can observe, where the dispatch comes from
2. **Hook reference** — the eight names with payload shapes
3. **A complete worked example** — class plugin with all eight hooks, file layout, registration commands
4. **Registration** — `grimoire add` / `plugin list` / `plugin inspect` / `plugin disable`
5. **Constraints** — sync only; exception isolation; no monkey-patching; payload is read-only by convention; per-invocation lifecycle
6. **Loading model** — module-level vs class entrypoints, sys.path requirements, import isolation
7. **Cross-links** — `api.md` plugin section, `COMMAND_CONTRACTS.md` plugin-dispatch section, `dispatcher.py` source

## Out of scope

- Code changes
- Async plugin support
- Plugin signing / sandboxing
- Distribution / packaging story (npm-style ecosystem) — that's V2 Phase 7 territory

## Files to Touch

| File | Change |
|---|---|
| `docs/plugins.md` | NEW |
| `docs/INDEX.md` | Add link under "Operator Docs" |
| `docs/api.md` | Cross-link to plugins.md from the plugin command section |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New 2026-04-29 entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [x] Draft `docs/plugins.md` (9 sections, ~270 lines)
- [x] Add INDEX.md link under Operator Docs
- [x] Cross-link api.md plugin paragraph to the new guide
- [x] Validate code snippets — both example plugins parse as valid Python; CLI command syntax matches actual surface
- [x] CHANGELOG entry
- [x] DEVLOG entry with continuity thread
- [x] Memory snapshot updated
- [x] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. Match the existing operator-docs voice — prose is concise, examples are runnable.
3. Validate code snippets by pasting into a temp dir and running `mythic-vibe grimoire add ...` against them.
4. Don't reproduce the full payload contract from `COMMAND_CONTRACTS.md` — link to it for the canonical version; the guide gets a worked summary.
