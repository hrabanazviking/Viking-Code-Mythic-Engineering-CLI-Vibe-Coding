# TASK — PH-14 Policy Engine & Constraint Verification

**Created:** 2026-05-01
**Branch:** `development`
**Operator:** Volmarr
**Resume from:** HEAD `40ebd1a` (PH-06 Slice 6.4 closeout)

PH-14 enforces documented constraints at command time. Operator-
recorded oaths, ADRs, and an explicit `mythic/constraints.md`
file feed a typed constraint store. A policy gate sits in front
of write commands; if a command would violate a recorded
constraint, the CLI warns and requires explicit `--override
"<reason>"`. Overrides are logged for audit.

**Master roadmap dependency:** `[PH-11, PH-13]` — both closed.

---

## Slice 14.1 — Constraint store

**Goal:** new `mythic_vibe_cli/policy/` package + `constraint_store.py`
that reads typed `Constraint` records from three sources:
- `mythic/oaths.md` — one constraint per `## ` heading with
  body bullets.
- `docs/ADRS/*.md` — one constraint per ADR (uses the `## Status`
  + `## Decision` sections to derive a constraint summary).
- `mythic/constraints.md` — flat bullet list, one constraint per
  bullet.

**Files:**
- `mythic_vibe_cli/policy/__init__.py` (new package).
- `mythic_vibe_cli/policy/constraint_store.py` — typed
  `Constraint` dataclass + `load_constraints(root) -> list[Constraint]`.
- Tests.

**Constraint shape:**
```python
@dataclass(frozen=True)
class Constraint:
    id: str            # stable id (slug of source + heading)
    kind: str          # "oath" | "adr" | "rule"
    text: str          # human-readable constraint
    severity: str      # "blocking" | "warn" | "advisory"
    source_path: str   # relative posix path
    source_section: str  # heading / line reference
```

**Acceptance:** missing files → empty list (no crash).
Malformed sections → skipped silently with notes in result.

**Progress:** [ ] not started

---

## Slice 14.2 — Pre-command policy gate

**Goal:** `mythic_vibe_cli/policy/policy_gate.py` provides a
`PolicyDecision evaluate(constraints, *, action, command, root)`
function that returns:
- `allowed: bool` — final permit/deny.
- `violations: list[Constraint]` — which constraints were hit.
- `requires_override: bool` — true when blocking violations exist.

**Approach:** **opt-in wrapping**, not blanket interception. A
helper `enforce_policy_or_exit(args, *, action, command)` is
called by writing commands that opt in. We wire ONE demo
command this slice (`cmd_oath` itself, since it's about
constraint acceptance) and document the pattern for others.

**Files:**
- `mythic_vibe_cli/policy/policy_gate.py` (new).
- `mythic_vibe_cli/commands.py` — wire `cmd_oath` through the
  gate.
- Tests.

**Acceptance:** disabled by default (no `mythic/constraints.md`
+ no override → command runs unchanged). Enabled when any
constraint source has rules.

**Progress:** [ ] not started

---

## Slice 14.3 — Override workflow

**Goal:** `--override "<reason>"` flag on commands that opt
into the policy gate. Records overrides to
`mythic/policy_overrides.jsonl` with timestamp + actor + reason
+ violated_constraint_ids.

**Files:**
- `mythic_vibe_cli/policy/override_log.py` (new) — append +
  read helpers for `mythic/policy_overrides.jsonl`.
- `mythic_vibe_cli/policy/policy_gate.py` — accept override
  reason, route to log writer.
- Tests.

**Acceptance:** override fires only when there are blocking
violations; logged entry has all fields populated; gate still
emits a warning to stderr when overridden.

**Progress:** [ ] not started

---

## Slice 14.4 — `mythic-vibe policy report`

**Goal:** new top-level command that lists current constraints
+ override history. JSON and text modes. Useful for audits.

**Files:**
- `mythic_vibe_cli/commands.py` — `cmd_policy_report` +
  `cmd_policy_dispatch`.
- `mythic_vibe_cli/app.py` — `mythic-vibe policy report` argparse.
- `runtime/slash_commands.py` — `/policy` BuiltinSlashCommand.
- Tests.

**Acceptance:** json mode emits `{constraints: [...],
overrides: [...], counts: {...}}`. Text mode tables them.

**Progress:** [ ] not started

---

## Phase finale

After all 4 slices ship:
- `PHASE14_FINALE_CLOSEOUT.md` — summary memo.
- Update memory + status file.
- Push.
- PH-14 closed in tracker.

---

## Operational notes

- ME laws: stdlib-first, default-off feature gates, cross-
  platform.
- The policy gate is **opt-in by command** — wholesale
  interception of every write command would silently change
  behaviour project-wide. Slice 14.2 wires one demo command;
  follow-ups roll out gradually.
- All artefacts go under `mythic/` (gitignored runtime).
  ADRs are read-only.
- After each slice: update memory + status file immediately.
