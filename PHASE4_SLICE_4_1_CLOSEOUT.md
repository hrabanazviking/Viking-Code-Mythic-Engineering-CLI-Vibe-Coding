---
title: "Phase 4 — Slice 4.1 Close-out (Loop Navigator Sidebar)"
phase: PH-04
slice: 4.1
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 997f255
head_at_close: 1f73b3e
test_baseline_open: 538 + 14 subtests
test_baseline_close: 546 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 4 Slice 4.1 — Loop Navigator Sidebar Close-out

## Purpose

First slice of Phase 4 (TUI Revolution v2). The previous TUI
showed status / verification / handoff / plugins in a 2×2 grid,
but the Mythic Engineering loop itself was invisible — operators
had to guess where they were in the cycle from the "Phase: …" line
in the Status panel.

This slice adds a left sidebar dedicated to the loop, showing all
seven phases stacked vertically with state markers so the operator
sees the cycle's shape and their position in it at a glance.

## Layout shift

**Before:**

```
Header
[Grid 2x2: Status / Verify / Handoff / Plugins]
[Events panel]
Footer line
Footer
```

**After:**

```
Header
[Horizontal main-row:
   [Loop sidebar — 26 columns wide]
   [Right column:
      [Grid 2x2 — unchanged]
      [Events panel — unchanged]
   ]
]
Footer line
Footer
```

The 2×2 grid and events panel are intentionally unchanged. Slices
4.2 / 4.3 / 4.4 will eventually replace them with Artifact Viewer /
Packet Viewer / Status Bar; slice 4.1 keeps the existing widgets in
place so the change is strictly additive.

## What landed

### Public surface in `mythic_vibe_cli/tui/app.py`

```python
PHASE_STATE_CURRENT = "current"
PHASE_STATE_COMPLETED = "completed"
PHASE_STATE_PENDING = "pending"

@dataclass
class LoopNavigatorEntry:
    phase: str
    state: str
    marker: str

@dataclass
class LoopNavigatorData:
    entries: list[LoopNavigatorEntry]
    current_phase: str

def build_loop_navigator_data(root: Path) -> LoopNavigatorData
def _format_loop_navigator(data: LoopNavigatorData) -> str
```

### Phase state markers

Single ASCII glyph each — no unicode / emoji, so Windows legacy code
pages render cleanly:

| State | Marker | Rich-tag styling |
|---|---|---|
| `current` | `>` | bold |
| `completed` | `x` | dim |
| `pending` | `.` | default |

### Defensive behaviour

- Missing or unreadable `status.json` → default `ProjectState`
  (every phase pending) — never raises.
- Bogus phase names in `completed_phases` → silently filtered
  against the canonical `core.state.PHASES` set.
- Unknown `current_phase` value → `data.current_phase = ""` and
  every entry lands as pending. (Operator garbage in status.json
  doesn't break the TUI.)

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 538 | **546** (+8) |
| Slash builtins | 52 | 52 |
| Argparse handlers | 50 | 50 |
| Source files | 72 | 72 |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## Tests added (8)

Three test classes in `tests/test_tui.py`:

- **`LoopNavigatorDataTests` (5)** — default state marks `intent`
  current and rest pending; explicit `completed_phases` honoured;
  bogus names filtered; unknown `current_phase` yields all-pending;
  `to_dict()` round-trip shape.
- **`LoopNavigatorFormatTests` (2)** — default render uses `>` glyph
  for current; empty entries yields placeholder text.
- **`TuiLoopNavigatorIntegrationTests` (1)** — headless TUI renders
  the `#loop-nav-panel` widget with every canonical phase visible.

## What this slice deliberately did not do

- Did not replace the 2×2 grid with the Artifact Viewer (slice 4.2).
- Did not add a Packet Viewer panel (slice 4.3).
- Did not reshape the bottom into a proper Status Bar (slice 4.4).
- Did not add keyboard navigation between phase rows. Slice 4.7
  (Full keymap + `?` help screen) covers that.
- Did not surface forge-cycle progress in the loop nav. The forge
  has its own `mythic/forge_ledger.json` and reflections — those
  could overlay the phase markers in a future slice but slice 4.1
  reads only from the project state.
- Did not theme the colours. Default Textual colours used; slice
  4.8 (Theme support) covers customisation.
- Did not add an accessibility/keyboard pass. Slice 4.9 covers
  that.

## Phase 4 progress

| Slice | Status |
|---|---|
| 4.1 Loop Navigator sidebar | ✅ done |
| 4.2 Artifact Viewer | next |
| 4.3 Packet Viewer | open |
| 4.4 Status Bar | open |
| 4.5 Diff review screen | open |
| 4.6 Real-time diagnostics | open |
| 4.7 Full keymap + `?` help | open |
| 4.8 Theme support | open |
| 4.9 Accessibility audit | open |

## Smoke verification

```bash
$ mythic-vibe tui --path .
# Sidebar shows:
#  Loop
#  > intent
#  . constraints
#  . architecture
#  . plan
#  . build
#  . verify
#  . reflect
```

## Next slice (4.2)

**Artifact Viewer panel.** Replaces (or extends alongside) the
current 2×2 grid: a scrollable list of the current phase's
required artefacts (`SYSTEM_VISION.md`, `ARCHITECTURE.md`,
`DOMAIN_MAP.md`, etc.) with present/missing/stale status icons.
Selecting an artefact opens it in an editor panel — a simple
pager for slice 4.2; slice 4.3 turns the editor into the Packet
Viewer.
