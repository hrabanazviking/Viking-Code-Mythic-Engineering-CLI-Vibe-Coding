---
title: "Phase 1 — Slice 1.4 Close-out (Coverage Hygiene)"
phase: PH-01
slice: 1.4
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: bc65c80
head_at_close: c62db96
test_baseline_open: 276 + 14 subtests
test_baseline_close: 308 + 14 subtests
coverage_open: 74%
coverage_close: 76%
coverage_close_excl_tui: 79%
ruff_status: clean
mypy_status: clean
status: complete
new_findings: F-021, F-022
---

# Phase 1 Slice 1.4 — Coverage Hygiene Close-out

## Purpose

Run `pytest --cov=mythic_vibe_cli`, identify untested public
surface, and add tests until line coverage on the active runtime
reaches a sound baseline. Tests-only slice — zero production code
changes are allowed in 1.4 by contract.

## Honest scope-setting

The runtime audit set a target of "≥ 85% line coverage on
`mythic_vibe_cli/` excluding TUI" without measuring the starting
point. Baseline measurement on slice open showed:

- Overall: **74%** (6047 stmts, 1361 missing).
- Excluding TUI: **77%**.
- Worst module: `commands.py` at **56%** (1877 stmts, 768 missing).

Driving from 56 → 85% on `commands.py` alone would require ~570 more
covered statements — many of which sit behind real network calls
(provider adapters, sync, plunder), real git state (verify/git_diff
beyond what the new test repo gives), or are unreachable error
branches. That is a multi-slice effort, not a single 1.4 hygiene
pass.

The right call is: lift the cheapest, highest-value gaps in this
slice, document the remaining work, and route the long tail to
**PH-18 Round 4 (Resilience simulation)**, which already requires
deep coverage of failure paths to do its job.

## Final coverage delta

| Scope | Open | Close | Delta |
|---|---|---|---|
| Overall | 74% | **76%** | +2 |
| Excluding TUI | 77% | **79%** | +2 |
| `commands.py` | 56% | **58%** | +2 |
| `verify/git_diff.py` | 28% | **90%** | +62 |
| `verify/doc_checker.py` | 57% | **100%** | +43 |
| `verify/invariant_checker.py` | 70% | **80%** | +10 |
| `__main__.py` | 0% | **100%** | +100 |
| Test count | 276 | **308** | +32 |

22 modules now have complete coverage (vs. 20 at slice open). Ruff
and mypy stay clean.

## What landed

### Batch 1 — Ritual + verify-helper coverage

| Field | Value |
|---|---|
| Commit | `0a71722` |
| Files added | `tests/test_ritual_commands.py`, `tests/test_verify_helpers.py` |
| Tests added | 18 (7 ritual + 11 verify-helper) |
| Modules lifted | `git_diff` 28→90%, `doc_checker` 57→100%, `invariant_checker` 70→80% |
| New findings discovered | F-021, F-022 (see below) |

### Batch 2 — Command-path coverage

| Field | Value |
|---|---|
| Commit | `c62db96` |
| Files added | `tests/test_command_paths.py` |
| Tests added | 14 |
| Modules lifted | `commands.py` 56→58%, `__main__.py` 0→100% |
| Handlers covered | `cmd_sync` (dry-run text+json), `cmd_codex_log` (dry-run+happy+rejected-phase), `cmd_state_show` (text+json+missing×2), `cmd_state_validate` (text+json+missing+corrupt) |

## New findings discovered during this slice

The act of writing coverage tests surfaced two real bugs that the
runtime audit (slice 1.1) had not caught:

### F-021 — `cmd_weave` blocked by reflect-gate without prior verification

| Field | Value |
|---|---|
| Tag | BUG |
| Severity | warning |
| Location | `mythic_vibe_cli/commands.py:2735-2754` (call site) → `mythic_vibe_cli/workflow.py` (`check_in('reflect', ...)` gate) |
| Discovered by | `tests/test_ritual_commands.py::test_cmd_weave_blocked_by_reflect_gate_without_prior_verification` |
| Summary | `cmd_weave` delegates to `check_in('reflect', ...)`, which now refuses to advance until a successful verification record exists (the reflect-gate added in stage 8). On a fresh project that has not yet run `verify --record`, `weave` always returns `USER_INPUT_ERROR` with the message "reflection is blocked until a successful verification is recorded." |
| Additive remediation | Either (a) when PH-13 grows `weave` into a real drift-reconciliation command, route it through a different phase that does not hit the reflect-gate; or (b) add a `--allow-without-verification` flag with a clear warning. The current behaviour is locked in by the test so any future change is observable. |
| Blast radius | low — single command currently in scaffold mode |
| Target slice | PH-13 slice 13.3 (`heal v2`/drift work owns the rebuild of `weave`) |

### F-022 — `MythicWorkflow.doctor(repo_boundary=True)` raises `TypeError` on non-Mythic projects

