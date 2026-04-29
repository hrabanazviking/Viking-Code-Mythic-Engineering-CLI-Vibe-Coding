# TASK — Pi Plunder Slice 3: Event Bus

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor slices:** `549c8a1` (file-mutation-queue), `0ae9d54` (output-guard), `c150359` (wiring).

---

## Why this primitive next

The runtime subpackage now holds two safety primitives — both wired and active. The next foundation is the event bus: pi's internal coordination layer that lets ~30 core modules emit and listen on a shared bus instead of calling each other directly.

From the Pi guide section 6.8:

> *"Mythic's command surface has not yet needed this, but as the workflow runner grows, an event bus is the right shape for `before_*` / `after_*` plugin hooks, telemetry, and live-status panels."*

Mythic's `plugins/api.py` already declares `before_scan` / `after_scan` / `before_packet` / `after_packet` / `before_verify` / `after_verify` / `before_reflect` / `after_reflect` hook names — but they are name declarations only, no emitter exists. The event bus is the natural emitter. Landing it now means the next wiring slice can dispatch real events through the declared hooks without inventing the dispatch primitive at the same time.

## Goal

Land:

1. `mythic_vibe_cli/runtime/event_bus.py` — Python port of pi's `src/core/event-bus.ts`
2. Update `mythic_vibe_cli/runtime/__init__.py` to re-export the public surface
3. `tests/test_event_bus.py` — unit tests (no analog exists upstream)
4. Plunder map row in `THIRD_PARTY_NOTICES.md`
5. Per-file Pi attribution header on the new module
6. CHANGELOG Unreleased entry
7. DEVLOG entry with continuity thread

## Public surface (Python translation)

| pi (TS) | mythic (Py) | Notes |
|---|---|---|
| `EventEmitter` | `EventBusController` class | Internal — wraps a per-channel handler dict |
| `EventBus` interface | `EventBus` Protocol | Public `emit` + `on` |
| `createEventBus()` | `create_event_bus()` | Factory returning `EventBusController` |
| `bus.emit(channel, data)` | `bus.emit(channel, data)` | Synchronous (Python) |
| `bus.on(channel, handler)` | `bus.on(channel, handler)` | Returns `unsubscribe()` callable |
| `bus.clear()` | `bus.clear()` | Removes all handlers |
| `console.error` on handler error | `traceback.print_exc(file=sys.stderr)` | Match pi's "log + continue, never crash the bus" contract |

Pi uses async handlers because Node is async-first. We use sync handlers because the Mythic codebase is sync throughout. A future async layer can extend the bus (or wrap handlers) without breaking the sync contract.

## Out of scope

- Wiring the bus into `cmd_*` handlers or `plugins/api.py` — separate slice
- Wildcard subscriptions, namespacing, or priority ordering — pi doesn't have these and we don't need them
- Async handler support — defer until provider execution arrives
- Persistence / replay of past events — out of scope

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/runtime/event_bus.py` | NEW (Python port + Pi attribution header) |
| `mythic_vibe_cli/runtime/__init__.py` | Re-export `create_event_bus`, `EventBus`, `EventBusController` |
| `tests/test_event_bus.py` | NEW (unit tests; no upstream analog) |
| `THIRD_PARTY_NOTICES.md` | Append plunder map row |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New 2026-04-29 entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Port `event_bus.py`
- [ ] Update `runtime/__init__.py` re-exports
- [ ] Write tests (subscribe/emit/multi-handler/channel-isolation/unsubscribe/error-containment/clear/threading)
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
2. The Python port is sync-only; pi's async wrapper around handlers is replaced by a try/except that prints the traceback to stderr and continues.
3. Use `threading.Lock` for thread-safety — the bus may be hit from multiple threads even though most of our code is single-threaded today.
4. Snapshot handlers before iterating in `emit()` so a handler that unsubscribes itself doesn't break iteration mid-emit.
5. Pi's `console.error("Event handler error (channel):", err)` translates to `print(..., file=sys.stderr)` plus `traceback.print_exc(file=sys.stderr)` — preserve the channel name in the error line.
