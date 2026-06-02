---
title: "Phase 3 — Slice 3.8 Close-out (Forge Resume — Phase 3 Finale)"
phase: PH-03
slice: 3.8
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: e313862
head_at_close: 9093846
test_baseline_open: 528 + 14 subtests
test_baseline_close: 538 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
phase_status: PHASE 3 COMPLETE
---

# Phase 3 Slice 3.8 — Forge Resume Close-out

## Purpose

The Phase 3 finale. Picks up a partially-completed forge run from
the ledger and re-executes only the steps that are not already
`succeeded`. Closes the operator loop that the slice-3.7
reflection's recommendation pointed at:

```
forge run fails
    ↓
reflection: "Step <X> failed. Rerun with forge resume."
    ↓
forge resume
    ↓
continues from the failed step, with prior succeeded outputs flowing
    ↓
new reflection written, replacing the old one
```

## Public surface

```bash
mythic-vibe forge resume --provider <name>
                         [--workflow <id>]
                         [--interactive] [--strict]
                         [--skip-ledger] [--skip-reflection]
```

`--workflow` defaults to the most recent ledger entry. The resume
reconstructs the plan from the original task (read from the first
ledger entry's `agent_input.task`) and pins the existing
workflow_id, so newly-appended ledger entries share the resumed
workflow's identity.

## Resume logic

```
1. Resolve workflow_id (--workflow or latest from ledger).
2. Read original task from existing ledger entries.
3. Rebuild plan via WorkflowEngine.build_plan, pin existing id.
4. Walk plan steps; find the first whose latest ledger entry is
   NOT `succeeded` — the resume point.
5. Skip every step before the resume point; record them in the
   payload as ``resumed_skipped`` with their original summary.
6. From the resume point onwards: same loop as cmd_forge_run
   (materialize input with prior_outputs, validate, append running
    entry, call provider, run Auditor gates if applicable,
    update_step to succeeded/failed, fire gate handler if
    interactive).
7. Build + write a fresh reflection (overwriting the old one for
   the same workflow id).
```

When every step in the workflow already succeeded, resume returns
`SUCCESS` with `noop=true` and a clear message — no provider call
is made.

## Exit code matrix

Same as `forge run`:

| Outcome | Code |
|---|---|
| Every re-executed step succeeded | `SUCCESS` (0) |
| Any re-executed step failed | `OPERATIONAL_FAILURE` (1) |
| Operator aborted at gate | `UNSAFE_OPERATION_BLOCKED` (4) |
| `--strict` triggered on Auditor failure | `UNSAFE_OPERATION_BLOCKED` (4) |
| Missing `--provider` | `USER_INPUT_ERROR` (2) |
| Empty ledger / unknown workflow | `USER_INPUT_ERROR` (2) |

## New helpers

- `_latest_workflow_id_from_ledger(ledger)` — most recent ledger
  row's workflow_id (the default when `--workflow` isn't supplied).
- `_resolve_resume_target(workflow_id, ledger)` — folds the "no
  workflow / unknown workflow" branches into a single
  `(workflow_id, error_message, entries)` return.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 528 | **538** (+10) |
| Slash builtins | 52 | 52 |
| Argparse handlers | 50 | 50 |
| Source files | 72 | 72 |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## Tests added (10)

Six test classes in `tests/test_forge_resume.py`, all using stub
providers with optional per-role failure injection:

- **`ResumeAfterProviderFailureTests`** (2)
  - `test_resume_reruns_only_failed_and_remaining_steps` — seed
    with Auditor failure, resume re-runs Auditor + Scribe only
    (healing provider sees `{"Auditor", "Scribe"}`); final ledger
    has every step `succeeded`.
  - `test_resume_writes_a_new_reflection_replacing_the_old_one` —
    original reflection records `failure`; after resume the same
    file records `success` with full step count.
- **`ResumeAfterGateFailureTests`** (1) — Auditor gate failure on
  seed (slice-3.6 verifier); resume with passing gates recovers
  the run.
- **`ResumeByWorkflowIdTests`** (2) — `--workflow` picks specified;
  no flag picks latest by mtime.
- **`ResumeNoOpTests`** (1) — every step already succeeded yields
  `noop=true` in JSON; provider not called.
- **`ResumeUserErrorTests`** (3) — empty ledger / unknown workflow
  / missing `--provider` all return `USER_INPUT_ERROR`.
- **`ResumeWorkflowIdContinuityTests`** (1) — every ledger entry
  shares the original workflow_id after resume.

## What this slice deliberately did not do

- Did not extract a shared `_execute_step` helper between
  `cmd_forge_run` and `cmd_forge_resume`. The two functions share
  loop logic but the duplication was tractable for slice 3.8;
  extracting could land as a future hygiene pass when a third
  caller appears.
