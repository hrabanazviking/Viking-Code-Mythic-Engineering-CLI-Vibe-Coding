---
title: "Phase 3 — Slice 3.1 Close-out (Agent Contract Spec)"
phase: PH-03
slice: 3.1
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 50887a6
head_at_close: 2920aa4
test_baseline_open: 364 + 14 subtests
test_baseline_close: 402 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 3 Slice 3.1 — Agent Contract Spec Close-out

## Purpose

First slice of Phase 3 (Multi-Agent Forge). Pure declarative
foundation — no provider calls, no filesystem side-effects, no
`mythic-vibe forge` command. Defines the typed input/output contract
every Mythic agent role must satisfy when running a six-role cycle.

This slice is the structural underpinning for everything PH-03
adds: 3.2 (handoff ledger), 3.3 (forge dry-run), 3.4 (approval
gates), 3.5 (provider-backed forge), 3.6 (verifier integration),
3.7 (reflection capture), 3.8 (forge resume).

## Naming note

Master roadmap section 5 prescribed `workflow/agents.py` but
`workflow.py` already exists as a top-level module. Python doesn't
allow `workflow.py` and `workflow/` to coexist as siblings, so
restructuring would mean converting `workflow.py` into
`workflow/__init__.py` and updating every importer — non-additive.

Chose `workflow_agents.py` as a sibling module instead. Recording
this naming variance here so future PH-03 work doesn't re-litigate
it.

## What landed

### `mythic_vibe_cli/workflow_agents.py` (~360 lines)

Four frozen dataclasses, one constant, one registry, six helpers.

#### `VerificationResult`

```python
VerificationResult(name: str, passed: bool, detail: str = "")
```

One named gate's outcome. Round-trip serialisable via
`to_dict()` / `from_dict()`.

#### `AgentInput`

```python
AgentInput(
    role: str,
    task: str,
    phase: str,
    workflow_id: str | None = None,
    workflow_step_id: str | None = None,
    prior_outputs: tuple[str, ...] = (),
    context_files: tuple[str, ...] = (),
    forbidden_files: tuple[str, ...] = (),
    invariants: tuple[str, ...] = (),
    notes: tuple[str, ...] = (),
)
```

What flows INTO an agent invocation. Tuples (not lists) so the
dataclass stays frozen and hashable. `from_dict` filters non-string
collection entries silently — defensive against malformed JSON
ledgers.

#### `AgentOutput`

```python
AgentOutput(
    role: str,
    timestamp: str,
    workflow_id: str | None = None,
    workflow_step_id: str | None = None,
    summary: str = "",
    artefacts: tuple[str, ...] = (),
    decisions: tuple[str, ...] = (),
    risks: tuple[str, ...] = (),
    handoff_notes: tuple[str, ...] = (),
    verification_results: tuple[VerificationResult, ...] = (),
    raw_response: str | None = None,
)
```

What flows OUT of an agent invocation. The `all_gates_passed`
property aggregates verification results — empty results means
"passing" (the orchestrator decides whether gates are required).

#### `AgentContract`

```python
AgentContract(
    role: str,
    input_required_fields: tuple[str, ...],
    output_required_fields: tuple[str, ...],
    output_artefact_kinds: tuple[str, ...],
    verification_gate: tuple[str, ...],
    handoff_to_role: str | None,
)
```

The static description: required fields, expected artefact kinds,
named gates, default next role.

### `DEFAULT_AGENT_SEQUENCE`

```python
("Skald", "Architect", "Cartographer", "Forge Worker", "Auditor", "Scribe")
```

Equal to `workflow_engine.DEFAULT_ROLE_SEQUENCE` (locked by test).
Handoffs in `AGENT_CONTRACTS` are derived from this tuple so the
two tables cannot drift apart.

### `AGENT_CONTRACTS` registry

| Role | Required input fields | Required output fields | Verification gates |
|---|---|---|---|
| Skald | task, phase | summary, decisions | names-map-to-identifiable-concepts; vision-stays-implementation-aligned |
| Architect | task, phase, prior_outputs | summary, decisions, artefacts | boundaries-declared; dependency-direction-consistent; every-new-component-has-an-owner |
| Cartographer | task, phase, prior_outputs | summary, artefacts, handoff_notes | every-affected-path-mapped; blast-radius-explicit |
| Forge Worker | task, phase, prior_outputs | summary, artefacts | tests-pass; lint-clean; edit-surface-bounded |
| Auditor | task, phase, prior_outputs | summary, verification_results | diff-reviewed-against-architecture; no-invariant-violation; test-evidence-recorded |
| Scribe | task, phase, prior_outputs | summary, artefacts, handoff_notes | docs-match-implementation; handoff-recorded |

### Helpers

