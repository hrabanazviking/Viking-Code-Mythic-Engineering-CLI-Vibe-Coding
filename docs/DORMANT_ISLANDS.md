# Dormant Islands

Dormant islands are valuable material, but they are not active Mythic Vibe CLI runtime code.

## Why They Are Quarantined

This repository contains research, vendor snapshots, historical runtime fragments, and experimental systems. Without a clear quarantine, contributors can accidentally wire active CLI behavior to code that is incomplete, import-broken, vendor-owned, or designed for another product.

The quarantine protects:

- installable CLI reliability,
- clean dependency direction,
- provenance and licensing clarity,
- contributor orientation,
- future adapter design.

## Dormant Island Inventory

| Island | Paths | Allowed Use | Forbidden Use |
|---|---|---|---|
| Legacy runtime cluster | `ai/`, `core/`, `systems/`, `sessions/`, `yggdrasil/`, `imports/norsesaga/` | Study as source material; extract ideas through reviewed work | Direct imports from `mythic_vibe_cli/` |
| WYRD protocol island | `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/` | Research protocol patterns and future adapters | Implicit CLI dependency |
| MindSpark thoughtform island | `mindspark_thoughtform/` | Research cognition and inference patterns | Product-critical runtime behavior |
| Vendor mirrors | `ollama/`, `whisper/`, `chatterbox/` | Upstream reference snapshots | Direct active CLI imports or local patching as product fixes |
| Research corpus | `research_data/`, `docs/research/`, `docs/specs/` | Inform planning, architecture, and documentation | Runtime authority without implementation and tests |

## Adapter Gate

A dormant island may influence active runtime only after all of the following exist:

1. An ADR describing the need and boundary.
2. A small adapter module inside `mythic_vibe_cli/`.
3. Tests proving the adapter behavior.
4. Documentation updates explaining the dependency and ownership.
5. Provenance notes when code or design is copied.

Until then, dormant islands remain outside the active runtime boundary.
