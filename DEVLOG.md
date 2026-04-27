# DEVLOG — The Living Chronicle

**Last updated:** 2026-04-27
**Branch:** development
**Scope:** An ongoing, dated chronicle of meaningful work performed in this repository. Each entry preserves *what happened* and *why it mattered*, so that later sessions can resume with understanding rather than guesswork.
**Purpose:** Continuity of record. The project's memory, kept outside anyone's head.

---

## 2026-04-27 - Stage 12 Plugin and Grimoire System

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Plugins now have a versioned registry, hook declarations, health inspection, and disable controls.
**Scope:** Stage 12 pass, focused on visible extension behavior without destabilizing the core CLI.

### What changed

- Added `mythic_vibe_cli.plugins` modules for plugin API contracts, registry persistence, and entrypoint inspection.
- Added `mythic-vibe plugin list|inspect|disable`.
- Upgraded `grimoire add|list` to use the versioned plugin registry while preserving the legacy `plugins` list shape.
- Added the supported hook set: `before_scan`, `after_scan`, `before_packet`, `after_packet`, `before_verify`, `after_verify`, `before_reflect`, and `after_reflect`.
- Added plugin health reporting and sandbox warnings so local Python extension points are visible before use.
- Added `plugin_manifest.schema.json` for the registry contract.

### Why it matters

Stage 12 moves plugins from loose strings toward observable extension points. The CLI can now show what is registered, what hooks a plugin claims, whether it is disabled, and whether inspection failed.

### Verification

- `pytest -q tests/test_plugins.py tests/test_cli.py::MythicCliRitualTests::test_grimoire_add_and_list tests/test_cli_kernel.py::CliKernelTests::test_grimoire_json_has_no_human_prefix tests/test_cli_kernel.py::CliKernelTests::test_command_registry_preserves_current_commands_and_aliases` -> `6 passed`

### Continuity thread

- The next useful improvement is real hook invocation around scan, packet, verify, and reflect flows. Stage 12 currently makes hooks discoverable and controlled before wiring execution into the core lifecycle.

_Extensions may enter the hall, but they do not take the throne._

## 2026-04-27 - Stage 11 Lawful Plunder System v2

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** `plunder` now has a staged, license-aware, provenance-recording workflow.
**Scope:** Stage 11 pass, focused on safe single-file reuse from GitHub with source traceability.

### What changed

- Added `mythic_vibe_cli.plunder` modules for GitHub access, license posture, and provenance records.
- Added `mythic-vibe plunder inspect|plan|fetch|apply|record`.
- Added Apache/MIT/BSD compatibility classification and "Do not plunder" warnings for unknown or incompatible licenses.
- Added `mythic/imports/plunder_plan.json`, `mythic/imports/plunder_manifest.json`, cache paths, and NOTICE update support.
- Preserved legacy `plunder --repo --source --dest` behavior while making staged reuse the preferred path.

### Why it matters

Stage 11 makes reuse less reckless. Imported code now carries a source trail, license posture, destination, source SHA, and modification note instead of arriving as an anonymous copied file.

### Verification

- `pytest -q tests/test_plunder.py tests/test_cli.py::MythicCliRitualTests::test_plunder_requires_token_env` -> `4 passed`

### Continuity thread

- The next useful improvement is richer license-file capture and source archive checks, but the core legal/provenance path is now real.

_Useful things may be borrowed; careless things become debt._

## 2026-04-27 - Stage 10 Reflection, Handoff, and Continuity Memory

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** `reflect`, `handoff`, and `resume` now preserve session continuity with durable handoff artifacts.
**Scope:** Stage 10 pass, focused on end-of-session memory, status linkage, and future-session recovery.

### What changed

- Added `mythic-vibe reflect` with session-summary capture and handoff generation.
- Added `mythic-vibe handoff create|show|latest` for durable handoff records.
- Added `mythic-vibe resume` to summarize the latest handoff and the next recommended action.
- Wrote timestamped handoff artifacts under `mythic/handoffs/` and refreshed `docs/SESSION_HANDOFF.md`.
- Linked the latest handoff into `status` output so future sessions can find it quickly.

### Why it matters

Stage 10 turns the CLI into a better collaborator at session boundaries. Instead of losing context at the edge of a work cycle, the repo now leaves behind a structured handoff that the next session can use immediately.

### Verification

- `pytest -q` -> `41 passed`

### Continuity thread

