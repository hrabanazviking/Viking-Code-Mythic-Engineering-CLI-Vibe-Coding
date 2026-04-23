# Rúnhild Self-Healing & Error-Proofing Playbook

## 1) Runtime Reliability State Machine
`HEALTHY -> DEGRADED -> CONTAINED -> HEALING -> VERIFIED -> HEALTHY`

- Transition to `DEGRADED` on SLO breach, repeated contract failures, or anomaly spike.
- Transition to `CONTAINED` when circuit breaker or bulkhead rules are activated.
- Transition to `HEALING` once a remediation workflow is selected.
- Transition to `VERIFIED` only after post-heal invariants pass.

## 2) Automated Remediation Library

| Failure Signature | Detector | First Action | Second Action | Final Escalation |
|---|---|---|---|---|
| Timeout spike | p95 latency monitor | reduce concurrency | switch to cached partial path | isolate dependency |
| Contract mismatch | schema validator | reject + quarantine | run compatibility shim | rollback caller version |
| Queue saturation | queue depth alert | apply backpressure | scale worker pool | switch to degraded mode |
| Memory drift | consistency auditor | freeze writes in segment | replay event ledger | restore last verified snapshot |
| Repeated policy conflicts | policy monitor | activate strict mode | notify orchestrator to simplify plan | require manual policy review |

## 3) Guardrails Against Cascading Failure
- circuit breakers per dependency.
- bulkhead isolation per domain.
- per-route resource budgets.
- maximum retry caps with exponential backoff + jitter.
- dead letter queues for non-recoverable jobs.

## 4) Self-Correction Intelligence
- incident signatures persisted with root-cause label.
- remediation success rates tracked to adapt future playbook priority.
- “known-bad deploy” detector gates rollout automatically.

## 5) Data Repair and Reconciliation
- dual-read compare for critical stores.
- periodic reconciliation job with discrepancy report.
- authoritative source election rules.
- conflict resolver strategy: deterministic merge > last-known-good fallback > manual arbitration.

## 6) Error-Proof Developer Workflow
- pre-merge contract diff check.
- invariant simulation tests.
- migration rehearsal in shadow environment.
- release checklist includes rollback rehearsal.

## 7) User-Facing Reliability UX
- clear status modes: Normal / Limited / Recovery.
- visible fallback reason + expected recovery path.
- safe retry buttons for user-initiated actions.
