---
title: "Phase 8 — Finale (Provider Routing & Hardware-Aware Selection)"
phase: PH-08
slices: 8.1, 8.2, 8.3, 8.4
opened: 2026-04-29
closed: 2026-04-29
phase_open_head: f7964d4
phase_close_head: ec715fd
phase_open_tests: 947 + 14 subtests
phase_close_tests: 1005 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
---

# Phase 8 — Provider Routing & Hardware-Aware Selection (Finale)

## What Phase 8 was for

Add a router that picks the right provider/model per task type
and available hardware, with explicit user-overridable defaults.

The phase composes three earlier capabilities into a coherent
routing layer:

- **PH-06 slice 6.6 hardware profile** — the per-machine snapshot
  routing predicates evaluate against.
- **PH-06 slice 6.5 telemetry** — the per-call ledger the
  cost guard reads.
- **PH-06 + PH-15 providers** — the destinations the router
  resolves to (anthropic / openai / gemini / openrouter / ollama
  / local / copy-paste).

## Slice-by-slice ledger

### Slice 8.1 — Routing table
- `mythic_vibe_cli/ai/router.py` — `RoutingRule` /
  `RoutingTable` / `RouteDecision` / `route()`.
- 8-rule default table covering the six Mythic roles + a
  copy-paste catch-all.
- `mythic/ai/routing.json` overlay loader; corrupt/missing files
  silently fall back to defaults.
- 19 tests. Commit `2bcb93d`.

### Slice 8.2 — Cost guards
- `mythic_vibe_cli/ai/cost_guard.py` — `compute_today_spend_usd`
  + `BudgetCheck` + `check_budget`.
- `MYTHIC_DAILY_COST_CAP_USD` env var (default disabled).
- `cmd_ai_run` consults the guard before live calls; blocked
  calls return `OPERATIONAL_FAILURE` with a clear "daily cap
  exceeded ... use --dry-run to bypass" reason.
- 16 tests. Commit `d180f68`.

### Slice 8.3 — Fallback chain
- `mythic_vibe_cli/ai/routing_runtime.py` — `run_with_fallback`
  with provider-resolver indirection (decoupled from the
  registry for test ergonomics).
- Skip rules: unknown name → unconfigured (except copy-paste) →
  validate_config raised → run raised.
- copy-paste auto-appended as terminal fallback (always succeeds).
- Per-attempt `routing_attempt` entries written to
  `provider_calls.jsonl` for slice 6.5 telemetry visibility.
- 13 tests. Commit `dd9ba19`.

### Slice 8.4 — `ai route` CLI
- New `mythic-vibe ai route [--role R] [--task T] [--explain]
  [--no-hardware]` — pure routing explainer; never invokes a
  provider.
- JSON or text output; `--explain` dumps every rule the router
  considered.
- `--no-hardware` treats hardware predicates as pass (useful for
  remote-box debugging).
- 10 tests. Commit `ec715fd`.

## Cumulative numbers

| Metric | Phase open | Phase close | Δ |
|---|---|---|---|
| Tests | 947 | **1005** | +58 (first time crossing 1000) |
| Source files | 89 | **92** | +3 |
| Slash builtins | 58 | 58 | 0 (`ai route` is a sub-action) |
| Argparse handlers | 56 | 56 | 0 |
| New modules | 0 | **3** | `ai/router.py`, `ai/cost_guard.py`, `ai/routing_runtime.py` |
| Sub-actions on `ai` | 6 | **7** | +1 (`route`) |

Ruff + mypy clean throughout.

## Master-roadmap target table

| Gate | Status |
|---|---|
| Router picks provider/model per task type + hardware | ✅ slices 8.1 + 8.4 |
| User-overridable defaults | ✅ `mythic/ai/routing.json` overlay (slice 8.1) |
| Cost guards block runaway spend | ✅ slice 8.2 (env-var-controlled, opt-in by default) |
| Fallback chain (preferred → secondary → copy-paste) | ✅ slice 8.3 |
| Logging of every fallback | ✅ `routing_attempt` entries in `provider_calls.jsonl` |
| `ai route --explain` / `--dry-run` | ✅ slice 8.4 (`ai route` is always pure-routing — no `--dry-run` flag needed) |

## Composition with earlier phases

PH-08 is the consumer side of several earlier capabilities:

