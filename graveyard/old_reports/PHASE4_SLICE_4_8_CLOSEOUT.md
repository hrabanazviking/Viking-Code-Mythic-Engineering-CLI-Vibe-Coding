---
title: "Phase 4 — Slice 4.8 Close-out (Theme Support)"
phase: PH-04
slice: 4.8
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: d8bdd28
head_at_close: 6d204d6
test_baseline_open: 632 + 14 subtests
test_baseline_close: 651 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 4 Slice 4.8 — Theme Support Close-out

## Purpose

Let the operator pick the TUI's palette without leaving the keyboard:

- ``mythic-vibe tui --theme <name>`` for a known preference.
- Press ``t`` from any screen to cycle through six broadly-readable
  themes (dark / light / ANSI / Nord / Gruvbox / Monokai).
- All 20 of Textual 8.x's built-in themes are accepted by ``--theme``;
  the cycle is a curated subset for discoverability.

## Audit (Rich tag adaptation)

`grep` for hard-coded Rich tags across `mythic_vibe_cli/tui/`:

| Tag | Where | Theme behaviour |
|---|---|---|
| `[green]` | diagnostics, status bar warnings, formatters | ANSI colour — adapts |
| `[red]` | diagnostics, verify-failed | ANSI colour — adapts |
| `[yellow]` | diagnostics, plugin warnings | ANSI colour — adapts |
| `[cyan]` | help-overlay keys, diagnostics `before_*` | ANSI colour — adapts |
| `[dim]` | timestamps, placeholders | Textual semantic — adapts |
| `[b]` | titles, channel names | Textual semantic — adapts |

**Verdict:** Rich named ANSI colours and the `dim` / `b` semantic
tags are intrinsically theme-adaptive — the terminal renders them
through whatever palette the active theme installs. No hard-coded
hex values to migrate, no per-theme branches needed. The slice
ships *theme switching* without touching the rendering tags.

## New module — `mythic_vibe_cli/tui/themes.py`

```python
DEFAULT_THEME = "textual-dark"
THEME_CYCLE: tuple[str, ...]            # 6 entries — for the `t` key
TEXTUAL_BUILTIN_THEMES: tuple[str, ...] # 20 entries — argparse choices
def next_theme(current: str) -> str
def validate_theme(name: str) -> str
```

`next_theme` wraps at the cycle boundary and **lands off-cycle
themes on the first cycle entry** instead of no-oping — so an
operator launching with ``--theme dracula`` (not on the cycle) and
then pressing ``t`` gets a deterministic anchor instead of a frozen
palette.

`validate_theme` returns the name on hit and raises `ValueError`
listing every valid choice on miss — used as the polite alternative
to argparse's terse `choices=` rejection. Pure-Python, no Textual
import, so the validator works even when Textual isn't installed.

## Wiring

| Surface | Change |
|---|---|
| `MythicTuiApp.__init__` | new keyword arg `theme: str \| None = None`; stored as `_initial_theme` |
| `MythicTuiApp.on_mount` | applies `_initial_theme` if set; swallows any rejection from Textual's setter so a bad name can't crash the TUI |
| `MythicTuiApp.action_cycle_theme` | computes `next_theme(self.theme)` and assigns; never raises |
| `run_tui` | accepts `theme=` and forwards into the App |
| `cmd_tui` | reads `args.theme` and passes through |
| `app.py` argparse | `--theme NAME` with `choices=TEXTUAL_BUILTIN_THEMES` (parse-time rejection) |

### `t` binding, every screen

Each Screen subclass now registers
``Binding("t", "app.cycle_theme", "Theme")``. The action lives on
the App (not duplicated per screen) so the cycle logic has one
home. Six screens covered:

- `StatusScreen`, `SlashPickerScreen`, `CommandPreviewScreen`,
  `RunningCommandScreen`, `DiffReviewScreen`, `HelpOverlayScreen`.

