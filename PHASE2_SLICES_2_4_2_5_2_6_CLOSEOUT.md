---
title: "Phase 2 — Slices 2.4 / 2.5 / 2.6 Close-out"
phase: PH-02
slices: 2.4, 2.5, 2.6
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 6f307d6
head_at_close: 2fa5097
test_baseline_open: 664 + 14 subtests
test_baseline_close: 686 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 2 Slices 2.4 / 2.5 / 2.6 Close-out

## Purpose

Finish Phase 2 by adding three remaining slices, each scoped to
what the underlying handler layer can actually back today.

## Scope reality check

The master roadmap's slice-2.4 / 2.5 target lists were aspirational
— several entries (`/architect-agent`, `/planner`, `/builder`,
`/verifier`, `/voice`, `/chat`, `/review`, `/security`, `/shield`,
`/simulate`) point at handlers that don't exist yet and require
PH-15 / PH-19 / future forge work to back them. Inventing thin
slashes over non-existent handlers would be the kind of
half-finished implementation Runa does not ship.

What this session shipped:

| Slice | Adds | Deferred (with PH dependency) |
|---|---|---|
| 2.4 | `/provider` (alias for `ai providers`) | per-agent (PH-03 forge per-role), `/voice` (PH-19), `/chat` (PH-15) |
| 2.5 | `/audit` (alias for `doctor --json`) | `/review` (PH-15), `/security`/`/shield`/`/simulate` (no handlers) |
| 2.6 | `SlashCommandInfo.argv` + TUI dispatch | full plugin RPC (PH-15) |

## Slice 2.4 — Provider alias

Adds `mythic-vibe provider` as a top-level argparse subcommand
that delegates straight to `cmd_ai_providers`. No new behaviour;
just a friendlier name the slash picker can surface. Argparse
options match `ai providers`: `--path`, `--json`, plus the standard
runtime flags.

`cmd_provider` in `commands.py` is a one-liner that returns
`cmd_ai_providers(args)`. The slash catalog gains:

```python
BuiltinSlashCommand(name="provider",
    description="List configured AI providers (alias of `ai providers`)")
```

The TUI runner's path-aware allow-list adds `provider` so
`/provider` in the picker carries the project root through.

## Slice 2.5 — Audit alias

Adds `mythic-vibe audit` as a top-level subcommand wrapping
`cmd_doctor` with `args.json = True` injected before delegation.
The intent: an audit run should always be machine-readable, the
distinction from plain `doctor` (which renders a human report by
default).

```python
def cmd_audit(args: argparse.Namespace) -> int:
    setattr(args, "json", True)
    return cmd_doctor(args)
```

Catalog gains `BuiltinSlashCommand(name="audit", ...)`. TUI runner
adds it to the path-aware allow-list.

## Slice 2.6 — Plugin slash dispatch contract

The substantive slice. Before today, plugin-contributed slash
commands could be **discovered** but not **dispatched** — the
TUI's preview screen showed "(plugin dispatch not yet
implemented)" for any non-builtin source. This was a contract
hole: plugins had no way to opt into runnability.

### Contract change

```python
@dataclass(frozen=True)
class SlashCommandInfo:
    name: str
    source: SlashCommandSource
    source_info: SourceInfo
    description: str = ""
    argv: tuple[str, ...] = ()    # NEW — slice 2.6
```

A plugin that wants its slash entry runnable supplies an explicit
`argv` tuple. The TUI's `RunningCommandScreen` launches it as a
subprocess exactly the way it launches builtin commands. A plugin
that doesn't supply argv (default empty tuple) stays in the old
discover-only mode — the contract is fully backwards-compatible.

### TUI propagation

```python
@dataclass(frozen=True)
class PickerEntry:
    ...
    argv: tuple[str, ...] = ()

    @property
    def is_dispatchable(self) -> bool:
        return self.source == "builtin" or bool(self.argv)
```

`CommandPreviewScreen` switches its run-hint and its `r`-key gate
from `source == "builtin"` to `is_dispatchable`. Builtin entries
keep their existing dispatch path (`command_for_builtin` builds
the argv from the name); contributed entries with argv go through
`RunSpec(argv=list(entry.argv))` directly — no `--path` injection,
no Python-interpreter wrapping. The plugin owns the invocation
shape entirely.

### Why argv (not a callable)?

