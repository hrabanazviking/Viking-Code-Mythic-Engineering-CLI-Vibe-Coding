---
title: "Phase 4 — Slice 4.6 (Real-time diagnostics)"
phase: PH-04
slice: 4.6
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 3d59c1d
status: in_progress
---

# Slice 4.6 — Real-time Diagnostics

## Goal

Make the TUI's events panel feel **alive** — stream new entries from
`mythic/events.jsonl` via tail-style reads, surface a pulse + counter
that ticks when new events arrive, and colour-code by channel kind
(before_*, after_*, error/fail, warn).

## Plan

1. **Tail reader** in `mythic_vibe_cli/runtime/event_log.py`:
   - `EventStreamSnapshot` (frozen dataclass): `entries`,
     `new_in_last_poll`, `total_seen`.
   - `EventTailReader(log_path, window=14)`:
     - Seeds buffer from disk on construction (warm start — existing
       entries don't count as "new").
     - `.poll()` reads only bytes appended since last poll; trims to
       window; updates totals.
     - Robust to: missing file, no-grow, file rotation/truncation
       (size shrunk → re-seed without counting), malformed lines.

2. **Diagnostics panel** in `mythic_vibe_cli/tui/app.py`:
   - Replace `_format_events_panel(entries)` with
     `_format_diagnostics_panel(snapshot)` — header line with `●
     live +N new` or `○ idle` plus `seen: N`, then channel-coloured
     entry lines.
   - Channel colouring: `error|fail` → red, `warn` → yellow,
     `before_*` → cyan, `after_*` → green, default → bold.
   - Border title becomes "Diagnostics".
   - `StatusScreen` holds an `EventTailReader` per session; refresh
     calls `poll()` instead of `read_recent()`.

3. **Tests** (new `tests/test_event_tail_reader.py` + extension to
   existing `tests/test_tui.py`):
   - Tail reader: warm start, no-grow → 0 new, append between polls,
     malformed line skip, file rotation reset, missing file.
   - Formatter: pulse on/off, classify channel colours, empty placeholder.
   - Headless TUI: append event mid-flight → next refresh tick
     surfaces the pulse + counter; existing two events tests still
     pass.

## Definition of done

- All new tests green; existing 605 stay green.
- Ruff + mypy clean.
- `PHASE4_SLICE_4_6_CLOSEOUT.md` written.
- Tracker + memory updated.
- Pushed.
