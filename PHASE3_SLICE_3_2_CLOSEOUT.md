---
title: "Phase 3 — Slice 3.2 Close-out (Forge Handoff Ledger)"
phase: PH-03
slice: 3.2
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: a27ba0b
head_at_close: adc6ae1
test_baseline_open: 402 + 14 subtests
test_baseline_close: 430 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 3 Slice 3.2 — Forge Handoff Ledger Close-out

## Purpose

Pure persistence layer for the multi-agent forge. No orchestrator,
no CLI command, no provider call. Records every per-agent step the
future `mythic-vibe forge` orchestrator runs, with the typed
`AgentInput` / `AgentOutput` payloads from slice 3.1 plus status,
timing, and operator notes.

This slice is the foundation for slice 3.3 (forge command,
dry-run), which will write entries during plan generation, and
slice 3.5 (provider-backed forge), which will update them as
agents complete.

## Why a separate file from `workflow_history.json`

The master roadmap text says "extend `mythic/workflow_history.json`
to record per-agent step", but the existing file is per-plan
(consumed by `mythic-vibe workflow history`). Adding per-step
entries inside it would change semantics non-additively and would
require either a discriminator field or a breaking change to the
`workflow history` reader.

Two files, separate purposes:

| File | Granularity | Source | Reader |
|---|---|---|---|
| `mythic/workflow_history.json` | one entry per generated *plan* | `WorkflowEngine.append_history` (existing) | `mythic-vibe workflow history` (existing) |
| `mythic/forge_ledger.json` | one entry per *step* | `ForgeLedger.append` (new) | `mythic-vibe forge ledger` (slice 3.3) |

## What landed

### `mythic_vibe_cli/forge_ledger.py` (~225 lines)

#### Constants

```python
FORGE_LEDGER_FILENAME = "forge_ledger.json"
FORGE_LEDGER_LIMIT = 200
FORGE_LEDGER_SCHEMA_VERSION = 1
FORGE_STEP_STATUSES = ("pending", "running", "succeeded", "failed", "blocked")
```

#### `ForgeLedgerEntry` (frozen dataclass)

```python
ForgeLedgerEntry(
    workflow_id: str,
    step_id: str,
    role: str,
    status: str,                     # one of FORGE_STEP_STATUSES
    started_at: str,                  # ISO 8601
    agent_input: AgentInput,
    completed_at: str | None = None,
    duration_ms: int | None = None,
    agent_output: AgentOutput | None = None,
    notes: tuple[str, ...] = (),
)
```

- `to_dict()` / `from_dict()` round-trip — recursively walks
  `AgentInput` / `AgentOutput` via their slice-3.1 helpers.
- `with_status(status, *, completed_at=None, duration_ms=None,
  agent_output=None, notes=None)` returns a copy with replaced
  fields. Validates `status` against `FORGE_STEP_STATUSES`.

#### `ForgeLedger` (per-project handle)

| Method | Behaviour |
|---|---|
| `path` | `<root>/mythic/forge_ledger.json` |
| `load()` | parse → `list[ForgeLedgerEntry]`; empty list on missing file or corrupt JSON (defensive) |
| `append(entry)` | atomic write via `file_mutation_queue`; rotates at `FORGE_LEDGER_LIMIT` |
| `update_step(workflow_id, step_id, *, status, ...)` | replaces the most recent matching entry; raises `ValueError` on no-match |
| `latest(*, limit=20)` | newest window (newest last) |
| `find_by_workflow(workflow_id)` | every entry for that workflow in append order |
| `find_step(workflow_id, step_id)` | most recent matching entry or None |

### Lifecycle

A typical step's ledger trail across the upcoming slices 3.3–3.5:

```
slice 3.3 forge --dry-run → append(status="pending")
                            (no orchestrator yet; just records the plan)
slice 3.4 approval gate    → update_step(status="running")
                              after operator says "yes" at the gate
slice 3.5 provider runs    → update_step(status="succeeded" | "failed",
                                          completed_at=...,
                                          duration_ms=...,
                                          agent_output=...)
```

Failed contract validation (slice 3.1 `validate_input` /
`validate_output`) before the agent runs becomes
`update_step(status="blocked")` — the orchestrator records the
attempted handoff but refuses to advance.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 402 | **430** (+28) |
| Source files | 68 | **69** (+1) |
| Slash builtins | 51 | 51 |
| Argparse handlers | 49 | 49 |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## Tests added (28)

Eight test classes in `tests/test_forge_ledger.py`:

- `ForgeLedgerEntryRoundTripTests` (4) — pending entry round-trip;
  completed entry with full payload; rejection of missing
  `agent_input`; defensive parsing of invalid `duration_ms`.
- `WithStatusTests` (4) — replacement; unknown-status rejection;
  field preservation; status enum check.
- `ForgeLedgerPathTests` (1) — path resolves under `mythic/`.
- `ForgeLedgerEmptyAndCorruptTests` (4) — missing file → `[]`;
  corrupt JSON → `[]`; non-object top-level → `[]`; malformed rows
  skipped, valid rows kept.
- `ForgeLedgerAppendTests` (3) — single append; order preserved;
  rotation caps at `FORGE_LEDGER_LIMIT`.
- `ForgeLedgerUpdateStepTests` (5) — in-place replacement; full
  completion record; latest-match-only when same step appears
  twice; raises on no-match; rejects unknown status.
- `ForgeLedgerQueryTests` (5) — `latest()` window; zero/negative
  limit returns `[]`; `find_by_workflow` groups; `find_step`
  most-recent + None.
- `ForgeLedgerConcurrencyTests` (1) — 40 threads append in
  parallel; every entry survives (file_mutation_queue contract).
- `ForgeLedgerFileShapeTests` (1) — written file carries `version`
  + `entries` keys.

## What this slice deliberately did not do

- Did not implement `mythic-vibe forge` or `forge ledger` CLI
  commands. Those land in slice 3.3.
- Did not enforce status transition order (pending → running →
  succeeded/failed/blocked). The orchestrator (slice 3.4+) decides
  legal transitions; the ledger is a passive recorder.
- Did not validate the `AgentInput`/`AgentOutput` payloads against
  their slice-3.1 contracts. That validation happens at the
  orchestrator boundary, not at write time, so a `blocked` row can
  legitimately carry a contract-violating `agent_output`.
- Did not extend `workflow_history.json`. Two files, separate
  purposes (rationale above).
- Did not migrate any existing data. Fresh ledger; no prior file
  shape to convert.

## Phase 3 progress

| Slice | Status | Depends on |
|---|---|---|
| 3.1 agent contract spec | ✅ done | — |
| 3.2 handoff ledger | ✅ done | 3.1 |
| 3.3 forge command (dry-run) | next | 3.1 + 3.2 |
| 3.4 approval gates | open | 3.3 |
| 3.5 provider-backed forge | open | 3.4 |
| 3.6 verifier integration | open | 3.5 |
| 3.7 reflection capture | open | 3.5 |
| 3.8 forge resume | open | 3.2 + 3.5 |

## Next slice (3.3)

Forge command (dry-run). First user-facing slice of Phase 3:

```bash
mythic-vibe forge --dry-run --task "Refactor router"
```

Builds a `WorkflowPlan` via the existing engine, walks the role
sequence, materialises one `AgentInput` per step using the slice-3.1
contract, writes a `pending` `ForgeLedgerEntry` per step via the
slice-3.2 ledger, and prints the per-agent packets without invoking
any provider.
