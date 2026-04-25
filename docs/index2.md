# Documentation Hub

This hub orients contributors to the active Mythic Vibe CLI product and the surrounding mythic engineering workspace.

## Start Here

- `REPO_BOUNDARY.md` - repository-level active runtime and dormant island law.
- `docs/ACTIVE_PRODUCT_BOUNDARY.md` - exact product paths and runtime contract.
- `docs/DORMANT_ISLANDS.md` - quarantined reference, research, and vendor surfaces.
- `docs/ARCHITECTURE.md` - active runtime architecture and dependency direction.
- `docs/DOMAIN_MAP.md` - ownership map and routing rules.
- `docs/COMMAND_CONTRACTS.md` - CLI entrypoints, dispatch registry, aliases, and exit codes.
- `docs/DATA_FLOW.md` - state and artifact movement through the active CLI.

## Architecture Decisions

- `docs/ADRS/ADR-0001-active-runtime-boundary.md` - accepted active runtime boundary.
- `docs/ADRS/ADR-0002-no-direct-vendor-imports.md` - no direct dormant-island or vendor imports.

## Operator Docs

- `docs/quickstart.md` - first workflow and setup path.
- `docs/api.md` - command/API contract overview.
- `docs/hardware_profiles.md` - hardware-oriented guidance.
- `docs/DOCUMENTATION_STANDARDS.md` - documentation maintenance rules.
- `docs/SESSION_HANDOFF_TEMPLATE.md` - continuity template for session closure.

## Method And Philosophy

- `docs/SYSTEM_VISION.md` - product vision.
- `docs/PHILOSOPHY.md` - values and engineering stance.
- `MYTHIC_ENGINEERING.md` - method source and local project alignment.

## Boundary Verification

Run these before merging architecture-sensitive work:

```bash
python -m mythic_vibe_cli.cli doctor --repo-boundary --path .
pytest -q
```

If this file is reached through the lowercase `docs/index.md` path, treat it as the same canonical navigation hub.
