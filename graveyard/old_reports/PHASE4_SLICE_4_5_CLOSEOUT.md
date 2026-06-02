---
title: "Phase 4 — Slice 4.5 Close-out (Diff Review Screen)"
phase: PH-04
slice: 4.5
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: ca4a67b
head_at_close: ca4a67b
test_baseline_open: 579 + 14 subtests
test_baseline_close: 605 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 4 Slice 4.5 — Diff Review Screen Close-out

## Purpose

Implements **Law 4** ("AI output is never automatically trusted") at
the TUI level: every hunk in an AI-suggested patch is shown to the
operator for explicit accept / reject. Decisions land in a typed
`DiffReviewSession` that callers can persist or feed into a future
apply step.

This slice ships the *review* half (parser + screen + decision
state). Applying accepted hunks to disk is deliberately a separate
concern — slice 4.5 captures **what the operator chose**; a follow-on
slice can wire the actual apply.

## What landed

New module: **`mythic_vibe_cli/tui/diff_review.py`** — three layers in
one file, intentionally:

| Layer | Surface |
|---|---|
| Data | `DiffLine`, `DiffHunk` (frozen) + `DiffLineKind`, `HunkDecision` literals |
| Session | `DiffReviewSession` mutable dataclass with `record_decision`, `advance`, `retreat`, `accepted_hunks`, `to_dict` |
| Parser | `parse_unified_diff(text) -> list[DiffHunk]` (regex-based; tolerant) |
| Formatters | `_format_hunk_for_review`, `_format_review_progress`, `DIFF_REVIEW_BINDINGS_TEXT` |
| Screen | `DiffReviewScreen(Screen)` — only when Textual is importable |

### Parser behaviour (locked in by tests)

| Input | Behaviour |
|---|---|
| Empty / whitespace-only | `[]` |
| Non-diff prose | `[]` |
| Single-file unified diff | one `DiffHunk` per `@@` block |
| Multi-file diff | `+++ b/<path>` resets `current_file`; one hunk list, multiple paths |
| `@@ -N +N @@` (no count) | `old_count` / `new_count` default to 1 |
| `diff --git`, `old mode`, `new mode` | silently skipped |
| `\ No newline at end of file` | rendered as context |
| `+++ path` (no `b/` prefix) | accepted; the `b/` is optional |

### Hunk line classification

| Marker | Kind | Body text |
|---|---|---|
| `+...` (not `+++`) | `addition` | leading `+` stripped |
| `-...` (not `---`) | `deletion` | leading `-` stripped |
| ` ...` (leading space) | `context` | leading space stripped |
| `\ No newline...` | `context` | preserved verbatim |
| Other in-hunk lines | `context` | preserved |

### Session contract

| Method / property | Meaning |
|---|---|
| `total` | `len(hunks)` |
| `decided_count` | non-pending decisions |
| `is_complete` | empty session → True; otherwise all decided |
| `current_hunk` | hunk at `current_index`, or `None` if empty |
| `record_decision(d)` | sets current hunk's decision; validates against `_VALID_DECISIONS`; no-op on empty session |
| `advance()` / `retreat()` | bool — True iff the index moved |
| `accepted_hunks()` | tuple of accepted hunks in original order |
| `to_dict()` | serialisable snapshot (round-trippable) |

### Screen bindings

| Key | Action |
|---|---|
| `a` | accept current hunk + advance |
| `r` | reject current hunk + advance |
| `s` | skip current hunk + advance |
| `j` / `down` | next hunk (no decision change) |
| `k` / `up` | previous hunk |
| `q` / `escape` | pop the screen |
| `?` | toggle inline bindings hint |

`DiffReviewScreen` is only defined when Textual is importable —
non-TUI consumers can use the parser + dataclasses without paying
the Textual import cost. `__all__` reflects this conditionally.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 579 | **605** (+26) |
| Source files | 72 | **73** (+1: `diff_review.py`) |
| Slash builtins | 52 | 52 |
| Argparse handlers | 50 | 50 |
| Coverage | 76% | 76% (new module fully covered by tests) |
| Ruff / mypy | clean | clean |

## Tests added (26 total)

`tests/test_tui_diff_review.py` — three test classes plus a headless
TUI class.

**`ParseUnifiedDiffTests` (9)** — pure parser:

