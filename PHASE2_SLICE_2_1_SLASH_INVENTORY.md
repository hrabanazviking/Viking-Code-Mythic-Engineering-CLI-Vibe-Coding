---
title: "Phase 2 — Slice 2.1 Slash-Command Inventory"
phase: PH-02
slice: 2.1
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 8905a54
status: complete
discipline: strictly additive — every new slash entry resolves to an already-existing handler
---

# Phase 2 Slice 2.1 — Slash-Command Inventory

## Purpose

Catalogue every existing argparse handler against the current
`BUILTIN_SLASH_COMMANDS` list. Add any handler that exists today but
isn't yet exposed as a slash command. Identify which target slash
commands from the Master Roadmap aggregate need *new* implementation
work — those are routed to later phases.

## Existing argparse handlers (38 unique)

Source: `COMMAND_HANDLERS` in `mythic_vibe_cli/commands.py:3084-3125`.

```text
ai            checkin       codex-log     codex-pack    completion
config        db            doctor        evoke         examples
explain       grimoire      guide         handoff       heal
help          imbue         import-md     init          method
next          oath          packet        plugin        plunder
prune         reflect       resume        scan          scry
shell         slash         start         state         status
sync          tui           tutorial      verify        weave
workflow
```

(`start`, `imbue` alias `init`; `evoke` aliases `codex-pack`; `scry`
aliases `doctor`. So 41 names → 38 unique handlers.)

## Pre-slice slash catalog (14 builtins)

```text
help status scan packet verify reflect resume method handoff
workflow plugin grimoire reload quit
```

## Gap analysis

### A. Handlers that exist today but aren't yet in the slash catalog (24)

These all become new `BuiltinSlashCommand` entries in this slice:

| Slash | Handler | Notes |
|---|---|---|
| `/init` | `cmd_init` | New project scaffold |
| `/imbue` | `cmd_init` | Alias of init |
| `/start` | `cmd_init` | Alias of init |
| `/checkin` | `cmd_checkin` | Phase check-in + DEVLOG update |
| `/codex-pack` | `cmd_codex_pack` | Generate ChatGPT/Codex packet |
| `/codex-log` | `cmd_codex_log` | Log a Codex response |
| `/evoke` | `cmd_codex_pack` | Mythic alias of codex-pack |
| `/import-md` | `cmd_import_md` | Import Mythic Engineering corpus |
| `/sync` | `cmd_sync` | Sync method corpus from upstream |
| `/doctor` | `cmd_doctor` | Diagnostic checks |
| `/scry` | `cmd_doctor` | Mythic alias of doctor |
| `/next` | `cmd_next` | Show next recommended action |
| `/examples` | `cmd_examples` | Print canonical command examples |
| `/guide` | `cmd_guide` | Print short guide |
| `/explain` | `cmd_explain_dispatch` | Explain a phase or artifact |
| `/tutorial` | `cmd_tutorial` | Walk through the Mythic loop |
| `/completion` | `cmd_completion` | Print shell completion script |
| `/oath` | `cmd_oath` | Display + accept the AI-review oath |
| `/weave` | `cmd_weave` | Weave/check-in marker (currently F-021 gated) |
| `/prune` | `cmd_prune` | Stale-artifact cleanup (scaffold today) |
| `/heal` | `cmd_heal` | Repair workflow (scaffold today) |
| `/config` | `cmd_config_dispatch` | Show / set config values |
| `/state` | `cmd_state_dispatch` | Project state show / validate |
| `/db` | `cmd_db_dispatch` | Database / schema migrate |
| `/plunder` | `cmd_plunder` | Lawful single-file reuse |
| `/ai` | `cmd_ai_dispatch` | AI provider operations |

That's 26 names mapped to existing handlers — but `imbue` / `start`
are aliases, so 24 *unique* additions plus the two ritual aliases.
(`shell` and `tui` are deliberately not surfaced as slash commands —
`/shell` from inside the shell or `/tui` from inside the TUI is
nonsensical, and adding them just to have them invites confusion.)

### B. Target slash commands from the Master Roadmap that need *new* implementation

These do NOT land in slice 2.1 — they require new handlers that
will be implemented in later phase slices:

| Slash | Phase | Slice |
|---|---|---|
| `/intent` `/constraints` `/architecture` `/plan` `/build` | PH-02 | 2.3 (phase-capture commands) |
| `/test` `/lint` `/typecheck` | PH-02 | 2.2 (verify-shorthand aliases) |
| `/audit` `/review` `/security` `/shield` | PH-02 / PH-11 | 2.5 |
| `/scaffold` | PH-02 | 2.2 |
| `/changelog` `/version` | PH-02 | 2.2 |
| `/forge` `/architect-agent` `/planner` `/builder` `/verifier` | PH-03 | 3.3+ |
| `/graph` `/rehydrate` `/search` `/index` | PH-05 | 5.5+ |
| `/chat` | PH-06 | 6.x |
| `/voice` | PH-07 | 7.1 |
| `/policy` | PH-14 | 14.4 |
| `/memory` | PH-15 | 15.3 |
| `/simulate` `/resilience` | PH-18 | 18.4 |
| `/telemetry` | PH-16 | 16.4 |
| `/release` `/package` `/publish` `/export` | PH-12 / PH-19 | 12.3 / 19.x |
| `/ui` (alias for tui) | PH-04 | 4.x |
| `/web` `/mobile` | PH-17 | 17.x |
| `/ritual` `/extension` `/skill` `/prompt` | PH-10 | 10.3 |

That's roughly 38 future slash entries that come with their own
implementation work.

### C. Slash entries that already work as-is

`help`, `quit`, `reload` are interactive-surface concerns (REPL/TUI
local commands) and stay in the catalog as-is. `status`, `scan`,
`packet`, `verify`, `reflect`, `resume`, `method`, `handoff`,
`workflow`, `plugin`, `grimoire` map to existing argparse handlers
already and need no change.

## Implementation plan for slice 2.1

The plan, implemented in the companion commit:

1. Append 24 new `BuiltinSlashCommand` entries to
   `BUILTIN_SLASH_COMMANDS` (the 24 unique handlers listed in
   section A; the two pure aliases `imbue`/`start` are listed
   alongside `init` and counted as 26 total names).
2. Update `tests/test_slash_commands.py` to add a new lock-in test
   that the catalog now exposes every command in
   `COMMAND_HANDLERS` (allowing `shell`/`tui` as deliberate
   exclusions and the four interactive locals `help`/`quit`/`reload`
   as catalog-only).
3. Verify the existing slash-list test still passes (it asserts a
   subset, so a larger catalog cannot break it).

Slice 2.1 is purely additive: zero handler logic changes, zero
argparse changes, zero behaviour changes. Every new slash entry
resolves to an existing handler that is already tested.

## Out of scope for slice 2.1

- Implementing any of the section B commands (those have phase homes).
- Wiring the TUI dispatcher to actually run plugin/extension slash
  entries — that's slice 2.6 by the master roadmap.
- Building `/help <command>` introspection — that's slice 2.7.
- Adding plugin-contributed slash commands beyond the existing
  discovery contract — also slice 2.6.

## Slice 2.1 success criteria

- `BUILTIN_SLASH_COMMANDS` contains ≥ 38 entries after this slice
  (was 14).
- `mythic-vibe slash list --json` reports every entry with
  description and source.
- Test suite stays green and adds at least one new test locking the
  catalog-handler parity invariant.
