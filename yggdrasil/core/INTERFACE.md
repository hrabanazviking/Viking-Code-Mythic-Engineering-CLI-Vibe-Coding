# yggdrasil.core — INTERFACE

## Purpose
Core orchestration primitives for Yggdrasil runtime behavior.

## Public Interface
- `bifrost.py` — bridge/routing orchestration core.
- `dag.py` — dependency graph composition and traversal helpers.
- `llm_queue.py` — queueing boundary for LLM work units.
- `world_tree.py` — world-state tree orchestration.
- `wyrd_system.py` — Wyrd runtime coordination surface.

## Contracts
- Core modules provide deterministic orchestration APIs for higher layers (`router*`, `worlds`, `integration`).
- Data passed across module boundaries should be serializable and explicit (no hidden global mutation).

---
**Contract Version**: 1.0 | v8.0.0
