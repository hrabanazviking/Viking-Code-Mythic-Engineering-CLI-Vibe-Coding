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
- `import-md` - import the canonical markdown corpus and write both `method_manifest.json` and compatibility `_import_index.json`.
- If no canonical method cache exists, method status must use the built-in seven-phase fallback profile and emit a freshness warning.

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
