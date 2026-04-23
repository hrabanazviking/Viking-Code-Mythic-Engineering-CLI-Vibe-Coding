# API Reference

This document describes the primary integration surfaces for the active **Mythic Vibe CLI** product path.

> Note: This repository contains historical and research artifacts. Treat this file as authoritative only for active CLI-facing APIs/workflows.

---

## 1) CLI entrypoint

### Module execution

```bash
python -m mythic_vibe_cli.cli --help
```

### Installed command (environment-dependent)

```bash
mythic --help
```

If both are available, prefer the installed command for daily use and module execution for debugging.

---

## 2) Core modules and contracts

### `mythic_vibe_cli.cli`

Responsibility:
- command surface,
- argument parsing,
- dispatch to workflow/config/data subsystems.

Contract guidance:
- Keep command names and flags stable once published.
- Add aliases only when they do not create ambiguity.

### `mythic_vibe_cli.workflow`

Responsibility:
- orchestrates phase loop,
- manages artifact creation/updates,
- supports status/check-in behavior.

Contract guidance:
- Preserve deterministic phase ordering unless explicitly versioned.
- Emit actionable errors with remediation hints.

### `mythic_vibe_cli.config`

Responsibility:
- resolve layered configuration from defaults + files + env.

Contract guidance:
- Document precedence in code comments and user docs.
- Avoid side effects during parse/load.

### `mythic_vibe_cli.codex_bridge`

Responsibility:
- compose prompt/context packets,
- apply compaction and budget logic.

Contract guidance:
- Prefer explicit section boundaries.
- Keep packet outputs inspectable and reproducible.

### `mythic_vibe_cli.mythic_data`

Responsibility:
- sync/import/cache method data from supported providers.

Contract guidance:
- Isolate network concerns here.
- Avoid absorbing orchestration responsibilities.

---

## 3) Artifact interface (filesystem contract)

CLI workflows interact with project artifacts such as:

- `docs/` (governance and architecture notes)
- `tasks/` (execution plans/checklists)
- `mythic/` (method/runtime state)
- `DEVLOG.md` and related operational logs
- local cache/state files (for example `weave.db` where applicable)

These are part of the product contract: if you rename or relocate them, update docs and migration behavior together.

---

## 4) Backward compatibility guidance

When changing CLI/API behavior:

1. Prefer additive changes over breaking renames.
2. If breaking, provide migration notes in the same PR.
3. Update `docs/quickstart.md` and architecture docs concurrently.
4. Include verification commands proving new behavior.

---

## 5) Example integration pattern (subprocess)

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

Use subprocess execution when integrating from external tooling to keep process boundaries explicit.

---

## 6) Example integration pattern (in-repo module import)

```python
# Pseudocode pattern: import only stable module surfaces.
from mythic_vibe_cli import cli, workflow, config

# Build your wrapper around documented commands/workflows
# rather than reaching into private helper internals.
```

Prefer public, stable functions and avoid coupling to private helpers.

---

## 7) Change checklist for API-affecting PRs

- [ ] CLI help/output updated where relevant
- [ ] Docs updated (`quickstart`, `api`, and architecture/domain docs as needed)
- [ ] Tests/checks run and recorded
- [ ] Boundary rules validated (no forbidden cross-island imports)
