# Plugins

This guide shows how to write a Mythic Vibe CLI plugin — a small Python class or module that observes the CLI's life-cycle events as they happen.

The plugin layer is built on a synchronous event bus and a per-invocation dispatcher. Subscribed plugins receive events for every meaningful life-cycle moment: scan, packet, verify, reflect. A plugin can audit, log, mirror, or react — but it cannot mutate the CLI's behavior.

---

## 1) What a plugin is

A Mythic plugin is **a Python class or module that exposes one or more hook methods**. The CLI loads enabled plugins from `mythic/plugins.json` (managed via `mythic-vibe grimoire add`), looks for callable attributes named after the eight supported hooks, and subscribes them to a fresh event bus before each command runs the work that triggers events.

What plugins can do:

- observe every `before_*` and `after_*` event
- run side effects (write files, append to a log, post to a service, mirror to telemetry)
- read the project tree, the CLI's persisted state, or any normal Python data

What plugins cannot do (by current contract):

- mutate the payload an emitter sends to the next subscriber
- abort or replace the work being announced
- block the dispatch — handlers are called synchronously and quickly
- replace any Mythic command handler
- assume async execution; the dispatcher is sync and there is no asyncio loop

If a plugin handler raises, the bus logs the channel name and traceback to stderr and continues with the remaining subscribers. A buggy plugin never crashes the command.

---

## 2) The eight hooks

Hook names are declared in `mythic_vibe_cli.plugins.api.PLUGIN_HOOKS`. Each hook has a `before_*` and `after_*` form that receives a single payload argument — a small dict with stable keys.

| Hook | Emitter | Payload (representative) |
|---|---|---|
| `before_scan` / `after_scan` | `mythic-vibe scan` (real-work path; dry-run skips) | `{path, changed_only, docs_only, include_patterns, exclude_patterns}` (`after_` adds `index_path` and scalar counts) |
| `before_packet` / `after_packet` | `mythic-vibe packet create` (and `evoke` / `codex-pack` aliases), `mythic-vibe packet ingest`, `mythic-vibe workflow plan --packets` step loop (real-work path; dry-run skips) | `{source, path, phase, role, task, audience, format}` (`after_` adds `packet_id`, `packet_path`; ingest adds `ingest_source`; workflow adds `workflow_id`, `workflow_step_id`) |
| `before_verify` / `after_verify` | `mythic-vibe verify` | `{path, selected: {commands, changed_files, docs, invariants}}` (`after_` adds `result`, `level`, `verification_id`, `artifact_path`, `errors_count`, `warnings_count`, `blocked_count`) |
| `before_reflect` / `after_reflect` | `mythic-vibe reflect` (real-work path; dry-run skips) | `{path, summary, next_step, note}` (`after_` adds `handoff_id`, `json_path`, `markdown_path`, `next_recommended_action`) |

For the canonical and always-up-to-date payload shape, see [`docs/COMMAND_CONTRACTS.md`](COMMAND_CONTRACTS.md) under "Current plugin hook dispatch."

---

## 3) A complete worked example

A plugin module can be either a class with hook methods, or a module-level set of hook functions. Both shapes work. The class form is the most common.

