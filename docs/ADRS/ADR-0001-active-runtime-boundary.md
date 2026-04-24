# ADR-0001: Active Runtime Boundary

## Status

Accepted

## Context

The repository contains an installable CLI product, multiple dormant runtime islands, research documents, and vendor/reference snapshots. Without an explicit active runtime boundary, contributors can mistake adjacent code for product-critical implementation.

## Decision

The active runtime boundary for Mythic Vibe CLI is:

- `mythic_vibe_cli/`
- `tests/`
- `pyproject.toml`
- active governance and documentation under `docs/` and root continuity records

Dormant islands may be read as source material, but they are not active dependencies.

## Consequences

- CLI implementation work belongs in `mythic_vibe_cli/`.
- Tests for active behavior belong in `tests/`.
- Cross-island runtime dependencies require a new ADR and adapter contract.
- Documentation should continue to label dormant islands as reference material, not product runtime.

## Verification

Run:

```bash
mythic-vibe doctor --repo-boundary --path .
pytest -q
```
