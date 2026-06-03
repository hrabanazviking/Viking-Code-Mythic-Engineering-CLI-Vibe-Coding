# Repository Boundary

**Last updated:** 2026-05-03 (v1.0.0)

This repository is a multi-project mythic engineering workspace. The active shipped product is the Mythic Vibe CLI **v1.0.0**, and its runtime boundary is intentionally narrow.

## Active Runtime Path

The active product runtime lives in:

- `mythic_vibe_cli/` — installable CLI package (~150 source files across ~15 subpackages)
- `tests/` — unit, integration, property (`tests/property/`), snapshot (`tests/snapshots/`), provider-conformance tests
- `tools/` — out-of-package developer tools (`contract_audit.py` docs↔code drift detector)
- `scripts/` — operator scripts (`regenerate_sbom.py`, `check_changelog.py --classify`)
- `packaging/` — distribution templates (Homebrew formula, Scoop manifest, wheelhouse operator guide)
- `pyproject.toml`
- `.github/workflows/` — CI matrix + tag-driven release pipeline
- active documentation and governance under `docs/` (incl. `docs/security/` and `docs/governance/`)

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
5. **Optional dependencies are opt-in via extras and gated by env vars** (v1.0). Runtime base has zero non-stdlib deps. Island adapters (`MYTHIC_ISLAND_<NAME>_ENABLED`), AI providers (per-provider API keys), the chat bridge (`MYTHIC_CHAT_BRIDGE_ENABLED`), TTS (`MYTHIC_VOICE_TTS_ENABLED`), and OpenTelemetry (`MYTHIC_OTEL_ENABLED`) all require explicit operator opt-in.

## v1.0 enforcement gates

The boundary law is enforced by mechanical CI gates, not just by review:

```bash
mythic-vibe doctor --repo-boundary --path .   # original gate from this doc
python tools/contract_audit.py --strict       # PH-19.2 — docs↔code drift detector
ruff check mythic_vibe_cli tests scripts tools
mypy mythic_vibe_cli
pytest -q                                       # 2224 passed at the v1.0.0 cut
```

The cross-subpackage import boundary inside `mythic_vibe_cli/` itself is governed by [ADR-0009](docs/ADRS/ADR-0009-internal-api-surfaces.md) and audited by `mythic_vibe_cli.robustness.api_audit.audit_api_surfaces`.

The v1.0 binding compatibility-policy at [`docs/compatibility_policy.md`](docs/compatibility_policy.md) extends this boundary contract: **Stable**-tier surfaces (per §3 of that doc) are SemVer-governed; deprecations follow announce → wait one minor → remove.

## Related Records

- `docs/ACTIVE_PRODUCT_BOUNDARY.md`
- `docs/DORMANT_ISLANDS.md`
- `docs/compatibility_policy.md` (v1.0 binding)
- `docs/security/threat_model.md` (v1.0 — assets, attackers, mitigations across the boundary)
- `docs/ADRS/ADR-0001-active-runtime-boundary.md` (foundational decision)
- `docs/ADRS/ADR-0002-no-direct-vendor-imports.md`
- `docs/ADRS/ADR-0009-internal-api-surfaces.md` (cross-subpackage rules inside `mythic_vibe_cli/`)
- `docs/ADRS/ADR_SANITY_SWEEP_2026-05-03.md` (v1.0 verification of all 10 ADRs)
- `docs/DOMAIN_MAP.md`
- `docs/ARCHITECTURE.md`
