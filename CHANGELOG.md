# Changelog

All notable changes to this repository's active product documentation and runtime-facing records are documented in this file.

The format is inspired by Keep a Changelog and uses explicit dates for continuity.

## [Unreleased]

### Added

- Added `mythic-vibe tui` — a Textual-based status TUI showing project phase, last verification, latest handoff, and plugin counts in a four-panel grid with auto-refresh every 2 seconds. Keybindings: `q` quit, `r` manual refresh. Requires the new optional `[tui]` extra (`textual>=0.80`); when Textual is not installed the command surfaces a helpful install message and returns `OPERATIONAL_FAILURE` rather than raising. Cross-platform via Textual (pure Python, MIT) — no per-OS branches. Added `tui` to the `dev` group so test runs can exercise the TUI via Textual's built-in `App.run_test()` headless driver.
- Added `mythic-vibe shell` — a minimal interactive REPL. Reads command lines from stdin via `input()`, dispatches each to `app.main(argv)` so the full argparse + handler stack runs per command. Handles `/help` (prints the slash catalog inline including plugin-contributed entries), `/quit` / `/exit`, EOF (Ctrl+D), and Ctrl+C (returns to prompt). Bare commands without a leading `/` work too. Bad shlex-quotes emit a parse error and the loop continues; non-zero exit codes are surfaced and the loop continues. The REPL has no readline/history yet (deferred follow-on); no Textual dependency. First slice of the V2 Phase 3 (TUI) arc — establishes the REPL contract a future TUI will wrap or replace.
- Added `mythic-vibe slash list` for inspecting the slash-command catalog. Prints `BUILTIN_SLASH_COMMANDS` and any entries contributed by enabled plugins via an optional `slash_commands()` callable on the plugin class. Supports `--source builtin|extension|prompt|skill|plugin` to restrict output to a single source; `--source builtin` skips plugin loading entirely. JSON output exposes `{command, path, source_filter, builtin: [...], contributed: [...]}` with each entry as the dataclass `to_dict()` form.
- Added `PluginHookDispatcher.discover_slash_commands()` — a one-shot discovery method (separate from `PLUGIN_HOOKS`) that aggregates `SlashCommandInfo` instances from any loaded plugin exposing a callable `slash_commands` attribute. Plugin exceptions follow the bus log-and-continue contract; non-`SlashCommandInfo` items are silently skipped.
- Wired `exec_command` through every existing subprocess call site in production code: `verify/test_runner.py`, `verify/git_diff.py`, `handoff.py`, and `context/scanner.py`. Direct `subprocess.run` usage is now confined to `runtime/exec.py` itself. Behavior preserved (all 219 tests green); side benefit is graceful missing-binary handling — e.g., a missing `pytest` now becomes a verification failure (`code=127`) instead of an unhandled `FileNotFoundError`.
- Added `mythic_vibe_cli.runtime.exec` — subprocess execution primitive ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. `exec_command(command, args, cwd, *, timeout, cancel_event)` returns an `ExecResult` (`stdout`, `stderr`, `code`, `killed`, plus `to_dict`). `shell=False` is hard-coded; missing commands return `code=127` rather than raising. `timeout` uses `threading.Timer`; `cancel_event` (the Python equivalent of pi's `AbortSignal`) uses a watcher thread; both kill via `SIGTERM` then `SIGKILL` after a 5-second grace period. Pi's `waitForChildProcess` Node-stdio quirk handler is not needed — Python's `Popen.communicate()` handles the underlying issue natively.
- Updated `docs/runtime.md` to add §8 covering `exec`, renumbered the trailing sections, updated the at-a-glance table to show seven primitives, and updated the index in `docs/INDEX.md` accordingly.
- Added `docs/runtime.md` — operator-facing guide for the seven runtime primitives in `mythic_vibe_cli/runtime/`. Sections cover what each primitive does, public surface, usage examples, when to reach for it, common composition patterns, and cross-links. Mirrors the shape of `docs/plugins.md`. Cross-linked from `docs/INDEX.md` (Operator Docs) and `docs/plugins.md` (See also).
- Added `mythic_vibe_cli.runtime.source_info` — provenance type for contributed artifacts ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. Exports `SourceInfo` frozen dataclass (path, source, scope, origin, optional base_dir), `SourceScope` Literal (`"user" | "project" | "temporary"`), `SourceOrigin` Literal (`"package" | "top-level"`), and `synthetic_source_info(path, source, scope=..., origin=..., base_dir=None)` factory mirroring pi's `createSyntheticSourceInfo`. Pi's `PathMetadata`-dependent factory is intentionally not ported (out of scope; pi's package-manager subsystem is not being plundered).
- Upgraded `SlashCommandInfo.source_info` from `str` to `SourceInfo`, closing the deferred detail noted in the slash-commands catalog slice. Extension/skill/prompt/plugin-contributed commands now carry structured provenance with scope, origin, and an optional `base_dir`.
- Added `mythic_vibe_cli.runtime.slash_commands` — typed catalog of slash commands ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. Exports `BUILTIN_SLASH_COMMANDS` (Mythic-relevant defaults: `help`, `status`, `scan`, `packet`, `verify`, `reflect`, `resume`, `method`, `handoff`, `workflow`, `plugin`, `grimoire`, `reload`, `quit`), `BuiltinSlashCommand` and `SlashCommandInfo` frozen dataclasses, and the `SlashCommandSource` Literal (`"extension" | "prompt" | "skill" | "plugin"` — adds `"plugin"` to pi's three because Mythic has a first-class plugin layer). Catalog only — runtime dispatch belongs to whichever future surface (REPL/TUI/SDK) consumes the catalog.
- Wired the timings primitive into `app.main()` so `MYTHIC_TIMING=1 mythic-vibe ...` produces a startup-and-command profile to stderr (`argparse`, `configure_output`, `handler:<command>`, `TOTAL`). `print_timings()` runs in a `finally` block so even argparse-driven `SystemExit` (e.g., `--help`) prints the partial profile. With the env var unset, every call is a no-op and the function behaves identically to before.
- Added `mythic_vibe_cli.runtime.timings` — lightweight elapsed-time instrumentation primitive ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. Three functions: `reset_timings()`, `record(label)`, `print_timings()`. Gated by the `MYTHIC_TIMING` env var (accepts `1` / `true` / `yes` / `on`); when unset, all three functions are inexpensive no-ops so call sites can sprinkle `record(...)` without conditional gating. Output formatted in pi-style with a TOTAL footer to stderr. Re-exported from `mythic_vibe_cli.runtime`.
- Added `docs/plugins.md` — operator-facing guide for writing and registering Mythic plugins. Covers the eight hook signatures, payload shapes, complete worked example (`AuditPlugin` recording every life-cycle event to an append-only log), registration via `grimoire add` / inspection via `plugin inspect` / pause via `plugin disable`, the synchronous-only / exception-isolated / read-only-payload contract, and the per-invocation lifecycle. Cross-linked from `docs/INDEX.md` (Operator Docs) and `docs/api.md` (plugin command surface).
- Wired `before_reflect` / `after_reflect` emission into `cmd_reflect` real-work path; dry-run skips emission. `before_reflect` carries the user-supplied `summary` / `next_step` / `note`; `after_reflect` adds `handoff_id`, `json_path`, `markdown_path`, and `next_recommended_action`. **With this slice, all eight declared hooks in `PLUGIN_HOOKS` (scan/packet/verify/reflect, before+after each) now have real emitters; the plugin dispatch layer is fully load-bearing.**
- Wired `before_verify` / `after_verify` emission into `cmd_verify`. `before_verify` fires at the top with `{path, selected: {commands, changed_files, docs, invariants}}`. `after_verify` fires after the verification artifact is written with `{path, result, level, verification_id, artifact_path, errors_count, warnings_count, blocked_count}` — scalar summary only; full warning/error/command lists stay in the artifact.
- Wired `before_packet` / `after_packet` emission across three packet-write call sites: `packet create` (and the `codex-pack` / `evoke` aliases via the shared `cmd_packet_create`), `packet ingest`, and the `workflow plan --packets` step loop. Each emission is bracketed by `PluginHookDispatcher.emit("before_packet", ...)` / `emit("after_packet", ...)` with a small stable-key payload (`source`, `path`, `phase`, `role`, `task`, `audience`, `format`; `after_packet` adds `packet_id` + `packet_path`). The workflow path additionally surfaces `workflow_id` and `workflow_step_id`. Dry-run paths and `workflow plan` without `--packets` skip emission entirely.
- Added `mythic_vibe_cli.plugins.PluginHookDispatcher` — per-invocation dispatcher that loads enabled plugins from the project's `PluginRegistry`, resolves each plugin's `before_*` / `after_*` hook methods, and subscribes them to a fresh `EventBusController`. Plugins that fail to import are skipped silently; plugin handler exceptions are contained by the bus contract. Re-exported from `mythic_vibe_cli.plugins`.
- Wired `cmd_scan` to emit `before_scan` and `after_scan` through `PluginHookDispatcher` on the real-work path. Dry-run scans skip both hooks. The remaining declared hooks (`before_verify`, `after_verify`, `before_reflect`, `after_reflect`) stay wired through the dispatcher contract and will be emitted from their matching commands in subsequent slices.
- Added `mythic_vibe_cli.runtime.event_bus` — synchronous publish/subscribe coordination layer ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. `create_event_bus()` returns an `EventBusController` exposing `emit(channel, data)` / `on(channel, handler) -> unsubscribe` / `clear()`. Handler exceptions are logged to stderr (channel + traceback) and never crash the bus, matching pi's "log and continue" contract. Snapshots handlers before iterating so a handler can unsubscribe itself during dispatch. Re-exported from `mythic_vibe_cli.runtime`. The bus is unwired plumbing in this slice; future slices will connect it to the existing `before_*` / `after_*` plugin hook declarations.
- Wired `take_over_stdout()` into `app.main()` so every `--json` command runs under the stdout guard. Accidental `print()` and any third-party stdout writes route to stderr; only deliberate `write_json()` payloads reach real stdout (via `write_raw_stdout()`).
- Wired `file_mutation_queue` into `PacketBuilder` writer sites so `packet create`, `packet ingest`, and the underlying `_write_record` / `_write_ingested_record` / `_write_context_manifest` paths serialize per resolved path. Wrapped `create_packet` and `ingest_packet` with a packet-directory-level queue so concurrent calls cannot collide on `_next_packet_id` allocation. Verified by a new packet-writer concurrency test that issues 8 simultaneous `create_packet` calls and asserts 8 distinct PKT-IDs land on disk.
- Added `json_output_guard` context manager to `mythic_vibe_cli.runtime.output_guard` — `with json_output_guard(active=True):` installs the guard for the block and restores on exit (including on exceptions). `active=False` makes the block a transparent no-op.
- Added `mythic_vibe_cli.runtime.output_guard` — stdout cleanliness primitive ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. `take_over_stdout()` installs a proxy stream that routes all `sys.stdout` writes to `sys.stderr`; `write_raw_stdout()` and `flush_raw_stdout()` keep the protocol-output path usable while the guard is active; `restore_stdout()` undoes the takeover; `is_stdout_taken_over()` reports state. Idempotent takeover and no-op restore are both covered. Re-exported from `mythic_vibe_cli.runtime`.
- Added `mythic_vibe_cli.runtime.file_mutation_queue` — per-resolved-path serialization primitive ported from pi (pi-coding-agent), MIT-licensed by Mario Zechner. Symlink aliases share the same queue via `os.path.realpath`; entries are reference-counted so the lock map cleans up after the last waiter. Public surface: `file_mutation_queue` context manager and `with_file_mutation_queue` functional form. Companion test ported from pi's Vitest suite under `tests/test_file_mutation_queue.py`.
- Added `THIRD_PARTY_NOTICES.md` recording the Pi attribution stanza, the plunder map, and the full upstream MIT permission text. First entry in the file; future plundered material lands here.
- Added `mythic_vibe_cli.method_excerpt` (Stage 15 final box) — `select_method_excerpts(corpus_dir, sections, char_limit)`, `sections_for(role, phase)`, and `ROLE_METHOD_SECTIONS` / `PHASE_METHOD_SECTIONS` maps. Scans the imported method corpus for headings matching role-relevant section keywords and returns capped excerpts.
- Added method excerpt embedding to `packet create`. Markdown packets gain a `## 12. Method Excerpts` section between Check-in Summary and SAFETY; JSON packets gain a `method_excerpts` array. Sections are chosen by packet role with phase fall-back. When the corpus is missing or no headings match, the method section is omitted (graceful degradation, no error).
- Added `packet show --previous-workflow --step <step_id>` for resolving the workflow id from the second-most-recent entry in `mythic/workflow_history.json`. Same exclusivity rules as `--latest-workflow`; cannot be combined with it; errors when the ledger has fewer than two entries.
- Added `LATEST:<step_id>` and `PREVIOUS:<step_id>` self-describing sentinels to `packet diff --left` and `--right`. Mixing them in one call (e.g., `--left LATEST:step-01 --right PREVIOUS:step-01`) is the canonical cross-run regression diff pattern. The sentinels work without flag toggles and compose with the existing `WF-<id>:<step_id>` shorthand and `--latest-workflow` bare-step form.
- Added `_resolve_previous_workflow_id` helper for callers that need the second-most-recent workflow id from the ledger.
- Added `mythic/workflow_history.json` as an append-only ledger of workflow plan saves (workflow_id, task, created_at, plan_path, role_sequence). `workflow plan` (without `--dry-run`) appends an entry on every successful save; the ledger is capped at 50 entries.
- Added `mythic-vibe workflow history` for inspecting the ledger. Supports `--limit N` to cap the returned entries and `--json` for structured output that exposes `count`, `total`, and the resolved `history_path`.
- Added `WorkflowEngine.append_history`, `WorkflowEngine.load_history`, and `WorkflowEngine.history_path` plus `WORKFLOW_HISTORY_FILENAME` and `WORKFLOW_HISTORY_LIMIT` constants for callers that need to read or write history programmatically.
- Added `packet list --latest-workflow` so packet listings can scope to the saved `mythic/workflow_plan.json` without restating the workflow id. Cannot be combined with `--workflow`. Errors when the saved plan is missing or has no `workflow_id`. JSON output exposes the resolved `latest_workflow_id` for symmetry with `packet show` and `packet diff`.
- Added `packet show --latest-workflow --step <step_id>` and `packet diff --latest-workflow` so packet refs can resolve against the saved `mythic/workflow_plan.json` without restating the workflow id. With `packet diff --latest-workflow`, `--left` and `--right` additionally accept a bare `step-NN` form. Errors when the saved plan is missing or has no `workflow_id`. JSON output reports the resolved `latest_workflow_id` for `packet diff`.
- Added `packet show --workflow <id> --step <step_id>` for resolving a packet by its workflow stamp instead of by `PKT-` ID. Both flags are required together and cannot be combined with `--packet-id`; missing matches return `USER_INPUT_ERROR`.
- Added `WF-<id>:<step_id>` shorthand to `packet diff --left` and `--right`, resolving the shorthand to a stored packet at run time. JSON output reports both the original references (`left_ref`, `right_ref`) and the resolved packet IDs.
- Added `PacketBuilder.find_packet_by_workflow_step` helper that returns the latest packet stamped with a given `workflow_id` and `workflow_step_id`.
- Added `packet list --workflow <id>` and `packet list --workflow <id> --step <step_id>` filters for showing only the packets belonging to one workflow run; `--step` requires `--workflow` and returns `USER_INPUT_ERROR` otherwise. Legacy packets without IDs are excluded when a workflow filter is set, and JSON output exposes a `filters` object reporting the applied scope.
- Added deterministic `workflow_id` (form `WF-<UTC compact>-<sha8(task+created_at)>`) to every freshly built workflow plan, persisted in `mythic/workflow_plan.json` and surfaced in `workflow plan`, `workflow packets`, and `workflow run` JSON output.
- Added `workflow_id` and `workflow_step_id` stamping on packets generated via `workflow plan --packets`, written to each packet's `.meta.json`.
- Added ID-first packet matching to `workflow packets` and `workflow run --dry-run --packets-only`, with the existing `(role, phase, task, audience, output_format)` text match preserved as a legacy fallback. Each `packet_status` entry now reports `match_strategy` (`"id"`, `"text"`, or `null`).
- Added `mythic-vibe workflow packets` for read-only packet readiness listings, including `--missing-only` filtering.
- Added `workflow run --dry-run --packets-only` to validate that every workflow step has a matching packet artifact before provider execution is introduced.
- Added `mythic-vibe workflow run --dry-run` for safe ordered role-execution previews from saved or generated workflow plans.
- Added `workflow plan --packets`, `--audience`, and `--format` so workflow plans can generate one packet artifact per role step without provider execution.
- Added `mythic-vibe workflow plan` for writing and previewing role orchestration plans from the CLI.
- Added `mythic_vibe_cli.workflow_engine` for deterministic six-role orchestration plans, handoff order, packet request export, and durable `mythic/workflow_plan.json` writing.
- Added `mythic_vibe_cli.ai.prompts.roles` as the first real packet-role catalog, including first-class `Skald` support.
- Added Stage 15 method profile visibility with `mythic-vibe method status`, `method show`, and `method sync`.
- Added `method_manifest.json` generation for `import-md`, including source ref, file count, relative paths, byte sizes, and SHA-256 hashes.
- Added `mythic-vibe method diff` to compare an imported method corpus against its manifest.
- Added `mythic-vibe method pin` to write a reproducibility pin for clean imported method corpora.
- Added configurable `method.source` support, including `MYTHIC_METHOD_SOURCE`, project config loading, and `config` reporting.
- Added method version detection, fallback profile reporting, method section labels, and freshness warnings for uncached method corpora.
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

- Packet role presets now live outside `codex_bridge.py`, keeping packet building separate from role identity and prompt definitions.
- `next` human output now shows failed verification commands, verification errors, and blocked reasons as separate sections when the latest verification is not passing.
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

