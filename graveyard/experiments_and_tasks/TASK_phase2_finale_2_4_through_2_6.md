---
title: "Phase 2 — Finishing Slices 2.4 / 2.5 / 2.6"
phase: PH-02
slices: 2.4, 2.5, 2.6
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 6f307d6
status: in_progress
---

# Phase 2 Finishing Slices

## Scope reality check

The master roadmap target list for slices 2.4 / 2.5 was aspirational
— several entries (`/architect-agent`, `/planner`, `/builder`,
`/verifier`, `/voice`, `/chat`, `/review`, `/security`, `/shield`,
`/simulate`) point at handlers that don't exist yet and require
PH-15 / PH-19 / future forge work to back them. Inventing thin
slashes over non-existent handlers would be the kind of half-finished
implementation Runa does not ship.

**Realistic, additive scope this session:**

| Slice | Adds | Defers (with PH dependency) |
|---|---|---|
| 2.4 — Provider/AI aliases | `/provider` (top-level alias for `ai providers`) | `/architect-agent`/`/planner`/`/builder`/`/verifier` (PH-03 forge per-role), `/voice` (PH-19 audio), `/chat` (PH-15 conversation) |
| 2.5 — Diagnostic aliases | `/audit` (top-level alias for `doctor --json`) | `/review` (PH-15 PR review), `/security`/`/shield`/`/simulate` (no backing handlers yet) |
| 2.6 — Plugin slash dispatch | `SlashCommandInfo.argv` field + TUI runner uses it when present | full plugin RPC dispatch (PH-15) |

Each slice is shipped as its own commit with its own close-out memo.
At the end, a PHASE2_FINALE_CLOSEOUT.md summarises 2.1–2.8 and
declares Phase 2 complete.

## Slice 2.4 — Provider alias

Implementation:
- `mythic-vibe provider` — new top-level argparse subcommand that
  delegates to `cmd_ai_providers` (no new behaviour, just a friendlier
  name).
- `BuiltinSlashCommand(name="provider", ...)` added to the catalog.

Tests:
- argparse parses `mythic-vibe provider` → routes to `cmd_ai_providers`.
- `/provider` appears in `BUILTIN_SLASH_COMMANDS`.
- Integration smoke: provider lists at least the copy-paste provider.

## Slice 2.5 — Audit alias

Implementation:
- `mythic-vibe audit` — new top-level subcommand that calls
  `cmd_doctor` with `--json` injected (so audit always returns
  machine-readable output).
- `BuiltinSlashCommand(name="audit", ...)` added.

Tests:
- argparse parses `mythic-vibe audit` → routes to `cmd_doctor`.
- `/audit` appears in catalog.
- Integration: `audit` exits cleanly on a fresh project.

## Slice 2.6 — Plugin slash dispatch contract

Implementation:
- Extend `SlashCommandInfo` with `argv: tuple[str, ...] = ()` —
  optional argv list a plugin can register for its slash.
  Backward-compatible (default empty).
- Update `tui/runner.py:command_for_builtin` companion path —
  if a plugin entry has a non-empty `argv`, the TUI dispatches it
  via the same `RunningCommandScreen` instead of the
  "(plugin dispatch not yet implemented)" notice.
- Update `tui/picker.py:CommandPreviewScreen.action_run_command`
  to also accept plugin entries when their underlying
  `SlashCommandInfo` has a non-empty argv.

Tests:
- `SlashCommandInfo(argv=("mythic-vibe", "scan"))` round-trips.
- Plugin fixture registering a slash with argv → discoverable.
- TUI integration: plugin slash with argv runs via runner; without
  argv shows the deferred-dispatch notice.

## Definition of done

- All three slices' tests green; existing 664 stay green.
- Ruff + mypy clean.
- Three close-out memos + PHASE2_FINALE_CLOSEOUT.md.
- Tracker + memory updated to "PH-02 fully complete".
- Pushed.
