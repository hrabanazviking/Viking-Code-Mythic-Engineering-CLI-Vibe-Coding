---
title: "Phase 4 — Finale (TUI Layout & Interaction)"
phase: PH-04
slices: 4.1–4.9
opened: 2026-04-29
closed: 2026-04-29
phase_open_head: 855e0ae
phase_close_head: b32d814
phase_open_tests: 538 + 14 subtests
phase_close_tests: 664 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
---

# Phase 4 — TUI Layout & Interaction (Finale)

## What Phase 4 was for

Take the slice-1.x scaffold-and-runtime base and the slice-3.x
multi-agent forge engine and **make them visible**. Phase 4 is the
operator-experience layer: the keyboard-driven Textual TUI where
the seven-phase loop, the Mythic ledger, the diff-review gate, the
plugin event stream, and the slash command catalog all become
tangible.

Master roadmap quadrant vision:

| Quadrant | Slice |
|---|---|
| Loop Navigator (left sidebar) | 4.1 |
| Artifact Viewer (mid-row left) | 4.2 |
| Packet Viewer (mid-row right) | 4.3 |
| Status Bar (bottom) | 4.4 |

Plus five capability slices on top of that layout:

| Capability | Slice |
|---|---|
| Diff review screen (Law 4) | 4.5 |
| Real-time diagnostics stream | 4.6 |
| Uniform `?` help overlay | 4.7 |
| 20-theme support + `t` cycle | 4.8 |
| Accessibility audit lock-in | 4.9 |

## Slice-by-slice ledger

### Slice 4.1 — Loop Navigator sidebar
- `LoopNavigatorEntry` / `LoopNavigatorData` dataclasses + glyph
  table (`>` current, `x` completed, `.` pending).
- 26-column left sidebar with all 7 Mythic phases visible at once.
- +8 tests → 546 total. Commit `1f73b3e`.

### Slice 4.2 — Artifact Viewer panel
- `ArtifactViewerData` + `_format_artifact_viewer` showing the
  active phase's artefacts (codex/handoff/reflection/verification).
- +12 tests → 558 total. Commit `8e1662c`.

### Slice 4.3 — Packet Viewer
- `PacketViewerData` + renderer for the current codex packet
  (prompt / tools / context / metadata).
- +12 tests → 570 total. Commit `5cd80a8`.

### Slice 4.4 — Status Bar
- Replaced the 2x2 grid with a single dense `#status-bar` line:
  project · phase · verify · handoff · plugins · warnings.
- Freed ~14 rows for the mid-row's three panels.
- +9 net tests (1 rewritten) → 579 total. Commit `e026101`.

### Slice 4.5 — Diff review screen (Law 4)
- New module `tui/diff_review.py`: parser + `DiffHunk` /
  `DiffReviewSession` + `DiffReviewScreen` Textual widget.
- Per-hunk accept/reject/skip recorded in a typed session;
  applying to disk deferred to a future slice.
- +26 tests → 605 total. Commit `20fe227`.

### Slice 4.6 — Real-time diagnostics
- New `EventTailReader` + `EventStreamSnapshot` in
  `runtime/event_log.py` — tail-style streaming with byte-offset
  tracking, robust to missing/no-grow/rotation/malformed.
- New `_format_diagnostics_panel` with `● live` / `○ idle` pulse +
  channel-class colour coding.
- "Recent Events" panel renamed to "Diagnostics".
- +16 tests → 621 total. Commit `81c3cd4`.

### Slice 4.7 — Full keymap + `?` help
- New module `tui/help_overlay.py` with `binding_help_pairs`,
  `format_help_table`, stateless `HelpOverlayScreen`.
- Every Screen subclass gets `?` Help that pushes the same overlay
  sourced from its own `BINDINGS` list.
- DiffReviewScreen migrated from inline-toggle to overlay push.
- Audit test enforces every Screen has a `?` binding.
- +11 tests → 632 total. Commit `e3f9018`.

### Slice 4.8 — Theme support
- New module `tui/themes.py`: 6-entry curated `THEME_CYCLE` for the
  `t` key, full 20-entry `TEXTUAL_BUILTIN_THEMES` for `--theme`
  argparse choices, `next_theme` + `validate_theme`.
- `MythicTuiApp(theme=...)` constructor arg + `app.cycle_theme`
  action shared across every screen.
- `mythic-vibe tui --theme NAME` flag.
- Audit verdict on Rich tags: ANSI named colours adapt
  automatically — no migration needed.
