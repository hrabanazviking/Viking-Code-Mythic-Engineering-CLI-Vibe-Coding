---
title: "Phase 4 — Slice 4.9 (Accessibility audit — Phase 4 finale)"
phase: PH-04
slice: 4.9
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: a01e36a
status: in_progress
---

# Slice 4.9 — Accessibility Audit (Phase 4 finale)

## Audit lens

For every screen and every renderer in `mythic_vibe_cli/tui/`,
verify:

1. **Keyboard-only operation.** Every action surface (open picker,
   run command, accept hunk, cycle theme, dismiss overlay…) is
   reachable via a registered `Binding`. No mouse-only paths.
2. **Bindings have descriptions.** Every visible binding (`show=True`)
   carries a non-empty description string — so Textual's footer line,
   the slice 4.7 help overlay, and any screen-reader narrating the
   key labels all have something to surface.
3. **Non-colour status signals.** Anywhere we colour-code state (red
   for fail, green for live, cyan for `before_*`), there's also a
   word and/or glyph carrying the same information so a colour-blind
   user, a monochrome terminal, or a high-contrast theme still
   reads correctly.
4. **Theme-agnostic rendering.** Sample-render the TUI under
   `textual-light`. Key text (phase, plugins, channel names, hunk
   diff bodies) must still appear; nothing relies on a dark
   background to be readable.
5. **Focus order.** `compose()` yields widgets in a visually logical
   top-to-bottom order so Tab navigation (when invoked) follows the
   same path the eye does.

## Pre-audit findings (eyeballed)

| Surface | Colour-coded? | Non-colour signal present? |
|---|---|---|
| Status bar warnings | red / yellow / green | words: `verify-failed`, `N plugin(s) disabled`, `ok` |
| Diagnostics pulse | green / dim | glyph + word: `● live` / `○ idle` |
| Diagnostics channels | cyan / green / red / yellow | channel name itself (`before_scan`, `after_verify`, `plugin_error`) |
| Loop nav phase markers | (no colour) | glyph: `>` current, `x` done, `.` pending |
| Diff review hunk lines | green `+` / red `-` | `+` / `-` prefix glyph |
| Status bar verify | colour tag | words: `verify: pass (id)` / `verify: fail (id)` |
| Help overlay keys | cyan column | key string is the canonical signal |

Pre-audit verdict: **no code changes needed**. Every colour-coded
surface already carries text or a glyph that conveys the same state
in monochrome. The slice's value is locking these properties down
with **regression tests** so future work can't quietly remove the
fallback signal.

## Plan

1. **`tests/test_accessibility.py`** — five test classes:
   - `BindingDescriptionAudit` — every visible Binding across all
     six TUI screens has a non-empty description.
   - `NonColourSignalAudit` — for each colour-coded indicator, the
     rendered text also contains the relevant word / glyph: pulse
     contains "live"/"idle" + `●`/`○`, status bar warnings contain
     "ok"/"failed"/"disabled" word, loop nav contains `>`/`x`/`.`,
     diff hunk contains `+`/`-` prefix.
   - `KeyboardActionReachabilityAudit` — every `action_<name>`
     method on a Screen subclass has at least one Binding that
     resolves to it (or to a class-level / app-level alias).
   - `ThemeRenderingAudit` — headless render under `textual-light`
     surfaces key text (phase, plugins, channel names).
   - `FocusOrderAudit` — `StatusScreen.compose()` yields widgets in
     the visual top-to-bottom order (sidebar → mid-row →
     status-bar → footer-line).

2. **`PHASE4_SLICE_4_9_CLOSEOUT.md`** — close-out memo with audit
   table and locked-in invariants.

3. **`PHASE4_FINALE_CLOSEOUT.md`** — single document summarising
   all nine Phase 4 slices, totals, and pointing to the master
   roadmap's PH-05 entry.

4. Tracker + memory updates marking Phase 4 fully complete.

## Definition of done

- New tests green; existing 651 stay green.
- Ruff + mypy clean.
- `PHASE4_FINALE_CLOSEOUT.md` exists, summarising 4.1–4.9.
- Memory + tracker mark Phase 4 complete.
- Pushed.
