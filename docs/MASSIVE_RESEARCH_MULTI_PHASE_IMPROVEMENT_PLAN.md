# Massive Research: Multi-Phase Improvement Plan for Mythic Vibe CLI

**Date:** 2026-05-02  
**Scope reviewed:** active runtime (`mythic_vibe_cli/`), governance docs, architecture contracts, command contracts, verification posture, plugin/TUI workflows.  
**Research sources:** repository architecture and policy documents listed at the end.

---

## Executive Summary

The project already has strong foundations: explicit architecture boundaries, command contracts, verification gates, and a durable artifact model. The highest-leverage improvements now are less about inventing new features and more about **operational rigor at scale**:

1. **Contract-to-implementation enforcement** (automated drift checks).
2. **Reliability hardening** (property tests, chaos-style CLI failure tests, recovery drills).
3. **Provider and plugin safety** (trust boundaries, capability-scoped execution).
4. **Performance and UX telemetry** (cold-start, command latency, packet size budgets).
5. **Release engineering maturity** (matrix CI, compatibility promises, upgrade playbooks).
6. **Security posture upgrades** (threat model, provenance, tamper evidence).

This plan is structured into phases designed to reduce risk while compounding value.

---

## Current-State Findings (What is working well)

- Clear active-vs-dormant monorepo boundaries and dependency direction law.
- Durable state model and migration safeguards (backup + lock + atomic write pattern).
- Explicit command contracts and compatibility aliases.
- Verification as a first-class artifact, with gatekeeping before reflect/check-in.
- Static-first model listing policy with remote opt-in fallback behavior.
- Plugin hooks now mapped to real command surfaces.

These are excellent primitives; the recommendations below build on them.

---

## Phase 0 (Week 0-1): Baseline and Truth Alignment

### Goals
- Create objective baselines for quality, speed, reliability, and drift.

### Recommendations
- Add a **docs-to-code contract auditor** that validates:
  - every documented command exists,
  - every alias resolves,
  - every documented exit code appears in runtime behavior.
- Add a **runtime topology report** (import graph snapshot) that flags boundary violations against architecture law.
- Record baseline metrics:
  - command startup time,
  - median runtime for `status`, `doctor`, `verify`, `workflow plan`, `packet create`,
  - packet artifact size distribution,
  - state migration success/failure rate.

### Deliverables
- `tools/contract_audit.py`
- `tools/import_boundary_audit.py`
- `docs/quality/baseline_metrics_2026-05-02.md`

### Exit Criteria
- CI fails on contract drift.
- Baseline report committed and reproducible locally.

---

## Phase 1 (Week 1-3): Verification and Reliability Hardening

### Goals
- Make failures predictable, diagnosable, and recoverable.

### Recommendations
- Expand tests from happy-path to **adversarial-path**:
  - malformed/corrupt JSON state,
  - lock contention,
  - interrupted writes,
  - missing artifact directories,
  - partial packet metadata.
- Add **property-based tests** for state migration and schema round-trips.
- Introduce **golden snapshot tests** for high-value JSON outputs (`status --json`, `workflow plan --json`, `packet list --json`, `next --json`).
- Add a **verification replay command** to rerun latest verification command set from artifact history.

### Deliverables
- `tests/property/test_state_migrations.py`
- `tests/snapshots/*`
- `mythic-vibe verify replay` (or equivalent command)

### Exit Criteria
- Demonstrated deterministic behavior under injected filesystem failure scenarios.

---

## Phase 2 (Week 3-5): Plugin and Extension Safety Model

### Goals
- Preserve extensibility without turning plugins into a reliability/security liability.

### Recommendations
- Introduce plugin **capability declarations** (read-only, network, subprocess, file-write scopes).
- Add plugin **trust levels** and default-deny for risky capabilities.
- Add `plugin doctor` for:
  - import health,
  - hook conformance,
  - capability/reporting mismatch,
  - execution timeout warnings.
- Add **hook execution budget** (timeout + circuit breaker) to prevent hanging command flows.
- Add structured per-hook telemetry records in machine-readable logs.

### Deliverables
- `docs/plugins/capability_model.md`
- `mythic/plugins.schema.json` updates
- `plugin doctor` command + tests

### Exit Criteria
- Enabled plugin cannot stall core CLI indefinitely.
- Operators can audit plugin risk quickly.

---

## Phase 3 (Week 5-7): AI Provider Abstraction and Model Governance

### Goals
- Stabilize multi-provider behavior and reduce model-selection fragility.

### Recommendations
- Add **provider conformance tests** for shared contracts (list, run, errors, timeout, retries).
- Build a **model profile registry** with standardized metadata:
  - context length, reasoning profile, tool-calling support, latency class, cost class.
- Add model recommendation command:
  - `ai recommend --task <...> --constraints <...>` based on policy + local profile catalog.
- Add **pinning policy** for reproducible runs (explicit provider/model/version markers in artifacts).
- Add stale-catalog watchdog that opens actionable warning when `last_updated` exceeds policy threshold.