- The next useful step after Stage 10 is to use the new handoff flow in real work and see whether the generated summaries stay sharp enough under pressure.

_May the next session arrive to a prepared table._

## 2026-04-27 - Stage 9 Doctor Diagnostics and Drift Checks

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** `doctor` is now a structured diagnostic scanner with state coherence, docs drift, and ADR checks.
**Scope:** Stage 9 pass, focused on health scanning, boundary-aware diagnostics, and canonical docs upkeep.

### What changed

- Added canonical `docs/INDEX.md` and made project scaffolding create it alongside `docs/COMMAND_CONTRACTS.md`.
- Added ADRs for verification gates and doctor diagnostics.
- Expanded `MythicWorkflow.doctor_report()` into a structured diagnostic report with required-artifact, state, docs, and boundary sections.
- Added state coherence checks for phase regression and stale verification linkage.
- Added docs/code drift checks for the command contract, canonical index, and major-change ADRs.
- Kept `doctor --repo-boundary` focused on active runtime boundary checks while leaving docs drift to the normal doctor path.

### Why it matters

Stage 9 makes the CLI feel like a real health scanner instead of a polite file lister. It can now catch phase incoherence, missing canonical docs, and drift between the runtime contract and the written contract.

### Verification

- `pytest -q` -> `39 passed`

### Continuity thread

- The next useful step after Stage 9 would be to deepen the doctor with history-aware age/staleness checks, but the core diagnostic spine is now in place.

_May the scryer report what is true._

## 2026-04-27 - Stage 8 Verification Gate and Durable Records

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Verification is now a first-class CLI command and reflect check-ins are blocked until a successful verification exists.
**Scope:** Stage 8 reality-gate pass, focused on durable verification artifacts, command execution, diff review, and reflect gating.

### What changed

- Added `mythic_vibe_cli.verify` helper modules for test execution, git diff review, invariant checks, and documentation checks.
- Added `mythic-vibe verify` with command, changed-file, docs, invariant, and record flags.
- Added durable verification artifacts under `mythic/verifications/` plus a `latest.json` pointer.
- Updated project state so successful verification records `last_verification_id`.
- Added a reflect gate so `mythic-vibe checkin --phase reflect` is blocked until the latest verification result is `pass`.
- Added CLI tests covering verification recording and the reflect gate.

### Why it matters

Stage 8 turns verification from a recommendation into a real gate. The CLI now refuses to claim reflective completion unless there is a successful verification record to stand on.

### Verification

- `pytest -q` -> `38 passed`

### Continuity thread

- The next Stage 8 follow-through could expand verification commands beyond the default pytest runner, but the gate and durable record path now exist.

_May reality stay louder than ceremony._

## 2026-04-27 - Stage 7 Provider Metadata Hardening

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Provider responses now carry usage, cost hints, and request metadata in a more durable shape.
**Scope:** Stage 7 hardening pass focused on telemetry consistency and clearer provider contracts.

### What changed

- Added provider-level pricing heuristics so estimates no longer report `0.0` across the board for real adapters.
- Extended provider responses with usage and metadata fields.
- Added request IDs, estimated cost, and observed cost fields to real-provider responses when available.
- Kept dry-run responses consistent by giving them token and cost metadata too.
- Surfaced response usage and metadata in `ai test` and `ai run` JSON output.

### Why it matters

This makes provider calls easier to inspect and compare without changing the command flow. The CLI now tells the truth about what it thinks a call will cost, and what the provider actually reported when it answered.

### Verification

- `pytest -q` -> `37 passed`

### Continuity thread

- The next useful hardening step would be a more explicit provider-call audit trail or provider-specific retry/backoff policy, if the project wants that before Stage 8.

_May the record carry the weight of the call._

## 2026-04-27 - Stage 7 Provider Execution and Log Redaction

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Direct providers now execute real HTTP calls when configured, while the local bridge modes stay dry-run safe.
**Scope:** Stage 7 follow-through, focused on live provider execution, packet resolution, and redacted provider call logs.

### What changed

- Threaded project roots into the AI provider registry so provider runs can write logs under `mythic/ai/provider_calls.jsonl`.
- Added packet resolution for `ai test` and `ai run`, including stored packet IDs and on-disk packet files.
- Kept `ai test` dry-run-only and made `ai run` honor `--dry-run` explicitly.
- Added real HTTP execution for `openai`, `anthropic`, `gemini`, and `openrouter` providers with explicit API-key checks.
- Added request and response logging with secret redaction before persistence.
- Preserved `copy-paste` and `local` as always-available bridge modes with `manual` and `local` packet labels for inline input.
- Added focused tests for live provider execution, redacted logs, and packet-ID resolution.

