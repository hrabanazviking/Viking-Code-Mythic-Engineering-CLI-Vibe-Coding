# ADR-0002: No Direct Vendor Or Dormant-Island Imports

## Status

Accepted

## Context

The repository includes vendor mirrors and large dormant code islands. Direct imports from these paths would make the active CLI depend on code outside its package boundary, creating hidden coupling, licensing ambiguity, and unstable release behavior.

## Decision

Active CLI code under `mythic_vibe_cli/` must not directly import from:

- `ai`
- `core`
- `systems`
- `sessions`
- `yggdrasil`
- `imports.norsesaga`
- `mindspark_thoughtform`
- `ollama`
- `whisper`
- `chatterbox`

If reuse is needed, build a small adapter inside `mythic_vibe_cli/`, document the boundary, preserve provenance, and test the adapter.

## Consequences

- Vendor snapshots remain references, not runtime libraries.
- Dormant islands can still inform design through explicit, reviewed work.
- Boundary violations can be detected by `mythic-vibe doctor --repo-boundary`.

## Verification

Run:

```bash
mythic-vibe doctor --repo-boundary --path .
pytest -q
```
