# TASK — Pi Plunder Slice 5: Slash-Commands Catalog

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor slices:** queue / guard / bus / timings — all four prior runtime primitives wired.

---

## Why this primitive next

Pi's `core/slash-commands.ts` is a typed **catalog** of slash command names and descriptions, plus a type backbone for extension/skill/prompt-contributed commands. Pi's TUI and SDK both consume this catalog — the same `/foo` works in interactive mode and via the SDK because the catalog is separated from the dispatcher.

Mythic does not have a TUI or REPL today. But the runtime subpackage already holds queue / guard / bus / timings — when a REPL or TUI lands (V2 Phase 3), having a pre-existing catalog with type system saves us from inventing it under deadline.

**Honest scope note:** this is a *typed catalog*, not a runtime dispatcher. The slice is small (~80 lines + tests). The plunder value is the separation-of-concerns pattern, not heavy logic. I'm landing it as a foundation for future REPL/TUI work, not because it's load-bearing today.

## Goal

Land:

1. `mythic_vibe_cli/runtime/slash_commands.py` — Python port of the pi catalog
2. Update `mythic_vibe_cli/runtime/__init__.py` re-exports
3. `tests/test_slash_commands.py` — unit tests on the catalog shape, uniqueness, source enum
4. Plunder map row in `THIRD_PARTY_NOTICES.md`
5. Per-file Pi attribution header
6. CHANGELOG Unreleased entry
7. DEVLOG entry

## Design adaptations

Pi-specific concepts that don't translate directly:

- pi has `scoped-models`, `share`, `tree`, `clone`, `fork`, `compact` — most are session/model concepts Mythic doesn't have
- pi imports `APP_NAME` from `../config.js` for the `quit` description; we hardcode "Mythic Vibe CLI"
- pi's `SourceInfo` is richer than we need; we use `source_info: str` for now

Mythic-relevant pre-populated builtins:

- `help`, `status`, `scan`, `packet`, `verify`, `reflect`, `resume`
- `method`, `handoff`, `workflow`, `plugin`, `grimoire`
- `reload`, `quit`

`SlashCommandSource` literal extends pi's `"extension" | "prompt" | "skill"` with `"plugin"` since we have a plugin layer pi doesn't have an analog of.

## Out of scope

- A runtime dispatcher (no REPL/TUI exists yet to consume one)
- Wiring slash commands into existing CLI sub-commands (the sub-command surface is already mature)
- Extension-contributed command resolution (pi defers to the TUI layer; we do too)
- Migration of legacy command names

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/runtime/slash_commands.py` | NEW (Python port + Pi attribution header) |
| `mythic_vibe_cli/runtime/__init__.py` | Re-export catalog + types |
| `tests/test_slash_commands.py` | NEW |
| `THIRD_PARTY_NOTICES.md` | Append plunder map row |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New 2026-04-29 entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Port `slash_commands.py`
- [ ] Update `runtime/__init__.py` re-exports
- [ ] Write tests (catalog shape, name uniqueness, source enum, info dataclass round-trip)
- [ ] `pytest -q` green
- [ ] `ruff` + `mypy` green
- [ ] Plunder map row added
- [ ] Per-file Pi attribution header
- [ ] CHANGELOG entry
- [ ] DEVLOG entry
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. The file is a *catalog only*. Resist adding a dispatcher — that's a TUI-consumer concern.
3. The Mythic builtin list should mirror our existing sub-command names so a future REPL feels consistent.
4. Use `Literal["extension", "prompt", "skill", "plugin"]` for the source enum so mypy can check call sites.