### Why it matters

Stage 7 now does the thing the CLI promised: it can talk to real providers when configured, but it still refuses to blur dry-run previews into live calls.

### Verification

- `pytest -q` -> `37 passed`

### Continuity thread

- The remaining Stage 7 work is mostly polish and safety hardening around provider request/response metadata, cost estimates, and any final adapter refinements.

_May the bridge stay explicit, and the logs stay honest._

## 2026-04-27 - Stage 7 Provider Adapter Spine

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Optional AI provider adapters exist behind explicit CLI commands and dry-run-first behavior.
**Scope:** First Stage 7 pass, focused on isolation, visibility, and safe defaults.

### What changed

- Added `mythic_vibe_cli.ai` with a provider registry and isolated provider modules.
- Added provider stubs for `copy-paste`, `local`, `openai`, `anthropic`, `gemini`, and `openrouter`.
- Added `mythic-vibe ai providers`, `mythic-vibe ai test`, `mythic-vibe ai run`, and `mythic-vibe ai ingest-response`.
- Added explicit API-key validation for direct provider adapters.
- Kept direct provider execution dry-run-first and metadata-oriented.
- Preserved copy-paste as a first-class, always-available mode.

### Why it matters

Stage 7 now has a real spine. The CLI can name providers, inspect their configuration, estimate usage, and record responses without losing the local-first method.

### Verification

- `pytest -q` -> `35 passed`

### Continuity thread

- The next Stage 7 work is real provider network execution, redaction, logging, and stricter safety records.

_May the bridge remain explicit and the fallback remain local._

---

## 2026-04-27 - Weighted Packet Budget Strategy

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Packet compaction now allocates character budget by section priority instead of flattening everything evenly.
**Scope:** Final visible Stage 6 budget-tuning pass.

### What changed

- Reworked packet compaction to weight priority sections more heavily than low-signal sections.
- Preserved more room for `project_index`, `architecture`, `verification`, and `invariants`.
- Tightened packet loading so stored packet IDs can resolve both markdown and JSON packet artifacts.
- Added a budget-allocation test to verify the weighted strategy behaves as intended.

### Why it matters

This makes truncated packets more useful under pressure. The sections that help a collaborator act safely and correctly now survive budget pressure better than the decorative ones.

### Verification

- `pytest -q` -> `31 passed`

### Continuity thread

- Stage 6 is now functionally strong; the remaining work is mostly polish or edge-case expansion unless a new need appears.

_May the scarce space be spent where it matters most._

---

## 2026-04-27 - Stage 6 Role Profiles, Formats, and Safety Sections

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Packet generation now supports named roles, packet formats, safety sections, and a context manifest.
**Scope:** Closing the remaining visible Stage 6 packet-engine gaps.

### What changed

- Added packet role presets for `Architect`, `Forge Worker`, `Auditor`, `Cartographer`, `Scribe`, `Debugger`, and `Refactorer`.
- Added packet output format selection, including Markdown, copy-paste, JSON, and provider-oriented format labels.
- Added packet safety sections for files in scope, files out of scope, invariants, verification commands, and check-in summary shape.
- Added `mythic/context_sources.json` as the packet context manifest.
- Added JSON packet rendering support when requested.
- Preserved `CodexBridge` compatibility while the internal builder continues to evolve as `PacketBuilder`.

### Why it matters

The packet engine now expresses the actual working contract the roadmap wanted: role-aware, format-aware, safety-bound, and grounded in local context.

### Verification

- `pytest -q` -> `30 passed`

### Continuity thread

- Stage 6 still has small polish items left if we want them later, but the major functional pieces are now in place.

_May the packet carry both intention and boundary._

---

## 2026-04-27 - Packet Ingest and Diff Lifecycle

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Packet artifacts can now be ingested and compared as first-class local records.
**Scope:** Stage 6 packet workflow completion for ingest/diff.

### What changed

- Added `mythic-vibe packet ingest` for importing Markdown or JSON packet artifacts into the local packet store.
- Added `mythic-vibe packet diff` for unified diffs between stored packet artifacts.
- Packet ingest preserves source path metadata and records a new canonical packet ID.
- Packet JSON records now carry optional source metadata for provenance.

### Why it matters

