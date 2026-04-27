# Changelog

All notable changes to this repository's active product documentation and runtime-facing records are documented in this file.

The format is inspired by Keep a Changelog and uses explicit dates for continuity.

## [Unreleased]

### Added

- Added `mythic-vibe ai providers`, `mythic-vibe ai test`, `mythic-vibe ai run`, and `mythic-vibe ai ingest-response`.
- Added an isolated provider registry with `copy-paste`, `local`, `openai`, `anthropic`, `gemini`, and `openrouter` adapters.
- Added explicit API-key validation and dry-run-first provider behavior.
- Added weighted packet budget allocation so high-priority sections retain more context under truncation.
- Added budget-allocation coverage to verify packet compaction keeps priority sections larger than low-signal ones.
- Added role presets, output formats, safety sections, and context manifest support to packet generation.
- Added JSON packet rendering as a first-class packet output format.
- Added packet context manifest writing to `mythic/context_sources.json`.
- Added `mythic-vibe packet ingest` to import packet artifacts into the local packet store.
- Added `mythic-vibe packet diff` to compare stored packet artifacts.
- Packet ingestion now preserves source path and provenance metadata.
- Added `mythic-vibe packet create`, `mythic-vibe packet show`, and `mythic-vibe packet list`.
- Added packet IDs and metadata files under `mythic/packets/`.
- Renamed the internal packet concept to `PacketBuilder` while keeping `CodexBridge` compatibility.
- Added project-index context into Codex prompt packet generation.
- Added automatic `mythic/project_index.json` writing during packet creation.
- Added `mythic-vibe scan` with project indexing, changed-file mode, docs mode, and JSON output.
- Added `mythic_vibe_cli.context` scanner and indexer modules for local project context mapping.
- Added `.mythicignore` to define local context-scan exclusions.
- Added `python -m mythic_vibe_cli` package execution via `mythic_vibe_cli/__main__.py`.
- Added `mythic_vibe_cli.commands` for command implementations and registry ownership.
- Added `mythic_vibe_cli.output` and `mythic_vibe_cli.errors` as shared command rendering/error helpers.
- Added `mythic_vibe_cli.exit_codes` to name the CLI return-code policy.
- Added shared command controls for JSON output, quiet/verbose output, and dry-run previews where commands can support them safely.
- Added `docs/COMMAND_CONTRACTS.md` for entrypoints, dispatch aliases, and exit-code contracts.
- Added CLI kernel tests for module execution, registry aliases, and exit-code policy.
- Added Stage 0 repository boundary records: `REPO_BOUNDARY.md`, `docs/ACTIVE_PRODUCT_BOUNDARY.md`, `docs/DORMANT_ISLANDS.md`, and two ADRs under `docs/ADRS/`.
- Added `mythic-vibe doctor --repo-boundary` to validate active runtime boundary records and forbidden dormant-island imports.
- Added active product repo-boundary tests.
- Added `docs/INDEX.md` as a canonical documentation navigation map and upkeep protocol.
- Added first formal `CHANGELOG.md` to establish release-facing history discipline.
- Added `docs/DOCUMENTATION_STANDARDS.md` as the durability, drift-control, and update-obligation charter for active docs.
- Added `docs/SESSION_HANDOFF_TEMPLATE.md` for consistent end-of-session continuity capture.

### Changed

- Moved the real CLI kernel into `mythic_vibe_cli/app.py` while preserving `mythic_vibe_cli.cli:main` as the public compatibility entrypoint.
- Extracted command behavior out of `mythic_vibe_cli/app.py` so `app.py` now owns parsing/dispatch while `commands.py` owns command execution.
- Replaced the long command dispatch chain with a `COMMAND_HANDLERS` registry while preserving existing commands and ritual aliases.
- Updated architecture, domain, and API docs for the Stage 1 CLI kernel contract.
- Updated command contract docs to define shared runtime options and machine-readable output behavior.
- Configured pytest to collect only active product tests from `tests/`, preventing dormant islands and vendor mirrors from polluting the active verification gate.
- Fixed config home-directory resolution so `HOME` overrides are honored consistently in tests and nonstandard environments.
- Expanded root `README.md` with explicit documentation governance and continuity obligations.
- Reworked `docs/index.md` into a compatibility redirect to remove duplicated navigation authority.
- Expanded `docs/quickstart.md` with first-loop workflow, bridge usage, and troubleshooting.
- Expanded `docs/ARCHITECTURE.md` with detailed component contracts, risk model, and review checklist.
- Expanded `docs/DOMAIN_MAP.md` with stricter ownership/dependency boundaries and exception protocol.
- Expanded `docs/api.md` with module contracts, compatibility policy, and integration examples.
- Expanded `docs/SYSTEM_VISION.md` with mission detail, UX outcomes, and evolution horizons.
- Expanded `docs/INDEX.md` into a canonical map with update matrices, maintenance cadence, and quality gates.
- Updated `DEVLOG.md` with an additional continuity entry for this scribe-level documentation expansion.

## [2026-04-23]

### Added

- Documentation continuity framework upgrades for active product records.

### Changed

- Multiple core docs were rewritten and expanded for clarity, durability, and contributor onboarding.

