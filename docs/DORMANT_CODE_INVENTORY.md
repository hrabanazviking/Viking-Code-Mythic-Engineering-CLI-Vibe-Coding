# Dormant Code Inventory

**Last Updated:** 2026-06-02

This document provides a canonical inventory of all dormant islands, borrowed modules, research prototypes, and archived code paths in the repository.

Per the massive codebase hardening plan (Phase 12), these root directories are considered outside the active boundary of `mythic_vibe_cli`. They are intentionally excluded from active runtime imports, release-blocking quality gates, and standard test scans to prevent stale contracts from breaking the active product.

## Inventory

| Directory | Status | Description |
|---|---|---|
| `ai/` | Archived / Legacy | Legacy AI package, superseded by `mythic_vibe_cli/ai/`. |
| `core/` | Archived / Legacy | Legacy core functionality, superseded by `mythic_vibe_cli/core/`. |
| `systems/` | Archived / Legacy | Historical systems code from previous architectures. |
| `sessions/` | Archived / Legacy | Historical session management module. |
| `imports/` | Archived / Legacy | Vendored/borrowed legacy imports (e.g., `norsesaga`). |
| `yggdrasil/` | Adapter-only | Dormant island. The active runtime only interacts with this via the try-import gate in `mythic_vibe_cli/ai/providers/yggdrasil.py`. |
| `mindspark_thoughtform/` | Adapter-only | Dormant island. The active runtime uses the try-import gate in `mythic_vibe_cli/ai/providers/mindspark.py`. |
| `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/` | Adapter-only | Dormant island. Superseded or bridged through `yggdrasil` provider logic in the active CLI. |
| `chatterbox/` | Adapter-only | Dormant island. Future voice/TTS integration. |
| `ollama/` | Archived / Research | Prototype code for local Ollama integration. |
| `whisper/` | Archived / Research | Prototype code for local Whisper TTS/STT integration. |
| `research_data/` | Archived / Data | Stale data, notes, and experimental output. |

## Exclusion Rules

1. **Scans & Audits**: Tools like `scripts/quality_gate.py` and `tools/contract_audit.py` exclude these directories by default.
2. **Packaging**: `pyproject.toml` explicitly only packages `mythic_vibe_cli`, dropping all of the above from the final wheel.
3. **Runtime Protection**: The test suite includes boundary checks (see `tests/test_dormant_isolation.py`) to verify that invoking the active CLI does not implicitly trigger an import from any of these directories.
