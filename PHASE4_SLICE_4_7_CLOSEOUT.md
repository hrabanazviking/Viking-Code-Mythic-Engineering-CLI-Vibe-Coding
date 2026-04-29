---
title: "Phase 4 — Slice 4.7 Close-out (Full keymap + ? help)"
phase: PH-04
slice: 4.7
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: e7895ba
head_at_close: ea82584
test_baseline_open: 621 + 14 subtests
test_baseline_close: 632 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 4 Slice 4.7 — Full Keymap + `?` Help Close-out

## Purpose

Give the operator a single muscle-memory across the whole TUI: press
**`?` on any screen** to see exactly what that screen accepts.
Replaces the slice-4.5-era inline help-line on `DiffReviewScreen`
with a uniform overlay so no screen is special-cased.

Before this slice, only the diff review screen knew how to surface
its own bindings — the other four screens silently relied on
Textual's footer line (which only shows the first few visible
keys). After this slice every screen has a `?` action that pushes
the same `HelpOverlayScreen`, sourced from its own `BINDINGS` list.

## Architecture

### New module — `mythic_vibe_cli/tui/help_overlay.py`

```python
def binding_help_pairs(bindings: list[Binding]) -> list[tuple[str, str]]
def format_help_table(title: str, pairs: list[tuple[str, str]]) -> str
class HelpOverlayScreen(Screen):
    def __init__(self, title: str, pairs: list[tuple[str, str]]) -> None
```

The screen is **stateless** — caller passes title + pairs; overlay
renders. Three dismiss keys (`escape`, `q`, `?`) all map to
`app.pop_screen` so the operator can leave the same way they came in.

`binding_help_pairs` filters out hidden aliases (e.g. `ctrl+c` →
`q`) so the help table shows only the canonical key-per-action.

### Screen-by-screen wiring

| Screen | Before | After |
|---|---|---|
| `StatusScreen` | `q`, `r`, `slash` | + `?` Help |
| `SlashPickerScreen` | `escape` | + `?` Help |
| `CommandPreviewScreen` | `escape`, `r`, `enter` | + `?` Help |
| `RunningCommandScreen` | `escape`, `q` | + `?` Help |
| `DiffReviewScreen` | inline-toggle `?` | overlay-push `?` |

Each screen now has an `action_show_help()` method that calls:

```python
self.app.push_screen(
    HelpOverlayScreen("<title>", binding_help_pairs(self.BINDINGS))
)
```

`DiffReviewScreen` lost the inline `#diff-review-help` widget and
its CSS rule (no longer needed). The constant
`DIFF_REVIEW_BINDINGS_TEXT` is still exported for any non-screen
caller that wants the legacy single-line summary.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 621 | **632** (+11) |
| Source files | 73 | **74** (+1: `help_overlay.py`) |
| Slash builtins | 52 | 52 |
| Argparse handlers | 50 | 50 |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## Tests added (11 total)

`tests/test_help_overlay.py` — three test classes plus an audit:

**`BindingHelpPairsTests` (3)** — pure helper:
- visible bindings pass through verbatim
- hidden bindings (`show=False`) are filtered out
- empty description renders as empty string

**`FormatHelpTableTests` (2)** — pure formatter:
- empty pairs render the `(no bindings registered)` placeholder
- non-empty pairs render with key padding aligned to the longest key

**`HelpBindingAuditTests` (1)** — walk every Screen subclass shipped
under `mythic_vibe_cli.tui` and assert each has a `question_mark`
binding. Sanity floor enforces all six known screens are present
(`StatusScreen`, `SlashPickerScreen`, `CommandPreviewScreen`,
`RunningCommandScreen`, `DiffReviewScreen`, `HelpOverlayScreen`).

**`HelpOverlayIntegrationTests` (5)** — headless TUI:
- `?` from `StatusScreen` pushes overlay; render contains `Status`,
  `Refresh`, `Quit`
- `escape` from overlay pops back to caller `StatusScreen`
- `?` from `SlashPickerScreen` (after defocusing input) pushes
  overlay with `Cancel`
- `?` from `CommandPreviewScreen` pushes overlay with `Run` + `Back`
- `?` from `RunningCommandScreen` pushes overlay with `Back`

Plus `test_tui_diff_review.py::test_question_mark_pushes_help_overlay`
(replaces the old inline-toggle test).

## What this slice deliberately did not do

- **Did not add `q` to `SlashPickerScreen`'s top-level bindings.**
  The picker focuses an `Input` on mount; a `q` binding would either
  be swallowed by the input (if focused) or quit unexpectedly (if
  not). `escape` is the canonical exit there.
- **Did not solve the focused-input quirk.** When the picker's
  search input is focused, printable keys including `?` go to the
  input first. Operator works around it by pressing `escape` to
  defocus, then `?`. A future slice could promote `?` to a priority
  binding, but that has its own footguns (can't type `?` in any
  filter that legitimately needs it).
- **Did not add per-binding category grouping.** The help table is
  flat — slice 4.9 (accessibility audit) might revisit grouping if
  a screen ends up with > 12 bindings.
- **Did not auto-generate help from action docstrings.** The
  description string in each `Binding(...)` is the source of truth
  — that's the same string Textual's footer renders, and keeping it
  the single canonical surface avoids drift.
- **Did not theme the overlay.** Default Textual palette + Rich
  cyan tags. Slice 4.8 (theme support) covers that.

## Phase 4 progress

| Slice | Status |
|---|---|
| 4.1 Loop Navigator sidebar | ✅ done |
| 4.2 Artifact Viewer panel | ✅ done |
| 4.3 Packet Viewer | ✅ done |
| 4.4 Status Bar | ✅ done |
| 4.5 Diff review screen | ✅ done |
| 4.6 Real-time diagnostics | ✅ done |
| 4.7 Full keymap + `?` help | ✅ done |
| 4.8 Theme support | next |
| 4.9 Accessibility audit | open |

**Seven of nine Phase 4 slices done.**

## Smoke verification

```bash
$ mythic-vibe tui --path .
# Press ? from any screen — a centred bordered overlay appears
# listing every visible binding for that screen, with cyan keys
# left-aligned and padded:
#
#   Status — keys
#
#     q              Quit
#     r              Refresh
#     slash          /  Slash picker
#     question_mark  Help
#
# Press Esc, q, or ? again to dismiss back to where you were.
```

## Next slice (4.8)

**Theme support.** Wire Textual's theme system so the operator can
switch between dark, light, and high-contrast palettes. Likely adds
a `mythic-vibe tui --theme <name>` flag plus a new `t` binding on
each screen (or a single switcher slash command). Audit hard-coded
Rich tags (`[green]`, `[red]`, `[cyan]`) so they degrade gracefully
on light themes — many of slice 4.6's diagnostics colours assume a
dark background.
