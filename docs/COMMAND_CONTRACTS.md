# Command Contracts

This document records the active Mythic Vibe CLI command-kernel contract.

## Entrypoints

The CLI must remain reachable through all current public entrypoints:

```bash
mythic-vibe --help
mythic --help
python -m mythic_vibe_cli --help
python -m mythic_vibe_cli.cli --help
```

`python -m mythic_vibe_cli` is the preferred package-module entrypoint for debugging install and path issues. `python -m mythic_vibe_cli.cli` remains supported for backward compatibility.

## Dispatch Contract

`mythic_vibe_cli.commands.COMMAND_HANDLERS` is the in-process command registry. `mythic_vibe_cli.app` imports it for dispatch, and `mythic_vibe_cli.cli` re-exports it for compatibility. New commands and ritual aliases must add parser support in `mythic_vibe_cli.app`, implementation in `mythic_vibe_cli.commands`, and registry wiring in `COMMAND_HANDLERS`.

Current Stage 10 continuity commands:

- `reflect` - create a reflection handoff from the current session summary.
- `handoff create` - create a handoff record from the current repository state.
- `handoff show` - show a stored handoff record by ID or the latest record.
- `handoff latest` - show the newest handoff record.
- `resume` - summarize the latest handoff and next recommended action.

Current Stage 11 plunder commands:

- `plunder inspect` - inspect a GitHub source repository and classify its license posture.
- `plunder plan` - create `mythic/imports/plunder_plan.json` with source, destination, license, and modification notes.
- `plunder fetch` - fetch one source file into the local plunder cache.
- `plunder apply` - apply the fetched file, refuse silent overwrites, and record provenance.
- `plunder record` - append provenance from the current plan without applying a file.
- legacy `plunder --repo --source --dest` remains available for one-file copying, but new reuse work should prefer the staged workflow.

Current Stage 12 plugin commands:

- `grimoire add|list` - compatibility registry commands for adding and listing plugin entrypoints.
- `plugin list` - list plugin health without importing plugin code.
- `plugin inspect` - inspect one registered plugin, import its entrypoint, and report declared hooks.
- `plugin disable` - mark a plugin disabled without removing its provenance from `mythic/plugins.json`.
- Plugin hooks are versioned and limited to `before_scan`, `after_scan`, `before_packet`, `after_packet`, `before_verify`, `after_verify`, `before_reflect`, and `after_reflect`.
- Plugins are local Python extension points; inspect and trust them before enabling.

Current packet role contract:

- Packet roles are defined in `mythic_vibe_cli.ai.prompts.roles`.
- First-class Mythic roles are `Skald`, `Architect`, `Forge Worker`, `Auditor`, `Cartographer`, and `Scribe`.
- Utility roles `Debugger` and `Refactorer` remain supported for focused repair and cleanup packets.
- `codex-pack`, `evoke`, and `packet create` must use the same role catalog.

Current workflow orchestration contract:

