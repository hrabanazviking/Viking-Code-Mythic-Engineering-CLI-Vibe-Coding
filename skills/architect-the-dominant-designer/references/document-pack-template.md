# Architect Document Pack Template

Use this template when producing deep architecture packets for this repository.

## 1) Domain map

- Canonical bounded contexts
- Domain owners
- Allowed/forbidden dependencies
- Interface contracts
- Change control ownership

## 2) Layer law

- Interface/API layer responsibilities
- Application orchestration responsibilities
- Domain model/service responsibilities
- Infrastructure adapter responsibilities
- Observability and policy placement

## 3) Capability matrix

- Existing capabilities by subsystem
- Missing capabilities required for target state
- Keep / modify / replace / deprecate decisions
- Sequence constraints and hard blockers

## 4) Refactor strategy

- Stabilization phase (no behavior changes)
- Contract extraction phase
- Module migration phase
- Cleanup and deletion phase
- Validation and rollback points

## 5) Robustness roadmap

- Reliability requirements (timeouts, retries, idempotency)
- Security requirements (secrets, authz, supply chain)
- Performance requirements (budgets and SLOs)
- Test strategy (unit/integration/e2e/chaos)
- Operational readiness (runbooks, dashboards, alerts)

## 6) Delivery governance

- ADR policy
- Release gating checklist
- Definition of done by phase
- Risk register and mitigation ownership