A callable would require the plugin to live inside the same
process as the TUI (no subprocess isolation), and would block
crash-isolation for bad plugin code. An argv tuple keeps every
plugin invocation in its own subprocess, matches the existing
builtin dispatch model, and lets plugins ship in any language as
long as they provide an executable.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 664 | **686** (+22) |
| Source files | 75 | 75 |
| Slash builtins | 52 | **54** (+2: provider, audit) |
| Argparse handlers | 50 | **52** (+2: cmd_provider, cmd_audit) |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## Tests added (22 total)

`tests/test_phase2_finale_aliases.py` (12) — slices 2.4 + 2.5:

- ProviderAliasTests (5): argparse parses; routes through
  `COMMAND_HANDLERS["provider"]`; cmd_provider delegates to
  cmd_ai_providers; `/provider` in catalog; runs end-to-end with
  copy-paste provider.
- AuditAliasTests (5): same shape; cmd_audit forces json=True;
  emits JSON envelope on a fresh project; `/audit` in catalog.
- TuiRunnerForwardsPathForNewAliases (2): both new commands in
  `command_for_builtin` allow-list (`--path` gets forwarded).

`tests/test_plugin_slash_dispatch.py` (10) — slice 2.6:

- SlashCommandInfoArgvTests (3): default empty; argv round-trips
  through `to_dict()` (list-form); frozen-dataclass immutability.
- PickerEntryDispatchAuditTests (3): builtin always dispatchable;
  contributed without argv not; contributed with argv yes.
- CommandPreviewScreenDispatchTests (3): pressing `r` on a
  contributed entry with argv pushes RunningCommandScreen;
  pressing `r` on one without argv is a no-op; preview body's
  run-hint flips on `is_dispatchable`.
- PluginDispatcherSlashArgvRoundTripTests (1): real plugin fixture
  via `_SyntheticPluginHarness` pattern — slash_commands()
  returning SlashCommandInfo(argv=...) survives
  PluginHookDispatcher.discover_slash_commands() with argv intact.

Plus two fixups for tests that asserted on the pre-2.4/2.5 state:

- `test_cli_kernel.py::test_command_registry_preserves_current_commands_and_aliases`
  — added `provider`, `audit` to expected set.
- `test_slash_inspect.py::test_inspect_plugin_contributed_entry`
  — synthetic plugin slash renamed `audit` → `audit-probe` to
  avoid colliding with the new builtin.

## What this slice deliberately did not do

- **Did not implement the deferred slash aliases.** Per the scope
  table above, those need backing handlers we don't have yet.
- **Did not introduce a callable dispatch contract for plugins.**
  Argv tuple is the deliberate choice — keeps subprocess
  isolation, language-agnostic plugins, no in-process crashing.
- **Did not extend `BuiltinSlashCommand` with argv.** Builtins
  reconstruct their argv from the name via `command_for_builtin`
  so an extra field would just duplicate that logic.
- **Did not modify existing plugin dispatcher contract.** Plugins
  that returned `SlashCommandInfo` without argv before this slice
  continue to work with empty argv after — they're discoverable
  but not runnable, exactly like before.
- **Did not validate argv content.** A plugin can register any
  argv (including dangerous ones); the TUI subprocess-launches it
  verbatim. Same trust model as the builtin path: the operator
  installed the plugin and is responsible for what it executes.

## Phase 2 progress (final)

| Slice | Status |
|---|---|
| 2.1 Slash inventory + catalog mirror | ✅ done |
| 2.2 Developer-tool shortcuts | ✅ done |
| 2.3 Workflow-phase capture | ✅ done |
| 2.4 Provider/AI alias | ✅ done (this session, scope-bounded) |
| 2.5 Diagnostic alias | ✅ done (this session, scope-bounded) |
| 2.6 Plugin slash dispatch contract | ✅ done (this session) |
| 2.7 Slash help + introspection | ✅ done |
| 2.8 REPL/TUI/plugin parity tests | ✅ done |

**🎉 Phase 2 complete — all eight slices shipped.** See
`PHASE2_FINALE_CLOSEOUT.md` for the full retrospective.

## Smoke verification

```bash
$ mythic-vibe provider
AI providers
  - copy-paste: configured
    ...

$ mythic-vibe audit --path .
{"errors": [...], "ok": false, ...}

# In the TUI:
$ mythic-vibe tui
# / picker → /provider visible; /audit visible
# Press r on either — RunningCommandScreen runs them with --path
# forwarded.
```

## Next phase

PH-04 already closed (this session). PH-02 now closed (this
session). Master roadmap candidates: PH-05, PH-13 (forge drift
detection), or any of the as-yet-unstarted phases.
