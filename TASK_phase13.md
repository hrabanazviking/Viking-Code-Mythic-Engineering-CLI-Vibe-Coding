---
title: "Phase 13 — Drift Detection & Self-Healing"
phase: PH-13
slices: 13.1, 13.2, 13.3, 13.4
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: ec06f12
status: in_progress
---

# Phase 13 — Drift Detection & Self-Healing

## Roadmap dependency note

Master roadmap declares `depends_on: [PH-05, PH-11]`. PH-05 (Knowledge
Graph & Persistent Memory) is not yet started, and PH-13 slice 13.1
calls for "graph-backed query for orphaned functions, undocumented
modules, superseded decisions". Pragmatic adaptation: ship a
**filesystem-heuristic v1** that detects the same drift categories
without requiring a graph. When PH-05 lands, slice 13.1 can be
re-implemented over the graph as a refinement; slices 13.2 / 13.3 /
13.4 don't change.

PH-11 (Security/Sandbox/Permissions) doesn't gate PH-13 — that
dependency was about safe `heal` execution, which today's heal
already covers via additive-only / no-overwrite semantics.

## Slices

### Slice 13.1 — Drift index (data layer + CLI scan)

- New `mythic_vibe_cli/drift.py` module:
  - `DriftFinding` frozen dataclass (severity, category, path, description)
  - `scan_for_drift(root) -> list[DriftFinding]`
  - Three heuristic detectors:
    1. **`undocumented_handler`** — every `cmd_*` function in
       `commands.py` without a docstring (auditor lens — handlers
       are user-facing surface; a missing docstring means
       `slash inspect` and `--help` lose the description)
    2. **`undocumented_module`** — Python modules under
       `mythic_vibe_cli/` whose first non-blank, non-import,
       non-future line is not a docstring (excludes tests/)
    3. **`superseded_decision_referenced`** — markdown files under
       `docs/decisions/` or `mythic/decisions/` with a
       `status: superseded` (or `deprecated`) frontmatter that are
       still referenced from at least one other markdown file
- New top-level `mythic-vibe drift` subcommand calling
  `scan_for_drift` and rendering findings (text + JSON via `--json`)
- `BuiltinSlashCommand(name="drift", ...)` in catalog
- TUI runner allow-list: `drift` gets `--path`

### Slice 13.2 — Doctor integration

- `cmd_doctor` calls `scan_for_drift` after its existing checks
- Findings appear in the `drift` section of the doctor JSON output
- Severity bumps the overall doctor exit-code only on `error` (today
  the heuristics emit `info` / `warning` only — no behaviour change
  to existing exit code)

### Slice 13.3 — `heal` v2 reconciliation packet

- Replace the scaffold-only `cmd_heal` with a real implementation:
  - Run `scan_for_drift`
  - Group findings by category
  - Write a Scribe-targeted packet to
    `mythic/heal/<timestamp>-reconciliation.md` plus a JSON sidecar
  - Packet describes **additive** reconciliations only — never
    proposes overwriting or deleting existing content
  - Print the packet path on stdout for caller chaining
  - Honour `--dry-run` (compute, don't write)

### Slice 13.4 — TUI drift panel

- New `DriftScreen(Screen)` in `mythic_vibe_cli/tui/drift_panel.py`
  - Lists current drift findings grouped by severity
  - Re-runs `scan_for_drift` on a 5s interval (longer than the main
    refresh — drift checks are heavier than status reads)
  - Bindings: standard `?` / `q` / `escape` / `t` / `r` (refresh now)
- Slash entry `/drift-screen` (or just `/drift` opens the screen
  inside the TUI vs. running the CLI scan from the picker — TBD;
  start with `/drift` opening the screen, `mythic-vibe drift` from
  CLI runs the scan)

## Definition of done

- All four slices' tests green; existing 686 stay green.
- Ruff + mypy clean throughout.
- Four slice close-out memos + PHASE13_FINALE_CLOSEOUT.md.
- Tracker + memory updated to "PH-13 fully complete".
- Pushed.
