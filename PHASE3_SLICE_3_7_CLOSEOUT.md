---
title: "Phase 3 — Slice 3.7 Close-out (Forge Reflection Capture)"
phase: PH-03
slice: 3.7
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 45e1af0
head_at_close: 17e1d57
test_baseline_open: 501 + 14 subtests
test_baseline_close: 528 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 3 Slice 3.7 — Forge Reflection Capture Close-out

## Purpose

Each forge run now leaves a structured **reflection** at
`mythic/reflections/<workflow_id>.{md,json}` summarising the cycle:
which steps succeeded, which failed, what gates blocked the
Auditor (if any), and what the operator's next step should be.

The reflection is the Scribe's permanent contribution to project
memory: future operators reading the markdown should be able to
reconstruct what happened without trawling the per-step ledger.

## Why two files

| File | Purpose | Reader |
|---|---|---|
| `<workflow_id>.json` | Structured data; round-trippable through `ForgeReflection.from_dict` | `forge reflection show --json`, future TUI / drift detection |
| `<workflow_id>.md` | Human-readable rendering | `cat`, editors, docs sites, `forge reflection show` (default) |

Both files contain the same information; the markdown is generated
from the JSON via `render_forge_reflection_markdown` so the two
cannot drift.

## Public surface

```bash
# Reflection auto-written at end of every forge run
mythic-vibe forge run --provider <name> --task "X"
# -> mythic/reflections/<workflow_id>.json
# -> mythic/reflections/<workflow_id>.md

# Suppress for tests / CI
mythic-vibe forge run --provider <name> --task "X" --skip-reflection

# Inspection (mirrors forge ledger surface)
mythic-vibe forge reflection list
mythic-vibe forge reflection latest
mythic-vibe forge reflection show --workflow WF-... [--json]
```

## Reflection data shape

```python
@dataclass(frozen=True)
class ForgeStepReflection:
    step_id: str
    role: str
    phase: str
    status: str
    summary: str = ""
    failed_gates: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    duration_ms: int | None = None

@dataclass(frozen=True)
class ForgeReflection:
    schema_version: int
    workflow_id: str
    task: str
    created_at: str
    completed_at: str
    final_status: str  # "success" | "failure" | "aborted" | "no-steps"
    success_count: int
    failure_count: int
    blocked_count: int
    aborted: bool
    steps: tuple[ForgeStepReflection, ...]
    next_step_recommendation: str
```

## `final_status` derivation

The orchestrator sets `final_status` from the resolved per-step
counts (not raw entry counts):

| Condition | `final_status` |
|---|---|
| Operator aborted at any gate | `"aborted"` |
| At least one step ended `failed` | `"failure"` |
| No ledger entries for the workflow | `"no-steps"` |
| Otherwise | `"success"` |

`aborted` precedence over `failure` matches the operator's mental
model: an explicit decline is more meaningful than a failure
buried somewhere upstream.

## Markdown layout

```markdown
# Forge Reflection

- Workflow: WF-...
- Task: ...
- Created at: ...
- Completed at: ...
- Final status: **success | failure | aborted | no-steps**
- Steps: 6 (succeeded=5, failed=1, blocked=0)

## Per-role outcomes

### step-01 :: Skald (intent) — succeeded

> captured intent

- Duration: 100 ms

### step-05 :: Auditor (verify) — failed

- Failed gates:
  - no-invariant-violation
- Notes:
  - verification gates failed: no-invariant-violation

## Next step

Step step-05 (Auditor) failed. Review the notes...
```

## `next_step_recommendation` matrix

| `final_status` | Recommendation pattern |
|---|---|
| `success` | "Cycle completed with every step succeeded. Review the per-agent artefacts and start the next forge cycle when ready." |
| `failure` | "Step `<step_id>` (`<role>`) failed. Review the notes in `mythic/forge_ledger.json` and rerun with `forge resume` (slice 3.8) once the failure is addressed." |
| `aborted` | "Run aborted at gate after `<step_id>` (`<role>`). Address the operator's concerns and rerun with `mythic-vibe forge run`." |
| `no-steps` | "No steps were recorded. Check the workflow plan and rerun." |

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 501 | **528** (+27) |
| Slash builtins | 52 | 52 |
| Argparse handlers | 50 | 50 |
| Source files | 71 | **72** (+1) |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## Tests added (27)

