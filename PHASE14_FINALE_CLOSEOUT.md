# PH-14 — Phase Finale Close-out (2026-05-01)

**Branch:** `development`
**Final HEAD:** `0c3454d` (this memo will land the next commit)
**Resume from:** `40ebd1a` (PH-06 Slice 6.4 closeout)

PH-14 enforces documented constraints at command time. Operator-
declared oaths, ADRs, and an explicit `mythic/constraints.md`
file feed a typed constraint store; a policy gate sits in front
of opt-in writing commands; blocking violations require explicit
`--override "<reason>"` and overrides are logged for audit.

All 4 slices shipped in one bundled commit; working tree clean,
every commit pushed, every existing test still passes.

---

## What landed

| Slice | Title | Commit | Net |
|---|---|---|---|
| TASK file | — | `6f75a64` | +145 lines |
| 14.1 + 14.2 + 14.3 + 14.4 | bundled (constraint store + gate + override log + report) | `0c3454d` | +1,490 lines, +44 tests |

**Test delta:** 1475 → 1519 (+44 net).
**Coverage:** 76% (held).
**Lint / type:** clean throughout.

---

## Capability summary

### Slice 14.1 — Constraint store

`mythic_vibe_cli/policy/constraint_store.py` reads typed
:class:`Constraint` records from three sources:

- **`mythic/oaths.md`** — one constraint per `## ` heading. Body
  bullets append to the summary. Severity tag `[blocking]` /
  `[warn]` / `[advisory]` is picked up from heading or any body
  line; body wins when both are tagged.
- **`mythic/constraints.md`** — flat bullet list, one constraint
  per `- ` bullet.
- **`docs/ADRS/*.md`** — one constraint per active ADR. Status
  must be `Accepted` (case-insensitive) or `Active`; anything
  else (Superseded, Deprecated) is skipped silently with a note.

Default severity is `"warn"`. Stable id slugs derived from
heading/bullet text. Dedup by id so duplicate sources don't
produce duplicate constraints. Missing / malformed sources
contribute zero constraints and never raise.

### Slice 14.2 — Policy gate

`mythic_vibe_cli/policy/policy_gate.py`:
- `PolicyDecision` dataclass (allowed, violations,
  requires_override, notes).
- `evaluate(constraints, action, command)` — returns a typed
  decision. Today's matching rule is broad: every blocking
  constraint surfaces as a violation regardless of command
  scope. Operators write narrow constraints; future enhancement
  may add `[command:<name>]` scoping.
- `evaluate_for_root(root, ...)` — load + evaluate convenience.
- `enforce_policy(root, *, action, command, override_reason)` —
  top-level helper. Returns `(proceed, decision)`. Override path
  logs to `mythic/policy_overrides.jsonl` then proceeds.

**Demo wire-in:** `cmd_oath` calls `enforce_policy` with
`action="write", command="oath"`. When blocking constraints
exist:
- Without `--override`: writes "Policy gate blocks `oath`"
  error and returns `UNSAFE_OPERATION_BLOCKED`.
- With `--override "<reason>"`: logs to override ledger and
  proceeds.
- When no constraints exist: command runs unchanged
  (backwards-compat preserved).

### Slice 14.3 — Override workflow

`mythic_vibe_cli/policy/override_log.py`:
- `OverrideRecord` dataclass (timestamp, action, command,
  reason, actor, host, violation_ids).
- `append_override` / `read_overrides` for round-trip audit.
- Actor resolved from `USER` / `USERNAME` / `LOGNAME` env;
  host via `socket.gethostname()`; UTC timestamps.
- Defensive read: missing file → `[]`; malformed JSON lines
  skipped.

### Slice 14.4 — `mythic-vibe policy report`

New top-level command + `/policy` slash entry. Lists current
constraints + override history with counts (by kind, by
severity). JSON mode emits the full payload; text mode prints a
human-readable summary.

```bash
mythic-vibe policy report --json
mythic-vibe policy report                  # text mode
```

---

## Master-roadmap impact

PH-14 closed. All 4 slices shipped:
- 14.1 Constraint store ✓
- 14.2 Policy gate (+ cmd_oath demo wire-in) ✓
- 14.3 Override workflow ✓
- 14.4 `policy report` command ✓

**Phases now fully closed:** PH-01..14 + PH-15. (15 of 20 — 75%
of roadmap.)

PH-14 unblocks no other phase directly — pure capability
addition. Remaining phases: PH-16, PH-17, PH-18, PH-19, PH-20.

**Recommended next move:** PH-18 (Robustness Sweeps Round 1–4) —
"spans all phases" priority and would harden every layer
including the new policy + streaming + sandbox paths under
failure injection. PH-16 (MCP/ACP/OpenTelemetry) is the
strategic alternative if you want protocol bridges before
hardening.

---

## Operational notes

- The policy gate is **opt-in by command**. Wholesale
  interception of every write command would silently change
  behaviour project-wide. Slice 14.2 wires one demo
  command (`cmd_oath`); follow-ups roll out gradually as each
  command opts in via `enforce_policy`.
- Every PH-14 capability is **off by default**. Projects
  without `mythic/oaths.md`, `mythic/constraints.md`, or any
  ADR see zero behavioural change.
- Severity vocabulary kept narrow on purpose: blocking, warn,
  advisory. Only blocking gates the command. Warn/advisory
  surface in `policy report` for documentation but never block.
- ADR `Status` field disambiguates active vs superseded
  constraints — no manual constraint editing needed when an
  ADR is replaced; flip the `Status` line and the constraint
  drops out of the active set automatically.
- Memory updated incrementally after each slice (per the
  durable rule about not batching).
- No new ADRs required — PH-14 lives entirely inside the
  active runtime boundary defined by ADR-0001 + ADR-0002.
