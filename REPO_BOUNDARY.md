# Repository Boundary

This repository is a multi-project mythic engineering workspace. The active shipped product is the Mythic Vibe CLI, and its runtime boundary is intentionally narrow.

## Active Runtime Path

The active product runtime lives in:

- `mythic_vibe_cli/`
- `tests/`
- `pyproject.toml`
- active documentation and governance under `docs/`

Changes intended to affect the installable CLI must land inside that active boundary unless an architecture decision explicitly creates an adapter.

## Dormant And Reference Islands

These paths are source material, research, vendor snapshots, or historical runtime fragments. They are not active CLI dependencies:

- `ai/`
- `core/`
- `systems/`
- `sessions/`
- `yggdrasil/`
- `imports/norsesaga/`
- `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/`
- `mindspark_thoughtform/`
- `ollama/`
- `whisper/`
- `chatterbox/`
- `research_data/`
- `docs/research/`
- `docs/specs/`

Dormant code may be studied, copied through an approved provenance workflow, or wrapped behind a documented adapter. It must not become an implicit dependency of `mythic_vibe_cli/`.

## Boundary Law

1. Active CLI code may import Python standard library modules and modules under `mythic_vibe_cli/`.
2. Active CLI code must not import directly from dormant islands or vendor mirrors.
3. Cross-island reuse requires an ADR, a named adapter boundary, and tests proving the adapter contract.
4. Documentation changes must preserve the distinction between active runtime, dormant islands, research, and vendor snapshots.
5. `mythic-vibe doctor --repo-boundary` is the first automated guard for this law.

## Related Records

- `docs/ACTIVE_PRODUCT_BOUNDARY.md`
- `docs/DORMANT_ISLANDS.md`
- `docs/ADRS/ADR-0001-active-runtime-boundary.md`
- `docs/ADRS/ADR-0002-no-direct-vendor-imports.md`
- `docs/DOMAIN_MAP.md`
- `docs/ARCHITECTURE.md`
