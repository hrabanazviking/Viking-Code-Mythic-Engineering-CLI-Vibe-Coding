---
title: "Phase 3 — Slice 3.3 Close-out (Forge Command — Dry-Run)"
phase: PH-03
slice: 3.3
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 888e710
head_at_close: cbc2b24
test_baseline_open: 430 + 14 subtests
test_baseline_close: 451 + 14 subtests
slash_builtins_open: 51
slash_builtins_close: 52
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 3 Slice 3.3 — Forge Command (Dry-Run) Close-out

## Purpose

First user-facing Phase 3 slice. Builds on slice 3.1 (agent
contract spec) and slice 3.2 (forge ledger) to deliver
`mythic-vibe forge` — a multi-agent orchestrator that today runs
in dry-run only (slice 3.5 makes it provider-backed).

Two operator surfaces:

- `forge plan` — generate the six-role plan, write pending ledger
  entries, render copy-paste-ready packets.
- `forge ledger list / latest / show` — inspect the
  `mythic/forge_ledger.json` file written by slice 3.2.

## Public surface

```bash
# Plan generation (dry-run only today)
mythic-vibe forge plan --dry-run --task "Refactor router"
mythic-vibe forge plan --dry-run --task "X" --skip-ledger
mythic-vibe forge plan --dry-run --task "X" --json

# Ledger inspection
mythic-vibe forge ledger list
mythic-vibe forge ledger latest --limit 3
mythic-vibe forge ledger show --workflow WF-20260429200335-29f6b66a
mythic-vibe forge ledger show --workflow WF-... --step step-02 --json
```

A non-dry-run invocation today returns `UNSAFE_OPERATION_BLOCKED`
with a clear message:

```
Provider-backed forge is not enabled yet. Re-run with `--dry-run`
to preview the role sequence and packets.
```

## What `forge plan --dry-run` does

1. Builds a `WorkflowPlan` via the existing `WorkflowEngine`.
2. For each step, materialises an `AgentInput` via slice-3.1
   contracts:
   - role / task / phase / workflow_id / workflow_step_id
   - invariants from the role prompt + `GATE: <name>` entries
     for every contract gate
   - `prior_outputs` left empty (slice 3.5 will populate from
     the ledger)
3. Validates each input against `AGENT_CONTRACTS`:

   | Role | Required input | Dry-run status |
   |---|---|---|
   | Skald | task, phase | **pending** (passes) |
   | Architect | task, phase, prior_outputs | **blocked** (missing prior_outputs) |
   | Cartographer | task, phase, prior_outputs | **blocked** |
   | Forge Worker | task, phase, prior_outputs | **blocked** |
   | Auditor | task, phase, prior_outputs | **blocked** |
   | Scribe | task, phase, prior_outputs | **blocked** |

   This is **correct-by-design**. Slice 3.5 will fix the blocked
   states by populating `prior_outputs` from the ledger as
   previous agents complete; pinned by test
   `test_dry_run_writes_ledger_entries_by_default` so the
   transition is observable.
4. Appends one `ForgeLedgerEntry` per step (unless
   `--skip-ledger`). Validation errors land in `notes`.
5. Renders one Mythic Forge Packet per step in seven sections:

   ```markdown
   # Mythic Forge Packet
   - Workflow / Step / Task / Hand off to ...

   ## 1. Role
   - Identity / Focus
   ## 2. System prompt
   ## 3. Step objective
   ## 4. Invariants
   ## 5. Verification (gates that must pass to advance)
   ## 6. Expected output artefacts
   ## 7. AgentInput payload (JSON)
   ```

   The packet is copy-paste-ready for ChatGPT / Claude / Gemini /
   any other LLM. Slice 3.5 will route the same packet directly
   through a configured provider.

## What `forge ledger` does

| Subcommand | Behaviour |
|---|---|
| `list` | Every recorded entry, oldest first |
| `latest --limit N` | Newest N entries (default 5) |
| `show --workflow <id>` | Every entry for one workflow id |
| `show --workflow <id> --step <id>` | Filter to a specific step |

