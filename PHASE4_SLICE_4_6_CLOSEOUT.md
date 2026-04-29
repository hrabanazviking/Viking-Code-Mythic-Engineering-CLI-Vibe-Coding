---
title: "Phase 4 — Slice 4.6 Close-out (Real-time Diagnostics)"
phase: PH-04
slice: 4.6
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 3d59c1d
head_at_close: 8f382f8
test_baseline_open: 605 + 14 subtests
test_baseline_close: 621 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 4 Slice 4.6 — Real-time Diagnostics Close-out

## Purpose

Make the TUI's events panel feel **alive**. Before slice 4.6 the
panel re-read the entire `events.jsonl` on every refresh tick and
displayed the result as a static list — there was no signal that
something just happened. After this slice the panel:

- Tracks the file's byte offset between polls and reads only the
  delta (tail-style streaming).
- Surfaces a green ``● live +N new`` pulse the tick after new events
  arrive, otherwise dim ``○ idle``.
- Carries a `seen: N` cumulative counter for the lifetime of the
  TUI session.
- Colour-codes each entry by channel kind: cyan for `before_*`,
  green for `after_*`, red for anything containing `error` /
  `fail`, yellow for `warn`, bold default otherwise.

The panel is now formally renamed **Diagnostics** (was "Recent
Events") to reflect the shift from snapshot view to live stream.

## Architecture

### New surface in `mythic_vibe_cli/runtime/event_log.py`

```python
@dataclass(frozen=True)
class EventStreamSnapshot:
    entries: tuple[EventLogEntry, ...]
    new_in_last_poll: int
    total_seen: int
    def to_dict(self) -> dict[str, Any]: ...

class EventTailReader:
    def __init__(self, log_path: Path, *, window: int = 14) -> None: ...
    def poll(self) -> EventStreamSnapshot: ...
```

`EventTailReader` is **stateful** — one per screen lifetime. On
construction it warm-starts: existing entries on disk populate the
buffer immediately, but the first poll reports `new_in_last_poll == 0`
so they don't flash as live.

### Robustness contract (locked in by tests)

| Condition | Behaviour |
|---|---|
| File missing | empty snapshot; `total_seen` unchanged |
| No growth between polls | `new_in_last_poll == 0` |
| Append between polls | new entries appear at end; `new_in_last_poll == count` |
| Multiple appends collapse | one snapshot delivers them all in order |
| Buffer overflow | trimmed to `window` (configurable, default 14) |
| File rotation / truncation | re-seed buffer; `new_in_last_poll == 0` (rotation isn't a real event) |
| Malformed JSON line | silently skipped |

### New surface in `mythic_vibe_cli/tui/app.py`

```python
def _classify_channel(channel: str) -> str  # Rich colour tag
def _format_diagnostics_panel(snapshot: EventStreamSnapshot) -> str
```

`_format_events_panel` (the old per-entries formatter) is gone — the
diagnostics formatter takes a snapshot and renders the pulse line +
the colour-coded entry list. `StatusScreen.__init__` now constructs
`self._event_reader = EventTailReader(event_log_path_for(self.root))`
and `_refresh_panels` calls `self._event_reader.poll()` instead of
`read_recent(...)`.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 605 | **621** (+16) |
| Source files | 73 | 73 |
| Slash builtins | 52 | 52 |
| Argparse handlers | 50 | 50 |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## Tests added (16 total)

**`EventTailReaderTests` (9)** — pure tail-reader against real temp
files, exercising every branch of the robustness table above:

- missing file → empty snapshot
- warm start seeds buffer without counting "new"
- no-growth poll returns 0 new
- appended event produces a pulse on the next poll
- multiple appends collapse into one snapshot, preserving order
- window trims the buffer correctly (5 events, window=3 → tail of 3)
- rotation / shrink resets the offset and reports 0 new
- malformed lines are silently skipped
- `EventStreamSnapshot.to_dict()` round-trip

**`DiagnosticsFormatTests` (5)** — pure formatter:

- idle pulse renders when `new_in_last_poll == 0`
- live pulse + counter render when `new_in_last_poll > 0`
- empty snapshot still renders pulse line + placeholder
- `_classify_channel` heuristics: cyan / green / red / yellow / bold
- formatter emits the right Rich tag per channel kind

**`TuiDiagnosticsLiveStreamTests` (2)** — headless integration:

- append event mid-flight + press `r` → pulse flips from idle → live,
  counter increments, new entry visible
- panel `border_title` is "Diagnostics"

## What this slice deliberately did not do

- **Did not switch to async / inotify-style streaming.** Textual's
  `set_interval` already polls every 2s; tail-style reads of a small
  JSONL file are sub-millisecond. Async file watching would buy
  nothing on this workload and would add a Windows-vs-POSIX branch.
- **Did not visually distinguish individual "new" entries inside the
  buffer.** The pulse line carries the new-count; per-entry "fresh"
  highlighting would require entry-level state tracking that's not
  worth the complexity.
- **Did not cap `total_seen` or persist it across sessions.** It's a
  session-lifetime counter on purpose — a fresh TUI launch starts at
  zero so the operator can track "what happened while I was watching".
- **Did not add a clear / pause binding.** Slice 4.7 (full keymap +
  `?` help) is the natural home for that.
- **Did not surface forge-loop events specifically.** The reader is
  channel-agnostic; PH-13 may add a forge-only filter view, but
  that's a different lens, not a richer reader.

## Phase 4 progress

| Slice | Status |
|---|---|
| 4.1 Loop Navigator sidebar | ✅ done |
| 4.2 Artifact Viewer panel | ✅ done |
| 4.3 Packet Viewer | ✅ done |
| 4.4 Status Bar | ✅ done |
| 4.5 Diff review screen | ✅ done |
| 4.6 Real-time diagnostics | ✅ done |
| 4.7 Full keymap + `?` help | next |
| 4.8 Theme support | open |
| 4.9 Accessibility audit | open |

**Six of nine Phase 4 slices done.** The TUI now has all four
canonical quadrants (sidebar / artifact / packet / status bar),
diff-review at the slash-command level, and a live diagnostics
stream — all headlessly testable.

## Smoke verification

```python
>>> from mythic_vibe_cli.runtime.event_log import EventTailReader, append_event
>>> reader = EventTailReader(Path("mythic/events.jsonl"))
>>> reader.poll()  # idle, returns warm-start window with new_in_last_poll=0
>>> append_event(...)
>>> reader.poll()  # live, new_in_last_poll incremented
```

In the TUI: open `mythic-vibe tui`, then in another terminal run
`mythic-vibe scan --path .` (or anything that fires plugin events).
Within ~2s the diagnostics panel flips from `○ idle` to
`[green]● live[/green] +1 new` and the new entry appears at the top
in cyan / green per its channel.

## Next slice (4.7)

**Full keymap + `?` help.** Catalogue every binding across every
screen, ensure each screen exposes a `?` key that pushes a help
overlay listing its bindings, and audit consistency (e.g., `q`
quits everywhere, `escape` pops everywhere, `r` refreshes only
where it makes sense). Slice 4.5 already added `?` to the diff
review screen; slice 4.7 generalises the pattern.
