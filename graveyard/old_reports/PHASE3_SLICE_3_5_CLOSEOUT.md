---
title: "Phase 3 — Slice 3.5 Close-out (Provider-Backed Forge Run)"
phase: PH-03
slice: 3.5
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 60251bb
head_at_close: fe763e1
test_baseline_open: 468 + 14 subtests
test_baseline_close: 483 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 3 Slice 3.5 — Provider-Backed Forge Run Close-out

## Purpose

The largest slice in Phase 3. Lifts the `UNSAFE_OPERATION_BLOCKED`
gate from slice 3.3 by adding `mythic-vibe forge run`, which
actually executes the workflow against a configured provider.

This is where forge stops being a planner and starts being an
orchestrator. With slice 3.5 in place, the slice-3.1 contracts
(`AGENT_CONTRACTS`), the slice-3.2 ledger (`forge_ledger.json`),
the slice-3.3 packet renderer, and the slice-3.4 gate machinery
all combine into a single execution loop.

## Public surface

```bash
# End-to-end provider-backed run
mythic-vibe forge run --provider copy-paste --task "Refactor router"

# Interactive run with gates between steps
mythic-vibe forge run --provider openai --task "X" --interactive

# Machine-readable + ledger-suppressed run
mythic-vibe forge run --provider local --task "X" --json --skip-ledger
```

## Step lifecycle

For each role in the canonical sequence (Skald → Architect →
Cartographer → Forge Worker → Auditor → Scribe):

```
prior_outputs ← prior_outputs_for_step(plan, step, ledger)
agent_input   ← materialize_agent_input(plan, step, prior_outputs=…)

if validate_input(agent_input, contract):
    ledger.append(blocked)              # contract failure
else:
    ledger.append(running)               # entry started
    try:
        response = provider.run(packet)
        agent_output = build_agent_output_from_response(response, …)
        ledger.update_step(succeeded, agent_output, duration_ms)
    except:
        ledger.update_step(failed, notes=("provider raised: …",))

if interactive and not last_step:
    decision = gate_handler(context)
    if decision == abort:
        ledger.append(blocked) for every remaining step
        break
    if decision == skip:
        skip_next_step = True
```

## Exit code matrix

| Outcome | Code |
|---|---|
| Every step succeeded | `SUCCESS` (0) |
| At least one step failed | `OPERATIONAL_FAILURE` (1) |
| Missing `--task` or `--provider` | `USER_INPUT_ERROR` (2) |
| Unknown provider name | `USER_INPUT_ERROR` (2) |
| Operator aborted at any gate | `UNSAFE_OPERATION_BLOCKED` (4) |

## New helpers (all in `forge.py`)

### `prior_outputs_for_step(plan, step, ledger) -> tuple[str, ...]`

The slice-3.5 mechanism that unblocks slice-3.1 contracts. Walks
every step before this one, finds the latest ledger entry for each,
and returns the JSON-serialised `AgentOutput` strings of every
prior step that has a recorded output. Skipped / blocked / failed
priors contribute nothing.

With this populated, Architect / Cartographer / Forge Worker /
Auditor / Scribe all pass contract validation when their
predecessors have succeeded — exactly the transition slice-3.3 left
visible as `blocked` entries.

### `build_agent_output_from_response(response, agent_input) -> AgentOutput`

Minimal text → structured. Slice 3.5 captures the full provider
response as `raw_response` and uses the first non-empty line
(truncated to 200 chars) as `summary`. Structured fields
(artefacts, decisions, risks, handoff_notes, verification_results)
stay empty until a richer extraction pass lands later — operators
can still walk the ledger and pull richer detail from the packet's
text field if needed.

### `_resolve_provider(name, root, *, provider_factory)`

Looks up the provider via `ProviderRegistry` by default; tests pass
`provider_factory` to inject stubs without touching the registry.
Calls `validate_config()` so unconfigured providers fail with a
clear message rather than crashing mid-run.

### `_duration_ms(start_iso, end_iso) -> int | None`

Best-effort millisecond delta between two ISO-8601 timestamps for
the ledger's `duration_ms` field. Returns None on parse failure —
duration is decorative metadata, not load-bearing.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 468 | **483** (+15) |
| Slash builtin entries | 52 | 52 |
| Argparse handlers | 50 unique | 50 unique |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