Save this as `audit_plugin.py` somewhere on your `PYTHONPATH` (e.g., your project root or a directory you'll add via `PYTHONPATH=...:$PYTHONPATH`):

```python
# audit_plugin.py
"""Append-only audit log for Mythic life-cycle events."""

from datetime import datetime, timezone
from pathlib import Path


class AuditPlugin:
    """Records every life-cycle event the CLI emits to an append-only log."""

    LOG_NAME = "mythic-audit.log"

    @classmethod
    def _emit(cls, channel: str, payload: dict) -> None:
        log_path = Path(payload.get("path", ".")) / "mythic" / cls.LOG_NAME
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{timestamp} {channel} {payload}\n")

    # Scan
    @classmethod
    def before_scan(cls, payload):
        cls._emit("before_scan", payload)

    @classmethod
    def after_scan(cls, payload):
        cls._emit("after_scan", payload)

    # Packet
    @classmethod
    def before_packet(cls, payload):
        cls._emit("before_packet", payload)

    @classmethod
    def after_packet(cls, payload):
        cls._emit("after_packet", payload)

    # Verify
    @classmethod
    def before_verify(cls, payload):
        cls._emit("before_verify", payload)

    @classmethod
    def after_verify(cls, payload):
        cls._emit("after_verify", payload)

    # Reflect
    @classmethod
    def before_reflect(cls, payload):
        cls._emit("before_reflect", payload)

    @classmethod
    def after_reflect(cls, payload):
        cls._emit("after_reflect", payload)
```

The plugin only needs to define methods for the hooks it cares about. Omitted methods are simply not subscribed.

A minimal single-hook plugin is just as valid:

```python
# scan_telemetry.py
class ScanTelemetry:
    @classmethod
    def after_scan(cls, payload):
        print(f"[telemetry] scan finished: {payload['languages']} languages, {payload['changed_files']} changed files")
```

---

## 4) Registering a plugin

Plugins are recorded in `mythic/plugins.json` (the "grimoire"). Use `mythic-vibe grimoire add` to register one:

```bash
mythic-vibe grimoire add audit_plugin:AuditPlugin
mythic-vibe grimoire list
```

The entrypoint is `module:object`. The module must be importable by the Python interpreter running the CLI — that is, it must be on `sys.path` or installed as a package.

To verify a registered plugin imports cleanly and exposes the expected hooks:

```bash
mythic-vibe plugin inspect --entrypoint audit_plugin:AuditPlugin --json
```

This returns plugin health (status, errors, warnings) and the list of hooks the plugin actually exposes. A registry record can declare `hooks: [...]`; if the plugin's resolved object has additional callable hook attributes, those are also subscribed at dispatch time.

To pause a plugin without removing it:

```bash
mythic-vibe plugin disable audit_plugin:AuditPlugin
```

Disabled plugins remain in the registry but are skipped during dispatcher subscription. Re-enable by editing `mythic/plugins.json` and toggling `enabled` back to `true`.

---

## 5) Watching it work

With the audit plugin from §3 registered, run a real command:

```bash
mythic-vibe scan --path .
mythic-vibe packet create --task "Demo task" --phase build --role "Forge Worker" --path .
mythic-vibe verify --path . --commands
mythic-vibe reflect --summary "Demo session"
```

Then look at `mythic/mythic-audit.log`:

```text
2026-04-29T12:00:00+00:00 before_scan {'path': '.../project', 'changed_only': False, ...}
2026-04-29T12:00:00+00:00 after_scan {'path': '.../project', 'index_path': '.../project/mythic/project_index.json', 'changed_files': 3, ...}
2026-04-29T12:00:01+00:00 before_packet {'source': 'packet create', 'path': '.../project', 'phase': 'build', 'role': 'Forge Worker', ...}
2026-04-29T12:00:01+00:00 after_packet {'source': 'packet create', ..., 'packet_id': 'PKT-000001', 'packet_path': '.../project/mythic/packets/PKT-000001.md'}
...
```

Eight events, four life-cycle pairs, one append-only log.

---

## 6) Constraints and contracts

These are the rules the dispatcher and bus enforce or assume:

1. **Synchronous only.** Hook methods run on the main thread. Don't use `async def`. Don't sleep, don't make slow network calls inline — they will block the command.
2. **Exceptions are isolated.** If your hook raises, the channel name and traceback go to stderr and the dispatcher continues to the next subscribed plugin. The command itself is not interrupted. Use this for hardening, not as a control-flow mechanism.
3. **Payloads are read-only by convention.** The dispatcher does not deep-copy the payload between subscribers (it does snapshot the handler list before iterating, so unsubscribing during dispatch is safe). Treat the dict as immutable; mutating it is undefined behavior across plugin order.
4. **No monkey-patching.** Plugins must not replace functions in `mythic_vibe_cli.*` or other plugins' modules. The dispatcher gives you observation, not interception.
5. **Per-invocation lifecycle.** A fresh `PluginHookDispatcher` is created for each command run, plugins are loaded, hooks fire, plugins are torn down. Module-level state in your plugin persists across runs (Python imports cache); per-run state should live on the payload's `path` key (typically the project state under `mythic/`).
6. **Dry-run skips emission.** Commands with `--dry-run` do not emit any plugin hooks. This is intentional — observers should only see real work.

---

## 7) Loading model details

When a command runs:

1. The command constructs a `PluginHookDispatcher(root)`.
2. `dispatcher.load_and_subscribe()` reads `mythic/plugins.json` via `PluginRegistry`, filters to enabled plugins, imports each `module:object` entrypoint, and for every name in `PLUGIN_HOOKS` checks whether `getattr(plugin_obj, name, None)` is callable. Callable attributes are subscribed.
3. Plugins whose entrypoints fail to import are skipped silently. Investigate failures via `mythic-vibe plugin inspect --entrypoint module:object`.
4. The command emits `before_*` events at the top of its real-work block and `after_*` events after the work resolves.
5. `dispatcher.teardown()` (or the context-manager exit) unsubscribes every handler this dispatcher registered.

The plugin module is imported through Python's normal import system. If you keep your plugin alongside the project, prepend the project root to `PYTHONPATH`:

```bash
PYTHONPATH="$(pwd):$PYTHONPATH" mythic-vibe scan --path .
```

If you publish your plugin as a package (e.g., `pip install my-mythic-plugin`), no `PYTHONPATH` work is needed.

---

## 8) When to write a plugin

Plugins are for **observation and side effects**. Reach for one when you want to:

- mirror packet creation to a separate audit store
- emit telemetry to your team's monitoring service
- maintain a `last_run.json` cache that other tools can poll
- alert when verification fails or is blocked
- archive every reflect handoff to long-term storage
- gate downstream automation on `after_verify` results

Don't reach for a plugin when you want to:

- change the rendered packet content (use packet templates instead, or fork the packet builder)
- block a command (the dispatcher does not give you veto power)
- replace a `cmd_*` handler (extend the command surface itself)
- make a network call slower than ~50 ms inline (queue work to a separate process; emit a marker event from the queue worker)

---

## 9) See also

- [`docs/COMMAND_CONTRACTS.md`](COMMAND_CONTRACTS.md) — canonical payload shapes per emitter
- [`docs/api.md`](api.md) — `plugin list|inspect|disable` and `grimoire` command surfaces
- `mythic_vibe_cli/plugins/api.py` — `PLUGIN_HOOKS` declaration, `PluginRecord`, `PluginHealth`
- `mythic_vibe_cli/plugins/dispatcher.py` — the dispatcher implementation
- `mythic_vibe_cli/runtime/event_bus.py` — the underlying sync event bus
- `mythic_vibe_cli/plugins/loader.py` — `inspect_plugin` source for the `plugin inspect` command
- `tests/test_plugin_dispatcher.py` — runnable specs for dispatcher behavior

The plugin layer is intentionally minimal. The bus is small, the dispatcher is small, the contract is small — three constraints (sync, isolated, read-only payloads) keep it maintainable as the rest of the CLI grows.
