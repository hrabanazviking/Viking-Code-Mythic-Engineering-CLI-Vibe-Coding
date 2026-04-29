# TASK — TUI Slice 2: Slash-Commands Picker Screen

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `2bbcf00` — event log + Recent Events panel.

---

## Why this slice

The TUI shows status passively. Users need a way to find the right command without leaving the TUI. A picker screen accessible via `/` opens an interactive list filtered by typed substring, so the operator can browse the catalog (built-in + plugin-contributed) without remembering exact names.

This slice **does not dispatch** the selected command — that's slice 3. The picker shows the catalog, lets the user filter and select, and pushes a preview screen showing the chosen command's description and source. Esc cancels back.

## Goal

Land:

1. A `SlashPickerScreen` Textual screen with:
   - `Input` widget for the substring filter
   - `OptionList` showing matching commands (name + description + source tag)
   - `q` / `Esc` to cancel back; `Enter` to select
2. A `CommandPreviewScreen` Textual screen showing the selected command's metadata
3. Trigger from the main `StatusScreen` via the `/` keybinding (push the picker)
4. Helper that reads builtins + plugin-contributed entries and combines them
5. Tests via `App.run_test()` exercising filter + selection
6. Doc updates

## Interaction model

```
StatusScreen
  ↓  press "/"
SlashPickerScreen [search input, filtered list]
  ↓  type to filter, arrow keys to navigate, Enter to select
CommandPreviewScreen [name, description, source, source_info path]
  ↓  Esc to go back
StatusScreen
```

## Out of scope

- Actually running the selected command (slice 3)
- Fuzzy matching algorithms — just simple substring is enough for now
- Command-name alias collapsing
- Help-text rendering of descriptions richer than the catalog entries already provide

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/tui/picker.py` | NEW — `SlashPickerScreen`, `CommandPreviewScreen`, helpers |
| `mythic_vibe_cli/tui/__init__.py` | Re-export the two screens |
| `mythic_vibe_cli/tui/app.py` | Add `/` binding to `StatusScreen` that pushes the picker |
| `tests/test_tui.py` | New tests for filter, selection, preview, esc-cancel |
| `docs/runtime.md` / `docs/plugins.md` | Brief notes |
| `CHANGELOG.md` + `DEVLOG.md` |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Implement `SlashPickerScreen` + `CommandPreviewScreen`
- [ ] Wire `/` binding from `StatusScreen`
- [ ] Tests: open picker, filter, select, preview, cancel
- [ ] Gates green
- [ ] Docs + CHANGELOG + DEVLOG
- [ ] Memory + push
