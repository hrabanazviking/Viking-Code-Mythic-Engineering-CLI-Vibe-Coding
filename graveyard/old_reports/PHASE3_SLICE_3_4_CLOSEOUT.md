---
title: "Phase 3 — Slice 3.4 Close-out (Forge Approval Gates)"
phase: PH-03
slice: 3.4
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: e3adc5b
head_at_close: 9231073
test_baseline_open: 451 + 14 subtests
test_baseline_close: 468 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 3 Slice 3.4 — Forge Approval Gates Close-out

## Purpose

Operator gates between forge steps. Without `--interactive`,
behaviour is unchanged from slice 3.3 (the orchestrator proceeds
straight through). With `--interactive`, after each step except
the final one, a gate handler decides whether to advance, abort
the run, or skip the next step.

This slice is the bridge between slice 3.3 (rendering packets in
dry-run) and slice 3.5 (provider-backed forge). Slice 3.5 will
gate **between provider invocations** rather than between packet
renders, but the gate machinery is identical.

## Public surface

```bash
# Non-interactive (default — unchanged from slice 3.3)
mythic-vibe forge plan --dry-run --task "X"

# Interactive — gate after each step
mythic-vibe forge plan --dry-run --task "X" --interactive
```

```python
# Programmatic injection (used by tests and slice 3.5)
from mythic_vibe_cli.forge import cmd_forge_plan, ForgeGateContext

def my_handler(context: ForgeGateContext) -> str:
    return "advance"  # or "abort" / "skip"

cmd_forge_plan(args, gate_handler=my_handler)
```

## Public API additions in `forge.py`

```python
GateDecision = Literal["advance", "abort", "skip"]

@dataclass(frozen=True)
class ForgeGateContext:
    workflow_id: str
    completed_step_index: int          # 0-based
    completed_step_id: str
    completed_role: str
    completed_status: str               # "pending" | "blocked" | etc.
    completed_validation_errors: tuple[str, ...]
    next_step_id: str | None
    next_role: str | None
    total_steps: int
    def to_dict(self) -> dict[str, Any]: ...

GateHandler = Callable[[ForgeGateContext], GateDecision]

def default_gate_handler(context: ForgeGateContext) -> GateDecision: ...
```

## Decision behaviour

| Decision | What the orchestrator does |
|---|---|
| `advance` | Proceed to the next step |
| `abort` | Stop the run; mark every remaining step as `blocked` with note `"operator aborted at gate"`; JSON payload reports `aborted=true` |
| `skip` | Mark ONLY the next step as `blocked` with note `"operator skipped at preceding gate"`; the step after that resumes normal processing |

A skipped step does NOT fire its own gate at the end of its
iteration — operators only see gates after steps that actually
ran. This means the gate handler can never see
`completed_role == "Architect"` if Architect was skipped at the
preceding gate.

## Default gate handler (stdin)

Used when `cmd_forge_plan` is called without an injected handler.
Prompts `[y/n/?/s]` after each step.

| Input | Result |
|---|---|
| `y` / `yes` / `<empty>` | advance (empty defaults to advance — safe for Ctrl+D-style flows) |
| `n` / `no` / `abort` | abort |
| `s` / `skip` | skip |
| `?` | print `_describe_gate_context()` detail and re-prompt |
| anything else | print "Unknown response" and re-prompt |
| `EOFError` (piped input ran out) | advance (safe default) |

Case-insensitive throughout.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 451 | **468** (+17) |
| Slash builtin entries | 52 | 52 |
| Argparse handlers | 50 unique | 50 unique |
| Source files | 70 | 70 |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## Tests added (17)

Five test classes in `tests/test_forge_gates.py`:

- `GateHandlerInvocationTests` (3) — handler called once per pair
  when advancing through; never called when `--interactive` off;
  no gate after final step (Scribe).
- `AbortDecisionTests` (1) — aborting halfway through marks every
  remaining step `blocked` with the abort note (4 trailing
  entries in this case) and the JSON payload reports
  `aborted=true`.
- `SkipDecisionTests` (2) — skip marks ONLY the next step
  `blocked` with the skipped note; subsequent steps re-evaluate
  their own contracts; gates continue to fire for steps that
  actually ran.
- `GateContextRoundTripTests` (1) — `to_dict()` preserves every
  field.
- `DefaultGateHandlerStdinTests` (10) — every prompt parsing path
  via mocked `input()`: y/yes/empty/n/no/s, ?-then-y reprompt,
  unknown-then-y reprompt, `EOFError` → advance, case-insensitive
  parsing.

## What this slice deliberately did not do

- Did not implement provider-backed `forge run`. Slice 3.5 is
  next; the gate machinery built here is the foundation it
  reuses.
- Did not add a TUI version of the gate prompt. The master
  roadmap mentions a "TUI version exposes a modal" — that's a
  PH-04 (TUI v2) concern, not slice 3.4.
- Did not record gate decisions in the ledger as separate
  entries. The decision shows up as the resulting status (`blocked`
  with note) on the affected entry, which is enough provenance
  for slice 3.8 (forge resume) to know how the run ended.
- Did not let `?` show packet contents. The `_describe_gate_context`
  output is intentionally compact (workflow / step / status /
  next role / validation errors). Operators can read the full
  packet from the rendered output earlier in the run.
- Did not let the operator edit a packet at the gate. That's a
  much bigger feature; for now the operator's only choices are
  advance / abort / skip / re-show.

## Phase 3 progress

| Slice | Status | Depends on |
|---|---|---|
| 3.1 agent contract spec | ✅ done | — |
| 3.2 handoff ledger | ✅ done | 3.1 |
| 3.3 forge command (dry-run) | ✅ done | 3.1 + 3.2 |
| 3.4 approval gates | ✅ done | 3.3 |
| 3.5 provider-backed forge | next | 3.4 |
| 3.6 verifier integration | open | 3.5 |
| 3.7 reflection capture | open | 3.5 |
| 3.8 forge resume | open | 3.2 + 3.5 |

## Next slice (3.5)

**Provider-backed forge.** Lifts the
`UNSAFE_OPERATION_BLOCKED` gate that today wraps non-dry-run
runs. When a provider is configured, the orchestrator routes each
agent's packet through the configured provider, captures the
response into an `AgentOutput`, updates the ledger entry from
`pending` → `running` → `succeeded` / `failed`, and reuses this
slice's gate machinery between agents.
