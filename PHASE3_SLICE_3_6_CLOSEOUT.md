---
title: "Phase 3 — Slice 3.6 Close-out (Verifier Integration)"
phase: PH-03
slice: 3.6
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: c326ec9
head_at_close: c0da15b
test_baseline_open: 483 + 14 subtests
test_baseline_close: 501 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 3 Slice 3.6 — Verifier Integration Close-out

## Purpose

The Auditor's slice-3.1 contract declared three named verification
gates that slice 3.5 left empty (every Auditor step succeeded
purely on the provider's say-so). Slice 3.6 fills the gap so the
Auditor actually checks the project state, not just its own prose.

## What landed

### `mythic_vibe_cli/forge_verifier.py` (~210 lines)

Three gate runners, each reusing an existing `verify/` helper:

| Gate | Backed by | Pass condition |
|---|---|---|
| `diff-reviewed-against-architecture` | `verify.git_diff.collect_changed_files` | Audit response mentions every changed file by path, OR there are no changed files, OR git is unavailable |
| `no-invariant-violation` | `verify.invariant_checker.check_invariants` | Invariant check reports zero errors |
| `test-evidence-recorded` | `verify.load_latest_verification` | `mythic/verifications/latest.json` exists with `result == "pass"` or `"succeeded"` |

Plus:

```python
DEFAULT_AUDITOR_GATES: dict[str, GateRunner] = {
    "diff-reviewed-against-architecture": gate_diff_reviewed,
    "no-invariant-violation": gate_no_invariant_violation,
    "test-evidence-recorded": gate_test_evidence_recorded,
}

def run_auditor_gates(
    plan, agent_input, agent_output, root,
    *,
    gate_names: tuple[str, ...] | None = None,
    gates: dict[str, GateRunner] | None = None,
) -> tuple[VerificationResult, ...]
```

Unknown gate names (typos at the contract layer) become
`VerificationResult(passed=False, detail="no runner registered for
gate ...")`, and runner exceptions are caught and returned as
`"runner crashed: ..."` results — so a buggy gate runner never
crashes the orchestrator.

### `cmd_forge_run` integration

Three changes in `forge.py`:

1. **New `auditor_gates` keyword** with three semantics:
   - `auditor_gates=None` (production default) → use
     `DEFAULT_AUDITOR_GATES`.
   - `auditor_gates={}` (test opt-out) → skip gate execution
     entirely; Auditor succeeds purely on the provider's response,
     same as slice 3.5 behaviour.
   - `auditor_gates={"name": runner, ...}` → use the supplied
     dict. Tests inject pass/fail stubs.

2. **Gate execution after the Auditor's provider response** —
   `dataclasses.replace` puts the gate results onto the
   `AgentOutput.verification_results` field. If
   `agent_output.all_gates_passed` is False, the step transitions
   to `failed` (with `notes=("verification gates failed: …",)`)
   instead of `succeeded`.

3. **New `--strict` flag** — when set, any Auditor gate failure
   aborts the run, marks every remaining step as `blocked` with
   note `"verifier strict-mode abort"`, and the exit code is
   `UNSAFE_OPERATION_BLOCKED`. Default is non-strict: a failed
   Auditor records the failure and the run continues to the
   Scribe.

### `forge run` argparse

`--strict` flag added to `forge run` parser. Both flags
(`--interactive` and `--strict`) are independent and can be
combined.

## Step lifecycle (updated)

```
contract validation fails       -> blocked
provider call begins            -> running
provider call returns           -> succeeded (non-Auditor)
provider call returns + Auditor + all gates pass    -> succeeded
provider call returns + Auditor + any gate fails    -> failed
provider call raises            -> failed
operator aborts at gate         -> all remaining blocked
operator skips at gate          -> next step blocked
--strict + Auditor gate failure -> all remaining blocked
```

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 483 | **501** (+18) |
| Slash builtins | 52 | 52 |
| Argparse handlers | 50 | 50 |
| Source files | 70 | **71** (+1) |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## Tests added (18)

Eight test classes in `tests/test_forge_verifier.py`:

- **`GateDiffReviewedTests` (5)** — empty changed-files passes; full
  mention passes; missing mention fails; empty response with
  changes fails; git crash treated as no-diff (passes).
- **`GateInvariantViolationTests` (3)** — clean check passes;
  errors fail with summary + "(+N more)" tail; checker crash fails
  with "invariant checker crashed".
- **`GateTestEvidenceRecordedTests` (3)** — missing latest.json
  fails; pass result passes; fail/non-pass result fails.
- **`RunAuditorGatesTests` (3)** — unknown gate name → "no runner
  registered" failure; runner exception contained as "runner
  crashed"; default registry has the three canonical names.
- **`AuditorAllGatesPassTests` (1)** — Auditor succeeds with three
  passing results attached.
- **`AuditorGateFailureTests` (2)** — non-strict mode fails Auditor
  but continues to Scribe; strict mode aborts run with Scribe
  blocked.
- **`AuditorGatesOptOutTests` (1)** — `auditor_gates={}` opts out;
  Auditor succeeds with empty `verification_results`.

The four slice-3.5 happy-path tests in `test_forge_run.py` were
updated to pass `auditor_gates={}` explicitly — they target the
orchestration loop, not the gate runners, so opting out keeps
slice-3.5's invariants stable while slice-3.6's invariants are
tested in their dedicated file.

## What this slice deliberately did not do

- Did not add structured-extraction of gate hints from the
  Auditor's prose response. `raw_response` parsing for richer
  hints could come later.
- Did not let the Auditor's response *override* a failing gate.
  Real gate failures stay failed regardless of what the audit
  text claims.
- Did not gate the other roles. Skald / Architect / Cartographer
  / Forge Worker / Scribe contracts have their own gate names
  declared in the registry, but slice 3.6 only wires the
  Auditor's three. The remaining gates would benefit from the
  same pattern; PH-13 / PH-14 are the natural homes.
- Did not add `forge run --gate <name>` to filter which gates
  run. The contract's `verification_gate` tuple is the source of
  truth; future overrides could extend this.
- Did not record per-gate timings or compute trend across runs.
  That's PH-13 (drift detection) territory.

## Phase 3 progress

| Slice | Status | Depends on |
|---|---|---|
| 3.1 agent contract spec | ✅ done | — |
| 3.2 handoff ledger | ✅ done | 3.1 |
| 3.3 forge command (dry-run) | ✅ done | 3.1 + 3.2 |
| 3.4 approval gates | ✅ done | 3.3 |
| 3.5 provider-backed forge | ✅ done | 3.4 |
| 3.6 verifier integration | ✅ done | 3.5 |
| 3.7 reflection capture | next | 3.5 |
| 3.8 forge resume | open | 3.2 + 3.5 |

Six of eight Phase 3 slices closed.

## Smoke verification

```bash
$ mythic-vibe forge run --provider copy-paste --task "X" --strict
# In a real Mythic project: the Auditor step now actually checks
# git diff, invariant violations, and verification evidence.
# In a bare temp project: Auditor fails the no-invariant-violation
# gate (boundary docs missing), --strict aborts, exit 4.
```

## Next slice (3.7)

**Reflection capture.** The Scribe agent's response gets routed
into a structured reflection artifact at `mythic/reflections/`
(separate from the existing per-session handoff). Each forge run
produces one reflection summarising what the cycle did, what
verifier failed (if any), and what the operator's next step
should be. The Scribe's contract gates (`docs-match-implementation`,
`handoff-recorded`) would then become real gate runners similar to
slice 3.6's Auditor gates.
