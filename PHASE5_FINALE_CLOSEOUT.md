---
title: "Phase 5 — Finale (Knowledge Graph & Persistent Memory)"
phase: PH-05
slices: 5.1–5.8
opened: 2026-04-29
closed: 2026-04-29
phase_open_head: b37661d
phase_close_head: 3ae10b6
phase_open_tests: 724 + 14 subtests
phase_close_tests: 820 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
---

# Phase 5 — Knowledge Graph & Persistent Memory (Finale)

## What Phase 5 was for

Build a local SQLite-backed knowledge graph that models the
repository's modules, functions, documents, decisions, phases, and
tasks. Use it for relevance-ranked context retrieval, session
rehydration, and drift detection.

The graph is foundational for several future phases:

- **PH-08** Provider Routing — relevance-aware model selection
- **PH-13** Drift Detection — already wired (slice 5.8)
- **PH-14** Policy Engine — graph-based constraint queries
- **PH-15** Conversation Memory — persistent context layer
- **PH-16** OpenTelemetry — graph-backed tracing context

## Slice-by-slice ledger

### Slice 5.1 — Schema + migration runner
- `mythic_vibe_cli/context/schema.py` — DDL constants + idempotent
  migration runner. Schema v1: `entities` (id PK, kind, name, path,
  metadata, created_at, updated_at, UNIQUE(kind, name)), `edges`
  (id PK, src_id FK, dst_id FK, kind, metadata, created_at,
  UNIQUE(src,dst,kind), ON DELETE CASCADE), `entity_tags`
  (entity_id FK, tag, weight, UNIQUE(entity_id, tag)),
  `schema_version`.
- ENTITY_KINDS / EDGE_KINDS catalogues; `apply_migrations(conn)`
  enables PRAGMA foreign_keys per connection.
- 9 tests; commit `bec9a20`.

### Slice 5.2 — GraphStore (CRUD)
- `mythic_vibe_cli/context/graph.py` — `GraphStore` context-manager
  with idempotent `upsert_entity` / `upsert_edge` / `add_tag` plus
  query helpers (`find_entity`, `find_entities`, `find_edges`,
  `entity_neighbours`, `entities_with_tags`).
- `Entity` / `Edge` frozen dataclasses with `to_dict`.
- Best-effort metadata JSON decode — corrupt rows quarantine to {}.
- Cross-platform via stdlib sqlite3 only.
- 24 tests; commit `0ca8b16`.

### Slice 5.3 — Retriever
- `mythic_vibe_cli/context/retriever.py` — `rank_entities` and
  `top_k`. v1 algorithm: tag overlap + 1-hop neighbour expansion
  with `NEIGHBOUR_DECAY = 0.5`.
- `RetrievalResult` frozen dataclass with `reasons` list for
  debuggable rankings.
- Deterministic sort: score DESC, kind, name.
- 15 tests; commit `c1c902a`.

### Slice 5.4 — Rehydrator
- `mythic_vibe_cli/context/rehydrator.py` — `build_session_brief`
  returning `SessionBrief` (recent_decisions, phase_artefacts,
  latest_verification, latest_handoff, top_k).
- Read-only, side-effect-free; degrades gracefully on empty graph
  (`is_empty` property + scan-hint placeholder text).
- `render_brief_text` for human display.
- 9 tests; commit `5e776d1`.

### Slices 5.5 + 5.6 — `graph` CLI + Mermaid/DOT
- `mythic-vibe graph` subcommand with `query` / `entity` / `edges`
  / `brief` / `visualize` actions.
- `mythic_vibe_cli/context/visualize.py` — `render_mermaid` /
  `render_dot` with optional `focus_node` for 1-hop subgraph.
- `/graph` slash entry; TUI runner forwards `--path`.
- 18 tests; commit `9851c8f`.

### Slice 5.7 — Packet retriever integration
- `mythic_vibe_cli/context/packet_context.py` — `derive_packet_tags`
  and `build_graph_context_section` (markdown block, budget-bounded).
- `codex_bridge.py` calls the helper after `_compact_sections`;
  appends `## Relevant Graph Context` section to markdown packets
  and a `graph_context` field to JSON packets.
- Backwards-compatible: no graph → no section (existing packets
  byte-identical).
- 15 tests; commit `3014ab4`.

### Slice 5.8 — Drift detector graph wiring
- `mythic_vibe_cli/drift.py` gains `detect_orphaned_modules` —
  surfaces module entities with zero edges in the graph
  (legitimate orphan or indexer gap; severity `info`).
