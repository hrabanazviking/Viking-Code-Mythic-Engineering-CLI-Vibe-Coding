---
title: "Phase 2 — Slices 2.7 + 2.8 Close-out (Slash Help & Parity)"
phase: PH-02
slices: ["2.7", "2.8"]
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: fee9a02
head_at_close: 69be161
test_baseline_open: 340 + 14 subtests
test_baseline_close: 364 + 14 subtests
slash_builtins_open: 51
slash_builtins_close: 51
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 2 Slices 2.7 + 2.8 — Close-out

## Purpose

Two consecutive Phase 2 slices addressing the slash-introspection
gap and locking in the catalog-parity invariant before later phases
add more entries.

- **Slice 2.7** — `slash inspect <name>` introspection surface +
  REPL `/help <name>` routing.
- **Slice 2.8** — REPL/TUI/plugin parity test suite locking the
  catalog-consistency invariant across all consumer surfaces.

Both are strictly additive. Slice 2.7 adds one new argparse
subcommand and one REPL routing branch; slice 2.8 is test-only.

## Slice 2.7 — Slash help & introspection

### Public surface

```bash
mythic-vibe slash inspect <name>
mythic-vibe slash inspect /<name>      # leading slash accepted
mythic-vibe slash inspect <name> --json
```

### Resolution order

1. `BUILTIN_SLASH_COMMANDS` catalog
2. Plugin-contributed entries (via
   `PluginHookDispatcher.discover_slash_commands()`)

### Output

For builtin entries that map onto a top-level argparse subcommand
(everything except the three interactive locals
`help`/`reload`/`quit`), the parser's `--help` text is rendered so
the operator sees exactly what `mythic-vibe <name> --help` would
print.

For interactive locals, output flags `interactive-local — handled by
the REPL/TUI directly; no argparse subcommand`.

For plugin-contributed entries, output shows source / description /
origin path / scope (no argparse help — that contract belongs to
slice 2.6).

### JSON payload

```json
{
  "command": "slash inspect",
  "name": "<name>",
  "ok": true,
  "source": "builtin" | "plugin" | "extension" | ...,
  "entry": <BuiltinSlashCommand.to_dict() or SlashCommandInfo.to_dict()>,
  "argparse_help": "<text>" | null,
  "interactive_local": true | false
}
```

### REPL `/help <name>` routing

The REPL's existing `/help` (no argument) still prints the inline
catalog. Adding any argument routes the line to
`slash inspect <name>` via `main([...])`, so the REPL and CLI share
one source of truth for help content.

`/help /<name>` strips the leading slash before dispatch
(`/help /verify` and `/help verify` resolve identically).

### Implementation notes

- Subparser help-text extraction walks `parser._actions` for the
  `_SubParsersAction` and looks up `name` in `action.choices`. This
  uses argparse private API; the alternative would be shelling out
  to `mythic-vibe <name> --help`, which is slower and fragile.
- `SLASH_LOCALS_WITHOUT_ARGPARSE = {"help", "reload", "quit"}` is now
  defined in `commands.py` so the test suite and implementation share
  one canonical definition of which entries are catalog-only.

### Tests added (13)

- `SlashInspectBuiltinTests` (5) — argparse-backed entries, leading
  slash, interactive locals, intent capture parent, unknown names.
- `SlashInspectJsonShapeTests` (2) — JSON payload shape for
  argparse-backed and interactive-local entries.
- `SlashInspectPluginContributedTests` (1) — synthetic plugin
  resolves through dispatcher.
- `SlashInspectMissingNameTests` (1) — argparse blocks missing
  positional.
- `ReplHelpRoutingTests` (3) — `/help <name>` routes via main, leading
  slash stripped, `/help` no-arg preserves inline catalog.

## Slice 2.8 — REPL/TUI/plugin parity tests

Eleven tests in three classes; all production code untouched.

### Invariant locked

Every slash entry — builtin or plugin-contributed — must surface
and resolve identically across:

