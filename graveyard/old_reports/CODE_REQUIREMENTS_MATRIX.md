# CODE_REQUIREMENTS_MATRIX.md — Required Code, Modifications, and New Build Targets

**Date:** 2026-04-23

This matrix turns architectural intent into concrete code work.

---

## 1. Scope

Primary product scope in this matrix:
- `mythic_vibe_cli/` package

Secondary governance scope:
- architecture and agent/skill infrastructure (`skills/`, `.claude/agents/`, `.roo/`)

Dormant islands are considered only as future integration sources, not direct dependencies.

---

## 2. Keep / Modify / Add matrix

| Area | Current state | Action | Why |
|---|---|---|---|
| CLI command routing | broad command surface in one module | **Modify** | maintainability and testability improve with command-handler decomposition |
| Workflow lifecycle | good baseline state machine | **Modify** | add stronger schema validation, state integrity checks, and migration versioning |
| Config loading | layered and functional | **Modify** | add schema typing + source diagnostics for invalid values |
| Codex packet rendering | deterministic enough but coupled to file reads | **Modify** | improve context provider abstraction and test fixture coverage |
| Method sync | direct network pull/caching | **Modify** | add robust retry policy, ETag/conditional fetch, better failure messages |
| Domain governance docs | present but fragmented | **Add** | codify ownership boundaries and refactor plan |
| Skill catalog | has Cartographer + others | **Add** | include Architect skill for repeatable future calls |
| Cross-tool agent persona files | partial | **Add** | ensure future invocation across setups (.claude/.roo/skills) |

---

## 3. Required modifications to existing code

## 3.1 `mythic_vibe_cli/cli.py`

**Needed changes**
1. Split command handlers into a `commands/` package (one module per command family).
2. Keep parser registration in one place; move behavior out.
3. Add consistent structured exit codes enum.
4. Normalize command aliases through shared dispatch table.

**Expected impact**
- Lower merge conflict rates.
- Easier addition of new commands.
- Improved test granularity.

## 3.2 `mythic_vibe_cli/workflow.py`

**Needed changes**
1. Add versioned status schema (`schema_version` in `status.json`).
2. Add strict validation before write (phase transitions, history shape).
3. Add migration helper for older status files.
4. Add invariant checks (e.g., completed phase ordering).

**Expected impact**
- Safer long-term project persistence.
- Better backward compatibility under upgrades.

## 3.3 `mythic_vibe_cli/config.py`

**Needed changes**
1. Add schema validation layer (typed errors surfaced to CLI).
2. Track invalid source fragments for debugging.
3. Add optional `--explain` mode in CLI to show precedence resolution.

**Expected impact**
- Faster diagnosis of malformed config.
- Reduced silent fallback surprises.

## 3.4 `mythic_vibe_cli/codex_bridge.py`

**Needed changes**
1. Extract context section providers into composable interfaces.
2. Add stable ordering and formatting guarantees.
3. Add packet truncation telemetry (what got compacted and why).
4. Add snapshot tests using fixed fixture files.

**Expected impact**
- Deterministic packets for robust prompting workflows.
- Safer evolution of packet format.

## 3.5 `mythic_vibe_cli/mythic_data.py`

**Needed changes**
1. Introduce retry/backoff with bounded attempts.
2. Add conditional request support (ETag/If-None-Match) to reduce bandwidth.
3. Add source integrity metadata to cache records.
4. Add circuit-breaker style fallback messaging for persistent outages.

**Expected impact**
- Better resilience to upstream network and API instability.

---

## 4. New code that should be added (priority order)

## P0 (must-have)

1. **Boundary check script**
   - Path: `scripts/check_domain_boundaries.py`
   - Purpose: fail CI if forbidden imports cross domain law.

2. **Config/status schema validators**
   - Path: `mythic_vibe_cli/validation.py`
   - Purpose: central typed validators for config and workflow status.

3. **Command-level test suite expansion**
   - Path: `tests/test_cli_commands_*.py`
   - Purpose: verify outputs and side-effects by command group.

## P1 (high value)

4. **Structured logging utility**
   - Path: `mythic_vibe_cli/logging_utils.py`
   - Purpose: JSON logs with run_id and command context.

5. **Integration adapter interfaces**
   - Path: `mythic_vibe_cli/integrations/interfaces.py`
   - Purpose: future-safe extension points for external knowledge/runtime providers.

6. **Packet fixture snapshots**
   - Path: `tests/fixtures/packet/`, `tests/test_codex_packet_snapshot.py`
   - Purpose: prevent accidental prompt drift.

## P2 (advanced hardening)

7. **Plugin lifecycle manager**
   - Path: `mythic_vibe_cli/plugins/manager.py`
   - Purpose: validate, load, and isolate plugin failure behavior.

8. **Metrics export hooks**
   - Path: `mythic_vibe_cli/metrics.py`
   - Purpose: optional counters/timers for command performance and reliability.

---

## 5. Deprecation targets

1. Root-level architectural ambiguity (implicit relation among dormant islands).
2. Any future direct imports from active CLI into dormant trees.
3. Untyped ad-hoc JSON writes that bypass validation layer.

---

## 6. Delivery sequencing plan

1. Governance and guardrails (docs + boundary checker).
2. Validation and reliability primitives (config/workflow/network).
3. Refactor for maintainability (command decomposition + packet providers).
4. Advanced observability and plugin hardening.
5. Optional cross-island integration pilots under feature flags.

---

## 7. Minimum robust baseline (MRB)

The project reaches MRB when all of the following are true:

- Boundary checker enforced and passing.
- Config and status are validated with typed errors.
- Network operations have bounded retries and graceful fallback.
- Core commands have regression tests.
- Packet rendering has fixture-based deterministic checks.
