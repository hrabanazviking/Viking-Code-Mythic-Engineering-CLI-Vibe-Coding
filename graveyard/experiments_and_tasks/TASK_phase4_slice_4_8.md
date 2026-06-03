---
title: "Phase 4 — Slice 4.8 (Theme support)"
phase: PH-04
slice: 4.8
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: d8bdd28
status: in_progress
---

# Slice 4.8 — Theme Support

## Audit (current state)

- **Textual version:** 8.2.4 — exposes `App.theme: str` (settable) and
  `App.available_themes` (dict of registered theme names).
- **Built-in themes shipped by Textual:** `textual-dark` (default),
  `textual-light`, `textual-ansi`, `nord`, `gruvbox`, `monokai`,
  `dracula`, `tokyo-night`, several catppuccin / solarized /
  rose-pine / atom-one variants, `flexoki`. Total 20.
- **Hard-coded Rich tags** in `mythic_vibe_cli/tui/`: `[green]`,
  `[red]`, `[yellow]`, `[cyan]`, `[dim]`, `[b]`. All ANSI named
  colours that map to the terminal's palette — inherently
  theme-adaptive. **Audit verdict:** no per-theme branching needed.
- **CLI surface:** `mythic-vibe tui` → `cmd_tui` (commands.py:3736)
  → `run_tui(root)` (tui/app.py:840). No theme arg today.

## Plan

1. **New module** `mythic_vibe_cli/tui/themes.py`:
   - `DEFAULT_THEME = "textual-dark"`
   - `THEME_CYCLE` — small curated tuple for the `t` keybinding
     (`textual-dark`, `textual-light`, `textual-ansi`, `nord`,
     `gruvbox`, `monokai`).
   - `TEXTUAL_BUILTIN_THEMES` — full set the `--theme` flag accepts.
   - `next_theme(current) -> str` — wrap-around cycle.
   - `validate_theme(name) -> str` — return name if known, else raise
     `ValueError` with the list of valid choices.

2. **Wire `MythicTuiApp`**:
   - Accept `theme: str | None = None` constructor arg.
   - On `on_mount`, if a theme was supplied, call `self.theme = theme`.
   - Add `action_cycle_theme` on the App so any screen binding can
     fire it via `app.cycle_theme` action notation.

3. **`t` binding on every Screen subclass** — use the
   shared `Binding("t", "app.cycle_theme", "Theme")` notation so we
   don't repeat the cycle logic per screen. Audit test gets a sibling
   that asserts every Screen registers `t`.

4. **CLI plumbing**:
   - `app.py` argparse — add `--theme <name>` to the `tui` subparser
     (with `choices=` to reject bogus names at parse time).
   - `commands.py:cmd_tui` — read `args.theme` and pass to
     `run_tui(root, theme=...)`.
   - `tui/app.py:run_tui` — forward into `MythicTuiApp(root, theme=...)`.

5. **Tests** in `tests/test_tui_themes.py` (new):
   - `next_theme` cycle wraps after the last entry.
   - `validate_theme` accepts every name in `TEXTUAL_BUILTIN_THEMES`
     and raises on unknown.
   - `MythicTuiApp(theme="textual-light")` actually applies the
     theme post-mount.
   - Pressing `t` advances `app.theme` to the next entry in the cycle.
   - `cmd_tui` forwards `args.theme` into `run_tui` (mocked).
   - `--theme bogus` is rejected by argparse with non-zero exit.
   - Audit: every Screen subclass under `mythic_vibe_cli.tui`
     registers a `t` binding.

6. **Close-out memo** + tracker + memory + push.

## Definition of done

- Tests green; existing 632 stay green.
- Ruff + mypy clean.
- Pushed.