| Field | Value |
|---|---|
| Tag | BUG |
| Severity | error |
| Location | `mythic_vibe_cli/workflow.py:269` |
| Discovered by | `tests/test_verify_helpers.py::InvariantCheckerTests` (couldn't write a direct integration test because of this bug) |
| Summary | `_doctor_repo_boundary` performs `errors.append(...); return` (bare return, no value) when the project lacks a `mythic_vibe_cli/` directory at its root. The caller at line 195 unpacks the result as `boundary_errors, boundary_warnings, boundary_sections = self._doctor_repo_boundary()` and crashes with `TypeError: cannot unpack non-iterable NoneType object`. |
| Additive remediation | Replace the bare `return` on line 269 with `return errors, warnings, sections`. One-line fix. Slice 1.3 is closed — this fix lands in PH-13 alongside the `heal v2` work, or a future targeted slice. |
| Blast radius | high — `verify --invariants` and any code path that invokes `MythicWorkflow.doctor(repo_boundary=True)` on a non-Mythic project will crash. The Mythic Vibe CLI's own development repo has the structure, so dogfood usage doesn't see it; but the audit's claim that `doctor` works on arbitrary user projects is wrong as written. |
| Target slice | high-priority insertion in PH-01 slice 1.5, or as part of PH-13 |

Both findings have regression tests that lock in the current
behaviour so the eventual fixes are observable in CI.

## Modules deliberately not driven to 85%

| Module | Current | Reason for deferral |
|---|---|---|
| `ai/providers/anthropic.py` | 32% | Requires a live `ANTHROPIC_API_KEY` to exercise the network path. Mock-based coverage is achievable but adds maintenance burden; deferred to PH-06/PH-08 when the provider layer is rebuilt. |
| `ai/providers/gemini.py` | 29% | Same as anthropic — needs `GEMINI_API_KEY` or mocks. |
| `ai/providers/openrouter.py` | 33% | Same as anthropic — needs `OPENROUTER_API_KEY` or mocks. |
| `ai/providers/local.py` | 71% | Will be rewritten in PH-06 against the real Ollama Python client; covering the placeholder is wasted effort. |
| `plunder/github.py` | 46% | Requires either real GitHub responses or a mocked HTTP layer. The plunder system is already shipped and stable; coverage of the network path is deferred to PH-10 when the plugin/registry tests need it. |
| `commands.py` long tail | 58% | The bulk of remaining gaps are in `cmd_plunder_*`, `cmd_method_*`, `cmd_handoff_*` failure branches, and `cmd_workflow_*` deep paths. PH-18 round 4 (resilience simulation) drives this through systematic failure-injection tests. |

## What this slice deliberately did not do

- Did not change any production code. Two real bugs (F-021, F-022)
  were discovered; both are documented and locked-in by tests but
  not fixed in this slice.
- Did not add provider-integration tests requiring API keys.
- Did not refactor `commands.py` to make it more testable. PH-18
  rounds 1–3 own that work.
- Did not add property-based or fuzz tests. Those wait for PH-14/18.
- Did not commit any TUI-adjacent tests. Coverage of the TUI is
  excluded from the slice 1.4 target by the original audit charter.

## Slice 1.4 close

Coverage lifted **74→76% overall, 77→79% excluding TUI**, with
**+32 tests** and **2 real bug discoveries** (F-021, F-022). The
85% target on the active runtime is honestly deferred to PH-18 round
4, which already requires deep failure-path coverage to do its job.

## Phase 1 — overall close

Phase 1 (Foundation Audit & Quality Sweep) is **substantively
complete** at the end of slice 1.4:

- Slice 1.1: 20 findings catalogued (`PHASE1_RUNTIME_AUDIT.md`)
- Slice 1.2: 21 issues triaged (`PHASE1_ISSUE_TRIAGE.md`)
- Slice 1.3: 7 info-severity additive fixes shipped (`PHASE1_SLICE_1_3_CLOSEOUT.md`)
- Slice 1.4: +32 coverage tests, 2 new bugs discovered (`PHASE1_SLICE_1_4_CLOSEOUT.md`)

Slice 1.5 (boundary re-audit) and slice 1.6 (Phase 1 close-out memo)
remain in the master roadmap for completeness, but the next
high-value move is to begin **Phase 2 (Slash Command Surface
Expansion)** or address the warning-severity F-022 bug as a targeted
hot-fix.

## Next decision point

Three viable next moves, in order of expected user value:

1. **Hot-fix F-022** (one-line return-tuple fix in `workflow.py`) so
   `verify --invariants` works on user projects. Trivial code
   change but fixes a real production bug.
2. **Slice 1.5 (boundary re-audit)** — run `mythic-vibe doctor
   --repo-boundary`, capture diagnostics, file ADRs for any
   missing-but-justified imports.
3. **Begin Phase 2** — start the slash-command surface expansion
   (39+ commands from the aggregate report).

The decision is Volmarr's.
