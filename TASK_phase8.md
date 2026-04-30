---
title: "Phase 8 — Provider Routing & Hardware-Aware Selection"
phase: PH-08
slices: 8.1, 8.2, 8.3, 8.4
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: f7964d4
status: in_progress
---

# Phase 8 — Provider Routing & Hardware-Aware Selection

## Goal (master roadmap)

Add a router that picks the right provider/model per task type
and available hardware, with explicit user-overridable defaults.

## Architecture

The phase composes three earlier capabilities:

- **PH-06 slice 6.6 hardware profile** — the per-machine snapshot
  used by routing predicates.
- **PH-06 slice 6.5 telemetry** — the per-call ledger that backs
  cost-guard math.
- **PH-06 slice 6.1 ollama** + the existing API providers — the
  destinations the router resolves to.

```
mythic_vibe_cli/ai/
  router.py       (slice 8.1 — declarative routing rules)
  cost_guard.py   (slice 8.2 — daily spend cap)
  routing_runtime.py  (slice 8.3 — fallback orchestration)
```

## Slices

### 8.1 — Routing table
- `mythic_vibe_cli/ai/router.py`:
  - `RoutingRule` frozen dataclass: `role` (Mythic role or `"*"`),
    `task_type` (free string or `"*"`), `min_ram_mb`,
    `min_logical_cpus`, `prefer_local`, `provider`, `model`,
    `fallbacks` (tuple of provider names).
  - `RoutingTable.from_default()` — built-in rules covering the
    six Mythic roles + a generic catch-all.
  - `RoutingTable.load(root)` — overlays
    `mythic/ai/routing.json` on top of defaults if present.
  - `RouteDecision` frozen dataclass: `provider`, `model`,
    `rule_matched`, `fallbacks` (tuple), `reasons` (debuggable
    explanations).
  - `route(table, role, task_type, hardware) -> RouteDecision`.

### 8.2 — Cost guards
- `mythic_vibe_cli/ai/cost_guard.py`:
  - `compute_today_spend_usd(root) -> float` — reads
    `provider_calls.jsonl`, filters by today's UTC date, sums
    `observed_cost_usd` from each entry's response metadata.
  - `BudgetCheck` frozen dataclass: `allowed`, `today_spent_usd`,
    `cap_usd`, `projected_cost_usd`, `reason`.
  - `check_budget(root, projected_cost_usd, *, cap_usd_override)
    -> BudgetCheck` — honours `MYTHIC_DAILY_COST_CAP_USD` env var.
  - Default cap: 0.0 (cap disabled). Operators must explicitly
    opt in.
- `cmd_ai_run` consults the guard before non-dry-run, non-zero-cost
  calls; surfaces a clean error and returns `OPERATIONAL_FAILURE`
  when the cap would be exceeded.

### 8.3 — Fallback chain
- `mythic_vibe_cli/ai/routing_runtime.py`:
  - `run_with_fallback(registry, decision, packet, *, dry_run)
    -> ProviderResponse` — tries the primary; on
    `ConnectionError` / config-not-configured / unspecified
    `Exception`, walks the decision's `fallbacks` tuple in order;
    final fallback is always `copy-paste` (configured-by-default).
  - Every attempt records a `routing_attempt` entry into
    `provider_calls.jsonl` with `from_provider` / `to_provider` /
    `reason` for traceability.

### 8.4 — `mythic-vibe ai route` command
- New `ai route` subaction:
  - `--role <role>` (default: forge)
  - `--task <task_type>` (default: build)
  - `--explain` — verbose reasons trace
  - JSON / text output
- Prints the matched rule + chosen provider/model + fallback
  chain. Pure routing — never invokes the provider.

## Definition of done

- All four slices' tests green; existing 947 stay green.
- Ruff + mypy clean throughout.
- Each slice ships its own commit + close-out shape.
- PHASE8_FINALE_CLOSEOUT.md after slice 8.4.
- Tracker + memory updated to "PH-08 fully complete".
- Pushed.
