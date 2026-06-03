# TASK — Pi Plunder Slice 6: Source-Info Companion

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `faac5e5` — slash-commands catalog (which left `source_info: str` as a deferred detail).

---

## Why this primitive next

In the slash-commands slice, I noted: *"pi's `SourceInfo` is richer than we need; we use `source_info: str` for now."* That deferred detail is closable now. Pi's `core/source-info.ts` is 852 bytes and has one foreign import (`PathMetadata` from `package-manager.js`). We can port the **synthetic factory** path cleanly without touching `package-manager.ts`, then upgrade `SlashCommandInfo.source_info` from `str` to the real `SourceInfo` type.

This makes the runtime subpackage tighter: extension/skill/prompt/plugin-contributed commands now carry structured source provenance, not opaque strings.

## Goal

Land:

1. `mythic_vibe_cli/runtime/source_info.py` — Python port of pi's `core/source-info.ts` (synthetic factory only)
2. Update `mythic_vibe_cli/runtime/slash_commands.py` so `SlashCommandInfo.source_info` is `SourceInfo` instead of `str`
3. Update `mythic_vibe_cli/runtime/__init__.py` re-exports
4. `tests/test_source_info.py` — new unit tests
5. Update `tests/test_slash_commands.py` — adjust the `SlashCommandInfo` construction test
6. Plunder map row in `THIRD_PARTY_NOTICES.md`
7. Per-file Pi attribution header on the new module
8. CHANGELOG Unreleased entry
9. DEVLOG entry

## Design adaptations

Pi-specific concepts:

- `PathMetadata` from `package-manager.js` — pi's plugin-package locator. We don't have an analog and aren't porting `package-manager.ts`.
- The `create_source_info(path, metadata)` factory unpacks `PathMetadata` fields. We omit this factory; instead the only port is `create_synthetic_source_info` which takes explicit params.

Mythic adaptation:

- Rename `create_synthetic_source_info` to `synthetic_source_info` (Python convention)
- Use `dataclass(frozen=True)` for `SourceInfo`
- Keep `SourceScope = Literal["user", "project", "temporary"]` and `SourceOrigin = Literal["package", "top-level"]` matching pi exactly

## Out of scope

- Porting `package-manager.ts` (multi-slice arc; pi-specific concept)
- Wiring `SourceInfo` into any `cmd_*` site (no consumer exists yet)
- Migrating `BUILTIN_SLASH_COMMANDS` entries to carry source info (they're builtin-typed; only contributed commands carry SourceInfo)

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/runtime/source_info.py` | NEW (port, synthetic factory only) |
| `mythic_vibe_cli/runtime/slash_commands.py` | `SlashCommandInfo.source_info` typed as `SourceInfo` |
| `mythic_vibe_cli/runtime/__init__.py` | Re-export `SourceInfo`, `SourceScope`, `SourceOrigin`, `synthetic_source_info` |
| `tests/test_source_info.py` | NEW |
| `tests/test_slash_commands.py` | Update `SlashCommandInfo` construction test to use `SourceInfo` |
| `THIRD_PARTY_NOTICES.md` | Append plunder map row |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [x] Port `source_info.py` (synthetic factory only; PathMetadata-dependent factory deliberately skipped)
- [x] Update `slash_commands.py` to use `SourceInfo` (one type annotation + `to_dict` nesting via `SourceInfo.to_dict`)
- [x] Re-export from `runtime/__init__.py` (`SourceInfo`, `SourceScope`, `SourceOrigin`, `synthetic_source_info`)
- [x] Write source-info unit tests — 6 cases (default scope/origin, overrides, to_dict omit/include base_dir, immutability, return type)
- [x] Update slash-commands tests — 2 adjusted cases that construct via `synthetic_source_info` and assert nested `to_dict` shape
- [x] `pytest -q` green — 210 passed, 14 subtests passed
- [x] `ruff` + `mypy` green — 60 source files
- [x] Plunder map row added (production + tests; 10 rows total now)
- [x] Per-file Pi attribution header
- [x] CHANGELOG entry
- [x] DEVLOG entry with continuity thread
- [x] Memory snapshot updated
- [x] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. Don't port `create_source_info(path, metadata)` — the `PathMetadata` dep is not portable in this slice.
3. The Python factory becomes a regular function `synthetic_source_info(...)` returning a frozen `SourceInfo` dataclass instance.
4. The slash-commands upgrade is tiny — one type annotation change + one test-construction update.
