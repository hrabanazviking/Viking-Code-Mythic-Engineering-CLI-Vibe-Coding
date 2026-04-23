# yggdrasil.integration — INTERFACE

## Purpose
External integration boundary between Yggdrasil and host systems.

## Public Interface
- `deep_integration.py` — deeper host/runtime coupling hooks.
- `norse_saga.py` — Norse Saga Engine integration entrypoints.

## Contracts
- Integration adapters must preserve Yggdrasil core invariants while translating external payloads.
- Failures should be surfaced as integration-layer errors without mutating upstream state.

---
**Contract Version**: 1.0 | v8.0.0
