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
| `--json` | Emits a machine-readable JSON payload with no human preface text. Supported by structured reporting commands such as `status`, `doctor`, `config`, `codex-pack`, `grimoire`, `db migrate`, and `plunder`. |
| `--quiet` | Suppresses non-error human text output. JSON output remains emitted because it is the primary result. |
| `--verbose` | Emits additional operational detail when a command has meaningful extra detail. |
| `--dry-run` | Previews write/sync operations without writing files, modifying registries, creating databases, or fetching remote files. |

## Stage 1 Boundary

The current kernel hardening keeps `mythic_vibe_cli/cli.py` as the public compatibility module because `pyproject.toml` exposes `mythic_vibe_cli.cli:main`. Parser and top-level dispatch code lives in `mythic_vibe_cli/app.py`; command implementations and the registry live in `mythic_vibe_cli/commands.py`; shared terminal rendering and structured CLI errors live in `mythic_vibe_cli/output.py` and `mythic_vibe_cli/errors.py`. A future package split must preserve the public import path or provide an intentional migration path before moving command handlers into subpackages.
