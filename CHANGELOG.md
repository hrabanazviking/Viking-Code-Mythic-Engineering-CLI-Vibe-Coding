# Changelog

All notable changes to this repository's active product documentation and runtime-facing records are documented in this file.

The format is inspired by Keep a Changelog and uses explicit dates for continuity.

## [Unreleased]

### Added

- Added argparse help examples for high-traffic commands: `init`, `next`, `verify`, `packet create`, `reflect`, `resume`, and `doctor`.
- Added Stage 14 UX commands: `examples`, `guide`, `next`, `explain phase`, `explain artifact`, `tutorial`, and `completion`.
- Added optional rich output support behind `MYTHIC_RICH=1` and the `ux` optional dependency group.
- Added shell completion generation for bash, zsh, and Windows PowerShell.
- Added Stage 13 packaging and release-quality configuration, including optional dependency groups for `dev`, `ai`, `docs`, `test`, `lint`, `type`, and `build`.
- Added GitHub Actions CI for tests, coverage, ruff, mypy, changelog checks, package builds, and distribution checks.
- Added `docs/INSTALL.md`, `docs/RELEASE_CHECKLIST.md`, and `scripts/check_changelog.py`.
- Added `mythic-vibe plugin list|inspect|disable` for visible plugin health and control.
- Added `mythic_vibe_cli.plugins` helpers for plugin API contracts, versioned registry records, and entrypoint inspection.
- Added hook declarations for `before_scan`, `after_scan`, `before_packet`, `after_packet`, `before_verify`, `after_verify`, `before_reflect`, and `after_reflect`.
- Added `plugin_manifest.schema.json` for the plugin registry contract.
- Added `mythic-vibe plunder inspect|plan|fetch|apply|record` for staged, lawful single-file reuse.
- Added `mythic_vibe_cli.plunder` helpers for GitHub fetches, license posture, provenance manifests, and NOTICE updates.
- Added `mythic/imports/plunder_plan.json`, `mythic/imports/plunder_manifest.json`, and local plunder cache support.
- Added Apache/MIT/BSD compatibility notes and "Do not plunder" warnings for unknown or incompatible licenses.
- Added `mythic-vibe reflect`, `mythic-vibe handoff create|show|latest`, and `mythic-vibe resume` for durable session continuity.
- Added timestamped handoff artifacts under `mythic/handoffs/` plus `docs/SESSION_HANDOFF.md` generation.
- Added latest-handoff linkage in `status` output so the current session handoff is easy to recover.
- Added canonical `docs/INDEX.md` and `docs/COMMAND_CONTRACTS.md` scaffolding during project initialization.
- Added `docs/ADRS/ADR-0003-verification-gates.md` and `docs/ADRS/ADR-0004-doctor-diagnostics.md`.
- Added structured `doctor` reporting with required-artifact, state-coherence, docs-drift, and boundary sections.
- Added `mythic-vibe verify` with command execution, changed-file review, docs checks, invariant checks, and durable verification records.
- Added `mythic/verifications/` artifacts with a `latest.json` pointer.
- Added a reflect gate so `mythic-vibe checkin --phase reflect` refuses to proceed until a successful verification exists.
- Added `mythic_vibe_cli.verify` helpers for test running, git diff review, doc checks, and invariant checks.
- Added provider usage and metadata fields to response objects and JSON command output.
- Added provider-side pricing heuristics so estimated costs are no longer zero for real adapters.
- Added real provider execution for `openai`, `anthropic`, `gemini`, and `openrouter` behind explicit API keys.
- Added provider request and response logging under `mythic/ai/provider_calls.jsonl` with secret redaction.
- Added packet resolution for `mythic-vibe ai test` and `mythic-vibe ai run`, including stored packet IDs and on-disk packet files.
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

- `next` now prioritizes failed or blocked verification records before normal phase guidance, and uses the latest handoff next step when verification is already passing.
- Expanded operator docs with Stage 14 guidance, shell completion setup, and optional rich-output notes.
- Expanded `pyproject.toml` metadata, Python classifiers, package URLs, ruff config, mypy config, and coverage config.
- `grimoire add|list` now writes a versioned plugin registry while preserving the legacy `plugins` list for compatibility.
- Legacy `plunder --repo --source --dest` now refuses silent overwrites unless `--force` is supplied.
- `status` now includes the latest handoff path, ID, and next recommended action when a handoff exists.
- `doctor --repo-boundary` now stays focused on runtime boundary checks, while the normal doctor path handles docs drift and ADR checks.
- Project scaffolding now creates the canonical docs index and command contract files by default.
- Successful verification now updates `last_verification_id` in project state.
- Verification artifacts are now durable, and blocked reflection emits a clear reason instead of pretending the gate passed.
- Real provider responses now include request IDs, usage, estimated cost, and observed cost metadata when available.
- `mythic-vibe ai test` now stays dry-run-only, and `mythic-vibe ai run` now honors `--dry-run` explicitly.
- `copy-paste` and `local` provider modes keep their always-available bridge behavior for inline packet input.
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