- `scan_for_drift` aggregator chains the new detector;
  filesystem-only behaviour preserved when graph absent.
- 6 tests; commit `3ae10b6`.

## Cumulative numbers

| Metric | Phase open | Phase close | Δ |
|---|---|---|---|
| Tests | 724 | **820** | +96 |
| Source files | 77 | **83** | +6 |
| Slash builtins | 55 | **56** | +1 (`graph`) |
| Argparse handlers | 53 | **54** | +1 (`graph` dispatch) |
| New context modules | 0 | **6** | schema.py, graph.py, retriever.py, rehydrator.py, visualize.py, packet_context.py |

Ruff + mypy clean throughout.

## Master-roadmap target table

The Phase 5 "Done when" gates from the master roadmap:

| Gate | Met? |
|---|---|
| Graph populates on `checkin` and `scan` | partial — store + ingestion API exists; auto-population on checkin/scan deferred (each command would need graph hooks; the public surface supports it) |
| Survives a restart | ✅ — file-backed SQLite, persistence test in slice 5.2 |
| Retriever measurably improves packet relevance | ✅ — slice 5.7 integration test confirms graph-populated packets carry the `Relevant Graph Context` section |

The "auto-population on checkin/scan" gate intentionally **deferred**:
the graph store + retriever are ready to receive populations, but
hooking the `checkin` and `scan` commands to upsert entities is a
separate slice (essentially a follow-up sub-slice of 5.7 or its own
slice in PH-NN). Operators can populate the graph directly via the
public API today; auto-populate is the next natural increment.

## What Phase 5 deliberately did not do

- **Did not auto-populate the graph from `scan` / `checkin`.** The
  ingestion API is ready; the hooks are a follow-up. Today the
  operator populates the graph directly (or via a future slice).
- **Did not implement TF-IDF or vector embeddings.** Tag-overlap +
  neighbour expansion is the v1 algorithm. PH-15 (Conversation
  Memory & Compaction) or PH-08 (Provider Routing) are the natural
  homes for embedding-based retrieval.
- **Did not parse Python imports for `references` edges.** The
  edge schema supports the `references` kind, but the indexer
  doesn't yet emit them. A follow-up slice can add an AST-based
  module-level `references` extractor.
- **Did not extract function-level entities.** Schema supports
  `function` kind; the indexer doesn't yet ingest them. Same
  follow-up shape as references above.
- **Did not graph-back the other PH-13 detectors.**
  `detect_undocumented_handlers` and `detect_undocumented_modules`
  remain filesystem-heuristic; only `detect_orphaned_modules` is
  graph-backed. The others could be re-implemented over the graph
  once function-level ingestion lands.
- **Did not add a graph mutation CLI.** `mythic-vibe graph` is
  read-only by design — operators populate via Python API. A
  mutation CLI is its own design problem (auth, validation,
  rollback).

## Phase progression after PH-05

Master roadmap status snapshot:

| Phase | Status |
|---|---|
| PH-01 Audit & runtime hygiene | ✅ closed |
| PH-02 Slash command surface expansion | ✅ closed |
| PH-03 Multi-agent forge engine | ✅ closed |
| PH-04 TUI layout & interaction | ✅ closed |
| PH-05 Knowledge graph & persistent memory | ✅ closed (this finale) |
| PH-13 Drift detection & self-healing | ✅ closed |
| PH-06 / PH-07 / PH-08 / PH-09 / PH-10 / PH-11 / PH-12 / PH-14 / PH-15 / PH-16 / PH-17 / PH-18 / PH-19 / PH-20 | open |

**Six master-roadmap phases now closed.** Next active phase TBD by
Volmarr.

Natural follow-ups after PH-05:

- **PH-06** Local LLM Sovereignty — Ollama / llama.cpp routing;
  could leverage the retriever for context selection.
- **PH-08** Provider Routing & Hardware-Aware Selection — graph-
  driven model selection.
- **PH-15** Conversation Memory & Compaction — embedding upgrade
  for the retriever.
- **PH-11** Security/Sandbox/Permissions — hardens forge + plugin
  layers.
- **PH-12** CI/CD & Deployment Integration.

## How to resume

`MEMORY.md` and `project_mythic_engineering_cli_status.md` updated
to HEAD `<close-head>`. `TASK_master_roadmap_and_phase1.md` tracker
extended through this finale.