The packet system is now a real artifact lifecycle instead of a one-way emitter. That makes packet reuse, comparison, and handoff much more practical.

### Verification

- `pytest -q` -> `29 passed`

### Continuity thread

- Stage 6 still has additional work left: richer roles, output formats, safety sections, and a context source manifest.

_May the artifact remember its own lineage._

---

## 2026-04-27 - Packet Command Family and Artifact Store

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Packet artifacts now have IDs, metadata, and dedicated CLI commands.
**Scope:** Stage 6 prompt-packet groundwork beyond the initial project-index integration.

### What changed

- Renamed the internal packet builder concept to `PacketBuilder` while preserving `CodexBridge` as a compatibility alias.
- Added packet IDs and packet metadata under `mythic/packets/`.
- Added `mythic-vibe packet create`, `mythic-vibe packet show`, and `mythic-vibe packet list`.
- Kept `codex-pack` and `evoke` as compatibility paths into the packet builder.
- Packet creation now carries role metadata and continues to embed the local project index.

### Why it matters

The prompt system is no longer a throwaway text emitter. It has a durable artifact store, which is the shape Stage 6 needs if it is to become reusable across tools and sessions.

### Verification

- `pytest -q` -> `29 passed`

### Continuity thread

- The next Stage 6 steps are packet ingest, packet diff, richer role presets, and stronger safety/format selection.

_May the artifacts outlast the moment that summoned them._

---

## 2026-04-27 - Packet Builder Context Integration

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Runtime packet generation now pulls from the local project index.
**Scope:** Stage 6-adjacent packet context hardening, built on top of the Stage 5 scanner work.

### What changed

- `CodexBridge` now builds and embeds a project index snapshot when generating prompt packets.
- `mythic/project_index.json` is written automatically as part of packet generation.
- The packet now includes a `PROJECT INDEX` section with git metadata, language stats, important files, docs, tests, risks, and recommended context.
- Tests were added to verify the packet contains the project index and that the index file is written.

### Why it matters

Prompt packets are now grounded in the local repository map, which makes them less speculative and more useful for real engineering work.

### Verification

- `pytest -q` -> `28 passed`

### Continuity thread

- The next logical step is to make packet context selection smarter so the bridge can prioritize changed files and task-relevant files even more precisely.

_May the packet know the ground it stands on._

---

## 2026-04-27 - Stage 5 Context Scanner and Project Index

**Session:** Continuing the Mythic Vibe CLI implementation on `development`.
**Status:** Runtime, tests, and project-records updated with a local context scanner and index writer.
**Scope:** First implementation slice of Stage 5 from `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md`.

### What changed

- Added `mythic_vibe_cli.context` with scanner and indexer modules.
- Added `mythic-vibe scan` with `--json`, `--changed`, `--docs`, `--include`, `--exclude`, and `--dry-run` support.
- Added `.mythicignore` as a local scan policy file.
- Added project-index generation at `mythic/project_index.json`.
- Added tests covering git-aware scanning, ignore rules, and the new command registry entry.

### Why it matters

The CLI now has a real local-project map, which makes future prompt packets and workflow guidance less blind and less hand-wavy. It can see the shape of the repo before it asks for attention.

### Verification

- `pytest -q` -> `27 passed`

### Continuity thread

- The next useful step is to wire the index into prompt packet generation so context selection becomes automatic rather than manual.

_May the map speak before the blade moves._

---

## 2026-04-24 - Stage 1 CLI Command Extraction and Runtime Controls

**Session:** Third implementation pass from `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md`.
**Status:** Runtime, tests, roadmap, and command-boundary documentation updated on `development`.
**Scope:** Completion-oriented slice of Stage 1 CLI kernel hardening.

### What changed

- Extracted command implementations from `mythic_vibe_cli/app.py` into `mythic_vibe_cli/commands.py`.
- Kept `mythic_vibe_cli/app.py` focused on parser construction and top-level dispatch.
- Preserved `mythic_vibe_cli/cli.py` as the public compatibility wrapper for `mythic_vibe_cli.cli:main`.
- Added `mythic_vibe_cli/output.py` for shared plain-text terminal rendering helpers.
- Added `mythic_vibe_cli/errors.py` for structured CLI error payloads and formatting.
- Added shared `--json`, `--quiet`, `--verbose`, and `--dry-run` command controls where each option can preserve existing behavior safely.
- Added JSON output paths for structured reporting commands and dry-run guards for file-writing/syncing commands.
- Updated `tests/test_cli_kernel.py` so the compatibility export, parser dispatch, and command registry are locked to the same handler table.
- Added tests for status JSON output, quiet output suppression, init dry-run safety, and clean grimoire JSON output.
- Updated command, architecture, domain, active-boundary, API, and changelog records so docs match the new runtime shape.
- Checked the Stage 1 completed items in `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md`, using the actual transitional module paths.