- `workflow plan` writes a deterministic role orchestration plan to `mythic/workflow_plan.json` unless `--out` is supplied.
- `workflow plan --dry-run` builds and displays the plan without writing files.
- `workflow plan --json` emits the full plan plus packet-ready requests for each step.
- Repeated `--role` flags customize the role sequence while preserving the supplied order.
- The default sequence is `Skald -> Architect -> Cartographer -> Forge Worker -> Auditor -> Scribe`.
- `workflow plan --packets` creates one packet artifact per workflow step under `mythic/packets/`.
- `workflow plan --audience` and `--format` control the generated packet requests and packet artifacts.
- `workflow plan --dry-run --packets` previews packet generation without writing plan or packet files.
- `workflow packets` lists packet readiness for a saved workflow plan or generated `--task`.
- `workflow packets --missing-only` shows only missing workflow packet steps.
- `workflow run --dry-run` previews ordered role execution from `mythic/workflow_plan.json` or an in-memory `--task`.
- `workflow run --dry-run --packets-only` validates that every workflow step has a matching stored packet artifact before any future provider execution is considered.
- `workflow run` without `--dry-run` is intentionally blocked until provider orchestration safety gates exist.
- `workflow plan` (without `--dry-run`) appends an entry to `mythic/workflow_history.json` after writing the plan; the ledger keeps at most 50 entries and never grows for `--dry-run` plans.
- `workflow history` lists recorded workflow plan saves newest-first. `--limit N` caps the returned entries; `--json` exposes the full ledger with `count`, `total`, and the resolved `history_path`.
- `workflow plan` assigns a deterministic `workflow_id` of the form `WF-<UTC compact>-<sha8(task+created_at)>` to every freshly built plan; the id is persisted in `mythic/workflow_plan.json` and surfaced in `workflow plan`, `workflow packets`, and `workflow run` JSON output.
- `workflow plan --packets` stamps `workflow_id` and `workflow_step_id` on every generated packet's `.meta.json` payload so packet readiness can be traced by ID instead of exact task text.
- `workflow packets` and `workflow run --packets-only` prefer ID-based matching when both plan and packet carry the IDs; legacy plans or packets without IDs fall back to the existing `(role, phase, task, audience, output_format)` text match. Each `packet_status` entry reports the chosen `match_strategy` (`"id"`, `"text"`, or `null` when no match).
- `packet list --workflow <id>` filters stored packets to those stamped with the supplied `workflow_id`. Adding `--step <step_id>` further narrows to a single workflow step; `--step` requires `--workflow` or `--latest-workflow` and returns `USER_INPUT_ERROR` otherwise. Legacy packets without an ID are excluded when a workflow filter is set. JSON output includes a `filters` object reporting the applied `workflow_id` and `workflow_step_id`.
- `packet list --latest-workflow` resolves the workflow id from `mythic/workflow_plan.json` and applies it as the `--workflow` filter. Cannot be combined with `--workflow`; returns `USER_INPUT_ERROR` when the saved plan is missing or has no `workflow_id`. JSON output exposes the resolved `latest_workflow_id` for symmetry with `packet show` and `packet diff`.
- `packet show --workflow <id> --step <step_id>` resolves to the latest packet stamped with that workflow id and step. `--workflow` and `--step` must appear together and cannot be combined with `--packet-id`; either constraint violation returns `USER_INPUT_ERROR`. Missing matches also return `USER_INPUT_ERROR`.
- `packet show --latest-workflow --step <step_id>` resolves the workflow id from `mythic/workflow_plan.json` before performing the lookup. `--latest-workflow` requires `--step`, cannot be combined with `--workflow` or `--packet-id`, and returns `USER_INPUT_ERROR` when the saved plan is missing or has no `workflow_id`.
- `packet show --previous-workflow --step <step_id>` resolves the workflow id from the second-most-recent entry in `mythic/workflow_history.json`. Same exclusivity rules as `--latest-workflow`; cannot be combined with it; returns `USER_INPUT_ERROR` when the ledger has fewer than two entries.
- `packet diff --left` and `--right` accept either a bare `PKT-...` packet ID, a `WF-<id>:<step_id>` shorthand, a `LATEST:<step_id>` sentinel, or a `PREVIOUS:<step_id>` sentinel. The shorthand and sentinels resolve to the matching packet at run time, with unresolved references returning `USER_INPUT_ERROR`. JSON output reports both the original `left_ref`/`right_ref` and the resolved `left`/`right` packet IDs.
- `packet diff --latest-workflow` lets `--left` and `--right` additionally accept a bare `step-NN` form that resolves against the workflow id stored in `mythic/workflow_plan.json`. `PKT-...` IDs, `WF-<id>:<step_id>` shorthand, and `LATEST:<step_id>` / `PREVIOUS:<step_id>` sentinels continue to work in the same call. JSON output reports the resolved `latest_workflow_id`.
- `LATEST:<step_id>` and `PREVIOUS:<step_id>` are self-describing sentinels that resolve through the saved plan or history ledger respectively; mixing them in one `packet diff` call (e.g., `--left LATEST:step-01 --right PREVIOUS:step-01`) is the canonical cross-run regression diff pattern.
- `packet create` now embeds role-relevant method excerpts into both markdown and JSON outputs when the imported method corpus exists at `docs/mythic_source/`. Section selection follows `ROLE_METHOD_SECTIONS` (role wins) with a fall-back to `PHASE_METHOD_SECTIONS`. Each excerpt is capped at ~600 chars and includes a `truncated` flag. When the corpus is missing or no headings match, the method section is omitted from the markdown packet entirely, and `method_excerpts` is an empty list in JSON.

Current Stage 14 UX commands:

- High-traffic command help for `init`, `next`, `verify`, `packet create`, `reflect`, `resume`, and `doctor` includes concrete copy-paste examples.
- `examples` - print copy-paste command examples.
- `guide` - print the compact operator guide for the Mythic loop.
- `next` - inspect local state and suggest the next phase and command; failed or blocked verification records take priority, then latest handoff next steps, then normal phase guidance.
- When `next` is driven by a non-passing verification record, human output must separate failed commands, verification errors, and blocked reasons when those details are available.
- `explain phase` - explain one Mythic phase.
- `explain artifact` - explain one generated artifact and how to verify it.
- `tutorial` - print a first workflow tutorial.
- `completion --shell bash|zsh|powershell` - print shell completion scripts.
- Optional rich terminal rendering is enabled only when `rich` is installed and `MYTHIC_RICH=1` is set; plain output remains the fallback.

