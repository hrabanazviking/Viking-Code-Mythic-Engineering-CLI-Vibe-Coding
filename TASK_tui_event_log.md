# TASK — TUI Slice 1: Event Log + Recent Events Panel

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `2215774` — Textual TUI first slice.

---

## Why this slice

The TUI shows project status snapshot but says nothing about what just happened. A "Recent Events" panel tailing a persistent event log gives glance-able activity feedback. The event bus already fires per-command emissions; we just need to persist them.

## Goal

Land:

1. `mythic_vibe_cli/runtime/event_log.py` — bounded JSONL append-and-tail helper
2. Modify `PluginHookDispatcher.emit()` to also append to the log
3. Add a 5th panel "Recent Events" to `StatusScreen` showing the tail
4. Tests: writer + tail + bounded rotation + panel content
5. Doc updates

## Persistence shape

Path: `mythic/events.jsonl` (relative to project root).

Each line: `{"timestamp": ISO8601, "channel": str, "summary": str}`.

Bounded to 200 entries / ~100KB. When exceeded, rewrite with the last 200 entries.

## Out of scope

- Cross-process sync / file locking (concurrent CLI runs may interleave entries — that's acceptable; the log is best-effort)
- Streaming events to the TUI in real time across processes (auto-refresh is enough)
- Filtering / searching the log
- Replaying past events to subscribers

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/runtime/event_log.py` | NEW |
| `mythic_vibe_cli/runtime/__init__.py` | Re-export |
| `mythic_vibe_cli/plugins/dispatcher.py` | `emit` writes to log |
| `mythic_vibe_cli/tui/app.py` | Add Recent Events panel; auto-refresh |
| `tests/test_event_log.py` | NEW |
| `tests/test_plugin_dispatcher.py` | New test verifying emit writes log |
| `tests/test_tui.py` | Test panel rendering |
| `docs/runtime.md` | Note the event log primitive |
| `docs/plugins.md` | Brief note |
| `CHANGELOG.md` + `DEVLOG.md` |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [x] Implement `event_log.py` (append, tail, atomic rotate via tempfile.mkstemp + os.replace)
- [x] Wire dispatcher emit (best-effort; IO errors swallowed)
- [x] Add Recent Events panel (12 entries newest-first, HH:MM:SS time tokens)
- [x] Tests — 12 new (9 event_log + 1 dispatcher + 2 TUI panel)
- [x] Existing test relaxed (test_scan_changed_only_limits_recommended_context — now allows mythic/ in changed files)
- [x] Gates green — 258 passed, 14 subtests passed; ruff/mypy clean; 65 source files
- [x] Docs (runtime.md table) + CHANGELOG + DEVLOG
- [x] Memory + push
