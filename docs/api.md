# API Reference

This document defines the primary integration surfaces for the active **Mythic Vibe CLI** product path.

> Scope note: this repository contains historical and research artifacts. This API record is authoritative only for active CLI-facing behavior.

---

## 1) Entrypoints

### Installed CLI (preferred for day-to-day use)

```bash
mythic --help
# or
mythic-vibe --help
```

### Module execution (useful for debugging/install edge cases)

```bash
python -m mythic_vibe_cli --help
python -m mythic_vibe_cli.cli --help
```

The package entrypoint (`python -m mythic_vibe_cli`) is preferred for install/path debugging. The `cli` module entrypoint remains supported for compatibility.

Argument parsing and top-level dispatch live in `mythic_vibe_cli.app`. Command implementations and the registry live in `mythic_vibe_cli.commands`. Compatibility re-exports remain available through `mythic_vibe_cli.cli`. The dispatch and exit-code policy are recorded in `docs/COMMAND_CONTRACTS.md`.

---

## 2) Command contracts (high-level)

### Initialization and setup

- `init` (alias: `imbue`)
  - Initializes a project scaffold aligned to method phases.

### Prompt bridge and AI collaboration

- `codex-pack` (alias: `evoke`)
  - Produces structured context packet artifacts for ChatGPT/Codex.
- `codex-log`
  - Records response summaries for continuity.

### Workflow continuity

- `checkin`
  - Persists structured phase updates.
- `status`
  - Reports current progress and phase state.
- `workflow plan`
  - Writes a deterministic six-role orchestration artifact and exposes packet-ready requests. With `--packets`, creates one packet artifact per role step without provider execution. Each freshly built plan carries a deterministic `workflow_id` of the form `WF-<UTC compact>-<sha8(task+created_at)>`, persisted in `mythic/workflow_plan.json` and stamped onto every generated packet's `.meta.json` payload.
- `workflow run`
  - Previews ordered role execution with `--dry-run`; `--packets-only` validates required packet artifacts; real provider execution is intentionally blocked until safety gates are added. Surfaces the plan's `workflow_id` in JSON output, and each `packet_status` entry reports a `match_strategy` of `"id"`, `"text"`, or `null`.
- `workflow packets`
  - Lists packet readiness for saved or generated workflow plans without executing providers. Prefers `(workflow_id, workflow_step_id)` matches when both plan and packet carry IDs; falls back to the legacy `(role, phase, task, audience, output_format)` text match when either side is missing IDs.
- `state show`
  - Displays schema-versioned project state from `mythic/status.json`.
- `state validate`
  - Validates `mythic/status.json` and returns verification failure on invalid state.

### Health and method state

- `doctor` (alias: `scry`)
  - Checks structural and state validity.
- `sync`
  - Pulls method content from configured source.
- `import-md`
  - Imports the canonical markdown corpus and writes `method_manifest.json` plus the compatibility `_import_index.json`.
- `method`
  - Displays active method notes.
- `method status`
  - Reports the active method source, profile, content-derived version, cache path, section labels, pin state, and freshness warning.
- `method show`
  - Displays the active method notes with optional JSON metadata.
- `method sync`
  - Syncs canonical Mythic Engineering notes into the local method cache.
- `method diff`
  - Compares an imported method corpus against `method_manifest.json`.
- `method pin`
  - Writes `method_pin.json` for a clean imported method corpus.

### Extended ritual surfaces

Depending on implementation state, additional commands may be exposed:

- `weave`
- `prune`
- `heal`
- `workflow plan`
- `workflow run`
- `workflow packets`
- `oath`
- `grimoire add|list`
- `plugin list|inspect|disable`
- `examples`
- `guide`
- `next`
- `explain phase|artifact`
- `tutorial`
- `completion`
- `config set`
- `db migrate`
- `plunder inspect|plan|fetch|apply|record`

Use `--help` for current option details and defaults.

`db migrate` upgrades legacy `mythic/status.json` files into the current schema-versioned `ProjectState` format, preserving the previous file under `mythic/backups/` before rewriting it. It also keeps the existing local `weave.db` migration behavior.

`plunder` is now a staged lawful reuse workflow. `inspect` classifies Apache/MIT/BSD-compatible licenses, `plan` writes `mythic/imports/plunder_plan.json`, `fetch` caches one source file, `apply` refuses incompatible or unknown licenses unless forced and records provenance in `mythic/imports/plunder_manifest.json`, and `record` can append provenance manually. Unknown, GPL, AGPL, or LGPL licenses emit a "Do not plunder" warning for explicit review.

`plugin` exposes the versioned grimoire registry. `plugin list` reports registry health without importing plugin code, `plugin inspect` imports one registered `module:object` entrypoint and reports declared hooks, and `plugin disable` preserves a plugin record while preventing it from being treated as active. Supported hooks are `before_scan`, `after_scan`, `before_packet`, `after_packet`, `before_verify`, `after_verify`, `before_reflect`, and `after_reflect`.

Stage 14 UX commands provide orientation without changing project state. `examples`, `guide`, `next`, `explain`, and `tutorial` answer what happened, what to do next, and how to verify it. `next` prioritizes failed or blocked verification records, then the latest handoff next step, then normal phase guidance; when verification is not passing, human output separates failed commands, verification errors, and blocked reasons. High-traffic command help for `init`, `next`, `verify`, `packet create`, `reflect`, `resume`, and `doctor` includes concrete examples. `completion --shell bash|zsh|powershell` prints shell completion scripts. Plain output is the default; optional rich rendering is enabled with `MYTHIC_RICH=1` when the `rich` package is installed.