| Function | Returns |
|---|---|
| `contract_for(role)` | `AgentContract` (raises `ValueError` if unknown) |
| `validate_input(input, contract)` | `list[str]` of violation messages (empty = OK) |
| `validate_output(output, contract)` | same shape as `validate_input` |
| `expected_handoff_chain()` | `tuple[(role, next_role), ...]` for sequence-consistency tests |
| `role_prose(role)` | dict drawn from `ai/prompts/roles.ROLE_PROMPTS` — the only sanctioned bridge between contract layer and prose layer |

## Layered design — why two modules instead of one

`ai/prompts/roles.py` (already existed) defines the **prose** half of
each role: identity, focus, system_prompt, prose-form invariants.
That module stayed untouched in this slice.

`workflow_agents.py` (new) defines the **typed contract** half:
required fields, machine-checkable gates, artefact kinds, handoff
direction. Pure data, no prose.

Keeping them separate means the contract validation can run without
loading the prose prompts (cheaper for tests and headless tools), and
a future provider-backed forge can swap prose styles without touching
the contract layer.

`role_prose(role)` is the only sanctioned import-bridge. Tests lock
that no role appears in one layer without the other.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 364 | **402** (+38) |
| Slash builtins | 51 | 51 |
| Argparse handlers | 49 unique | 49 unique |
| Coverage | 76% | 76% |
| Source files | 67 | **68** (+1: workflow_agents.py) |
| Ruff / mypy | clean | clean |

## Tests added (38)

Eleven test classes in `tests/test_workflow_agents.py`:

- `CanonicalSequenceTests` (4) — six roles in correct order;
  matches `workflow_engine.DEFAULT_ROLE_SEQUENCE`; full coverage in
  `AGENT_CONTRACTS`; no orphan contracts.
- `HandoffChainTests` (2) — `expected_handoff_chain()` matches
  sequence; per-contract `handoff_to_role` matches canonical chain.
- `ContractForTests` (2) — registered role resolves; unknown role
  raises with helpful message.
- `AgentInputRoundTripTests` (3) — `to_dict` / `from_dict` round-trip;
  missing optional fields default correctly; non-string entries
  filtered.
- `AgentOutputRoundTripTests` (4) — round-trip with full payload;
  `all_gates_passed` for mixed / all-pass / no-gates cases.
- `VerificationResultRoundTripTests` (2) — round-trip; `from_dict`
  defaults `passed=False`.
- `AgentContractSerializationTests` (3) — `to_dict` shape;
  every contract has gates; every contract has artefact kinds.
- `ValidateInputTests` (6) — well-formed; role mismatch; missing
  string; blank string; missing collection; well-formed with
  collection.
- `ValidateOutputTests` (4) — well-formed Scribe; role mismatch;
  Architect missing artefacts; Auditor missing verification_results.
- `RoleProseSeparationTests` (3) — bridge returns expected fields;
  unknown role raises; every canonical role has prose.
- `AgentInputHashabilityTests` (4) — every dataclass is hashable
  (sit in dicts/sets without surprise).
- `AgentInputContractKnownPhasesTests` (1) — sequence parity with
  `workflow_engine.ROLE_PHASES`.

## What this slice deliberately did not do

- Did not implement `mythic-vibe forge`. That command lives at slice
  3.5 (provider-backed) with the dry-run shape from 3.3.
- Did not write a handoff ledger. The forge ledger is slice 3.2.
- Did not modify `ai/prompts/roles.py`. The prose layer is
  intentionally untouched — slice 3.1 only adds the typed-contract
  layer next to it.
- Did not extend `WorkflowStep` / `WorkflowPlan`. The existing
  workflow_engine continues to handle the prose-flavoured plan
  (used by `mythic-vibe workflow plan`); the new contract layer is
  consulted at orchestration time, not plan-build time.
- Did not introduce provider adapters. The contract is
  provider-agnostic by design.
- Did not add validation for the prose layer's content — that's
  out of scope.

## Phase 3 progress

| Slice | Status |
|---|---|
| 3.1 agent contract spec | ✅ done |
| 3.2 handoff ledger | next candidate |
| 3.3 forge command (dry-run) | depends on 3.1 + 3.2 |
| 3.4 approval gates | depends on 3.3 |
| 3.5 provider-backed forge | depends on 3.4 |
| 3.6 verifier integration | depends on 3.5 |
| 3.7 reflection capture | depends on 3.5 |
| 3.8 forge resume | depends on 3.2 + 3.5 |

## Next slice options

1. **PH-03 slice 3.2 — handoff ledger.** Extend
   `mythic/workflow_history.json` (or add `mythic/forge_ledger.json`)
   to record per-agent handoff steps with `AgentInput` /
   `AgentOutput` payloads. Pure persistence layer; no orchestrator
   yet.
2. **PH-03 slice 3.3 — forge command (dry-run).** First user-facing
   slice: `mythic-vibe forge --dry-run --task "X"` builds the plan
   and renders the per-agent packets without invoking any provider.
3. **Begin a different phase.** Phase 5 (knowledge graph) and
   Phase 11 (security/sandbox) remain dependency-free.

The natural progression is **slice 3.2** — the ledger underpins
everything 3.3 onwards needs to persist.
