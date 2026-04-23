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
python -m mythic_vibe_cli.cli --help
```

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

### Health and method state

- `doctor` (alias: `scry`)
  - Checks structural and state validity.
- `sync`
  - Pulls method content from configured source.
- `method`
  - Displays loaded method notes.

### Extended ritual surfaces

Depending on implementation state, additional commands may be exposed:

- `weave`
- `prune`
- `heal`
- `oath`
- `grimoire add|list`
- `config set`
- `db migrate`

Use `--help` for current option details and defaults.

---

## 3) Core module contracts

### `mythic_vibe_cli.cli`

Responsibility:

- command definitions,
- argument parsing,
- dispatch boundaries.

Contract expectations:

- published flags remain stable where practical,
- aliases avoid ambiguity,
- error output is actionable.

### `mythic_vibe_cli.workflow`

Responsibility:

- phase sequencing,
- artifact updates,
- continuity state changes.

Contract expectations:

- deterministic phase transitions,
- explicit remediation hints on failure,
- no hidden global side effects.

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
