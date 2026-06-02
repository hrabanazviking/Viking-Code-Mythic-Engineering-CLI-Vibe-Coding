# ARCHITECT_REFACTOR_BLUEPRINT.md — Phased Refactor Strategy

**Date:** 2026-04-23  
**Intent:** Transform the repository from multi-island sprawl into a controlled super-repo with explicit contracts and high-confidence evolution.

---

## 1. Strategic objective

Create a robust architecture where:
- the active product (`mythic_vibe_cli`) remains stable,
- dormant islands are reusable but isolated,
- future integration is contract-first (not import-first),
- all changes are auditable via architecture artifacts.

---

## 2. Refactor principles (non-negotiable)

1. **Stability before expansion:** protect shipping CLI before integrating new subsystems.
2. **Contracts before coupling:** define API/event contracts before code reuse across islands.
3. **One-way dependencies:** active product must not absorb dormant runtime internals directly.
4. **Delete ambiguity:** every module has one owner and one purpose.
5. **Prove with checks:** each phase has explicit verification gates.

---

## 3. Current-state diagnosis

### 3.1 Positive assets
- Active package exists with clear entrypoints and tested CLI scope.
- Extensive architectural and mapping docs already present.
- Skills mechanism exists and can host reusable architecture agents.

### 3.2 Structural liabilities
- Multiple substantial code islands coexist with weak governance boundaries.
- Root runtime appears partially extracted and import-fragile.
- No single machine-readable domain policy to prevent accidental drift.
- Missing “integration contract layer” between projects.

---

## 4. Phase plan

## Phase 0 — Stabilize (1 week)

**Goal:** lock current product behavior and establish guardrails.

**Work:**
- Freeze active CLI public behavior for one iteration cycle.
- Add architecture control docs (`DOMAIN_MAP.md`, this blueprint, requirement matrix, robustness roadmap).
- Establish per-domain owners and review routing.

**Exit criteria:**
- Guardrail docs merged.
- Product commands still run.
- No new cross-island imports introduced.

---

## Phase 1 — Extract interfaces (1–2 weeks)

**Goal:** define contract points for future reuse.

**Work:**
- Introduce abstract interfaces/protocol docs for:
  - prompt/context providers,
  - method-data providers,
  - workflow state adapters.
- Define canonical DTO schema for packet/state exchange.
- Add adapter stubs where external islands *could* plug in later.

**Exit criteria:**
- Interface docs complete and versioned.
- CLI internals mapped to interfaces (even if single implementation).
- Contract tests scaffolded.

---

## Phase 2 — Isolate and quarantine legacy (1 week)

**Goal:** prevent accidental integration debt.

**Work:**
- Tag dormant islands with integration status metadata.
- Add static boundary check preventing imports from active CLI into dormant trees.
- Add “approved integration pathways” section in architecture docs.

**Exit criteria:**
- Boundary checks active in CI/local scripts.
- No forbidden imports.
- Clear pathway exists for future intentional integration.

---

## Phase 3 — Harden active product (2–4 weeks)

**Goal:** raise production reliability and observability.

**Work:**
- Add structured logging + run IDs across CLI flows.
- Add retry/backoff/timeouts for all network interactions.
- Add schema validation for config and status JSON.
- Add deterministic snapshot tests for codex packet rendering.

**Exit criteria:**
- Reliability and config validation tests pass.
- Failure modes are explicit and user-actionable.
- Packet outputs are regression-safe.

---

## Phase 4 — Optional integration pilots (2+ weeks)

**Goal:** integrate one capability from a dormant island through contracts only.

**Pilot candidate examples:**
- world-model summaries from WYRD as optional prompt-context plugin,
- knowledge enrichment from Thoughtform via offline extraction pipeline.

**Work:**
- Implement adapters in integration layer.
- Add feature flags and kill-switch config.
- Measure latency, error rate, and user-value impact.

**Exit criteria:**
- Pilot can be enabled/disabled safely.
- No boundary violations.
- Measured value justifies ongoing maintenance.

---

## 5. Refactor workstreams

1. **Architecture governance stream**
   - domain policy, ADR cadence, doc freshness automation.
2. **Core quality stream**
   - tests, validation, error handling, structured logs.
3. **Integration strategy stream**
   - contract docs + adapter prototypes + pilot decisions.
4. **Developer ergonomics stream**
   - command help consistency, contributor onboarding map, task runners.

---

## 6. Migration risk register

| Risk | Impact | Likelihood | Mitigation |
|---|---:|---:|---|
| Accidental cross-import from dormant island | High | Medium | CI import boundary checks + code-owner review gates |
| Refactor changes CLI UX unexpectedly | Medium | Medium | snapshot tests + golden output fixtures |
| Over-documentation without executable enforcement | Medium | High | convert key boundary rules into scripts/checks |
| Integration pilot introduces reliability regressions | High | Medium | feature flags + staged rollout + fallback path |

---

## 7. Definition of done for architectural refactor

- Domain boundaries are documented **and** checkable.
- Active product has deterministic tests for major flows.
- Network and file failure paths are intentionally handled.
- Integration into dormant code happens only via declared contracts.
- Architecture docs are aligned and current for the same commit SHA.
