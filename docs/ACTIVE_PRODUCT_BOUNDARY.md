# Active Product Boundary

The active product is **Mythic Vibe CLI**: a method-first command-line tool that turns creative intent into architecture-aware, verified, recoverable software work.

## Active Product Paths

| Path | Status | Responsibility |
|---|---|---|
| `mythic_vibe_cli/` | Active runtime | Installable CLI package, command dispatch, workflow state, config, packets, method sync |
| `tests/` | Active verification | Unit and CLI behavior tests for the active package |
| `pyproject.toml` | Active packaging | Package metadata, entrypoints, build configuration |
| `docs/` | Active governance | Architecture records, boundary rules, onboarding, API and workflow docs |
| root governance docs | Active continuity | Repository-level architecture, boundary, changelog, devlog, and data-flow records |

## Product Runtime Contract

The active CLI must remain independently executable without importing dormant runtime islands, research corpora, or vendor mirrors. It may read and write project artifacts such as `docs/`, `tasks/`, and `mythic/` in user projects, but its implementation dependencies stay inside `mythic_vibe_cli/` unless an ADR grants a specific adapter exception.

## Current Runtime Modules

| Module | Owns |
|---|---|
| `mythic_vibe_cli/__main__.py` | Package-module execution for `python -m mythic_vibe_cli` |
| `mythic_vibe_cli/cli.py` | Public compatibility entrypoint for `mythic_vibe_cli.cli:main` |
| `mythic_vibe_cli/app.py` | Argument parsing and top-level command dispatch |
| `mythic_vibe_cli/commands.py` | Command implementations, command registry, and compatibility aliases |
| `mythic_vibe_cli/output.py` | Shared terminal output helpers |
| `mythic_vibe_cli/errors.py` | Structured CLI error payloads and formatting |
| `mythic_vibe_cli/exit_codes.py` | Shared CLI return-code policy |
| `mythic_vibe_cli/workflow.py` | Mythic phases, scaffolding, status, check-ins, diagnostics |
| `mythic_vibe_cli/codex_bridge.py` | AI prompt packet rendering and context compaction |
| `mythic_vibe_cli/config.py` | Layered config resolution and env overrides |
| `mythic_vibe_cli/mythic_data.py` | Method source sync, markdown import, local cache |

## Change Rule

If a change modifies active runtime behavior, update at least one of these records when relevant:

- `docs/ARCHITECTURE.md`
- `docs/DOMAIN_MAP.md`
- `docs/DATA_FLOW.md`
- `docs/api.md`
- `CHANGELOG.md`
- `DEVLOG.md`

Use `mythic-vibe doctor --repo-boundary --path .` before merging boundary-sensitive work.