### Verification

- `python -m pytest tests/test_cli_kernel.py tests/test_cli.py -q` passed with 12 tests.
- `python -m pytest -q` passed with 21 tests.
- `python -m mythic_vibe_cli --help` rendered successfully.
- `python -m mythic_vibe_cli.cli --help` rendered successfully.
- `python -m mythic_vibe_cli.cli doctor --repo-boundary --path .` passed with no errors or warnings.
- `python -m mythic_vibe_cli status --json` emitted clean JSON.
- `python -m mythic_vibe_cli doctor --repo-boundary --path . --json` emitted clean JSON.
- `python -m mythic_vibe_cli init --goal "Preview only" --path .mythic-preview --dry-run` previewed without creating the target directory.
- `git diff --check` passed with only line-ending normalization warnings.

### Next thread

Move into Stage 2: create the schema-versioned project state engine, JSON persistence layer, migration path from current `mythic/status.json`, and state validation commands.

---

## 2026-04-24 - Stage 1 CLI Kernel Hardening Begins

**Session:** Second implementation pass from `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md`.
**Status:** Runtime, tests, and command-contract documentation updated on `development`.
**Scope:** First safe slice of Stage 1 CLI kernel hardening.

### What changed

- Added `mythic_vibe_cli/__main__.py`, enabling `python -m mythic_vibe_cli`.
- Added `mythic_vibe_cli/exit_codes.py` with the named return-code policy: success, operational failure, user/config error, verification failure, and unsafe operation blocked.
- Moved the real CLI kernel into `mythic_vibe_cli/app.py`, leaving `mythic_vibe_cli/cli.py` as the compatibility entrypoint for `mythic_vibe_cli.cli:main`.
- Replaced the long `main()` dispatch chain with `COMMAND_HANDLERS`, preserving existing commands and aliases.
- Added `tests/test_cli_kernel.py` to lock down module execution, alias preservation, and exit-code policy.
- Added `docs/COMMAND_CONTRACTS.md` for entrypoints, command dispatch, compatibility aliases, and exit codes.
- Updated `docs/api.md`, `docs/ARCHITECTURE.md`, `docs/DOMAIN_MAP.md`, and `docs/INDEX.md` to reflect the kernel contract.

### Verification

- `python -m pytest tests/test_cli_kernel.py -q` passed.
- `python -m mythic_vibe_cli --help` rendered successfully.
- `python -m mythic_vibe_cli.cli --help` rendered successfully.

### Next thread

Continue Stage 1 by extracting command groups from `app.py` into focused command modules, then introduce shared terminal output/error helpers.

---

## 2026-04-24 - Stage 0 Boundary Stabilization Begins

**Session:** First implementation pass from `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md`.
**Status:** Runtime and governance changes made on `development`.
**Scope:** Stage 0 repo boundary stabilization, with one small test-harness hardening fix.

### What changed

- Added `REPO_BOUNDARY.md` as the root law for active runtime, dormant islands, and adapter gates.
- Added `docs/ACTIVE_PRODUCT_BOUNDARY.md` and `docs/DORMANT_ISLANDS.md` so contributors can tell what is product runtime and what is reference material.
- Added `docs/ADRS/ADR-0001-active-runtime-boundary.md` and `docs/ADRS/ADR-0002-no-direct-vendor-imports.md` to make the boundary decisions durable.
- Updated `README.md` with an above-the-fold Active Runtime Path section.
- Expanded `docs/INDEX.md` into a real navigation hub for boundary, architecture, and operator docs.
- Added `mythic-vibe doctor --repo-boundary` to validate boundary docs and scan active runtime imports for direct dependencies on dormant islands.
- Added `tests/test_repo_boundary.py` for boundary-file and forbidden-import behavior.
- Configured pytest to collect only active product tests under `tests/`, preventing dormant island tests from breaking the product verification gate.
- Fixed `ConfigStore` to honor `HOME` environment overrides before falling back to `Path.home()`.

### Verification