- empty input → []
- non-diff prose → []
- single hunk: kinds, header counts, leading-marker stripping
- multi-file: file path resets; default count fallback
- `@@ -N +N @@` defaults to count=1
- `diff --git` / mode change lines silently skipped
- `\ No newline...` rendered as context
- `+++ path/to/file.py` (no `b/` prefix) accepted
- `to_dict()` round-trip on a parsed hunk

**`DiffReviewSessionTests` (9)** — pure session state:

- `__post_init__` seeds pending decisions
- decisions length mismatch raises ValueError
- `record_decision` writes the current index
- unknown decision string raises
- empty session: `record_decision` is a no-op
- `advance` / `retreat` clamp at boundaries (return False at ends)
- `is_complete` flips True when all decided
- `accepted_hunks()` preserves original order
- `to_dict()` round-trip on a partially-decided session

**`FormatterTests` (3)** — Rich-tag rendering:

- hunk render contains path, header, `[green]+`, `[red]-`
- progress line counts each decision kind
- empty session → "No hunks" message

**`DiffReviewScreenTests` (4)** — headless TUI via `App.run_test()`:

- screen mounts, header reads "Hunk 1 / 2", body shows the file path
- `a` records `accepted` and advances `current_index`
- `r` / `s` / `j` / `k` flow on a 4-hunk session leaves expected state
- `?` toggles the help text on/off

## Public surface

```python
from mythic_vibe_cli.tui.diff_review import (
    DIFF_REVIEW_BINDINGS_TEXT,
    DiffHunk,
    DiffLine,
    DiffLineKind,
    DiffReviewSession,
    DiffReviewScreen,    # only when Textual is installed
    HunkDecision,
    parse_unified_diff,
)
```

Internal helpers (underscored, exported on `__all__` for test access):
`_format_hunk_for_review`, `_format_review_progress`.

## What this slice deliberately did not do

- **Did not apply hunks to disk.** `accepted_hunks()` is the
  hand-off point; an apply step is a separate slice (likely PH-05
  or a Phase-7 patch-engine slice). The session is intentionally a
  pure decision log so a future apply can also cover dry-run and
  rollback.
- **Did not wire the screen into a slash command.** `mythic-vibe`
  doesn't yet have an entry point that invokes the screen with a
  parsed AI response. Slice 4.6 (real-time diagnostics) or a
  PH-03-adjacent slice will add `forge review <step>` or similar.
- **Did not parse Git's binary-patch format**, rename markers, or
  copy-mode markers. Those skip cleanly without breaking the parser
  but produce no `DiffHunk` for those segments.
- **Did not add diff-syntax highlighting** beyond the green / red
  marker tagging. A richer `Syntax(line, "diff")` render is a Phase
  4.8 (theme support) concern.
- **Did not record decisions to disk.** `to_dict()` is JSON-ready;
  a follow-on slice will define `mythic/diff_reviews/<id>.json` if
  the apply step needs it.

## Phase 4 progress

| Slice | Status |
|---|---|
| 4.1 Loop Navigator sidebar | ✅ done |
| 4.2 Artifact Viewer panel | ✅ done |
| 4.3 Packet Viewer | ✅ done |
| 4.4 Status Bar | ✅ done |
| 4.5 Diff review screen | ✅ done |
| 4.6 Real-time diagnostics | next |
| 4.7 Full keymap + `?` help | open |
| 4.8 Theme support | open |
| 4.9 Accessibility audit | open |

**Five of nine Phase 4 slices done.**

## Smoke verification

```python
>>> from mythic_vibe_cli.tui.diff_review import parse_unified_diff, DiffReviewSession
>>> hunks = parse_unified_diff(open("/tmp/some.diff").read())
>>> session = DiffReviewSession(hunks=tuple(hunks))
>>> session.record_decision("accepted"); session.advance()
>>> session.to_dict()
{'hunks': [...], 'decisions': ['accepted', 'pending', ...], 'current_index': 1, ...}
```

In a real TUI session: `app.push_screen(DiffReviewScreen(session))`
shows the hunk; the operator's keypresses mutate `session` in place.

## Next slice (4.6)

**Real-time diagnostics.** Stream live runtime events from the
`event_log` into a dedicated panel without blocking the UI thread.
Likely uses Textual's `set_interval` (already in use for refresh)
plus a tail-style read of `mythic/event_log.jsonl`. Slice 4.6 is
where the TUI starts to feel *alive* rather than a snapshot viewer.