- Did not add `forge resume --from-step <step_id>` to manually
  override the resume point. The default ("first non-succeeded")
  matches operator intuition; manual override could be added
  later.
- Did not deduplicate the existing ledger entries on resume. New
  entries are appended; the latest matching entry per
  (workflow_id, step_id) wins via `find_step`. The historical
  entries stay on the ledger as audit trail of what happened.
- Did not surface the resume in `mythic-vibe status` output. PH-04
  (TUI v2) is the natural home for forge state in the dashboard.

## Phase 3 — FULLY COMPLETE

All eight slices closed:

| Slice | Status | Closed at | Tests added |
|---|---|---|---|
| 3.1 agent contract spec | ✅ | `2920aa4` | +38 |
| 3.2 handoff ledger | ✅ | `adc6ae1` | +28 |
| 3.3 forge command (dry-run) | ✅ | `cbc2b24` | +21 |
| 3.4 approval gates | ✅ | `9231073` | +17 |
| 3.5 provider-backed forge | ✅ | `fe763e1` | +15 |
| 3.6 verifier integration | ✅ | `c0da15b` | +18 |
| 3.7 reflection capture | ✅ | `17e1d57` | +27 |
| 3.8 forge resume | ✅ | `9093846` | +10 |

**Phase 3 net delta**: +174 tests, +5 new modules
(`workflow_agents.py`, `forge_ledger.py`, `forge.py`,
`forge_verifier.py`, `forge_reflection.py`), 1 new top-level
argparse handler (`forge`) with five subcommands (`plan`, `run`,
`resume`, `ledger`, `reflection`), 1 new slash entry (`/forge`).

## Phase 3 capability summary

The Mythic Vibe CLI can now:

1. **Plan** a six-role forge cycle from a one-line task
   (`forge plan --dry-run --task "X"`).
2. **Execute** that cycle through a configured AI provider
   (`forge run --provider <name>`), with each agent's response
   captured into a typed `AgentOutput` and the contract gates
   enforced for the Auditor.
3. **Pause** at operator-controlled gates (`--interactive`) or
   abort on verifier failure (`--strict`).
4. **Reflect** on the cycle outcome with a structured
   markdown+JSON artifact at `mythic/reflections/`.
5. **Resume** from any failure point without re-running already
   succeeded agents (`forge resume`).
6. **Inspect** the per-step ledger (`forge ledger list/show/latest`)
   and the per-cycle reflections (`forge reflection list/show/latest`).

All of it runs hermetically against the `copy-paste` provider
without any cloud API key, so operators can prototype Mythic
Engineering rituals locally before configuring any LLM.

## Master roadmap progress

| Phase | Status |
|---|---|
| 1. Foundation Audit & Quality Sweep | ✅ closed |
| 2. Slash Command Surface | 🟡 5 of 8 slices done (rest blocked on later phases) |
| 3. Multi-Agent Forge | ✅ **CLOSED** — all 8 slices done |
| 4. TUI Revolution v2 | open |
| 5. Knowledge Graph & Persistent Memory | open |
| 6. Local LLM Sovereignty | open |
| 7. Voice & Multimodal | open |
| 8. Provider Routing & Hardware-Aware | open |
| 9. Island Integrations | open |
| 10. Plugin Ecosystem | open |
| 11. Security, Sandbox & Permissions | open |
| 12. CI/CD & Deployment | open |
| 13. Drift Detection & Self-Healing | open |
| 14. Policy Engine & Constraint Verification | open |
| 15. Conversation Memory & Compaction | open |
| 16. MCP / ACP / OpenTelemetry | open |
| 17. Multi-Surface Access | open |
| 18. Robustness Sweeps Round 1–4 | open |
| 19. Distribution | open |
| 20. v1.0.0 — Sovereign OS Launch | open |

## Next decision point

With Phase 3 closed, the next move is operator-priority. Three
viable candidates by master-roadmap dependency order:

1. **Begin Phase 4 (TUI Revolution v2)** — surface the forge state
   live in the Textual TUI. Slice 4.1 adds the Loop Navigator
   panel; subsequent slices add the diff review screen, packet
   viewer, and real-time diagnostics.

2. **Begin Phase 5 (Knowledge Graph & Persistent Memory)** —
   slice 5.1 designs the SQLite schema. Provides the retrieval
   foundation that future forge runs and PH-04 TUI will consume.

3. **Begin Phase 11 (Security, Sandbox & Permissions)** —
   slice 11.1 introduces approval modes
   (`suggest`/`auto-approve`/`partial`). Independent of PH-04 and
   PH-05; tightens the operator-safety story before more
   high-stakes phases (PH-06 local LLM, PH-09 island
   integrations) ship.

Phase 4 is the most natural follow-on (forge state begs to be
visualised). Awaiting Volmarr's call.
