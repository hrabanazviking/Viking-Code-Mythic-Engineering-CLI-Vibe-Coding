---
title: "Phase 4 — Slice 4.3 Close-out (Packet Viewer Panel)"
phase: PH-04
slice: 4.3
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: e50aade
head_at_close: 5cd80a8
test_baseline_open: 558 + 14 subtests
test_baseline_close: 570 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 4 Slice 4.3 — Packet Viewer Panel Close-out

## Purpose

Adds a Packet Viewer panel showing a preview of the current codex
packet (the operator-facing `mythic/codex_prompt.md` if present,
falling back to the most recently written `mythic/packets/PKT-*.md`).
The panel sits in the right-column mid-row alongside events and
artifacts, completing the third quadrant of the master roadmap's
Phase 4 vision.

The Loop Navigator (slice 4.1) tells the operator *where* they are.
The Artifact Viewer (slice 4.2) tells them *what's missing*. The
Packet Viewer (this slice) shows *what they're about to send*. The
three panels together turn the TUI into a usable command surface
for the Mythic Engineering loop.

## Layout shift

```
before: mid-row -> [events (1fr)] [artifact (1fr)]
after:  mid-row -> [events (1fr)] [artifact (1fr)] [packet (1fr)]
```

Three equal-width panels share the mid-row. Each refreshes on the
existing 2-second tick.

## Selection logic

`build_packet_viewer_data(root)` picks the packet to display in
this preference order:

1. `mythic/codex_prompt.md` (operator-facing current packet) — this
   is what `codex-pack` / `evoke` / `forge plan` overwrite.
2. Most recently modified `mythic/packets/PKT-*.md` (durable
   historical packet).
3. Empty data → placeholder render pointing at `codex-pack` / `forge plan`.

The "current vs historical" distinction matters: if a forge run
overwrites `codex_prompt.md` mid-session, the panel keeps showing
the freshest content. If the operator deletes `codex_prompt.md`,
the panel falls back to history rather than going blank.

## Public surface in `mythic_vibe_cli/tui/app.py`

```python
PACKET_PREVIEW_LINES = 12

@dataclass
class PacketViewerData:
    packet_id: str            # "codex_prompt" or "PKT-NNNN"
    relpath: str               # path relative to project root
    line_count: int
    byte_size: int
    modified_at: str           # ISO 8601 UTC
    preview_lines: list[str]
    truncated: bool            # True when file has more than the cap

def build_packet_viewer_data(root, *, preview_lines=12) -> PacketViewerData
def _format_packet_viewer(data) -> str

# Internal helpers (slice 4.3)
def _select_packet_path(root) -> Path | None
def _packet_id_from_filename(path) -> str
```

## Render shape

```
codex_prompt
mythic/codex_prompt.md  ·  47 lines  ·  3214B
modified 2026-04-29 21:30:55 UTC

# Mythic Engineering Task Packet

## 1. Role

- Identity: ...

## 2. System prompt
...
... (35 more lines)
```

Header lines are dim; preview body is the file's literal text
(Markdown is rendered as plain text — no syntax highlighting in
this slice).

## Defensive behaviour

- File read decode errors → empty data (panel shows placeholder).
- `stat()` failure → partial data with empty `modified_at` and
  zero `byte_size`.
- `codex_prompt.md` is a directory (corrupt project) → selector
  skips to the `packets/` fallback.
- `mythic/packets/` missing or unreadable → empty data.

The TUI must never crash because a packet file disappeared
mid-refresh; every failure path lands gracefully on the placeholder.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 558 | **570** (+12) |
| Slash builtins | 52 | 52 |
| Argparse handlers | 50 | 50 |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## Tests added (12)

Three test classes in `tests/test_tui.py`:

- **`PacketViewerDataTests` (7)** — empty project; codex_prompt
  preferred (cross-platform path comparison); fallback to most
  recent PKT; preview truncation; no truncation when within cap;
  corrupt codex_prompt-as-dir falls back gracefully; `to_dict`
  round-trip shape.
- **`PacketViewerFormatTests` (3)** — placeholder when empty;
  render includes packet_id + relpath + preview body; truncated
  render shows `(N more lines)` footer.
- **`TuiPacketViewerIntegrationTests` (2)** — headless TUI shows
  placeholder on bare project; renders `codex_prompt` content
  when packet exists.

## What this slice deliberately did not do

- Did not add edit support. The master roadmap mentioned edit-
  before-send as part of slice 4.3, but it wasn't strictly
  required and the read-only preview is the actually-useful
  baseline. A future slice could open the packet in an in-TUI
  editor (`TextArea` widget); for now operators edit packets via
  their own editor and the preview reflects the new content on
  the next refresh tick.
- Did not add syntax highlighting. The packet is plain Markdown
  rendered as text. Slice 4.8 (theme support) could revisit.
- Did not make the packet selector configurable. It's hardcoded
  to prefer `codex_prompt.md`. A `.mythic-vibe.json` override
  could come later.
- Did not surface forge-specific packets. The packet selector
  doesn't know about per-step forge packets at
  `mythic/packets/PKT-*.md` with workflow_id stamps — those land
  in slice 4.7 / PH-13 (drift detection) territory.
- Did not let the operator click a packet to inspect it deeper.
  Slice 4.7 (full keymap) adds the navigation.

## Phase 4 progress

| Slice | Status |
|---|---|
| 4.1 Loop Navigator sidebar | ✅ done |
| 4.2 Artifact Viewer panel | ✅ done |
| 4.3 Packet Viewer | ✅ done |
| 4.4 Status Bar | next |
| 4.5 Diff review screen | open |
| 4.6 Real-time diagnostics | open |
| 4.7 Full keymap + `?` help | open |
| 4.8 Theme support | open |
| 4.9 Accessibility audit | open |

Three of nine Phase 4 slices done. The dashboard now has all four
master-roadmap quadrants in some form (sidebar / left main /
right main / bottom row) — slice 4.4 reshapes the bottom into a
proper Status Bar.

## Smoke verification

```bash
$ mythic-vibe tui --path .
# Right column mid-row now shows three panels:
#   Recent Events      |  Artefacts (intent)        |  Packet (codex_prompt)
#   ...                |  + MYTHIC_ENGINEERING.md   |  codex_prompt
#                      |  + SYSTEM_VISION.md         |  mythic/codex_prompt.md
#                      |  ~ docs/PHILOSOPHY.md       |  47 lines · 3214B
#                                                   |
#                                                   |  # Mythic Engineering Task Packet
#                                                   |  ...
```

## Next slice (4.4)

**Status Bar.** Reshape the bottom area into a single status bar
(project name, active phase, last check-in time, active
warnings) replacing the current 2×2 grid that has been load-bearing
since pre-Phase-4. The 2×2 grid panels (Status / Verify / Handoff /
Plugins) get folded into a single dense status bar; the freed
vertical space gives the mid-row's three panels more breathing
room.
