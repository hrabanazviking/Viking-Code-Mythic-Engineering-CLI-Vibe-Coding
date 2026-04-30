---
title: "Phase 15 — Finale (Conversation Memory & Compaction)"
phase: PH-15
slices: 15.1–15.4
opened: 2026-04-29
closed: 2026-04-29
phase_open_head: 41d8b26
phase_close_head: b663c20
phase_open_tests: 820 + 14 subtests
phase_close_tests: 874 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
---

# Phase 15 — Conversation Memory & Compaction (Finale)

## What Phase 15 was for

Persist provider conversations and compact long histories so the
context window stays well-used without losing the reasoning trail.
The phase is a natural follow-up to PH-05 (knowledge graph) — slice
15.4 ties the graph-backed session brief together with the latest
conversation summary and the latest handoff into a one-call
session-resume cheat-sheet.

## Slice-by-slice ledger

### Slice 15.1 — Conversation log data layer
- New `mythic_vibe_cli/memory/__init__.py` package
- `mythic_vibe_cli/memory/conversation.py`:
  - `ConversationTurn` / `ConversationRecord` frozen dataclasses
    with `to_dict` / `from_dict` round-trip
  - `record_turn(root, conversation_id, role, content, ...)` —
    append-and-update primitive; creates record on first call;
    bumps `updated_at` on subsequent calls; supports mid-session
    provider/model swap
  - `read_conversation` / `list_conversations` / `latest_conversation`
    reader helpers; best-effort (None / empty on missing / corrupt)
  - `new_conversation_id()` — `CV-<6 hex>` via `secrets.token_hex`
  - `render_record_text` for human display
- Provider-call wiring (`cmd_ai_run` integration) deferred — slice
  15.1 ships the data layer.
- 20 tests; commit `e51c0be`.

### Slice 15.2 — Compaction summariser
- `mythic_vibe_cli/memory/compaction.py`:
  - `summarize_conversation(record, *, keep_recent=3)` — pure
    markdown rendering with three sections: salient buckets
    (decisions / constraints / risks / imperatives via case-
    insensitive prefix match), Earlier-turns roll-up, Recent N
    turns verbatim
  - `compact_conversation(root, conversation_id, *, keep_recent,
    dry_run)` — writes `mythic/ai/summaries/<id>.md` + JSON
    sidecar; original conversation file is **never mutated**
    (additive contract); `--dry-run` honoured
  - `latest_summary_for(root, conversation_id)` — slice 15.4 hook
  - `CompactionPayload` frozen dataclass with `to_dict`
- Salient prefix table covers decision / constraint / invariant /
  rule / policy / risk / TODO / note + must/should imperatives.
- 16 tests; commit `ea32851`.

### Slices 15.3 + 15.4 — `mythic-vibe memory` CLI
- New top-level `memory` subcommand with four actions:
  - `list` — every conversation, sorted newest-first
  - `show --id` — full transcript or JSON
  - `compact --id` — generates summary sidecar; `--keep-recent`
    + `--dry-run` honoured
  - `rehydrate --phase` — unified brief combining graph
    `SessionBrief` (PH-05 slice 5.4) + latest conversation summary
    + latest handoff
- `/memory` slash entry; TUI runner allow-list; test_cli_kernel
  expected-set updated.
- 18 tests; commit `b663c20`.

## Cumulative numbers

| Metric | Phase open | Phase close | Δ |
|---|---|---|---|
| Tests | 820 | **874** | +54 |
| Source files | 83 | **86** | +3 |
| Slash builtins | 56 | **57** | +1 (`memory`) |
| Argparse handlers | 54 | **55** | +1 (`memory` dispatch) |
| New memory modules | 0 | **3** | `__init__.py`, `conversation.py`, `compaction.py` |

Ruff + mypy clean throughout.

## Master-roadmap target table

The Phase 15 goal from the master roadmap:

> Persist provider conversations and compact long histories so context
> windows are well-used without losing reasoning trail.

| Goal element | Status |
|---|---|
| Persist provider conversations | ✅ data layer ready (`record_turn`); provider-call hooks deferred |
| Compact long histories | ✅ slice 15.2 deterministic algorithm |
| Context windows well-used | ✅ keep-recent passthrough + earlier-turns roll-up |
| Reasoning trail preserved | ✅ salient-line bucketing (decisions / constraints / risks / imperatives) |

## What Phase 15 deliberately did not do

- **Did not auto-record provider calls.** The data layer is ready;
  hooking `cmd_ai_run` / `cmd_ai_test` / `cmd_ai_ingest_response`
  to call `record_turn` is a follow-up sub-slice. Operators can
  populate the log directly via the public API today.
- **Did not implement LLM-driven abstractive summarisation.** The
  v1 summariser is pure-Python deterministic. A future PH-15 (or
  PH-08 routing) slice can layer an LLM-driven summary on top once
  a configurable provider is reliably available — gated to avoid
  blocking the operator on offline workflows.
- **Did not extract embedding vectors.** Embedding-based retrieval
  is the natural next step but belongs in a phase that owns the
  embedding model lifecycle (PH-08 or its own slice).
- **Did not rewrite old turns.** The compaction summary is an
  additive sidecar — the original conversation file is read-only
  to slice 15.2. A future "archive old turns" slice could move
  ancient turns into a cold-storage subfolder; explicitly out of
  scope here because deletion is irreversible and the operator
  must own that decision.
- **Did not build a TUI memory panel.** `mythic-vibe memory list`
  and `show` are CLI-only; a TUI panel would mirror the slice 13.4
  drift dashboard pattern but isn't requested yet.

## Phase progression after PH-15

Master roadmap status snapshot:

| Phase | Status |
|---|---|
| PH-01 Audit & runtime hygiene | ✅ closed |
| PH-02 Slash command surface expansion | ✅ closed |
| PH-03 Multi-agent forge engine | ✅ closed |
| PH-04 TUI layout & interaction | ✅ closed |
| PH-05 Knowledge graph & persistent memory | ✅ closed |
| PH-13 Drift detection & self-healing | ✅ closed |
| PH-15 Conversation memory & compaction | ✅ closed (this finale) |
| Other phases | open |

**Seven master-roadmap phases now closed.**

## How to resume

`MEMORY.md` and `project_mythic_engineering_cli_status.md` updated
to HEAD `<close-head>`. `TASK_master_roadmap_and_phase1.md` tracker
extended through this finale.

Natural follow-ups:

- **Provider-call recording wire-up** (sub-slice of 15.1) — hook
  `cmd_ai_run` / `cmd_ai_test` / `cmd_ai_ingest_response` to call
  `record_turn` so the log fills automatically.
- **PH-06** Local LLM Sovereignty — leverage rehydrate brief for
  context selection.
- **PH-08** Provider Routing & Hardware-Aware Selection — wire the
  retriever + memory into model selection.
- **PH-11** Security/Sandbox/Permissions.
- **PH-12** CI/CD & Deployment Integration.