JSON shape on `show` includes the full `ForgeLedgerEntry.to_dict()`
payload (with embedded `AgentInput` / `AgentOutput` if recorded);
JSON shape on `list` / `latest` is a per-entry summary
(workflow_id, step_id, role, status, started_at, completed_at,
duration_ms, notes).

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 430 | **451** (+21) |
| Slash builtin entries | 51 | **52** |
| Argparse handlers | 49 unique | **50 unique** |
| Source files | 69 | **70** (+1 forge.py) |
| Coverage | 76% | 76% |
| Ruff / mypy | clean | clean |

## Tests added (21)

Eight test classes in `tests/test_forge_command.py`:

- `ForgePlanDryRunTests` (5) — six-role payload, ledger writes
  by default, `--skip-ledger` suppresses, text rendering, JSON
  packet shape including `GATE:` invariants.
- `ForgePlanGuardsTests` (3) — argparse blocks missing `--task`;
  blank `--task` after strip returns USER_INPUT_ERROR; non-dry-run
  returns UNSAFE_OPERATION_BLOCKED.
- `MaterializeAgentInputTests` (2) — input carries workflow
  identity + GATE invariants; Skald passes contract validation,
  others fail on `prior_outputs` (designed slice-3.5 hand-off).
- `RenderForgePacketTests` (2) — packet contains all 7 canonical
  sections; Architect packet lists ARCHITECTURE.md /
  DOMAIN_MAP.md from contract artefact kinds.
- `ForgeLedgerListTests` (3) — text + JSON output; empty project
  reports empty.
- `ForgeLedgerLatestTests` (1) — `--limit` window respected in
  JSON.
- `ForgeLedgerShowTests` (3) — entries for workflow; step filter
  narrows to one; unknown workflow returns USER_INPUT_ERROR.
- `ForgeDispatcherFallthroughTests` (2) — both dispatchers
  surface visible error messages on unknown subcommands (per the
  slice 1.3 F-006/F-007 fix pattern).

## What this slice deliberately did not do

- Did not invoke any AI provider. `forge plan` is dry-run only;
  slice 3.5 lifts the gate.
- Did not add `forge run` subcommand. That's slice 3.5.
- Did not add `forge resume`. That's slice 3.8.
- Did not implement approval gates between steps. Slice 3.4
  adds those.
- Did not let the Auditor agent block Architect-level invariant
  violations. Slice 3.6 wires the verifier integration.
- Did not populate `prior_outputs` from the ledger. The
  Architect/Cartographer/Forge Worker/Auditor/Scribe roles all
  land as `blocked` in dry-run because their contracts demand
  prior_outputs; slice 3.5 will populate them as previous agents
  complete.
- Did not surface forge state in `mythic-vibe status` output.
  That's a wider observability concern for PH-04 / PH-13.

## Phase 3 progress

| Slice | Status | Depends on |
|---|---|---|
| 3.1 agent contract spec | ✅ done | — |
| 3.2 handoff ledger | ✅ done | 3.1 |
| 3.3 forge command (dry-run) | ✅ done | 3.1 + 3.2 |
| 3.4 approval gates | next | 3.3 |
| 3.5 provider-backed forge | open | 3.4 |
| 3.6 verifier integration | open | 3.5 |
| 3.7 reflection capture | open | 3.5 |
| 3.8 forge resume | open | 3.2 + 3.5 |

## Smoke verification

```bash
$ mythic-vibe forge plan --dry-run --task "Smoke test" --json
forge plan -> workflow_id= WF-20260429200335-29f6b66a / steps= 6 / first role= Skald
```

```bash
$ mythic-vibe forge ledger list
Forge ledger (6 entries)
- Path: ./mythic/forge_ledger.json
  - WF-20260429200335-29f6b66a :: step-01 :: Skald :: pending
  - WF-20260429200335-29f6b66a :: step-02 :: Architect :: blocked
  - WF-20260429200335-29f6b66a :: step-03 :: Cartographer :: blocked
  - ...
```

## Next slice (3.4)

**Approval gates.** Between each step, the operator gets a
short summary and is prompted `y/n/?` to advance. The TUI version
exposes a modal; the CLI version does inline prompts. Once the
gate logic exists, slice 3.5 wires real provider calls behind it.