Current Stage 15 method commands:

- `method` - compatibility form that prints the active method notes without requiring network access.
- `method status` - report active method source, profile, content-derived version, cache path, section labels, pin state, and freshness.
- `method show` - print the active method notes, with optional JSON metadata.
- `method sync` - sync the canonical Mythic Engineering method notes into the local method cache; supports dry-run and JSON output.
- `method diff` - compare an imported markdown corpus against `method_manifest.json`, reporting missing, changed, and untracked markdown files.
- `method pin` - write `method_pin.json` for a clean imported corpus, recording manifest hash, source, ref, file count, paths, timestamp, and optional note.
- `import-md` - import the canonical markdown corpus and write both `method_manifest.json` and compatibility `_import_index.json`.
- `method.source` may be set in configuration or with `MYTHIC_METHOD_SOURCE`; supported sources are GitHub repository URLs.
- If no canonical method cache exists, method status must use the built-in seven-phase fallback profile and emit a freshness warning.

Current plugin hook dispatch:

- `mythic-vibe scan` (real-work path) emits `before_scan` to enabled plugins before building the project index, and `after_scan` after, via a per-invocation `PluginHookDispatcher`. Dry-run scans skip both hooks. Payloads are small dicts (`path`, scan flags) and (`path`, `index_path`, scalar counts). Plugin handler exceptions are logged to stderr and never break the command.
- `mythic-vibe packet create` (and its `codex-pack` / `evoke` aliases) emits `before_packet` and `after_packet` per packet on the real-work path. Dry-run skips both. Payload includes `source` (the alias used), `path`, `phase`, `role`, `task`, `audience`, `format`; `after_packet` adds `packet_id` and `packet_path`.
- `mythic-vibe packet ingest` emits `before_packet` and `after_packet` on the real-work path; the payload also includes `ingest_source` (the file path being ingested). `after_packet` adds the resolved `packet_id`, `packet_path`, plus `phase`, `role`, `task`, `audience`, and `format` from the resolved record.
- `mythic-vibe workflow plan --packets` (real-work path) emits one `before_packet`/`after_packet` pair per generated workflow step under a single dispatcher instance. The payload also includes `workflow_id` and `workflow_step_id`. `workflow plan` without `--packets` and any dry-run path skip emission entirely.
- Other declared hooks (`before_verify`, `after_verify`, `before_reflect`, `after_reflect`) remain wired through the dispatcher contract but are not yet emitted from the corresponding command code; they will be wired in subsequent slices.
- Plugins whose entrypoints fail to import are skipped silently during dispatch; surface plugin health via `mythic-vibe plugin inspect` instead.

Current compatibility aliases:

| Alias | Canonical behavior |
|---|---|
| `start` | `init` |
| `imbue` | `init` |
| `evoke` | `codex-pack` |
| `scry` | `doctor` |

## Exit-Code Policy

Exit codes are defined in `mythic_vibe_cli.exit_codes`.

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Operational failure |
| `2` | User input or configuration error |
| `3` | Verification failure |
| `4` | Unsafe operation blocked |

Commands should return these constants rather than inventing new meanings. If a new failure class is needed, update this document, `exit_codes.py`, and tests in the same change.

## Shared Runtime Options

Commands may expose shared runtime options where the behavior is meaningful:

| Option | Contract |
|---|---|
| `--json` | Emits a machine-readable JSON payload with no human preface text. Supported by structured reporting commands such as `status`, `doctor`, `examples`, `guide`, `next`, `explain`, `tutorial`, `completion`, `reflect`, `handoff`, `resume`, `config`, `codex-pack`, `method`, `grimoire`, `plugin`, `db migrate`, and `plunder`. |
| `--quiet` | Suppresses non-error human text output. JSON output remains emitted because it is the primary result. |
| `--verbose` | Emits additional operational detail when a command has meaningful extra detail. |
| `--dry-run` | Previews write/sync operations without writing files, modifying registries, creating databases, or fetching remote files. |

## Stage 1 Boundary

The current kernel hardening keeps `mythic_vibe_cli/cli.py` as the public compatibility module because `pyproject.toml` exposes `mythic_vibe_cli.cli:main`. Parser and top-level dispatch code lives in `mythic_vibe_cli/app.py`; command implementations and the registry live in `mythic_vibe_cli/commands.py`; shared terminal rendering and structured CLI errors live in `mythic_vibe_cli/output.py` and `mythic_vibe_cli/errors.py`. A future package split must preserve the public import path or provide an intentional migration path before moving command handlers into subpackages.