- **PH-06 slice 6.5** (telemetry) — the `routing_attempt` entries
  show up in `mythic-vibe ai telemetry --provider X` alongside
  real calls. Operators can grep the ledger for fallback
  patterns.
- **PH-06 slice 6.6** (hardware profile) — slice 8.1 reads
  `HardwareProfile.ram_total_mb` / `logical_cpus` to gate the
  big-RAM Forge Worker → Anthropic Sonnet rule.
- **PH-15 sub-slice** (provider-call recording) — the fallback
  runtime is provider-agnostic; whatever provider lands the
  successful call still records turns into the conversation log
  via the existing `cmd_ai_run` recording path.

## What Phase 8 deliberately did not do

- **Did not auto-invoke `run_with_fallback` from `cmd_ai_run`.**
  Wiring the fallback chain into the live `ai run` flow is a
  follow-up — slice 8.3 ships the runtime; the integration sub-
  slice will swap `provider.run` for `run_with_fallback` and
  thread the slice-8.1 `RouteDecision`. Kept separate so the
  fallback runtime can be tested + iterated without touching the
  main user surface.
- **Did not implement per-call cost rate-limiting.** The slice
  8.2 cap is a daily envelope. A per-call hard ceiling (e.g.
  block any single call over $1) is a finer-grained gate that
  belongs in a future slice.
- **Did not surface routing decisions in the TUI.** The `ai route`
  CLI is the surface today; a TUI panel showing "this call would
  go to X" before launching is a future polish slice.
- **Did not validate `routing.json` against a schema.** Corrupt
  overlays silently fall back to defaults. PH-14 (Policy Engine)
  is the natural home for schema validation across all Mythic
  config files.

## Phase progression after PH-08

Master roadmap status snapshot:

| Phase | Status |
|---|---|
| PH-01 Audit & runtime hygiene | ✅ closed |
| PH-02 Slash command surface expansion | ✅ closed |
| PH-03 Multi-agent forge engine | ✅ closed |
| PH-04 TUI layout & interaction | ✅ closed |
| PH-05 Knowledge graph & persistent memory | ✅ closed |
| PH-06 Local LLM sovereignty | ✅ closed (5/6; 6.4 streaming deferred) |
| PH-08 Provider routing & hardware-aware selection | ✅ closed (this finale) |
| PH-13 Drift detection & self-healing | ✅ closed |
| PH-15 Conversation memory & compaction | ✅ closed |
| Other phases | open |

**Nine master-roadmap phases now closed.**

Natural next phases:

- **Routing wire-up sub-slice** — small follow-up that swaps
  `provider.run` for `run_with_fallback` in `cmd_ai_run`, gated
  by an opt-in flag at first.
- **PH-07** Voice & Multimodal — also leverages the provider
  layer.
- **PH-11** Security/Sandbox/Permissions — hardens forge + plugin
  execution.
- **PH-12** CI/CD & Deployment Integration.
- **PH-16** MCP / ACP / OpenTelemetry Protocols.
- **PH-18** Robustness Sweeps — would unblock the deferred 6.4
  streaming.

## How to verify

```bash
# Default routing for Forge Worker on a beefy host:
$ mythic-vibe ai route
Route: role='Forge Worker' task_type='*'  ->
  provider='anthropic' model='claude-sonnet-4'
  fallbacks: openai -> copy-paste

# Explain trace:
$ mythic-vibe ai route --role Skald --explain --json | jq

# Custom overlay:
$ cat mythic/ai/routing.json
[
  { "role": "Forge Worker", "task_type": "*",
    "provider": "openrouter", "model": "openai/gpt-4o",
    "fallbacks": ["copy-paste"] }
]
$ mythic-vibe ai route   # now lands on openrouter

# Cost cap trial:
$ MYTHIC_DAILY_COST_CAP_USD=1.00 mythic-vibe ai run \
    --provider anthropic --packet pkt.txt
# Blocks if today's spend + projected estimate > $1.

# Telemetry of fallback attempts:
$ mythic-vibe ai telemetry --limit 20
```

## How to resume

`MEMORY.md` and `project_mythic_engineering_cli_status.md` updated
to HEAD `<close-head>`. `TASK_master_roadmap_and_phase1.md` tracker
extended through this finale.
