# ADR-0007: Island D (WYRD Protocol) Adapter

## Status

Accepted

## Context

WYRD Protocol (World-Yielding Real-time Data) is Volmarr's
separate ECS-based AI world-model project. Its core innovation:
move world-state out of the LLM's context window into
deterministic structured state, exposed back to the LLM via a
typed interface. Shipped as the open-source `wyrd-protocol`
Python package.

The PH-09 master roadmap calls for binding WYRD's `passive_oracle`
into the Mythic Vibe CLI as an Auditor-agent verifier gate so the
forge cycle can include world-model consistency checks alongside
the existing diff / invariant / test-evidence gates.

## Decision

Add a binding at `mythic_vibe_cli/verify/wyrd_oracle.py` that:

1. **Try-imports the canonical Python package name `wyrd`.** No
   reference to any in-tree vendored snapshot. The adapter
   resolves whatever module the operator's `sys.path` / pip env
   makes available.

2. **Exports `gate_wyrd_oracle`** — a gate runner compatible with
   the slice 3.6 `forge_verifier.GateRunner` signature. Operators
   register it explicitly; **the default Auditor gate set is
   unchanged** to preserve backwards-compat for every project that
   doesn't opt in.

3. **Gates real activation behind two conditions** — same shape
   as Islands B and C:
   - The package import succeeds.
   - The operator sets `MYTHIC_ISLAND_WYRD_ENABLED=1`.

   When the flag is off, the gate runner returns `passed=True`
   with a "disabled" detail so operators can add the gate to
   their pipeline unconditionally and let the env flag drive
   activation. When the flag is on but the package is missing,
   the gate fails with the install hint.

4. **Provides `wyrd_gate_if_enabled()`** as a convenience helper
   for operators who want declarative env-driven registration:

   ```python
   from mythic_vibe_cli.forge_verifier import DEFAULT_AUDITOR_GATES
   from mythic_vibe_cli.verify.wyrd_oracle import wyrd_gate_if_enabled

   gates = {**DEFAULT_AUDITOR_GATES, **wyrd_gate_if_enabled()}
   run_auditor_gates(plan, agent_input, agent_output, root, gates=gates)
   ```

5. **Routes through a duck-typed contract** — tries
   `wyrd.passive_oracle(text)` / `oracle.passive_oracle` /
   `oracle.check` in order. The first callable wins. Verdict
   values are coerced from bool / dict / truthy-any into
   `(passed, detail)`.

6. **Adds the optional dep** to `pyproject.toml`:

   ```toml
   [project.optional-dependencies]
   wyrd = ["wyrd-protocol>=1.0"]
   ```

   Operators install with `pip install mythic-vibe[wyrd]`.

## Why opt-in registration (not in DEFAULT_AUDITOR_GATES)

If we added `wyrd-oracle` to `DEFAULT_AUDITOR_GATES`, every forge
run would call it by default. With the env flag off the gate
would short-circuit to "passed", but that still means an extra
gate result on every Auditor record — a behavioural change for
all existing projects.

Explicit registration via `wyrd_gate_if_enabled()` keeps the
default Auditor surface unchanged. Operators who want the gate
add three lines to their forge configuration; everyone else sees
zero diff.

## Provenance

- WYRD Protocol source lives at
  `github.com/hrabanazviking/WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model`
  (Volmarr's repo, v1.0.0 released 2026-04 per
  `project_wyrd_status.md`).
- The adapter writes new code under `mythic_vibe_cli/`; no
  vendor source is copied.
- The adapter contract is a duck-typed superset that any
  reasonable world-model oracle package can satisfy.

## Consequences

- The CLI gains an opt-in Verifier-agent world-model gate.
- ADR-0002's no-direct-vendor-imports rule is honoured — the
  adapter never imports from any in-tree WYRD mirror.
- Default behaviour is preserved: existing projects see no
  Auditor surface changes.
- A missing `wyrd-protocol` package only matters if the operator
  explicitly opted in.

## Verification

```bash
# Default behaviour unchanged.
pytest tests/test_forge_verifier.py

# Gate is opt-in and respects the env flag.
pytest tests/test_island_wyrd.py

# End-to-end: install + opt-in.
pip install mythic-vibe[wyrd]
MYTHIC_ISLAND_WYRD_ENABLED=1 mythic-vibe forge run --provider copy-paste --task "..."
```
