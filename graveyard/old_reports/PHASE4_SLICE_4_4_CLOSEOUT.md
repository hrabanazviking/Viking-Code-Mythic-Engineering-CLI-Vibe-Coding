---
title: "Phase 4 — Slice 4.4 Close-out (Status Bar)"
phase: PH-04
slice: 4.4
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 855e0ae
head_at_close: e026101
test_baseline_open: 570 + 14 subtests
test_baseline_close: 579 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 4 Slice 4.4 — Status Bar Close-out

## Purpose

Folds the four-panel 2×2 grid (Status / Verify / Handoff / Plugins)
into a single dense status line above the existing footer-line.
The mid-row's three panels (events / artifact / packet) get all
the freed vertical space.

This brings the TUI in line with the master roadmap's Phase 4
quadrant vision:

| Master roadmap quadrant | Slice |
|---|---|
| Loop Navigator (left sidebar) | 4.1 ✅ |
| Artifact Viewer (main left) | 4.2 ✅ |
| Packet Viewer (main right) | 4.3 ✅ |
| Status Bar (bottom) | 4.4 ✅ |

## Layout shift

```
before:                       after:
  Header                        Header
  [Sidebar | Right column:      [Sidebar | Right column:
    [Grid 2x2 (height: 14)]                  [mid-row: 1fr]
    [mid-row: 1fr]              ]
  ]                             [Status bar — 1 line]   <-- NEW
  [Footer line]                 [Footer line]
  [Footer]                      [Footer]
```

The grid's removal frees ~14 rows; the mid-row's three panels
(events / artifact / packet) now have full visible height.

## Status bar shape

```
myproj  ·  phase: build  ·  verify: pass (VER-ABCDE)  ·  handoff: HO-9XYZ  ·  plugins: 2+0  ·  ok
```

Six middle-dot-separated sections in fixed order:

| Section | Content | Source |
|---|---|---|
| Project | basename of `data.path` | `pathlib.Path(data.path).name` |
| Phase | `phase: <current>` | `data.phase` |
| Verify | `verify: <result> (<id>)` or `verify: -` | `data.last_verification_*` |
| Handoff | `handoff: <id>` or `handoff: -` | `data.latest_handoff_id` |
| Plugins | `plugins: <enabled>+<disabled>` | `data.plugins_enabled` / `data.plugins_disabled` |
| Warnings | colour-tagged status | derived |

## Warnings derivation

The rightmost "warnings" section is colour-coded so the operator
sees red / yellow / green at a glance:

| Condition | Tag |
|---|---|
| `last_verification_result == "fail"` | `[red]verify-failed[/red]` |
| `plugins_disabled > 0` | `[yellow]N plugin(s) disabled[/yellow]` |
| Both above | both shown, joined by middle-dot |
| Neither | `[green]ok[/green]` |

When any real warning exists the green "ok" is suppressed — so
the bar always says either `ok` (healthy) or one-or-more named
issues, never both.

## Public surface in `mythic_vibe_cli/tui/app.py`

```python
def _format_status_bar(data: StatusData) -> str
```

Removed (no longer needed):

- `Grid` import from `textual.containers`
- 4 panel widgets: `#panel-status` / `#panel-verify` / `#panel-handoff` / `#panel-plugins`
- 4 panel formatters: `_format_status_panel`, `_format_verify_panel`, `_format_handoff_panel`, `_format_plugins_panel`
- `.panel` CSS class (no remaining users)
- `#grid` CSS rule

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 570 | **579** (+9) |
| Slash builtins | 52 | 52 |
| Argparse handlers | 50 | 50 |
| Source files | 72 | 72 |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

The `+9` is net: 1 existing test (`test_status_screen_renders_panels_in_headless_mode`) was rewritten to query `#status-bar`; 9 new tests added across two new classes (`StatusBarFormatTests` + `TuiStatusBarIntegrationTests`).

## Tests added (9 new + 1 rewritten)

**`StatusBarFormatTests` (8)** — pure formatter against fabricated
`StatusData` instances with selective overrides:

- bar includes project basename, phase, verify, handoff, plugins
- healthy state shows green `ok`
- failed verify surfaces red warning and suppresses the green ok
- disabled plugins surface yellow warning
- multiple warnings join with middle-dot
- missing verification renders dash (`verify: -`)
- missing handoff renders dash (`handoff: -`)
- empty path falls back to `(no project)` placeholder

**`TuiStatusBarIntegrationTests` (1)** — headless TUI renders
`#status-bar` with phase + plugins visible in default project state.

**`TuiHeadlessTests.test_status_screen_renders_status_bar_in_headless_mode`** —
rewritten from the four-panel query to assert that `#status-bar`
surfaces phase + plugins and that the footer-line still carries
the refresh timestamp.

## What this slice deliberately did not do

- Did not surface forge-cycle status in the bar. The forge ledger
  has its own inspection commands (`forge ledger`/`forge reflection`);
  surfacing forge state in the bar would either duplicate or
  conflict with the status data. PH-13 (drift detection) might
  add a unified "live status" stream.
- Did not add a clickable status bar. Slice 4.7 (full keymap)
  may add quick-jump bindings.
- Did not fold the events panel into the status bar. Events are
  high-frequency stream content; the bar is a snapshot. They
  stay in separate widgets. Slice 4.6 (real-time diagnostics)
  may revisit.
- Did not theme the bar. Default Textual palette + Rich tags;
  slice 4.8 (theme support) covers.
- Did not add density modes (compact / extended) for the bar.
  Single dense line for now.

## Phase 4 progress

| Slice | Status |
|---|---|
| 4.1 Loop Navigator sidebar | ✅ done |
| 4.2 Artifact Viewer panel | ✅ done |
| 4.3 Packet Viewer | ✅ done |
| 4.4 Status Bar | ✅ done |
| 4.5 Diff review screen | next |
| 4.6 Real-time diagnostics | open |
| 4.7 Full keymap + `?` help | open |
| 4.8 Theme support | open |
| 4.9 Accessibility audit | open |

**Four of nine Phase 4 slices done.** All four canonical quadrants
of the master roadmap's Phase 4 vision are now in place. Slices
4.5–4.9 add capabilities (diff review, real-time diagnostics, full
keymap, theme support, accessibility) on top of the established
layout.

## Smoke verification

```bash
$ mythic-vibe tui --path .
# Status bar at the bottom (above the footer line):
#   myproj · phase: intent · verify: - · handoff: - · plugins: 0+0 · ok
#
# Mid-row's three panels are taller now:
#   Recent Events     |  Artefacts (intent)         |  Packet (codex_prompt)
```

## Next slice (4.5)

**Diff review screen.** Open from `codex-log` / response ingest
when the response contains code blocks. Each hunk displayed with
green/red highlighting; per-hunk accept/reject keys (`a` / `r` /
`s` / `q`). Only accepted hunks are written to disk — preserves
the slice 3.1 Law 4 ("AI output is never automatically trusted")
at the TUI level.
