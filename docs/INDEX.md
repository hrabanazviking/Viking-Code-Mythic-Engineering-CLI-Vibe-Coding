# Documentation Hub

This hub orients contributors to the active Mythic Vibe CLI product (v1.0.0) and the surrounding mythic engineering workspace. If you do not know where to stand, follow the stones in order.

## Start Here

- `README.md` — front door, install paths, command overview.
- `docs/quickstart.md` — first project, first loop, first reflection in five minutes.
- `docs/INSTALL.md` — full install matrix (PyPI / Homebrew / Scoop / wheelhouse / editable / pipx).
- `docs/compatibility_policy.md` — **v1.0 binding contract**: SemVer, Python + OS support window, deprecation cadence, public-surface tier table.

## Boundary And Architecture

- `REPO_BOUNDARY.md` — repository-level active runtime and dormant island law.
- `docs/ACTIVE_PRODUCT_BOUNDARY.md` — exact product paths and runtime contract.
- `docs/DORMANT_ISLANDS.md` — quarantined reference, research, and vendor surfaces.
- `docs/ARCHITECTURE.md` — active runtime architecture and dependency direction.
- `docs/DOMAIN_MAP.md` — ownership map and routing rules.
- `docs/COMMAND_CONTRACTS.md` — CLI entrypoints, dispatch registry, aliases, and exit codes.
- `docs/DATA_FLOW.md` — state and artifact movement through the active CLI.

## Architecture Decisions

- `docs/ADRS/ADR-0001-active-runtime-boundary.md` — accepted active runtime boundary.
- `docs/ADRS/ADR-0002-no-direct-vendor-imports.md` — no direct dormant-island or vendor imports.
- `docs/ADRS/ADR-0003-verification-gates.md` — verification records and reflect gating.
- `docs/ADRS/ADR-0004-doctor-diagnostics.md` — doctor as a first-class diagnostic scanner.
- `docs/ADRS/ADR-0005-island-b-yggdrasil-adapter.md` — Yggdrasil adapter contract.
- `docs/ADRS/ADR-0006-island-c-mindspark-adapter.md` — MindSpark adapter contract.
- `docs/ADRS/ADR-0007-island-d-wyrd-adapter.md` — WYRD adapter contract.
- `docs/ADRS/ADR-0008-island-e-chatterbox-adapter.md` — Chatterbox TTS adapter contract.
- `docs/ADRS/ADR-0009-internal-api-surfaces.md` — internal API surfaces.
- `docs/ADRS/ADR-0010-ai-model-listing-policy.md` — AI model listing policy (static-first with remote opt-in).

## Operator Docs

- `docs/api.md` — command/API contract overview.
- `docs/plugins.md` — operator guide for writing and registering Mythic plugins (eight life-cycle hooks; v1.0 capability declarations + circuit breaker).
- `docs/PLUGIN_AUTHORING_GUIDE.md` — plugin authoring template and conventions.
- `docs/runtime.md` — operator guide for the **ten** runtime primitives in `mythic_vibe_cli/runtime/` (file mutation queue, output guard, event bus, timings, slash-commands catalog, source-info provenance, exec, event log, plus the v1.0 additions cross-process lock and atomic write).
- `docs/hardware_profiles.md` — hardware-oriented guidance (Pi Zero / Pi 5 / desktop / server tiers).
- `docs/DOCUMENTATION_STANDARDS.md` — documentation maintenance rules.
- `docs/RELEASE_CHECKLIST.md` — release and packaging verification checklist + PH-19.7 tag-driven distribution flow.
- `docs/CHAT_BRIDGE_DEPLOYMENT.md` — Matrix / Telegram bridge deployment (systemd / NSSM / launchd).
- `docs/SSH_DEPLOYMENT.md` — SSH-surface deployment notes.
- `docs/INSTALL.md` — install matrix (also linked under "Start Here").
- `docs/quickstart.md` — first workflow walkthrough (also linked under "Start Here").
- `docs/SESSION_HANDOFF.md` — latest generated session handoff summary.
- `docs/SESSION_HANDOFF_TEMPLATE.md` — continuity template for session closure.

## Security And Supply Chain

- `docs/security/threat_model.md` — assets, attackers, mitigations (with file:line anchors).
- `docs/security/sbom.json` — CycloneDX v1.6 dependency manifest. Regenerate via `python scripts/regenerate_sbom.py`.

## Distribution Channels (v1.0)

- `packaging/README.md` — PyPI + Homebrew + Scoop channel inventory + trigger semantics + required secrets.
- `packaging/WHEELHOUSE.md` — operator guide for offline / air-gapped install.
- `packaging/homebrew/mythic-vibe.rb.template` — Homebrew formula template (auto-rendered by `release.yml`).
- `packaging/scoop/mythic-vibe.json.template` — Scoop manifest template (auto-rendered by `release.yml`).

## Governance

- `docs/governance/quarterly_review.md` — architecture-review cadence + agenda.

## Method And Philosophy

- `docs/SYSTEM_VISION.md` — product vision.
- `docs/PHILOSOPHY.md` — values and engineering stance.
- `MYTHIC_ENGINEERING.md` — method source and local project alignment.

## Boundary Verification

Run these before merging architecture-sensitive work:

```bash
python -m mythic_vibe_cli.cli doctor --repo-boundary --path .
python tools/contract_audit.py --strict
pytest -q
ruff check mythic_vibe_cli tests scripts tools
mypy mythic_vibe_cli
```

If this file is reached through the lowercase `docs/index2.md` path, treat it as the same canonical navigation hub.