- CLI (`mythic-vibe slash list`, `mythic-vibe slash inspect`)
- Shell REPL (`/help` inline, `/help <name>` routed)
- Textual TUI picker (`gather_picker_entries`)
- Argparse subparser tree (for non-interactive-local entries)

### Tests added (11)

**CatalogSurfaceParityTests (6)**
- CLI `slash list` builtin names equal `BUILTIN_SLASH_COMMANDS`
- TUI `gather_picker_entries` returns every builtin
- REPL `/help` lists every builtin inline
- Every catalog entry resolves cleanly via `slash inspect`
- Every non-interactive-local entry has an argparse handler
- The three interactive locals do NOT also exist as argparse
  subcommands

**CatalogConsistencyAcrossSurfacesTests (2)**
- CLI `slash list` description text equals `BUILTIN_SLASH_COMMANDS`
  description text
- TUI picker description text equals `BUILTIN_SLASH_COMMANDS`
  description text — locks against silent description drift

**PluginContributedParityTests (1)**
- A synthetic plugin's slash entry appears in CLI list, TUI picker,
  REPL inline help, and `slash inspect` JSON payload identically

**HelpSurfaceParityTests (2)**
- REPL `/help <name>` invokes `main(["slash", "inspect", ..., name])`
- Unknown names return `USER_INPUT_ERROR` consistently from both
  paths (CLI direct + REPL routed)

## Combined numbers

| Metric | Open | After 2.7 | After 2.8 |
|---|---|---|---|
| Test count | 340 | 353 (+13) | **364 (+11)** |
| Slash builtin entries | 51 | 51 | 51 |
| Argparse handlers | 49 unique | 49 unique | 49 unique |
| Coverage | 76% | 76% | 76% |
| Ruff / mypy | clean | clean | clean |

## What these slices deliberately did not do

- Did not implement plugin-contributed slash dispatch (the picker
  still says "plugin dispatch not yet implemented" — that's slice
  2.6 territory, gated on PH-04 TUI v2 work).
- Did not add argparse-help rendering for nested subcommands like
  `intent capture`. The current implementation shows the *parent*
  parser's help (which lists `capture`); deeper inspection is a
  refinement.
- Did not add tab-completion for slash names in the REPL. Out of
  scope; could land in a future ergonomics pass.
- Did not change any handler logic. Both slices respect the
  additive-only contract.

## Phase 2 progress

| Slice | Status |
|---|---|
| 2.1 catalog mirror | ✅ done |
| 2.2 dev-tool shortcuts | ✅ done |
| 2.3 workflow-phase capture | ✅ done |
| 2.4 provider/AI aliases | blocked on PH-03 |
| 2.5 diagnostic aliases | blocked on PH-11 |
| 2.6 plugin-contributed slash dispatch | blocked on PH-04 |
| 2.7 slash help & introspection | ✅ done |
| 2.8 REPL/TUI/plugin parity tests | ✅ done |

**Five of eight Phase 2 slices closed.** The three remaining
(2.4 / 2.5 / 2.6) all have legitimate phase dependencies and
shouldn't ship until those phases land.

## Next decision point

Phase 2 is functionally done for now. Three viable next moves:

1. **Begin Phase 3 (Multi-Agent Forge) slice 3.1** — agent contract
   spec. Foundation for slices 2.4 / 2.5 / 2.6 (which can ship
   incrementally as later phases unlock them) and a major
   architectural milestone.
2. **Begin Phase 5 (Knowledge Graph) slice 5.1** — schema design.
   Independent of Phase 3; provides the retrieval foundation needed
   by `forge` for richer packets.
3. **Begin Phase 11 (Security/Sandbox) slice 11.1** — approval
   modes. Independent of both; addresses real operator-safety gaps
   the audit didn't explicitly call out.

The natural progression by master-roadmap dependency is Phase 3
(multi-agent forge) — it's the largest remaining feature and unlocks
the most blocked work. Awaiting Volmarr's call.
