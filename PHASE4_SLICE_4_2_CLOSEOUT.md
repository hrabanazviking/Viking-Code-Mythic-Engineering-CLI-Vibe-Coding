---
title: "Phase 4 — Slice 4.2 Close-out (Artifact Viewer Panel)"
phase: PH-04
slice: 4.2
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 25dd585
head_at_close: 8e1662c
test_baseline_open: 546 + 14 subtests
test_baseline_close: 558 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 4 Slice 4.2 — Artifact Viewer Panel Close-out

## Purpose

Adds a new TUI panel that shows the current phase's required
artefacts with status icons. The Loop Navigator (slice 4.1) tells
the operator *where they are* in the cycle; the Artifact Viewer
tells them *what's missing or stale* for that phase. Together
they make the Mythic Engineering loop's expectations legible.

## Layout shift

```
[main-row:
   [Loop sidebar (26 cols)]
   [right-column:
      [Grid 2x2 (Status / Verify / Handoff / Plugins)]
      [mid-row:
         [Events panel (50%)] [Artifact panel (50%)]    <-- NEW
      ]
   ]
]
```

The events panel and the new artifact panel split the available
mid-row width 50/50. Both refresh on the existing 2-second tick.

## Status semantics

| Status | Marker | Colour | Trigger |
|---|---|---|---|
| `present` | `+` | green | Path exists with mtime within 14 days |
| `stale` | `~` | yellow | Path exists but mtime > 14 days |
| `missing` | `-` | red | Path doesn't exist |

ASCII glyphs only; Windows legacy code page-safe.

Directory artefacts use the most recent mtime among the directory
itself and its immediate (non-recursive) contents — so adding a
fresh ADR to `docs/ADRS/` flips the directory from `stale` back to
`present` without a recursive walk.

## Per-phase artefact registry

`PHASE_ARTEFACTS` declares the canonical files/dirs each phase
should have authored or updated:

| Phase | Tracked artefacts |
|---|---|
| intent | `MYTHIC_ENGINEERING.md`, `SYSTEM_VISION.md`, `docs/PHILOSOPHY.md` |
| constraints | `docs/INVARIANTS.md`, `docs/RISK_REGISTER.md`, `docs/PHILOSOPHY.md` |
| architecture | `docs/ARCHITECTURE.md`, `docs/DOMAIN_MAP.md`, `docs/DATA_FLOW.md`, `docs/ADRS` |
| plan | `tasks/current_GOALS.md`, `tasks/backlog.md`, `docs/INTERFACES` |
| build | `mythic/codex_prompt.md`, `mythic/packets`, `CHANGELOG.md` |
| verify | `docs/VERIFICATION.md`, `mythic/verifications`, `mythic/verifications/latest.json` |
| reflect | `docs/SESSION_HANDOFF.md`, `docs/DEVLOG.md`, `mythic/handoffs`, `mythic/reflections` |

The lists intentionally overlap (`docs/PHILOSOPHY.md` shows up
under both intent and constraints) — these aren't disjoint
deliverables, they're "what should be alive at this point in the
loop".

## Public surface in `mythic_vibe_cli/tui/app.py`

```python
ARTIFACT_STATUS_PRESENT = "present"
ARTIFACT_STATUS_MISSING = "missing"
ARTIFACT_STATUS_STALE = "stale"

PHASE_ARTEFACTS: dict[str, list[str]]
ARTIFACT_STALE_AFTER_DAYS = 14

@dataclass
class ArtifactEntry:
    relpath: str
    status: str
    marker: str
    age_days: int | None

@dataclass
class ArtifactViewerData:
    phase: str
    entries: list[ArtifactEntry]

def build_artifact_viewer_data(
    root: Path,
    phase: str,
    *,
    stale_after_days: int = ARTIFACT_STALE_AFTER_DAYS,
    now: float | None = None,
) -> ArtifactViewerData

def _format_artifact_viewer(data: ArtifactViewerData) -> str
```

## Defensive behaviour

- Unknown phase name → empty entry list with phase echoed; render shows
  "no canonical artefacts declared for phase 'X'".
- Empty phase string (e.g. when project state has a bogus
  `current_phase`) → "no phase set; nothing to track".
- `stat()` failure on a path → treated as missing; no exception
  propagates.
- `now` keyword exists for tests; production callers pass nothing
  and use `time.time()`.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 546 | **558** (+12) |
| Slash builtins | 52 | 52 |
| Argparse handlers | 50 | 50 |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## Tests added (12)

Three test classes in `tests/test_tui.py`:

- **`ArtifactViewerDataTests` (8)** — unknown phase / empty phase
  / bare-dir all-missing / present-recent / 30-day-old stale /
  directory most-recent-mtime semantics / custom-now-pinning /
  to_dict round-trip.
- **`ArtifactViewerFormatTests` (3)** — empty-phase placeholder /
  empty-entries placeholder with phase name / `[red]` tag for
  missing.
- **`TuiArtifactViewerIntegrationTests` (1)** — headless TUI
  renders `#artifact-panel` with intent's artefacts visible.

## What this slice deliberately did not do

- Did not add scrolling. Textual's `Static` widget overflows; long
  artefact lists truncate visually. Slice 4.7 (full keymap) adds
  proper scroll bindings.
- Did not let the operator click/select an artefact to open it.
  That's slice 4.3 (Packet Viewer) territory — the "open" target
  there is the AI packet, not an arbitrary file.
- Did not let `PHASE_ARTEFACTS` be project-overridable. Future
  customisation could come from `.mythic-vibe.json` — slice 4.7+
  or a config-engine slice.
- Did not surface forge ledger / reflection state in the panel.
  The artefact list is project-state-driven; forge state is
  separate (covered by the existing handoff/verify panels and the
  forge ledger CLI).
- Did not change the staleness threshold per-phase. Some phases
  rotate faster (build) and could benefit from shorter
  thresholds; that refinement waits for operator feedback.

## Phase 4 progress

| Slice | Status |
|---|---|
| 4.1 Loop Navigator sidebar | ✅ done |
| 4.2 Artifact Viewer panel | ✅ done |
| 4.3 Packet Viewer | next |
| 4.4 Status Bar | open |
| 4.5 Diff review screen | open |
| 4.6 Real-time diagnostics | open |
| 4.7 Full keymap + `?` help | open |
| 4.8 Theme support | open |
| 4.9 Accessibility audit | open |

## Smoke verification

```bash
$ mythic-vibe tui --path .
# Sidebar:
#  Loop
#  > intent
#  ...
#
# Right column mid-row:
#  Recent Events           |  Artefacts (intent)
#  ...                     |  + MYTHIC_ENGINEERING.md (3d)
#                          |  + SYSTEM_VISION.md (3d)
#                          |  ~ docs/PHILOSOPHY.md (62d)
```

## Next slice (4.3)

**Packet Viewer panel.** Replaces (or complements) one of the
existing right-column panels with a read/edit view of the current
codex packet. Operator can review and tweak the packet before
sending it to a provider. The eventual layout makes Artifact
Viewer the left main panel and Packet Viewer the right main panel,
matching the master roadmap's Phase 4 vision.
