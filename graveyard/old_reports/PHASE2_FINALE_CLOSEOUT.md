---
title: "Phase 2 — Finale (Slash Command Surface Expansion)"
phase: PH-02
slices: 2.1–2.8
opened: 2026-04-29
closed: 2026-04-29
phase_open_head: 26ee284
phase_close_head: 2fa5097
phase_open_tests: ~270
phase_close_tests: 686 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
---

# Phase 2 — Slash Command Surface Expansion (Finale)

## What Phase 2 was for

Take the slice-1.x scaffolded slash catalog (14 entries, mirror of
the existing argparse surface) and grow it toward the 39+ commands
documented in the Aggregate Feature Report — plus Mythic-specific
additions. Every slash command resolves to an existing argparse
handler, so the CLI / shell REPL / TUI / future plugin loader all
see the same surface.

Constraint kept throughout: **additive only, no behaviour change in
existing handlers**. Each new slash entry is a thin façade over a
real argparse subcommand; every catalog mutation is mirrored in the
parity test suite.

## Slice-by-slice ledger

### Slice 2.1 — Slash inventory + catalog mirror
- Catalog grew 14 → 40 entries by mirroring the existing argparse
  surface; no new handlers.
- 1 parity test added — every argparse top-level subcommand now
  appears in `BUILTIN_SLASH_COMMANDS`.
- Close-out: `PHASE2_SLICE_2_1_SLASH_INVENTORY.md`.

### Slice 2.2 — Developer-tool shortcuts
- Six new top-level subcommands: `test` (pytest), `lint` (ruff),
  `typecheck` (mypy), `scaffold` (artefact), `changelog`, `version`.
- Each runs the underlying tool via subprocess with `--command`
  override hook for project-specific commands.
- F-023 logged + fixed inline (argparse `--command` flag dest
  collided with top-level `dest="command"`; fixed with explicit
  `dest="override_command"`).
- 40 → 46 slash entries; +17 tests.
- Close-out: `PHASE2_SLICE_2_2_CLOSEOUT.md`.

### Slice 2.3 — Workflow-phase capture commands
- Five new top-level subcommands: `intent`, `constraints`,
  `architecture`, `plan`, `build` — each with a `capture`
  subcommand that writes a Mythic Phase Record under
  `mythic/checkins/<ts>-<phase>.md`.
- 46 → 51 slash entries; +13 tests.
- Close-out: `PHASE2_SLICE_2_3_CLOSEOUT.md`.

### Slice 2.4 — Provider/AI alias *(this session)*
- New top-level `provider` subcommand wrapping `cmd_ai_providers`.
- Scope-bounded: per-agent / voice / chat aliases deferred to
  PH-03 / PH-15 / PH-19 (need handlers we don't have yet).
- 51 → 53 slash entries; +5 tests (combined with 2.5).
- Close-out: `PHASE2_SLICES_2_4_2_5_2_6_CLOSEOUT.md`.

### Slice 2.5 — Diagnostic alias *(this session)*
- New top-level `audit` subcommand wrapping `cmd_doctor` with
  `--json` injected.
- Scope-bounded: review/security/shield/simulate deferred (no
  backing handlers).
- 53 → 54 slash entries; +5 tests + 2 TUI runner tests.

### Slice 2.6 — Plugin slash dispatch contract *(this session)*
- Extended `SlashCommandInfo` with optional `argv` field.
- Plugin authors can now register slash entries with explicit argv
  that the TUI dispatches via `RunningCommandScreen`. Plugins
  without argv stay discoverable-only (backwards-compatible).
- `PickerEntry.is_dispatchable` property unifies the gate;
  `CommandPreviewScreen` flips run-hint and `r`-key behaviour on
  it.
- +10 tests including a real plugin-fixture round-trip.

### Slice 2.7 — Slash help + introspection
- `mythic-vibe slash inspect <name>` — full provenance + argparse
  help dump.
- REPL `/help <name>` — same payload, REPL-friendly format.
- +13 tests.
- Close-out: `PHASE2_SLICES_2_7_2_8_CLOSEOUT.md`.

### Slice 2.8 — REPL/TUI/plugin parity tests
- Cross-surface parity test suite: every slash resolves identically
  through CLI, REPL, and TUI.
- +11 tests.

## Cumulative numbers

| Metric | Phase open (post-2.0) | Phase close | Δ |
|---|---|---|---|
| Slash builtins | 14 | **54** | +40 |
| Argparse handlers | ~40 | **52** | +12 |
| Test count | ~270 | **686 + 14 subtests** | +416 across PH-02/03/04 (~80 attributable to PH-02) |

Each slice ran ruff + mypy clean and passed every prior test.

## Master-roadmap target table

The Phase 2 "Done when" gate from the master roadmap:

| Gate | Met? |
|---|---|
| `slash list` reports ≥ 50 entries (39 from aggregate + Mythic-specific) | ✅ 54 |
| Every entry has source_info + description + non-empty argparse resolution | ✅ |
| Help, inspect, dispatch identical across CLI / REPL / TUI | ✅ (slice 2.8 parity tests) |

## What Phase 2 deliberately did not do

- **Per-agent forge slashes** (`/architect-agent`, `/planner`,
  `/builder`, `/verifier`). PH-03 forge runs the full role
  sequence; per-role isolation is a future concern.
- **Voice / chat slashes** (`/voice`, `/chat`). PH-15 / PH-19
  territory.
- **PR review / security / shield / simulate slashes**
  (`/review`, `/security`, `/shield`, `/simulate`). No backing
  handlers; would be PH-15 / future security slice.
- **Memory slash** (`/memory`). The existing `state` /
  `handoff` / `resume` cover memory operations; a unified
  `/memory` would be a UX consolidation slice, not a new
  capability.
- **Web / mobile / telegram surface slashes** (`/web`, `/mobile`,
  `/telegram`). PH-19 multimodal territory.
- **Release slashes** (`/release`, `/package`, `/publish`). PH-20
  release-engineering territory.

Each deferred slash has a clear PH dependency that, when
implemented, can register a thin alias here without re-opening
Phase 2.

## Phase progression after PH-02

Master roadmap status snapshot:

| Phase | Status |
|---|---|
| PH-01 Audit & runtime hygiene | ✅ closed |
| PH-02 Slash command surface expansion | ✅ closed (this finale) |
| PH-03 Multi-agent forge engine | ✅ closed |
| PH-04 TUI layout & interaction | ✅ closed |
| PH-05 ↑ | next active |

## How to resume

`MEMORY.md` quick-facts line and
`project_mythic_engineering_cli_status.md` are updated to HEAD
`<close-head>` and "PH-02 + PH-04 closed".
`MYTHIC_VIBE_CLI_MASTER_ROADMAP.md` remains the authoritative
roadmap. `TASK_master_roadmap_and_phase1.md` tracker is up to
date through this finale.

A future session can resume by opening that tracker, locating the
"next" row at the bottom, and starting that slice.