Eleven test classes in `tests/test_forge_reflection.py`:

- **Round-trip layer** (3) — `ForgeStepReflection` round-trip,
  invalid `duration_ms` decoded to None, full `ForgeReflection`
  round-trip.
- **`build_forge_reflection`** (5) — all-succeed yields `success`;
  failed step yields `failure` with role/step in recommendation;
  `aborted=True` takes precedence over failure; no ledger entries
  yields `no-steps` with all steps `not-run`; Auditor's
  `failed_gates` surface in the step reflection.
- **`render_forge_reflection_markdown`** (2) — canonical sections;
  failed gates listed.
- **`write_forge_reflection` / `load_forge_reflection`** (4) —
  both files created; round-trip via load; missing returns None;
  corrupt JSON returns None.
- **`list_forge_reflections`** (2) — sorted oldest-first by mtime;
  empty dir returns [].
- **Orchestrator integration** (3) — default writes both sidecars;
  `--skip-reflection` suppresses; `--skip-ledger` implies skip
  (no ledger to read from).
- **`forge reflection list`** (2) — list after run / empty
  project reports zero.
- **`forge reflection show`** (3) — markdown by default; JSON
  payload shape; unknown workflow_id returns USER_INPUT_ERROR.
- **`forge reflection latest`** (2) — picks newest by mtime;
  empty project reports no reflections.
- **Dispatcher** (1) — unknown subcommand emits visible error.

## What this slice deliberately did not do

- Did not update `docs/SESSION_HANDOFF.md`. The existing handoff
  machinery (`mythic_vibe_cli/handoff.py`) handles per-session
  handoffs separately from per-cycle reflections. A future slice
  could cross-link them, but this slice keeps the two surfaces
  independent.
- Did not implement `forge resume` — that's slice 3.8. The
  failure-mode recommendation in this slice already points at
  `forge resume` so when 3.8 lands the operator path is seamless.
- Did not gate the reflection write behind verification gates of
  the Scribe role. The Scribe's contract gates
  (`docs-match-implementation`, `handoff-recorded`) would need
  their own runners similar to slice 3.6's Auditor gates; that
  could land alongside slice 3.8 or as a follow-on.
- Did not surface reflections in the existing `status` / `next`
  output. PH-04 (TUI v2) is the natural home for that.
- Did not auto-publish reflections anywhere external. They live
  on disk only.

## Phase 3 progress

| Slice | Status | Depends on |
|---|---|---|
| 3.1 agent contract spec | ✅ done | — |
| 3.2 handoff ledger | ✅ done | 3.1 |
| 3.3 forge command (dry-run) | ✅ done | 3.1 + 3.2 |
| 3.4 approval gates | ✅ done | 3.3 |
| 3.5 provider-backed forge | ✅ done | 3.4 |
| 3.6 verifier integration | ✅ done | 3.5 |
| 3.7 reflection capture | ✅ done | 3.5 |
| 3.8 forge resume | next | 3.2 + 3.5 |

Seven of eight Phase 3 slices closed. Only `forge resume` remains.

## Smoke verification

```bash
$ mythic-vibe forge run --provider stub --task "test" --skip-reflection=false
# (with a real provider configured)
# Mythic forge run
# - Workflow: WF-20260429210301-abc12345
# - Task: test
# - Provider: stub
# - Steps: 6
# - Succeeded: 6
# - Failed: 0
# - Ledger: ./mythic/forge_ledger.json
# - Reflection (md): ./mythic/reflections/WF-...md
# - Reflection (json): ./mythic/reflections/WF-...json
```

## Next slice (3.8)

**Forge resume.** Read the most recent reflection (or accept a
`--workflow <id>` argument), find the first failed/blocked step,
and resume the run from there. Agents that already succeeded keep
their `AgentOutput` from the ledger; the resume picks up at the
failure boundary. The reflection's
`next_step_recommendation` already points at `forge resume`, so
when 3.8 lands the operator path is seamless.