Stage 15 method commands make the Mythic Engineering method profile visible. `method status` uses the local cache when available, otherwise reports the built-in fallback profile without requiring a network call. The reported version is derived from method content, so users can see when the active method corpus changes. `method.source` can be set in config or with `MYTHIC_METHOD_SOURCE` to point at another GitHub method repository. `import-md` writes a manifest-backed markdown corpus import with source ref, relative paths, byte sizes, and SHA-256 hashes. `method diff` uses that manifest to report missing, changed, and untracked markdown files. `method pin` refuses dirty corpora and writes `method_pin.json` with the manifest hash, source, ref, file count, paths, timestamp, and optional note.

### Shared runtime options

The active command surface now supports shared runtime controls where useful:

| Option | Use |
|---|---|
| `--json` | Return structured machine-readable output. Supported by reporting/structured commands including `status`, `state show`, `state validate`, `doctor`, `examples`, `guide`, `next`, `explain`, `tutorial`, `completion`, `config`, `codex-pack`, `method`, `grimoire`, `plugin`, `db migrate`, and `plunder`. |
| `--quiet` | Suppress non-error human text output. |
| `--verbose` | Show additional operational detail when the command provides it. |
| `--dry-run` | Preview write/sync operations without changing files, registries, databases, or remote state. |

---

## 3) Core module contracts

### `mythic_vibe_cli.cli`

Responsibility:

- public compatibility entrypoint,
- stable import surface for `main`, `build_parser`, and `COMMAND_HANDLERS`.

Contract expectations:

- stays thin and side-effect free,
- preserves installed script compatibility.

### `mythic_vibe_cli.app`

Responsibility:

- command definitions,
- argument parsing,
- top-level dispatch boundaries.

Contract expectations:

- published flags remain stable where practical,
- aliases avoid ambiguity,
- error output is actionable.

### `mythic_vibe_cli.commands`

Responsibility:

- command implementations,
- command registry,
- compatibility alias mapping.

Contract expectations:

- each command returns a documented exit-code constant,
- user-facing text goes through `mythic_vibe_cli.output`,
- actionable errors use `mythic_vibe_cli.errors` where structured context is needed.
- JSON-mode commands emit JSON without leading human text.
- dry-run paths avoid writes and avoid remote fetches.

### `mythic_vibe_cli.output` and `mythic_vibe_cli.errors`

Responsibility:

- shared plain-text terminal rendering,
- structured CLI error payloads and formatting.

Contract expectations:

- no command-specific business logic,
- stable formatting helpers for future `--json`, `--quiet`, and `--verbose` modes.

### `mythic_vibe_cli.workflow`

Responsibility:

- phase sequencing,
- artifact updates,
- continuity state changes.

Contract expectations:

- deterministic phase transitions,
- explicit remediation hints on failure,
- no hidden global side effects.

### `mythic_vibe_cli.workflow_engine`

Responsibility:

- deterministic six-role orchestration planning,
- handoff order between Mythic roles,
- packet-ready request generation,
- durable `mythic/workflow_plan.json` artifact writing.

Contract expectations:

- no external provider execution by default,
- role names come from `mythic_vibe_cli.ai.prompts.roles`,
- default order remains Skald -> Architect -> Cartographer -> Forge Worker -> Auditor -> Scribe unless a caller supplies an explicit sequence.

### `mythic_vibe_cli.config`

Responsibility:

- layered config resolution and coercion.

Contract expectations:

- documented precedence,
- deterministic parsing,
- low side-effect initialization.

### `mythic_vibe_cli.codex_bridge`

Responsibility:

- context packet assembly,
- budget-aware compaction,
- stable packet sectioning.

Contract expectations:

- reproducible output from same input/config,
- explicit section boundaries,
- transparent truncation/compaction behavior.

### `mythic_vibe_cli.mythic_data`

Responsibility:

- method sync/import/cache logic.

Contract expectations:

- provider/network logic isolated here,
- graceful degradation on network faults,
- no orchestration leakage into data layer.

---

## 4) Filesystem interface contract

The CLI operates on durable artifacts, including:

- `docs/` — architecture and governance records,
- `tasks/` — plans/checklists,
- `mythic/` — method/runtime state files,
- root records such as `DEVLOG.md` and `CHANGELOG.md`,
- local state files (e.g., `weave.db`, when enabled).

Any relocation/rename should be handled as a breaking change with migration notes.

---

## 5) Configuration interface summary

Precedence order (low -> high):

1. `~/.mythic-vibe.json`
2. `$XDG_CONFIG_HOME/mythic-vibe/config.json`
3. `<project>/.mythic-vibe.json`
4. environment variables

Known env overrides include:

- `MYTHIC_EXCERPT_LIMIT`
- `MYTHIC_PACKET_CHAR_BUDGET`
- `MYTHIC_AUTO_COMPACT`

Inspect current resolved config with:

```bash
mythic-vibe config --path .
```

---

## 6) Compatibility policy

When behavior changes:

1. Prefer additive changes over breaking ones.
2. If breaking, include migration notes in the same PR.
3. Update `docs/quickstart.md`, `docs/api.md`, and architecture docs together.
4. Include verification commands that prove new behavior.

---

## 7) Integration examples

### Subprocess integration

```python
import subprocess

result = subprocess.run(
    ["python", "-m", "mythic_vibe_cli.cli", "--help"],
    check=True,
    capture_output=True,
    text=True,
)
print(result.stdout)
```

### In-repo module usage (pattern)

```python
from mythic_vibe_cli import cli, workflow, config

# Build wrappers around documented surfaces
# rather than private helpers.
```

---

## 8) API-change PR checklist

- [ ] Help output/examples updated where relevant
- [ ] Docs updated (`quickstart`, `api`, architecture/domain docs)
- [ ] Tests/checks executed and recorded
- [ ] Boundary rules validated
- [ ] Continuity records updated (`DEVLOG`, `CHANGELOG`)
