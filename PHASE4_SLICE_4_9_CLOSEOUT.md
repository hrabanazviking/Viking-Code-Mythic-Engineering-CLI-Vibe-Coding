---
title: "Phase 4 — Slice 4.9 Close-out (Accessibility Audit — Phase 4 finale)"
phase: PH-04
slice: 4.9
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: a01e36a
head_at_close: b32d814
test_baseline_open: 651 + 14 subtests
test_baseline_close: 664 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 4 Slice 4.9 — Accessibility Audit Close-out

## Purpose

Close Phase 4 by **locking in** the accessibility properties the
slice 4.1–4.8 work was already respecting, so a future careless
change can't quietly remove the fallback signal a colour-blind /
monochrome / screen-reader user relies on.

This slice is **almost entirely tests** — pure-Python audit
fixtures that fail loudly if any of five invariants regress. No
TUI behaviour changes.

## Findings table

| Surface | Colour signal | Non-colour signal | Locked by test |
|---|---|---|---|
| Status bar warnings | red / yellow / green tags | words: `verify-failed`, `N plugin(s) disabled`, `ok` | `NonColourSignalAudit.test_status_bar_*` (3) |
| Diagnostics pulse | green tag | glyph + word: `● live` / `○ idle` | `NonColourSignalAudit.test_diagnostics_pulse_*` |
| Diagnostics channels | cyan / green / red / yellow | channel name itself | (channel name is a string in the render output) |
| Loop nav phase markers | (none — never coloured) | glyphs: `>` `x` `.` + phase name | `NonColourSignalAudit.test_loop_navigator_uses_ascii_glyphs` |
| Diff review hunks | green `+` / red `-` | `+ ` / `- ` line prefix | `NonColourSignalAudit.test_diff_review_hunk_lines_use_plus_minus_prefix` |
| Help overlay keys | cyan column | key string itself | (key text is the canonical signal) |
| Verify status | colour tag | words: `verify: pass (id)` / `verify: fail (id)` | `NonColourSignalAudit.test_status_bar_failed_verify_says_failed` |

**Audit verdict:** every colour-coded indicator already carries text
or a glyph that conveys the same state in monochrome. **No code
changes needed.** The slice's deliverable is the locking-in test
suite.

## Five invariants now under test

### 1. `BindingDescriptionAudit` (1 test)

Walks every Screen subclass under `mythic_vibe_cli.tui` and asserts
that every visible (`show=True`) `Binding` carries a non-empty
description string. Result: 0 offenders across the 6 screens.

### 2. `NonColourSignalAudit` (6 tests)

Pure-formatter tests — no Textual mount required:

- diagnostics pulse contains `●` + `live` (live state) and `○` +
  `idle` (idle state)
- status bar healthy state contains `ok`
- status bar failed verify contains `verify` + `fail`
- status bar disabled plugins contains `disabled`
- loop navigator render contains all three markers `>` / `x` / `.`
  plus every phase name
- diff review hunk renders use `+ ` / `- ` line prefix beyond the
  red/green tags

### 3. `KeyboardActionReachabilityAudit` (1 test)

For every Screen subclass, walks `cls.__dict__` for `action_<name>`
methods and confirms each one has at least one `Binding` whose
action resolves to it. Result: 0 keyboard-orphaned actions.

### 4. `ThemeRenderingAudit` (1 test)

Mounts `MythicTuiApp(theme="textual-light")` headlessly, asserts
the status bar still contains "phase:" and "plugins:" and the
diagnostics panel still contains "idle" — i.e., key text content
survives a non-default theme.

### 5. `FocusOrderAudit` (1 test)

Mounts `StatusScreen` and walks its top-level children, asserting
the IDs appear in the visual reading order: `main-row` →
`status-bar` → `footer-line`. Tab navigation and screen readers
both follow this order.

### Plus `AsciiGlyphsAudit` (3 tests)

Cross-platform safety — durable rule recorded in
`feedback_volmarr_preferences.md`:

- `_PHASE_GLYPHS` table is pure ASCII
- `DIFF_REVIEW_BINDINGS_TEXT` uses Latin-1-or-below characters
  (the middle-dot separator at U+00B7 is Latin-1 and renders
  cleanly on every modern terminal including Windows legacy code
  pages)
- The diagnostics pulse glyphs are documented at U+25CF / U+25CB
  with assertions that the formatter actually emits them

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 651 | **664** (+13) |
| Source files | 75 | 75 |
| Slash builtins | 52 | 52 |
| Argparse handlers | 50 | 50 |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## What this slice deliberately did not do

- **Did not run a real screen-reader test.** Textual emits ANSI to
  a terminal; verifying with NVDA/JAWS/VoiceOver belongs to a
  PH-04-adjacent manual QA session, not an automated audit.
- **Did not measure WCAG 2.x contrast ratios.** Rich named ANSI
  colours render through whatever palette the active theme installs
  — the actual ratio depends on the user's terminal config. We
  audit *that the signal exists in monochrome*, not the contrast of
  any specific rendering.
- **Did not add an explicit high-contrast theme.** Textual's
  `monokai` and `solarized-dark` are already high-contrast; the
  slice 4.8 `--theme` flag exposes them.
- **Did not implement Tab focus cycling overrides.** Textual's
  default focus order follows compose-yield order, which slice 4.9
  audited as already correct. Any future override goes in slice 4.7
  territory (full keymap), not here.

## Phase 4 progress (final)

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
| 4.9 Accessibility audit | ✅ done |

**🎉 Phase 4 complete — all nine slices shipped.** See
`PHASE4_FINALE_CLOSEOUT.md` for the full Phase-4 retrospective.

## Smoke verification

```bash
$ python -m pytest tests/test_accessibility.py -v
# 13 passed

$ mythic-vibe tui --path . --theme textual-light
# Verify status bar reads phase / plugins / ok in monochrome
# Verify diagnostics ○ idle / ● live with words alongside glyphs
# Verify loop nav shows > / x / . markers next to phase names
# Press / → picker; press ? on each screen for the help overlay;
# press t to cycle theme.
```

## Next phase

PH-04 is closed. The master roadmap's PH-05 (or whatever Volmarr
chooses next) is the next active phase. The Mythic Vibe TUI now
exposes:

- Four-quadrant 2x2 layout (slice 4.1–4.4)
- Diff review screen (slice 4.5)
- Live event diagnostics (slice 4.6)
- Uniform `?` help overlay (slice 4.7)
- 20 themes via `--theme` + `t` cycle (slice 4.8)
- Locked-in accessibility invariants (slice 4.9)