### Deliverables
- `tests/providers/test_contract_conformance.py`
- `mythic_vibe_cli/ai/model_profiles.py`
- `ai recommend` command

### Exit Criteria
- Provider swap does not change artifact schema or break core workflow semantics.

---

## Phase 4 (Week 7-9): Workflow Intelligence and Artifact Quality

### Goals
- Improve output usefulness while controlling context bloat.

### Recommendations
- Add packet **quality linting**:
  - missing acceptance criteria,
  - no test strategy,
  - ambiguous task language,
  - insufficient architectural anchors.
- Add **artifact lineage graph** (workflow -> step -> packet -> verify -> reflect).
- Add **context budget optimizer** in packet generation:
  - role-aware summarization,
  - token budget policy tiers,
  - duplicate excerpt elimination.
- Add “phase readiness score” from hard checks + soft heuristics.

### Deliverables
- `packet lint` command
- `workflow lineage` view (json + markdown export)
- `docs/quality/packet_quality_rubric.md`

### Exit Criteria
- Reduced packet size variance with no drop in auditability.

---

## Phase 5 (Week 9-11): UX, Onboarding, and Operator Ergonomics

### Goals
- Reduce cognitive load for new and returning users.

### Recommendations
- Add **interactive first-run wizard** (optional) that initializes goal, profile, and preferred output modes.
- Add **persona-driven command presets**:
  - solo builder,
  - team lead,
  - auditor/compliance reviewer.
- Improve `next` with confidence annotations and rationale snippets.
- Add `doctor --fix` for safe, reversible auto-remediation of common issues.
- TUI improvements:
  - inline verification history drill-down,
  - packet readiness heatmap,
  - plugin risk indicators.

### Deliverables
- `onboarding.md` rewrite with scenario tracks
- wizard command and tests
- TUI enhancements

### Exit Criteria
- Faster time-to-first-successful-loop for new users.

---

## Phase 6 (Week 11-13): Security, Provenance, and Supply Chain

### Goals
- Make trust and provenance explicit for both humans and automation.

### Recommendations
- Add threat model doc for CLI + plugin surfaces + provider IO.
- Add signed artifact option (checksums at minimum, signatures optional phase extension).
- Add plunder/import provenance enrichments:
  - source digest,
  - license decision rationale,
  - modified-lines attestation.
- Add dependency update policy and CVE triage workflow.

### Deliverables
- `docs/security/threat_model.md`
- `mythic-vibe provenance verify`
- `docs/security/supply_chain_policy.md`

### Exit Criteria
- Operator can prove artifact integrity and origin chain.

---

## Phase 7 (Week 13-16): Release Engineering and Long-Term Maintainability

### Goals
- Scale contributor velocity without destabilizing runtime behavior.

### Recommendations
- CI matrix:
  - Python versions,
  - Linux/macOS/Windows,
  - optional-dependency modes (minimal/full/tui).
- Compatibility policy:
  - command/JSON stability grades,
  - deprecation windows,
  - migration advisories.
- Add automated changelog classification from PR labels and command-surface diffing.
- Introduce quarterly architecture review cadence with drift scorecards.

### Deliverables
- `docs/compatibility_policy.md`
- release workflow templates
- architecture drift dashboard

### Exit Criteria
- Predictable releases with explicit compatibility guarantees.

---

## Cross-Cutting KPI Framework

Track the following from Phase 0 onward:

- **Reliability:** verification pass rate; migration recoverability success; plugin timeout incidents.
- **Quality:** packet lint pass rate; reflect-after-verify compliance; docs-contract drift incidents.
- **Performance:** P50/P95 command latency and startup times; packet generation time.
- **Safety:** provenance coverage; plugin capability coverage; security issue MTTR.
- **Adoption/UX:** time-to-first-loop; `doctor` success recovery rate; tutorial completion rates.

---

## Prioritized Top-15 Backlog (If you need to start tomorrow)

1. Contract drift CI guardrails.
2. Import-boundary auditor.
3. Snapshot tests for JSON contracts.
4. Property tests for migration invariants.
5. Plugin timeouts and circuit breakers.
6. Plugin capability declaration schema.
7. Provider conformance suite.
8. Model profile registry.
9. `ai recommend` command.
10. Packet lint command.
11. Workflow lineage export.
12. `doctor --fix` safe remediations.
13. Threat model publication.
14. Artifact integrity verification command.
15. Compatibility policy with deprecation windows.

---

## Suggested Implementation Rhythm

- **Cadence:** 2-week iterations.
- **Guardrail:** no new feature merges without tests + contract update checks.
- **Definition of done:** behavior + docs + test + changelog continuity in one PR.
- **Review split:** architecture review (boundary), UX review (operator clarity), reliability review (failure semantics).

---

## Repository Documents Reviewed

- `docs/ARCHITECTURE.md`
- `docs/ACTIVE_PRODUCT_BOUNDARY.md`
- `docs/COMMAND_CONTRACTS.md`
- `docs/quickstart.md`
- `docs/ADRS/ADR-0003-verification-gates.md`
- `docs/ADRS/ADR-0010-ai-model-listing-policy.md`

