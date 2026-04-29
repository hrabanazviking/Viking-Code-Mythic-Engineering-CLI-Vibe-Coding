---
title: "Phase 4 — Slice 4.7 (Full keymap + ? help)"
phase: PH-04
slice: 4.7
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: e7895ba
status: in_progress
---

# Slice 4.7 — Full keymap + `?` help

## Audit (current state)

| Screen | File | Visible bindings | `?` |
|---|---|---|---|
| `StatusScreen` | `tui/app.py` | `q` Quit, `r` Refresh, `slash` /-picker | NO |
| `CommandPreviewScreen` | `tui/picker.py` | `escape` Back, `r` Run | NO |
| `SlashPickerScreen` | `tui/picker.py` | `escape` Cancel | NO |
| `RunningCommandScreen` | `tui/runner.py` | `escape` Back | NO |
| `DiffReviewScreen` | `tui/diff_review.py` | `a` `r` `s` `j` `k` `?` `q` | YES (inline) |

## Plan

1. **New module** `mythic_vibe_cli/tui/help_overlay.py`:
   - `binding_help_pairs(bindings)` — extract visible `(key, description)` from Textual `Binding` objects.
   - `format_help_table(title, pairs)` — Rich-tagged table.
   - `HelpOverlayScreen(title, pairs)` — centred Screen subclass with `escape` / `q` / `?` to dismiss.

2. **Add `?` to every screen**:
   - `StatusScreen` — add `Binding("question_mark", "show_help", "Help")` + `action_show_help()`.
   - `CommandPreviewScreen`, `SlashPickerScreen`, `RunningCommandScreen` — same pattern.
   - `DiffReviewScreen` — replace inline-toggle with overlay push for consistency. Drop the `#diff-review-help` widget and its CSS. Keep `DIFF_REVIEW_BINDINGS_TEXT` exported (other tests assert against it).

3. **Tests** in `tests/test_help_overlay.py` (new):
   - `binding_help_pairs` filters hidden, preserves visible.
   - `format_help_table` shape (title, key column padding, empty case).
   - Headless: `HelpOverlayScreen` mounts, dismisses on `escape`.
   - Per-screen integration: pressing `?` pushes a `HelpOverlayScreen` whose render contains the screen's primary action description.
   - Audit: every Screen subclass in `mythic_vibe_cli.tui` registers a `?` binding.

4. **Close-out**: `PHASE4_SLICE_4_7_CLOSEOUT.md`, tracker, memory, push.

## Definition of done

- New tests green; existing 621 stay green.
- Ruff + mypy clean.
- Each Screen subclass has a registered `?` binding.
- Pushed.
