---
title: "Phase 15 — Conversation Memory & Compaction"
phase: PH-15
slices: 15.1, 15.2, 15.3, 15.4
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 41d8b26
status: in_progress
---

# Phase 15 — Conversation Memory & Compaction

## Goal (master roadmap)

Persist provider conversations and compact long histories so
context windows are well-used without losing the reasoning trail.

## Storage layout

```
mythic/ai/
  conversations/
    <conversation_id>.json       — structured turn-by-turn record
  summaries/
    <conversation_id>.md         — compacted summary
    <conversation_id>.json       — summary metadata
```

Conversation IDs follow the existing Mythic ID style: `CV-<6 hex>`.

## Slices

### 15.1 — Conversation log (data layer + writer)

- New `mythic_vibe_cli/memory/__init__.py` package
- New `mythic_vibe_cli/memory/conversation.py`:
  - `ConversationTurn` frozen dataclass: role, content, timestamp,
    metadata
  - `ConversationRecord` frozen dataclass: conversation_id,
    provider, model, created_at, updated_at, turns, metadata
  - `record_turn(root, conversation_id, role, content, *, provider,
    model, metadata)` — append-and-update primitive; creates the
    record on first call; bumps `updated_at` on subsequent calls
  - `read_conversation(root, conversation_id)` — load typed record
  - `list_conversations(root)` — sorted list of records
  - `conversation_path_for(root, conversation_id)` — canonical path
  - Best-effort: malformed file → skipped, never raises

Provider-call wiring (e.g. injecting `record_turn` into the AI
provider layer) is **deferred** — slice 15.1 ships the data layer;
provider integration is a follow-up sub-slice.

### 15.2 — Compaction summariser

- New `mythic_vibe_cli/memory/compaction.py`:
  - `summarize_conversation(record, *, keep_recent=3) -> str` —
    pure-Python summariser; preserves decisions / constraints /
    invariants lines verbatim; collapses other turns into a single
    "summary" paragraph; keeps the most recent N turns intact
  - `compact_conversation(root, conversation_id, *, keep_recent=3,
    dry_run=False)` — generates the summary, writes
    `mythic/ai/summaries/<id>.md` + `<id>.json` sidecar; returns
    payload describing the compaction
  - Best-effort and idempotent (re-running over already-compacted
    records produces a fresh summary)

### 15.3 — `mythic-vibe memory show`

- New `mythic-vibe memory` top-level subcommand with `show` /
  `list` actions
- `memory show --id CV-XXXXXX` prints the full record (text or
  JSON via `--json`)
- `memory list` prints all conversation IDs with timestamps and
  turn counts
- `/memory` slash entry; TUI runner allow-list

### 15.4 — `mythic-vibe memory rehydrate`

- `memory rehydrate --phase <phase>` action that:
  - Calls slice 5.4's `build_session_brief(store, phase)` if a
    graph exists
  - Adds the latest conversation summary (slice 15.2) and the
    latest handoff (existing infrastructure)
  - Returns a unified `RehydrationBrief` payload — the operator's
    "what was I doing" cheat-sheet on session resume

## Definition of done

- All new tests green; existing 820 stay green.
- Ruff + mypy clean throughout.
- Each slice ships its own commit; PHASE15_FINALE_CLOSEOUT.md after
  slice 15.4.
- Tracker + memory updated to "PH-15 fully complete".
- Pushed.

## Constraints

- JSON storage for round-trip; markdown rendering for human display.
- All paths use forward slashes in JSON / serialised output.
- `mythic/ai/` is the stable storage root — same prefix the existing
  `cmd_ai_*` family uses.
- No network. No filesystem writes outside the project root.
- Compaction is **additive** — original conversation file is never
  overwritten; the summary lives in its own sidecar.