An audit test (`ThemeBindingAuditTests`) walks every Screen subclass
in `mythic_vibe_cli.tui` and asserts the `t` binding exists — same
discipline as slice 4.7's `?` audit. New screens that forget the
binding fail CI.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 632 | **651** (+19) |
| Source files | 74 | **75** (+1: `themes.py`) |
| Slash builtins | 52 | 52 |
| Argparse handlers | 50 | 50 |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## Tests added (19 total)

`tests/test_tui_themes.py` — five test classes:

**`ThemeConstantsTests` (4)** — constants:
- `DEFAULT_THEME == "textual-dark"`
- every `THEME_CYCLE` entry is in `TEXTUAL_BUILTIN_THEMES`
- cycle includes both dark and light
- cycle has no duplicates

**`NextThemeTests` (3)** — cycle behaviour:
- walks through the cycle in order
- wraps at the end → first
- off-cycle input lands on first entry

**`ValidateThemeTests` (2)** — validation:
- accepts every built-in theme
- rejects unknown with the bad name + at least one valid name in the message

**`ThemeBindingAuditTests` (1)** — every Screen subclass under
`mythic_vibe_cli.tui` registers a `t` binding (sanity floor of 6).

**`MythicTuiAppThemeTests` (4)** — headless TUI:
- default construction keeps `textual-dark`
- `MythicTuiApp(theme="textual-light")` applies the theme on mount
- pressing `t` advances `app.theme` to `THEME_CYCLE[1]`
- bogus theme name on construction does not crash mount

**`CmdTuiThemeForwardingTests` (2)** — CLI plumbing:
- `cmd_tui` forwards `args.theme` into `run_tui` (mocked)
- `args.theme` absent → `run_tui` sees `None`

**`TuiArgparseThemeTests` (3)** — argparse:
- known theme accepted (`--theme nord`)
- unknown theme triggers `SystemExit` (with stderr captured)
- default value is `None`

## What this slice deliberately did not do

- **Did not migrate Rich tags to Textual semantic CSS variables.**
  ANSI named colours already adapt to the terminal palette installed
  by each theme; migrating to `$success` / `$error` / `$warning`
  variables would require Textual-rendering Static widgets instead
  of Rich-string updates, and the visual win is marginal.
- **Did not persist theme choice across sessions.** A `mythic/tui_config.json`
  could remember the last-cycled theme — deferred to a follow-on
  slice if there's demand. ``--theme`` already covers the
  "I always want light" case.
- **Did not add per-screen theme overrides.** All screens share the
  app-level theme. A diff-review-specific theme is not a request
  anyone has made.
- **Did not register custom Mythic themes.** The 20 built-ins cover
  the common preferences; a future "mythic-runic" theme would be a
  new slice with its own palette design.
- **Did not add a theme picker UI.** ``--theme`` + ``t`` cover both
  the discoverability and the stick-to-this-one cases. A picker
  screen would be over-engineering.

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
| 4.8 Theme support | ✅ done |
| 4.9 Accessibility audit | next (Phase 4 finale) |

**Eight of nine Phase 4 slices done.** Slice 4.9 closes Phase 4.

## Smoke verification

```bash
$ mythic-vibe tui --path .                  # default textual-dark
$ mythic-vibe tui --path . --theme nord     # launch in Nord
$ mythic-vibe tui --path . --theme bogus    # argparse rejects, exit 2

# Inside the TUI:
#   t  — cycles dark → light → ansi → nord → gruvbox → monokai → dark …
#   ?  — overlay shows "t Theme" alongside every other binding
```

## Next slice (4.9 — Phase 4 finale)

**Accessibility audit.** Walk every screen with the lens of
keyboard-only operation, screen-reader friendliness, contrast (now
that themes are pluggable, sample-render under `textual-light` to
verify nothing relies on a dark background), focus ordering, and
clear motion-based affordances (the slice 4.6 pulse must have a
non-colour fallback). Write `PHASE4_FINALE_CLOSEOUT.md` once 4.9
lands and migrate the master roadmap status to "Phase 4 complete".
