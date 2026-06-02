# TASK — PH-18 Robustness Sweeps Round 1–4

**Created:** 2026-05-01
**Branch:** `development`
**Operator:** Volmarr
**Resume from:** HEAD `6010881` (PH-14 finale)

PH-18 is described as four full passes of "make all code robust,
error correcting, bug resistant, self-healing, platform agnostic,
file-location agnostic, use API for internal communication,
modular." Per the master roadmap, literally four rounds — each
at a different layer of depth.

**Scope discipline note:** at our current size (1519 tests, 119
source files), wholesale refactors across every module would be
a multi-week effort. PH-18 here delivers **diagnostic + simulate
tooling** that surfaces findings + injects failures, **plus a
mythic-vibe simulate command** that exercises canonical failure
modes. Actual remediation of any findings happens incrementally
as a follow-up.

The slice 18.x "Done when" criteria from the master roadmap:
- ≥ 600 tests after the four rounds — **already vastly
  exceeded (1519 baseline)**.
- Coverage ≥ 90% on active runtime — **stretch from current 76%;
  treat as aspirational, not a gate**.
- No subprocess call bypasses `runtime.exec` — **slice 18.1's
  audit reports current bypasses; remediation is incremental**.
- No file write bypasses the mutation queue — **slice 18.2's
  audit reports current bypasses**.
- `simulate` runs cleanly through canonical failure modes —
  **slice 18.4 ships this**.

**Master roadmap dependency:** "spans all phases" (no specific
gate).

---

## Slice 18.1 — Round 1: boundary + subprocess audit

**Goal:** new `mythic_vibe_cli/robustness/` package +
`boundary_audit.py`. Walks the active runtime tree, finds:
- Direct `subprocess.run` / `subprocess.Popen` / `os.system`
  calls outside `runtime/exec.py`.
- Bare `except:` clauses.
- File IO operations without exception handling (best-effort
  via AST scan).

Surfaces typed `BoundaryFinding` records. Reporting only.

**Files:**
- `mythic_vibe_cli/robustness/__init__.py` (new package).
- `mythic_vibe_cli/robustness/boundary_audit.py` (new).
- Tests.

**Progress:** [ ] not started

---

## Slice 18.2 — Round 2: path + concurrency audit

**Goal:** `path_audit.py` finds:
- Hardcoded `"mythic/..."` string literals outside
  `core/state.py` (the canonical path-resolver).
- Direct `path.write_text` / `open(... "w")` calls outside the
  `file_mutation_queue` module (best-effort static find — file
  IO via the queue uses a specific helper signature).

Reporting only.

**Files:**
- `mythic_vibe_cli/robustness/path_audit.py` (new).
- Tests.

**Progress:** [ ] not started

---

## Slice 18.3 — Round 3: internal API surface audit + ADR-0009

**Goal:** `api_audit.py` finds cross-subpackage imports that
reach into private modules instead of the subpackage's
`__init__.py` public surface. Documents the contract in
ADR-0009.

Reporting only.

**Files:**
- `mythic_vibe_cli/robustness/api_audit.py` (new).
- `docs/ADRS/ADR-0009-internal-api-surfaces.md` (new).
- Tests.

**Progress:** [ ] not started

---

## Slice 18.4 — Round 4: `mythic-vibe simulate`

**Goal:** new top-level command that injects synthetic failures
across canonical scenarios:
- Malformed `mythic/status.json` → confirm `cmd_status` fails
  cleanly with a useful error.
- Missing required artefact → confirm `verify --invariants`
  surfaces it.
- Provider failure (non-fallback path) → confirm `cmd_ai_run`
  with `--no-fallback` propagates a clean error.
- Network timeout (mocked urllib) → confirm Ollama provider
  raises ConnectionError cleanly.

Each scenario runs the canonical CLI command in a temp project
+ checks the exit code. JSON output records pass/fail per
scenario.

**Files:**
- `mythic_vibe_cli/robustness/simulate.py` (new).
- `mythic_vibe_cli/commands.py` — `cmd_simulate` +
  `cmd_simulate_dispatch`.
- `mythic_vibe_cli/app.py` — `mythic-vibe simulate` argparse.
- `runtime/slash_commands.py` — `/simulate` + `/resilience`
  builtin entries.
- Tests.

**Progress:** [ ] not started

---

## Phase finale

After all 4 slices ship:
- `PHASE18_FINALE_CLOSEOUT.md` — summary memo.
- Update memory + status file.
- Push.
- PH-18 closed in tracker.

---

## Operational notes

- ME laws: stdlib-first, default-off, cross-platform.
- All four audits are **read-only** — they surface findings,
  never mutate code. Remediation happens incrementally as
  the team triages each finding.
- The simulate command is **opt-in** — operators run it when
  they want to verify resilience; never invoked from the
  normal flow.
- Memory updated incrementally after each slice.
