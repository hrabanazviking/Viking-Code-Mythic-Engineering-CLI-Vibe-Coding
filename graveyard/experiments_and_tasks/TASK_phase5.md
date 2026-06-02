---
title: "Phase 5 — Knowledge Graph & Persistent Memory"
phase: PH-05
slices: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: b37661d
status: in_progress
---

# Phase 5 — Knowledge Graph & Persistent Memory

## Goal (master roadmap)

Build a local SQLite-backed knowledge graph that models the
repository's modules, functions, documents, decisions, phases, and
tasks. Use it for relevance-ranked context retrieval, session
rehydration, and drift detection.

## Architecture sketch

**Storage**: `mythic/graph.sqlite3` — single-file SQLite database,
stdlib-only (no SQLAlchemy / no peewee), cross-platform.

**Entity kinds**: `module`, `function`, `document`, `decision`,
`phase`, `task`, `packet`, `verification`, `handoff`.

**Edge kinds**: `contains`, `references`, `mentions`, `supersedes`,
`targets`, `validates`, `resumes`, `precedes`.

**Schema (v1)**:

```sql
schema_version (version INT, applied_at TEXT)
entities (id PK, kind, name, path, metadata, created_at, updated_at, UNIQUE(kind, name))
edges (id PK, src_id FK, dst_id FK, kind, metadata, created_at, UNIQUE(src,dst,kind))
entity_tags (entity_id FK, tag, weight, UNIQUE(entity_id, tag))
```

## Slices

### 5.1 — Schema + migration runner
- `mythic_vibe_cli/context/__init__.py` package
- `mythic_vibe_cli/context/schema.py` — `SCHEMA_V1_SQL`, `MIGRATIONS`,
  `apply_migrations(conn) -> int`
- Tests: schema applies cleanly to empty DB; idempotent re-apply;
  schema_version row tracks current version.

### 5.2 — GraphStore (CRUD over sqlite3)
- `mythic_vibe_cli/context/graph.py` — `GraphStore` class with
  `open(path)`, `close()`, `upsert_entity(kind, name, ...)`,
  `upsert_edge(src, dst, kind)`, `add_tag(...)`, `find_entities(...)`,
  `find_edges(...)`, `entity_neighbours(...)`.
- Idempotent upserts; safe across processes via SQLite's own locking.
- Context-manager pattern for clean teardown.

### 5.3 — Retriever
- `mythic_vibe_cli/context/retriever.py` — `rank_entities(store, query)` and `top_k(store, query, k)`
- v1 ranking: tag overlap + 1-hop neighbourhood expansion.
- Returns typed `RetrievalResult` with score + match-reason fields
  so downstream consumers can debug rankings.

### 5.4 — Rehydrator
- `mythic_vibe_cli/context/rehydrator.py` — `build_session_brief(root, current_phase) -> SessionBrief`
- Brief = recent decisions + current-phase artefacts + recent
  verification + recent handoff + retriever's top-k for the phase.

### 5.5 — `mythic-vibe graph query` CLI
- New top-level `graph` subcommand with `query`, `entity`, `edges`
  subactions
- Read-only; works on the current `mythic/graph.sqlite3`
- `/graph` slash entry

### 5.6 — `mythic-vibe graph visualize`
- New `graph visualize` subaction emitting Mermaid (default) or DOT
- Operator can pipe to Mermaid renderer for visual debugging
- Optional `--node <id>` to focus on neighbourhood

### 5.7 — Packet retriever integration *(scope-bounded)*
- `cmd_codex_pack` consults the retriever when a graph is populated;
  honours `MYTHIC_PACKET_CHAR_BUDGET`
- Falls back to current fixed-file approach when graph is empty
- Backwards-compatible — existing tests stay green

### 5.8 — Drift detector wiring
- `mythic_vibe_cli/drift.py` PH-13 detectors gain optional graph-
  backed implementations that activate when the graph is populated;
  fall back to filesystem heuristics when not
- Same public surface — `scan_for_drift(root)` unchanged

## Definition of done per slice

- All new tests green; existing 724 stay green throughout.
- Ruff + mypy clean.
- Each slice commits with its own close-out memo.
- PHASE5_FINALE_CLOSEOUT.md after slice 5.8 closes the phase.
- Pushed.

## Constraints

- SQLite via stdlib `sqlite3` only — no third-party ORM.
- All paths use forward slashes in JSON / serialised output.
- Graph file lives at `mythic/graph.sqlite3` — same location pattern
  as other Mythic state files.
- No network. No filesystem outside the project root.
- Best-effort ingestion: errors during scan are recorded, not raised.
