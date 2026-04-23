# Yggdrasil — The Nine Worlds Cognitive Architecture

## Purpose
A DAG‑based orchestration layer that routes AI tasks through specialized “realms”, each with a distinct cognitive role. Huginn (thought) retrieves, Muninn (memory) stores, and the Nine Worlds process.

## Owns
- `WorldTree` – central orchestrator.
- `DAGEngine` – task graph execution.
- `Bifrost` – query router (matches requests to realms).
- `LLMQueue` – ensures sequential AI calls with priority.
- `Ravens` (Huginn, Muninn) – retrieval and storage.
- Nine realm modules (under `worlds/`).

## Reads
- Player input (via `router.py`).
- Memory tree (via Huginn) – persistent data in `data/yggdrasil_data/`.

## Does NOT
- Replace the main prompt pipeline – it enhances it (pre‑turn retrieval, post‑turn storage, and on‑demand complex queries).

## Key Concepts
- **Cognitive specialization** – each realm has a unique system prompt, so the AI “thinks” differently in each.
- **DAG workflow** – tasks can run sequentially or in parallel, with dependencies.
- **Memory as a tree** – Muninn stores nodes hierarchically (e.g., `characters/npcs/merchants/`).
- **Helheim** – persistent SQLite backup of the memory tree.