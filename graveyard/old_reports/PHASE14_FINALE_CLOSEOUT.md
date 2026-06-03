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

---

## Update Notice — 2026-05-02 (additive)

A later audit (`AUDIT_FAKE_TEMP_CODE_2026-05-02.md`, HEAD `e0953b6`) re-measured the project on 2026-05-02. The original closeout above is preserved unchanged; this notice is purely additive.

- **Coverage:** any "76%" figure in this or sibling closeouts was a stale carry-over. Live measurement (`pytest --cov=mythic_vibe_cli --cov-report=term-missing`) on 2026-05-02 reports **82%** branch+line coverage on the production package (1694 passed, 1 skipped, 14 subtests). Current coverage is ~6 points higher than recorded.

— *Sólrún Hvítmynd & Runa, additive correction*

---

## Update Notice — 2026-05-02 Phase A.2 (additive, audit remediation)

The 2026-05-02 pseudo-code audit (`AUDIT_PSEUDOCODE_DEEP_2026-05-02.md`,
finding #3) caught a real functional bug in the policy gate shipped by
PH-14 slice 14.2. `policy/policy_gate.py:evaluate()` accepted
`Iterable[Constraint]`. The body exhausted the iterable in a list-comp
at line 85, then called `any(constraints)` at the same name a few lines
later. **List inputs were unaffected** (lists support multiple
iteration); **generator/iterator inputs silently suppressed the
"no blocking violations" advisory note** because the iterator was
already drained.

**Fix shipped in Phase A.2 (additive, one line):**
`policy/policy_gate.py:evaluate()` now does
`constraints = list(constraints)` at the top of the body, before any
iteration. The list-comp and `any()` check that follow operate on the
same materialised list. **No prior logic was changed** — every
existing branch behaves identically; only generator-input callers see
corrected output.

Tests: `tests/test_policy_gate.py` gained three new regression tests
in `EvaluateTests`:
- `test_generator_input_with_warn_only_still_emits_note` — verified
  to fail against the un-fixed code with exactly the expected symptom
  (`notes=[]` instead of the advisory note); passes with the fix.
- `test_generator_input_with_blocking_constraint_still_blocks` —
  locks the blocking-decision path against generator inputs.
- `test_iterator_input_yields_same_decision_as_list` — parity guard
  ensuring list-vs-iter inputs always produce identical decisions.

Test count: 1723 → 1726 (+3). Lint + mypy clean.

— *Sólrún Hvítmynd & Runa, additive correction*

---

## Update Notice — 2026-05-02 Phase B (additive, audit remediation)

The 2026-05-02 pseudo-code audit (`AUDIT_PSEUDOCODE_DEEP_2026-05-02.md`,
finding #6) caught the `_matches_command()` private function in
`policy/policy_gate.py:57-67` as defined-but-never-called dead code.
The function's docstring promised `[command:<name>]` tag scoping
("Tag a constraint with `[command:<name>]` to scope it to a specific
command"), but `evaluate()` never called the function — every blocking
constraint was surfaced for every command regardless of any tag.

**Fix shipped in Phase B (additive, no behaviour regression):**
- The body of `_matches_command()` is **preserved verbatim** — it
  remains the legacy substring-match utility, available to plugins
  or callers that prefer the loose semantic. Its docstring gained
  an additive 2026-05-02 note explaining the new path.
- New helpers added: `_extract_command_tags(constraint)` parses
  `[command:<name>]` tags; `_constraint_applies_to_command(constraint,
  command)` returns True for untagged constraints (broad default)
  AND for tagged constraints whose tags list `command`.
- `evaluate()` now filters constraints through
  `_constraint_applies_to_command` before evaluating violations.
  **Untagged constraints continue to apply broadly** — pre-Phase-B
  behaviour preserved. Tagged constraints are correctly scoped.

Tests: `tests/test_policy_gate.py` `EvaluateTests` gained six new
tests covering tagged-blocks-named-command, untagged-still-broad,
case-insensitive tag matching, multi-tag OR semantics, advisory-note
suppression when all constraints scope away, and mixed
tagged+untagged filtering.

Test count: 1726 → 1732 (+6). Lint + mypy clean. No regressions
in the existing 24 policy_gate tests.

— *Sólrún Hvítmynd & Runa, additive correction*
