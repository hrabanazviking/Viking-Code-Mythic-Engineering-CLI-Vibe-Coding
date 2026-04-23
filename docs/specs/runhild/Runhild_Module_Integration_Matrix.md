# Rúnhild Integration Matrix — Complete Module Harmony Plan

## Integration Principle
Every module must be independently deployable, contract-tested, and observable, while still participating in a unified orchestration fabric.

## 1) Module Ownership and Contract Boundaries

| Module | Owns | Inputs | Outputs | Consistency Mode | Critical Invariants |
|---|---|---|---|---|---|
| Identity | user/session identity graph | auth claims, session events | identity context | Strong | no orphan sessions |
| Memory | episodic/semantic memory write-read | memory commands, retrieval query | memory records, recall sets | Strong/Eventual split | immutable event log |
| Emotion | affect state and transitions | user events, memory cues | affect vector, policy hints | Eventual + bounded lag | vector normalization |
| Cognition | reasoning pipeline and response plan | intent, context, memory recall | plan graph, response draft | Eventual | deterministic planner seed |
| Retrieval | ranking and context assembly | query + intent profile | ranked context bundles | Eventual | score monotonicity constraints |
| World Model | simulated state graph | world events, commands | current state snapshots | Strong for critical nodes | acyclic parent-child for tree domains |
| Orchestrator | workflow execution and saga state | user request, policy, module callbacks | execution decisions, compensations | Strong on saga state | single active owner per saga step |
| Policy/Guard | safety budgets and policy decisions | plans, prompts, outputs | allow/deny/transform | Strong | deny overrides enforceable |
| Telemetry | traces/logs/metrics storage | all module events | diagnostics and alerts | Eventual | no dropped critical incidents |
| Healing | remediation decisions | alerts, anomalies, failure contexts | repair actions, incident records | Strong for incident state | no infinite retry loops |

## 2) Internal API Channel Map

| Channel | Producer | Consumer | Contract Type | Retry Model |
|---|---|---|---|---|
| `identity.resolve.v1` | Interface | Identity | Request/Response | bounded retry + jitter |
| `memory.write.v2` | Orchestrator | Memory | Command | idempotent retry |
| `memory.recall.v2` | Cognition | Memory | Query | soft timeout + fallback |
| `emotion.update.v1` | Orchestrator | Emotion | Event | at-least-once with dedupe |
| `retrieval.rank.v1` | Cognition | Retrieval | Query | fallback to baseline ranker |
| `world.apply.v1` | Orchestrator | World Model | Command | saga compensation |
| `policy.evaluate.v3` | Orchestrator | Policy | Request/Response | no blind retry; deterministic reevaluate |
| `healing.execute.v1` | Telemetry/Policy | Healing | Command | guarded retry matrix |

## 3) Integration Sequence (Golden Path)
1. Interface validates request envelope.
2. Identity context resolved.
3. Policy pre-check executed.
4. Orchestrator creates saga plan.
5. Retrieval + memory + emotion updates run in bounded parallel.
6. Cognition composes response graph.
7. Policy post-check and transformation.
8. Response emitted with trace summary.
9. Telemetry + metrics flushed.
10. Reconciliation verifies consistency windows.

## 4) Integration Hardening Checklist
- Cross-module calls forbidden without contract registration.
- New endpoint blocked unless invariants declared.
- Chaos test required per new dependency.
- Each module publishes liveness, readiness, and dependency health.
- Rollout plan must include canary + rollback trigger thresholds.