The slash and argparse counts are unchanged because `forge run` is
a new subcommand of the existing `forge` parent (which was
introduced in slice 3.3). The new operator surface is the
subcommand, not a new top-level entry.

## Tests added (15)

Eight test classes in `tests/test_forge_run.py`, all using a
deterministic `StubProvider` so no live API key is needed:

- **`ForgeRunHappyPathTests` (2)** — every step runs through the
  provider and succeeds; ledger records `running` then
  `succeeded` with `agent_output`, `completed_at`, `duration_ms`.
- **`PriorOutputsTests` (2)** — Skald sees 0 priors; each
  subsequent agent sees N priors equal to its index in the
  sequence; no roles end up `blocked` when the provider succeeds.
- **`PriorOutputsForStepHelperTests` (2)** — helper returns
  serialised outputs for completed priors; silently skips priors
  without an `agent_output` (blocked / failed cases).
- **`ProviderErrorTests` (1)** — provider exception marks the
  step `failed` with `"provider raised: …"` in notes; subsequent
  steps blocked because their `prior_outputs` never arrived.
- **`MissingProviderTests` (3)** — unknown provider, missing
  `--provider`, missing `--task` all return `USER_INPUT_ERROR`
  with helpful messages.
- **`InteractiveAbortTests` (1)** — abort mid-run via stub gate
  handler returns `UNSAFE_OPERATION_BLOCKED`; every remaining step
  is `blocked`; provider was called only for the steps before the
  abort.
- **`BuildAgentOutputTests` (3)** — first non-empty line is the
  summary; summary truncated to 200 chars; empty response yields
  empty summary.
- **`SkipLedgerFlagTests` (1)** — `--skip-ledger` writes no
  `forge_ledger.json` file.

## What this slice deliberately did not do

- Did not add structured-output extraction. `agent_output.artefacts`,
  `decisions`, `risks`, `handoff_notes` stay empty in slice 3.5.
  A future slice or operator-side script can ingest the
  `raw_response` text into richer fields if needed.
- Did not wire the Auditor agent's verification gates. Slice 3.6
  owns that — it's where `verification_results` actually get
  populated and the run aborts on real architectural violations.
- Did not implement `forge resume`. Slice 3.8 owns that.
- Did not add streaming response handling. PH-06 slice 6.4 covers
  Ollama-streamed output.
- Did not add cost guardrails or per-day spending caps. PH-08
  slice 8.2 owns those.
- Did not extend `mythic-vibe ai providers` to show forge-specific
  status. The existing provider list is unchanged.
- Did not add per-role provider routing (e.g. "Skald uses
  copy-paste, Architect uses openai"). The slice ships single-
  provider runs; PH-08 slice 8.1 introduces the routing table.

## Phase 3 progress

| Slice | Status | Depends on |
|---|---|---|
| 3.1 agent contract spec | ✅ done | — |
| 3.2 handoff ledger | ✅ done | 3.1 |
| 3.3 forge command (dry-run) | ✅ done | 3.1 + 3.2 |
| 3.4 approval gates | ✅ done | 3.3 |
| 3.5 provider-backed forge | ✅ done | 3.4 |
| 3.6 verifier integration | next | 3.5 |
| 3.7 reflection capture | open | 3.5 |
| 3.8 forge resume | open | 3.2 + 3.5 |

Five of eight Phase 3 slices closed. The remaining three (3.6 / 3.7
/ 3.8) all build directly on slice 3.5's run loop.

## Smoke verification

```python
$ mythic-vibe forge --help
usage: mythic-vibe forge [-h] {plan,run,ledger} ...

positional arguments:
  {plan,run,ledger}
    plan             Build a workflow plan and per-agent packets (no provider call)
    run              Run the forge end-to-end through a configured provider (PH-03 slice 3.5)
    ledger           Inspect mythic/forge_ledger.json (per-agent step records)
```

## Next slice (3.6)

**Verifier integration.** Wire the Auditor agent's output through
the existing `verify/` module so contract gates like
`diff-reviewed-against-architecture` and `no-invariant-violation`
become real machine-checks rather than just declarations. A failing
verification gate in slice 3.6 transitions the Auditor entry from
`succeeded` to `failed` and (in interactive mode) the operator sees
the failure at the next gate.
