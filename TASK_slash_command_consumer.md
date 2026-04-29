# TASK — Slash-Command Plugin Hook + `slash list` Consumer

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `94abcf3` — exec wiring closeout.

---

## Why this slice

The runtime subpackage holds two foundation primitives — `slash_commands` (catalog) and `source_info` (provenance) — both unconsumed. This slice gives them a real consumer:

1. A new plugin discovery method `slash_commands()` that lets plugins contribute `SlashCommandInfo` entries.
2. A new `mythic-vibe slash list` CLI command that shows builtin + contributed slash commands.

The plugin discovery method is **not** an event hook (`PLUGIN_HOOKS` are observation hooks, fired when something happens). It's a separate one-shot discovery convention — the dispatcher reads it once at `load_and_subscribe` time.

## Goal

Land:

1. `mythic_vibe_cli/plugins/dispatcher.py` — new `discover_slash_commands()` method on `PluginHookDispatcher`
2. `mythic_vibe_cli/commands.py` — `cmd_slash_list(args)` and `cmd_slash_dispatch(args)`
3. `mythic_vibe_cli/app.py` — argparse for `slash list`
4. Tests covering dispatcher discovery + CLI command behavior
5. Update `docs/plugins.md` worked example to show `slash_commands()`
6. Update `docs/runtime.md` §6 to record that the catalog now has a consumer
7. Update `docs/COMMAND_CONTRACTS.md` and `docs/api.md`
8. CHANGELOG + DEVLOG

## Discovery contract

A plugin may define a callable named `slash_commands` (class method, static method, or module-level function — any callable accessed via `getattr(plugin_obj, "slash_commands", None)` and `callable()` check works). When called with no arguments, it returns an iterable of `SlashCommandInfo` instances. The dispatcher aggregates results across all loaded plugins.

If the method raises, the error is caught and logged to stderr (matching the bus contract), and the plugin contributes nothing.

If the method returns something other than an iterable of `SlashCommandInfo`, items that fail `isinstance` are skipped silently.

## CLI command contract

```bash
mythic-vibe slash list [--path .] [--json] [--source builtin|extension|prompt|skill|plugin]
```

- Default human output: prints builtin entries, then contributed entries grouped by source.
- JSON output: `{command, path, builtin: [...], contributed: [...]}` where each entry is the dataclass `to_dict()` form.
- `--source builtin` shows only `BUILTIN_SLASH_COMMANDS` (skips plugin discovery).
- `--source <other>` filters contributed entries by source.

## Out of scope

- A REPL or TUI surface that actually dispatches the listed commands
- Dispatching slash commands from existing CLI (sub-commands stay sub-commands)
- Allowing plugins to override builtin command behavior
- Persisting contributed slash commands to disk

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/plugins/dispatcher.py` | Add `discover_slash_commands()` |
| `mythic_vibe_cli/commands.py` | Add `cmd_slash_list`, `cmd_slash_dispatch`; register handler |
| `mythic_vibe_cli/app.py` | Argparse for `slash list` |
| `tests/test_plugin_dispatcher.py` | Add discovery tests |
| `tests/test_cli_kernel.py` | Add `slash list` integration tests |
| `docs/plugins.md` | Add `slash_commands()` to the worked example; cross-link to `slash list` |
| `docs/runtime.md` | Update §6 (slash_commands wired into) and at-a-glance table |
| `docs/COMMAND_CONTRACTS.md` | Add `slash list` contract |
| `docs/api.md` | Add `slash list` cross-link |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [x] Add `discover_slash_commands` to dispatcher (with exception isolation matching bus contract)
- [x] Add `cmd_slash_list` + `cmd_slash_dispatch` (with `--source builtin` short-circuit to skip plugin loading)
- [x] Add `slash list` argparse (with constrained `--source` choices)
- [x] Update `test_command_registry_preserves_current_commands_and_aliases` to include `slash`
- [x] Dispatcher tests — 4 cases (aggregates, skips missing, isolates exceptions + sibling continues, filters non-SlashCommandInfo items)
- [x] CLI-kernel tests — 4 cases (builtin listing, --source builtin short-circuit, plugin contribution end-to-end, --source plugin narrows)
- [x] `pytest -q` green — 227 passed, 14 subtests passed
- [x] `ruff` + `mypy` green
- [x] Update docs/plugins.md worked example (added slash_commands() to AuditPlugin) + new §9 + renumber
- [x] Update docs/runtime.md §6 wiring + table entries (no longer "no consumer yet")
- [x] Update docs/COMMAND_CONTRACTS.md and docs/api.md
- [x] CHANGELOG entry
- [x] DEVLOG entry with continuity thread
- [x] Memory snapshot updated
- [x] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. `discover_slash_commands` is a separate convention from `PLUGIN_HOOKS` — don't add `slash_commands` to `PLUGIN_HOOKS`.
3. Use the same exception-isolation contract as the bus: catch exceptions from plugin's `slash_commands()`, log to stderr, continue.
4. The `--source builtin` shortcut should skip plugin loading entirely (no plugin loading cost when only builtins are wanted).