- +19 tests → 651 total. Commit `0ee2780`.

### Slice 4.9 — Accessibility audit
- `tests/test_accessibility.py` with 5 invariant suites + an
  AsciiGlyphs sanity audit.
- Locks in: every visible Binding has a description; every
  colour-coded indicator has a non-colour fallback (word/glyph);
  every `action_*` method is bound to a key; key text survives
  `textual-light`; compose-yield order matches reading order.
- No code changes — pure regression-prevention test layer.
- +13 tests → 664 total. Commit forthcoming.

## Cumulative numbers

| Metric | Phase open | Phase close | Δ |
|---|---|---|---|
| Tests | 538 | **664** | +126 |
| Source files | 65 | **75** | +10 |
| New modules in `mythic_vibe_cli/tui/` | n/a | `app.py`, `picker.py`, `runner.py`, `diff_review.py`, `help_overlay.py`, `themes.py` | 6 |
| New runtime surface in `event_log.py` | n/a | `EventStreamSnapshot`, `EventTailReader` | 2 |
| Bindings catalogued | 0 (no audit) | `q` Quit · `r` Refresh · `slash` Picker · `?` Help · `t` Theme · per-screen actions | 7 + per-screen |
| Themes accepted | 1 (default) | 20 (Textual built-ins) | +19 |

Ruff + mypy: clean throughout.

## Master-roadmap integration

The TUI now exposes every existing CLI surface visually:

- `mythic-vibe status` ↔ live status bar (slice 4.4) + auto-refresh
  every 2 s.
- `mythic-vibe slash list` ↔ `/` opens the picker (slice 4.1
  baseline + slice 4.7 help).
- `mythic-vibe scan` / `verify` / `forge` ↔ runnable from the
  picker → preview → `RunningCommandScreen` (live elapsed time +
  exit code).
- Forge ledger / reflection / handoff ↔ Artifact + Packet viewers
  (slices 4.2/4.3) when the active phase has them.
- Plugin event stream ↔ live diagnostics panel (slice 4.6).
- AI response review ↔ `DiffReviewScreen` (slice 4.5).

## What Phase 4 deliberately did not do

- **Plugin / extension / skill / prompt slash dispatch from the
  TUI.** Builtin commands are dispatchable; non-builtins still show
  the "(plugin dispatch not yet implemented)" notice. Belongs to a
  PH-05-ish slice.
- **Apply accepted diff hunks to disk.** Slice 4.5 captures
  decisions; the apply step is deferred to a follow-on (PH-05 or a
  Phase-7 patch-engine slice).
- **Persist theme choice across sessions.** `--theme` covers
  the "I always want X" case; a `mythic/tui_config.json` slot is a
  future polish.
- **Async / inotify-style event streaming.** `set_interval` polling
  is sub-millisecond on the local JSONL file; no platform branches
  needed.
- **Custom Mythic-themed palette.** The 20 built-ins cover
  preferences; a runic-inspired theme would be its own slice.
- **WCAG 2.x contrast ratio measurements.** Slice 4.9 audited that
  the **signal exists in monochrome**, not the contrast of any
  specific rendering — that depends on the user's terminal palette.
- **Real screen-reader testing.** Manual QA session, not automated
  audit territory.

## Phase progression after PH-04

Master roadmap status:

| Phase | Status |
|---|---|
| PH-01 Audit & runtime hygiene | ✅ closed |
| PH-02 Slash & developer-tool shortcuts | 5 of 8 slices done |
| PH-03 Multi-agent forge engine | ✅ closed |
| PH-04 TUI layout & interaction | ✅ closed (this finale) |
| PH-05 ↑ | next active |

Volmarr chooses the next active phase. Suggested candidates:

- **PH-05** if the master roadmap's natural next sequence is the
  immediate-next phase.
- **PH-02 finishing slices** if the developer-tool shortcut backlog
  (3 of 8 remaining) is more pressing than PH-05.
- **PH-13 forge-loop drift detection** if observability is the
  current pain point.

## How to resume

`MEMORY.md` quick-facts line and
`project_mythic_engineering_cli_status.md` are both updated to
HEAD `<close-head>` and "PH-04 closed". `MYTHIC_VIBE_CLI_MASTER_ROADMAP.md`
remains the single authoritative roadmap. `TASK_master_roadmap_and_phase1.md`
tracker is up to date through slice 4.9 close-out.

A future session can resume by opening `TASK_master_roadmap_and_phase1.md`,
locating the "next" row at the bottom, and starting that slice.
