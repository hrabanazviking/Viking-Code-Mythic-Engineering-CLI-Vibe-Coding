# TASK — Wire Event Bus to Plugin Hooks via Dispatcher

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `0acf784` — event-bus plunder slice.

---

## Why this slice

`mythic_vibe_cli/plugins/api.py` already declares eight hook names — `before_scan`, `after_scan`, `before_packet`, `after_packet`, `before_verify`, `after_verify`, `before_reflect`, `after_reflect`. They have been declarations only; no emitter exists. The newly-landed event bus is the natural emitter.

This slice adds a `PluginHookDispatcher` that loads enabled plugins, subscribes their methods to a fresh per-invocation event bus, and exposes an `emit()` surface for command code. The first emitter wired through is `cmd_scan` — emitting `before_scan` and `after_scan` around the existing scan logic. Other commands (`packet create`, `verify`, `reflect`) get wired in subsequent slices so each slice stays small.

## Goal

Land:

1. `mythic_vibe_cli/plugins/dispatcher.py` — `PluginHookDispatcher` class
2. `mythic_vibe_cli/plugins/__init__.py` — re-export `PluginHookDispatcher`
3. `mythic_vibe_cli/commands.py` — wire dispatcher into `cmd_scan` (skipping dry-run path)
4. `tests/test_plugin_dispatcher.py` — unit tests on the dispatcher
5. `tests/test_cli_kernel.py` — integration test: synthetic plugin receives both events from `cmd_scan`
6. CHANGELOG Unreleased entry
7. DEVLOG entry with continuity thread

## Dispatcher contract

```python
class PluginHookDispatcher:
    def __init__(self, root: Path, *, bus: EventBusController | None = None): ...
    def load_and_subscribe(self) -> int:  # returns count of subscribed plugins
        # Loads enabled plugins from PluginRegistry, finds before_*/after_* methods,
        # subscribes them to the bus. Plugins that fail to import are skipped silently
        # (best-effort) so a single broken plugin never breaks every command.
    def emit(self, hook: str, payload: object) -> None:
        # Validates the hook name is in PLUGIN_HOOKS; emits via the bus.
    def teardown(self) -> None:
        # Unsubscribes every handler this dispatcher registered, clears the loaded list.
    def __enter__(self) -> "PluginHookDispatcher": ...  # convenience
    def __exit__(self, *exc): ...
```

The handler-finding rule:

- For each enabled plugin record, import the module and resolve the entrypoint object.
- For each name in `PLUGIN_HOOKS`, if `getattr(plugin_obj, name, None)` is callable, subscribe it.
- Class-style and module-style plugins both work: a class with `before_scan(self, payload)` is treated the same as a module-level `before_scan(payload)` callable when the plugin is the class instance vs the module.

## cmd_scan emission contract

Emit only on the real-work path (skip dry-run):

```python
with PluginHookDispatcher(root) as dispatcher:
    dispatcher.load_and_subscribe()
    dispatcher.emit("before_scan", {"path": str(root), "changed_only": ..., "docs_only": ...})
    index = indexer.build(...)
    dispatcher.emit("after_scan", {"path": str(root), "index_path": str(indexer.index_path), "summary": <small dict>})
```

Payload is a small dict with stable keys. Plugins may inspect but not mutate.

## Out of scope

- Wiring `before_packet`/`after_packet` into `packet create` (multiple call sites — separate slice)
- Wiring verify/reflect hooks (separate slices)
- Async plugin handlers
- Plugin signing or sandboxing beyond inspection
- Cross-command bus persistence

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/plugins/dispatcher.py` | NEW |
| `mythic_vibe_cli/plugins/__init__.py` | Re-export `PluginHookDispatcher` |
| `mythic_vibe_cli/commands.py` | Wire dispatcher into `cmd_scan` |
| `tests/test_plugin_dispatcher.py` | NEW (unit tests) |
| `tests/test_cli_kernel.py` | Integration test with synthetic plugin |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New 2026-04-29 entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Implement `PluginHookDispatcher`
- [ ] Re-export from `plugins/__init__.py`
- [ ] Wire into `cmd_scan`
- [ ] Unit tests (load/subscribe, missing entrypoint, disabled plugin, hook name guard, emit, teardown, context manager)
- [ ] Integration test (synthetic plugin receives before_scan + after_scan during cmd_scan)
- [ ] `pytest -q` green
- [ ] `ruff` + `mypy` green
- [ ] CHANGELOG entry
- [ ] DEVLOG entry
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. The dispatcher is a per-invocation object; do NOT cache it module-globally.
3. Plugins that fail to import are skipped silently — surface via `inspect_plugin` (existing) when the user explicitly asks; do not fail the command.
4. Synthetic plugin tests should write a `test_plugin.py` to a temp dir, prepend the temp dir to `sys.path`, register via `PluginRegistry.add(...)`, then exercise.
