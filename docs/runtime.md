# Runtime Primitives

`mythic_vibe_cli/runtime/` holds six small, single-purpose primitives that the rest of the CLI builds on. Each is self-contained, well-tested, and composable. Most are ports of equivalent primitives from [pi-coding-agent](https://github.com/badlogic/pi-mono) (MIT, Copyright (c) 2025 Mario Zechner) — see `THIRD_PARTY_NOTICES.md` for full attribution.

This guide is for developers writing CLI features, plugins, or extensions who want to know what's already available before reaching for `print()`, an ad-hoc lock, or `time.perf_counter()`.

---

## 1) The seven primitives at a glance

| Primitive | One-liner | Wired today |
|---|---|---|
| `file_mutation_queue` | Per-resolved-path serialization for mutation operations | Packet write paths |
| `output_guard` | Reroute `sys.stdout` writes to `sys.stderr` while preserving a "real stdout" path | Every `--json` command |
| `event_bus` | Synchronous publish/subscribe with exception-isolated handlers | `PluginHookDispatcher` |
| `timings` | Lightweight elapsed-time profiling, env-gated | `app.main()` startup boundaries |
| `slash_commands` | Typed catalog of slash command names + sources | Consumed by `mythic-vibe slash list` |
| `source_info` | Provenance dataclass for extension/plugin/skill/prompt-contributed artifacts | Used by `SlashCommandInfo`; surfaced via `mythic-vibe slash list` |
| `exec` | Subprocess execution with timeout and cancel-event | Wired across `verify/test_runner.py`, `verify/git_diff.py`, `handoff.py`, `context/scanner.py` |

All seven are re-exported from `mythic_vibe_cli.runtime` so callers can `from mythic_vibe_cli.runtime import ...` without thinking about submodule paths.

---

## 2) `file_mutation_queue`

**Purpose.** Serialize concurrent writes to the same path so they cannot overlap.

**Public surface.**

- `file_mutation_queue(path)` — context manager
- `with_file_mutation_queue(path, fn)` — functional form

**Usage.**

```python
from mythic_vibe_cli.runtime import file_mutation_queue
from pathlib import Path

target = Path("mythic/state.json")

with file_mutation_queue(target):
    target.write_text("...", encoding="utf-8")
```

Operations on different resolved paths run in parallel. Operations on the same resolved path serialize in arrival order. Symlink aliases that resolve to the same target share one queue.

**When to reach for it.** Any time multiple threads or call sites might write the same file concurrently — packet writers, state writers, manifest updaters. The queue's overhead is negligible (a `threading.Lock` per active path) and its absence shows up later as silent corruption when concurrency lands.

**Source:** `mythic_vibe_cli/runtime/file_mutation_queue.py`

---

## 3) `output_guard`

**Purpose.** When `--json` mode is active, stdout is the protocol surface — only the deliberate JSON payload may land there. The guard installs a `_StderrProxy` into `sys.stdout` so accidental `print()` and third-party library noise route to stderr; deliberate JSON output uses `write_raw_stdout()` to bypass the proxy.

**Public surface.**

- `take_over_stdout()` / `restore_stdout()` — install / uninstall
- `is_stdout_taken_over()` — query state
- `write_raw_stdout(text)` — write to the real stdout regardless of guard state
- `flush_raw_stdout()` — flush the real stdout
- `json_output_guard(active)` — context manager wrapping the install/restore pair

**Usage.**

```python
from mythic_vibe_cli.runtime import json_output_guard, write_raw_stdout

with json_output_guard(active=True):
    print("this lands on stderr")
    write_raw_stdout("this lands on real stdout\n")
```

`mythic_vibe_cli/output.py:write_json` already uses `write_raw_stdout` so deliberate JSON payloads always reach real stdout.

**When to reach for it.** Don't, directly. `app.main()` already wraps every `--json` command with `json_output_guard(args.json)`. The cases where you'd reach for it manually are inside a custom CLI surface (e.g., a future REPL or RPC mode) that needs the same protection.

**Source:** `mythic_vibe_cli/runtime/output_guard.py`

---

## 4) `event_bus`

**Purpose.** Synchronous publish/subscribe coordination. Subscribers register callables on named channels; publishers emit payloads; the bus iterates registered handlers in order, contains exceptions, and never crashes.

**Public surface.**

- `create_event_bus()` → `EventBusController`
- `EventBus` — Protocol (`emit`, `on`)
- `EventBusController` — concrete class with `clear()` admin operation
- `bus.on(channel, handler)` returns an `unsubscribe()` callable
- A handler that raises is logged to stderr (channel + traceback) and never short-circuits subsequent handlers

**Usage.**

```python
from mythic_vibe_cli.runtime import create_event_bus

bus = create_event_bus()
received = []
unsubscribe = bus.on("packet:created", lambda payload: received.append(payload))

bus.emit("packet:created", {"packet_id": "PKT-000001"})
print(received)  # [{"packet_id": "PKT-000001"}]

unsubscribe()
```

**When to reach for it.** When you have a producer (e.g., a command flow) and N consumers (e.g., audit, telemetry, plugin hooks) that should not know about each other. The plugin layer already uses the bus internally via `PluginHookDispatcher`; if you're writing plugin code, you don't touch the bus directly — the dispatcher does it for you.

**Source:** `mythic_vibe_cli/runtime/event_bus.py`

---

## 5) `timings`

**Purpose.** Lightweight elapsed-time profiling for startup, command execution, or any boundary you want to measure. Gated by the `MYTHIC_TIMING` environment variable so unmeasured runs pay zero cost.

**Public surface.**

- `reset_timings()` — clear in-memory list, re-baseline the clock
- `record(label)` — append a labelled millisecond delta since the last `record`
- `print_timings()` — flush a pi-style block to stderr with `TOTAL` footer

When `MYTHIC_TIMING` is unset (the default), all three are no-ops.

**Usage.**

```bash
MYTHIC_TIMING=1 mythic-vibe scan --path .
```

Sample output (to stderr):

```text
--- Mythic Timings ---
  argparse: 27.8ms
  configure_output: 0.0ms
  handler:scan: 142.3ms
  TOTAL: 170.1ms
------------------------
```

The labels record elapsed time at the boundaries of `app.main()`. To add your own timing checkpoints inside a command:

```python
from mythic_vibe_cli.runtime import record

def cmd_my_thing(args):
    record("start of cmd_my_thing")
    do_step_one()
    record("step one done")
    do_step_two()
    record("step two done")
```

The records flow into the same flush that `app.main()` triggers from its `finally` block.

**When to reach for it.** When you need to know where a slow command spent its milliseconds. Sprinkling `record(...)` calls is cheap when disabled and cheap-and-useful when enabled.

**Source:** `mythic_vibe_cli/runtime/timings.py`

---

## 6) `slash_commands`

**Purpose.** Typed catalog of slash command names. The catalog is the single source of truth for "what commands exist" so future REPL, TUI, and SDK surfaces dispatch the same `/foo` consistently.

**Public surface.**

- `BUILTIN_SLASH_COMMANDS` — frozen tuple of `BuiltinSlashCommand` (14 entries: `help`, `status`, `scan`, `packet`, `verify`, `reflect`, `resume`, `method`, `handoff`, `workflow`, `plugin`, `grimoire`, `reload`, `quit`)
- `BuiltinSlashCommand` — frozen dataclass: `name`, `description`
- `SlashCommandInfo` — frozen dataclass for any command (built-in or contributed): `name`, `source`, `source_info`, `description`
- `SlashCommandSource` Literal: `"extension" | "prompt" | "skill" | "plugin"`

**Usage (consumer side).**

```python
from mythic_vibe_cli.runtime import BUILTIN_SLASH_COMMANDS

for command in BUILTIN_SLASH_COMMANDS:
    print(f"/{command.name}\t{command.description}")
```

**Usage (contributor side).**

```python
from mythic_vibe_cli.runtime import (
    SlashCommandInfo,
    synthetic_source_info,
)

info = SlashCommandInfo(
    name="audit",
    source="plugin",
    source_info=synthetic_source_info(
        "audit_plugin:Plugin",
        source="audit_plugin",
        scope="project",
    ),
    description="Append-only audit log",
)
```

**When to reach for it.** When building a REPL, TUI, or SDK surface that needs to enumerate or dispatch slash commands. The catalog is intentionally separate from any dispatcher — the dispatcher belongs to the consumer surface, not the catalog.

**Today's consumer.** `mythic-vibe slash list` reads `BUILTIN_SLASH_COMMANDS` and aggregates plugin-contributed entries via the new `discover_slash_commands()` method on `PluginHookDispatcher`. Plugins that want to contribute commands declare a `slash_commands()` callable returning a list of `SlashCommandInfo`; see [`docs/plugins.md`](plugins.md) §9 for the plugin-side contract.

**Source:** `mythic_vibe_cli/runtime/slash_commands.py`

---

## 7) `source_info`

**Purpose.** Structured provenance for extension/plugin/skill/prompt-contributed artifacts. Records where a contributed thing came from, the scope it was registered under, and whether it lives inside a package or top-level.

**Public surface.**

- `SourceInfo` — frozen dataclass: `path`, `source`, `scope`, `origin`, optional `base_dir`
- `SourceScope` Literal: `"user" | "project" | "temporary"`
- `SourceOrigin` Literal: `"package" | "top-level"`
- `synthetic_source_info(path, source, scope=..., origin=..., base_dir=None)` — factory with sensible defaults (matches pi's `createSyntheticSourceInfo`)

**Usage.**

```python
from mythic_vibe_cli.runtime import synthetic_source_info

provenance = synthetic_source_info(
    "audit_plugin:Plugin",
    source="audit_plugin",
    scope="project",
    origin="top-level",
)
```

`scope` answers "where in the user/project/temporary spectrum did this come from?" — useful for policy decisions about which scopes can override which. `origin` answers "package or top-level?" — useful for distinguishing user-installed contributions from in-project ones.

**When to reach for it.** When registering an extension/plugin/skill/prompt-contributed artifact (a slash command, a packet template, a verification check). The provenance gives downstream consumers stable metadata to display, log, or gate on.

**Source:** `mythic_vibe_cli/runtime/source_info.py`

---

## 8) `exec`

**Purpose.** Run a subprocess with a uniform contract — captured stdout/stderr, an integer exit code, a `killed` flag, and optional timeout + caller-driven cancellation. The point is to keep ad-hoc `subprocess.run(...)` calls from scattering across the codebase with inconsistent timeout / kill / capture conventions.

**Public surface.**

- `exec_command(command, args, cwd, *, timeout=None, cancel_event=None)` → `ExecResult`
- `ExecResult` — frozen dataclass: `stdout`, `stderr`, `code`, `killed`, plus `to_dict`
- `shell=False` is hard-coded — callers split arguments themselves; no shell-injection footguns
- Missing commands return `code=127` with the error message in `stderr` rather than raising

**Usage.**

```python
from mythic_vibe_cli.runtime import exec_command

result = exec_command(
    "git",
    ["status", "--porcelain"],
    cwd=".",
    timeout=10.0,
)
if result.code == 0:
    process(result.stdout)
elif result.killed:
    log.warning("git status timed out")
```

**With cancellation.**

```python
import threading
from mythic_vibe_cli.runtime import exec_command

cancel = threading.Event()
# ... start a watcher thread that sets `cancel` on Ctrl+C or upstream signal ...

result = exec_command(
    "long-running-tool",
    ["--lots", "--of", "--work"],
    cwd=".",
    cancel_event=cancel,
)
```

When `cancel_event` is set during execution, the process is killed via `SIGTERM` with a 5-second `SIGKILL` fallback (Unix) / `terminate()` then `kill()` escalation (Windows). The kill behavior matches pi's `execCommand`.

**When to reach for it.** Tools that run external programs — git, ripgrep, formatters, linters, build systems, language servers, custom verification commands. Don't reach for it when you want to read a file (use `Path.read_text`) or when you want shell expansion (use Python's own primitives — globbing, env var resolution — rather than spinning up a shell).

**Source:** `mythic_vibe_cli/runtime/exec.py`

---

## 9) Composition patterns

The primitives compose. A few common patterns:

### `--json` command writing a packet

```python
# app.main() already enters json_output_guard for us when --json is set
def cmd_my_packet_writer(args):
    from mythic_vibe_cli.runtime import file_mutation_queue
    from pathlib import Path

    target = Path(args.path) / "mythic" / "packets" / "PKT-XXX.json"
    with file_mutation_queue(target):
        target.write_text("...", encoding="utf-8")
    # write_json() output reaches real stdout via write_raw_stdout
    return SUCCESS
```

### Plugin observing events with timed dispatch

```python
# Plugin code
class TelemetryPlugin:
    @classmethod
    def after_scan(cls, payload):
        # timings.record() works inside plugin handlers too
        from mythic_vibe_cli.runtime import record
        record(f"telemetry:after_scan:{payload['path']}")
        # ... ship to telemetry service ...
```

With `MYTHIC_TIMING=1`, the plugin's contribution appears in the `print_timings()` output, scoped under the `handler:<command>` block.

### Custom event channel inside a command

```python
from mythic_vibe_cli.runtime import create_event_bus

def cmd_long_running(args):
    bus = create_event_bus()
    received_progress = []
    bus.on("progress", lambda step: received_progress.append(step))

    for i, step in enumerate(work_steps):
        bus.emit("progress", {"index": i, "label": step.label})
        step.run()

    return SUCCESS
```

The bus is local to the command — no global state, no leakage across invocations.

---

## 10) Constraints and contracts

These rules apply across all primitives:

1. **Synchronous only.** No async/await. Plugin handlers, event subscribers, and timing call sites all run on the calling thread.
2. **Exception isolation where it matters.** The event bus catches handler exceptions and logs them to stderr; the file mutation queue does not (a write that raises propagates). Choose the primitive that matches your tolerance for failure.
3. **Module-level state where appropriate.** `output_guard` and `timings` use module-level state because there's only one stdout and one process-wide clock. `event_bus` and `file_mutation_queue` use per-instance or per-key state because there are many channels and many paths.
4. **No monkey-patching.** Primitives don't replace functions outside `mythic_vibe_cli/runtime/`. The output guard is the closest thing — it replaces `sys.stdout` — but it's bracketed by explicit takeover/restore calls.
5. **Env-gated where pay-for-what-you-use matters.** `timings` checks `MYTHIC_TIMING` lazily on every call so unmeasured runs cost nothing. The check is a plain `os.environ.get` lookup and is negligibly fast.
6. **Per-invocation lifecycle for command-scoped primitives.** A `PluginHookDispatcher` is created fresh per command invocation. The event bus inside it lives only for that command's run. This matches `app.main()`'s `try/finally` around the handler.

---

## 11) See also

- `docs/plugins.md` — operator-facing guide for writing plugins (consumes `event_bus` via the dispatcher)
- `docs/COMMAND_CONTRACTS.md` — canonical payload shapes per emitter
- `docs/api.md` — command/API contract overview
- `mythic_vibe_cli/runtime/__init__.py` — re-export surface; canonical "what's importable"
- `THIRD_PARTY_NOTICES.md` — Pi attribution and the plunder map
- Source files (each carries an attribution header where applicable):
  - `mythic_vibe_cli/runtime/file_mutation_queue.py`
  - `mythic_vibe_cli/runtime/output_guard.py`
  - `mythic_vibe_cli/runtime/event_bus.py`
  - `mythic_vibe_cli/runtime/timings.py`
  - `mythic_vibe_cli/runtime/slash_commands.py`
  - `mythic_vibe_cli/runtime/source_info.py`
  - `mythic_vibe_cli/runtime/exec.py`
- Tests as runnable specification:
  - `tests/test_file_mutation_queue.py`
  - `tests/test_output_guard.py`
  - `tests/test_event_bus.py`
  - `tests/test_timings.py`
  - `tests/test_slash_commands.py`
  - `tests/test_source_info.py`
  - `tests/test_exec.py`

The runtime layer is intentionally minimal. Seven primitives, seven docstrings, seven test files. Anything more complex than these primitives belongs in a feature module that *uses* the runtime, not in the runtime itself.
