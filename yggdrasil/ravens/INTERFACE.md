# yggdrasil.ravens — INTERFACE

## Purpose
Knowledge/recollection subsystem built around Huginn + Muninn patterns.

## Public Interface
- `huginn.py` — observation/intel collection interface.
- `muninn.py` — memory/recollection interface.
- `raven_rag.py` — retrieval-augmented composition over raven channels.

## Contracts
- Raven modules exchange normalized records suitable for retrieval and audit.
- Retrieval flows should remain composable by higher-level routers.

---
**Contract Version**: 1.0 | v8.0.0