- `python -m pytest tests/test_repo_boundary.py -q` passed.
- `python -m mythic_vibe_cli.cli doctor --repo-boundary --path .` passed with no errors or warnings.
- `python -m pytest -q` passed with 13 active product tests.
- `python -m mythic_vibe_cli.cli --help` rendered successfully.

### Next thread

Continue with Stage 1 CLI kernel hardening: add `mythic_vibe_cli/__main__.py`, begin command-router extraction, and preserve all existing command aliases while tests stay green.

---

## 2026-04-23 — The Gathering Hall is Mapped

**Session:** Repo-wide exploration pass.
**Status:** Read-only inventory and attribution phase. No source code was modified.
**Hands on the wheel:** Runa Gridweaver Freyjasdottir (orchestrator) directed the work. Védis Eikleið, the Cartographer, drew the structural maps (`MAP.md`, `ARCHITECTURE.md`, `DEPENDENCIES.md`, `DATA_FLOW.md`). I, Eirwyn Rúnblóm, the Scribe, wrote the narrative records: `INVENTORY.md` (the canonical inventory), `ORIGINS.md` (attribution of imported pieces), and this chronicle.

### What was discovered

The repository is, at present, a **gathering hall**, not a finished hall-bench. Volmarr has pulled material together from a constellation of prior projects and staged them beside the genuinely new work — the Mythic Vibe CLI — so that an integration phase can follow.

The shape, in plain terms:

- At the centre sits the new CLI — `mythic_vibe_cli/` — small, deliberate, and the only sub-tree authored *for* this repo. It carries the Mythic Engineering seven-phase workflow (`intent → constraints → architecture → plan → build → verify → reflect`) and a ChatGPT-Plus / Codex copy-paste bridge so that a Plus subscriber can vibe-code without paying for API access.
- Around the CLI, three substantial imports stand almost untouched: `mindspark_thoughtform/` (the MindSpark ThoughtForge project in near-full form), `WYRD-Protocol-.../` (the WYRD Protocol v1.0.0 source, including all twenty engine integrations), and — pulled from the Norse Saga Engine but distributed across several directories — the systems, core, ai, sessions, and yggdrasil trees, plus a thirty-five-thousand-line `config.yaml` whose own header names it as *Norse Saga Engine v8.0.0*.
- Three upstream open-source projects have been vendored whole: `chatterbox/` (TTS), `whisper/` (speech-to-text), and `ollama/` (Go-language LLM server — the source of the repo's 681 Go files, 185 C++ files, and 158 CUDA files).
- The methodology corpus — `Mystic_Engineering_Protocals1.0.md`, `Mythic_Engineers_Codex.md`, `Ada_Lovelace_Explains_Mythic_Engineering.md`, `practical_mythic_engineering_step_by_step.md`, `Quick_Guide_to_Mythic_Engineering_Vibe_Coding.md`, and a 178-kilobyte treatise on the Viking TTRPG Emotional Engine — sits at the root as reference scripture.
- Research and specs are in triplicate: `research_data/` appears identically at the repo root, inside `mindspark_thoughtform/`, and inside `WYRD-Protocol-.../`. The same holds for `Technical_Architecture_of_Volmarrs_AI_Ecosystem.md`, `WORLD_MODELING_SKILL.md`, `PHILOSOPHY.md`, and `RULES.AI.md`. These duplications are catalogued in `ORIGINS.md` so the integration phase can decide whether one canonical copy will suffice.

### What was preserved

- `INVENTORY.md` — a directory-by-directory narrative of what exists, its current function, and its state of completeness.
- `ORIGINS.md` — best-effort attribution for every major piece, indicating the prior project it most likely came from, plus a duplicate register.
- `DEVLOG.md` — this scroll, opened.

Cross-reference Védis's maps for the structural/diagrammatic view; the two sets of records are deliberately non-overlapping.

### Threads still loose

- `core/saga_odin_rag.py` imports `..yggdrasil_core`, which does not exist anywhere in the repository. At least one file arrived in a mid-refactor state. This is flagged in `INVENTORY.md` and `ORIGINS.md` as an orphan import to reconcile in a later phase.
- `diagnostics/` contains a single 46-megabyte `turn_trace.jsonl`. Its provenance (which session, which build, which character) is not declared in-file.
- The repo root's `systems/`, the embedded `imports/norsesaga/systems/`, and NSE's upstream all contain overlapping files (`event_dispatcher.py` appears in both). Which copy is canonical will be an integration-phase decision.
- `yggdrasil/` (earlier NSE-era Yggdrasil, OpenRouter-centric, with paired AI-sidecar markdown on every module) and `WYRD-Protocol-.../src/wyrdforge/ecs/yggdrasil.py` (the WYRD ECS spatial-hierarchy module of the same name) describe *two different Yggdrasils*. They must not be silently merged.

### The seed of the chronicle

This is the first entry. Every future pass — integration decisions, merges, removals, module rewrites — should add a dated entry here, so the living record keeps pace with the living code. Absolute dates only. One entry per session of meaningful work.

_May the record hold._

---

## 2026-04-23 — The Register of Keep and Let Go

**Session:** Second exploration pass — integration-readiness judgement.
**Status:** Read-only source. Only `.md` files written.
**Hands on the wheel:** Runa Gridweaver Freyjasdottir (orchestrator) directed a second pass. Védis Eikleið was commissioned to produce the structural/diagrammatic companions (`IMPACT_integration.md`, `DUPLICATES.md`, `YGGDRASIL_COMPARISON.md`). I, Eirwyn Rúnblóm, composed the narrative judgement — `RECOMMENDATIONS.md` — and added this entry.

### What the deeper reading revealed

The first pass mapped what exists. The second pass asked *what should become of it*, measured against the actual product — the Mythic Vibe CLI, whose sources were read in full during this session (`cli.py`, `workflow.py`, `codex_bridge.py`, `config.py`, `mythic_data.py`, `pyproject.toml`, `README.md`).

Three realisations shape every recommendation now on the table:

- **The CLI is a true island** — it imports nothing outside its own package and the Python stdlib. A keep-or-drop decision on any imported subtree therefore has *zero runtime cost* to the product. The question is entirely one of maintenance surface, distribution weight, and narrative clarity.
- **`pyproject.toml` packages only `mythic_vibe_cli`.** When this project is installed, none of the surrounding corpora ship. They are reference material, not product code — which is a strong structural hint about the author's real intent.
- **The CLI already syncs the canonical Mythic Engineering methodology from GitHub** (`mythic_data.py` pulls from `hrabanazviking/Mythic-Engineering`). A second copy of that methodology sitting at the repo root is therefore a silent duplication that will go stale.

### Recommendations now on the table

Full register is in `RECOMMENDATIONS.md`. In brief:

- **`KEEP AS-IS`** — the CLI package itself (`mythic_vibe_cli/`, `tests/`), the license/notice triad, the methodology-instruction scrolls at root (`PHILOSOPHY.md`, `PROJECT_LAWS.md`, `RULES.AI.md`, and kin), and the seed-chronicle we are writing now.
- **`DROP — DUPLICATE`** (unconditional) — the empty `mindspark_thoughtform/MindSpark_ThoughtForge/` nested shell; one of the two differently-cased copies of the *Emotional Engine Integration Plan for Norse Saga Engine*; the partial `research_data/src/wyrdforge/` shadow.
- **`DROP — UNUSED`** — the 46 MB `diagnostics/turn_trace.jsonl`; NSE-specific config (`config.yaml` = NSE v8.0.0) and schema (`CHARACTER_TEMPLATE_SCHEM.yaml`) at root; `sessions/`; NSE diagnostics entry points at root (`debug_router_integration.py`, `diagnostics.py`); `imports/norsesaga/systems/`.
- **`DEFER — NEEDS VOLMARR`** — the load-bearing decisions: does the CLI run local models (controls `ai/`, `ollama/`, `whisper/`, `chatterbox/`); which Yggdrasil survives (controls `yggdrasil/`, and the choice between NSE-era cognitive router and WYRD ECS hierarchy); is MindSpark/WYRD *incorporated* into this repo or *referenced* from it (controls the two largest subtrees); does the CLI *embody* the methodology or *reference* it (controls the big root-level essay corpus); and the MIT-vs-Apache license discrepancy between `pyproject.toml` and `LICENSE`.

Cross-reference Védis's forthcoming `IMPACT_integration.md` for the structural view of how these calls ripple through the dependency graph, `DUPLICATES.md` for the precise list of redundant files with byte-level evidence where available, and `YGGDRASIL_COMPARISON.md` for the two-Yggdrasils contrast (NSE-era cognitive-routing Yggdrasil at `yggdrasil/` vs the WYRD ECS spatial-hierarchy Yggdrasil at `wyrdforge/ecs/yggdrasil.py`).

### Corrections applied to `ORIGINS.md`

The deeper reading surfaced one missing duplicate and one cleaner attribution; both are noted in the dated corrections block now at the top of `ORIGINS.md`.

### Threads still loose — rolled into the register

The five upstream decisions named above are the only real open questions. Until Volmarr chooses on them, most of the register is `DEFER` not from timidity but from honesty: the calls are genuinely his to make, and pretending otherwise would be a disservice to the record.

### The seed-chronicle now carries two entries

This is the second entry of the exploration phase. The register is laid; the decisions wait. Future entries will mark each integration motion as it is taken — one rune cut at a time.

_May the record hold, and may the choices, when they come, be clear._

## 2026-04-23 — Scribe Sweep: Documentation Polished and Expanded

**Session:** Documentation consolidation and expansion pass.
**Status:** Markdown-only change set across active docs. No runtime Python code modified.
**Hands on the wheel:** Eirwyn Rúnblóm, The Scribe, performed a repository-facing continuity pass focused on the active Mythic Vibe CLI documentation suite.

### What was changed

This session executed a deep rewrite of the active documentation surfaces so they can function as durable, navigable, and contributor-safe records rather than short-form placeholders.

Updated/added artifacts:

- `README.md` — rewritten as a full operator/contributor guide with command orientation, repository posture notes, configuration model, and active-doc map.
- `docs/INDEX.md` — newly added canonical navigation index and maintenance protocol.
- `docs/index.md` — expanded user-facing hub with role-based reading paths.
- `docs/quickstart.md` — expanded onboarding flow with bridge usage and troubleshooting depth.
- `docs/ARCHITECTURE.md` — expanded component contracts, dependency law, risks, and architecture review checklist.
- `docs/DOMAIN_MAP.md` — expanded ownership matrix, dependency boundaries, escalation path, and drift indicators.
- `docs/api.md` — expanded command/module contracts, compatibility policy, and integration examples.
- `docs/SYSTEM_VISION.md` — expanded mission, scope, design principles, UX expectations, and evolution horizons.
- `CHANGELOG.md` — created release-facing history ledger.

### Why it matters

Before this pass, several docs were concise but shallow. The repository now has a clearer archival spine for:

- onboarding new contributors,
- preventing boundary drift in a large monorepo,
- preserving release/session continuity,
- and recovering intent after long pauses.

### Continuity note

This entry marks the beginning of explicit dual-record discipline:

- `DEVLOG.md` for narrative chronology and rationale,
- `CHANGELOG.md` for user/release-facing deltas.

The two records should now evolve together when meaningful behavior or governance changes occur.

_May the record hold._

---

## 2026-04-23 — Scribe Invocation: Continuity Charter and Handoff Ritual

**Session:** Focused documentation-governance hardening pass.
**Status:** Markdown-only updates; repository runtime code untouched.
**Hands on the wheel:** Eirwyn Rúnblóm, responding to a direct Scribe invocation, polished and expanded the active documentation layer with an emphasis on continuity under interruption.

### What was changed in this pass

- `docs/DOCUMENTATION_STANDARDS.md` was created as a formal charter for writing quality, update obligations, drift detection, and archival discipline.
- `docs/SESSION_HANDOFF_TEMPLATE.md` was created as a pragmatic close-out template to preserve rationale and next actions between sessions.
- `docs/INDEX.md` was expanded into a true canonical map with role-based pathways, update matrices, quality gates, and cadence guidance.
- `docs/index.md` was transformed into a compatibility redirect to prevent duplicate authority and future drift.
- `README.md` was updated with a dedicated governance section linking the continuity documents.
- `CHANGELOG.md` was synchronized with this session so user-facing records remain aligned with contributor-facing memory.

### Why this matters now

The earlier documentation sweep made the docs richer; this pass made them more **self-healing**. The project now has explicit rules for how docs remain trustworthy when features, priorities, and maintainers change.

In practical terms, this reduces three recurring failure patterns:

1. **Silent divergence** between command behavior and docs.
2. **Lost intent** after long pauses or handoffs.
3. **Navigation decay** caused by duplicated index surfaces.

### Continuity threads left deliberately open

- The broader monorepo still contains a large volume of historical/reference documentation outside the active CLI spine. A future archival curation pass can classify those files as canonical, reference-only, or frozen history.
- If command surfaces evolve significantly, the next maintainer should validate that `docs/api.md` still matches runtime semantics before release tagging.

_May the memory remain legible when the fire burns low._
