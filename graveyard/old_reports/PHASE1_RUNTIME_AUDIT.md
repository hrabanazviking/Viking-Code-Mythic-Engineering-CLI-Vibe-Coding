---
title: "Phase 1 — Runtime Audit (Slice 1.1)"
phase: PH-01
slice: 1.1
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_audit: d36a4ae
test_baseline: 270 passed, 14 subtests passed
ruff_status: clean
mypy_status: clean
scope: mythic_vibe_cli/ + tests/
discipline: additive-only — no code changes in this audit
status: complete
---

# Phase 1 Runtime Audit (Slice 1.1)

## Purpose

Walk every module in the active runtime (`mythic_vibe_cli/`) and tag
findings against a fixed taxonomy. Each finding becomes an additive
remediation item to be addressed in subsequent Phase 1 slices (1.3
quick-fix sweep, 1.4 coverage hygiene) or, when too large, recorded
in the master roadmap as a deferred item with a phase home.

This is **audit-only**. No code changes land in this slice.

## Audit method

1. Walk `mythic_vibe_cli/` recursively. Record line counts and module
   inventory. (56 Python modules, 10,703 total lines.)
2. Pattern-search for the standard incomplete-code markers: `TODO`,
   `FIXME`, `XXX`, `HACK`, `NotImplementedError`, "not yet
   implemented", "placeholder", "stub".
3. Pattern-search for fragile error handling: bare `except:`, `except
   Exception: pass`, `raise Exception(`.
4. Pattern-search for direct subprocess use outside `runtime.exec`
   (the runtime contract added in the Pi plundering pass).
5. Inspect every flagged location in context, plus the larger
   handler files (`commands.py`, `app.py`, `workflow.py`,
   `codex_bridge.py`).
6. Cross-reference findings against `MYTHIC_VIBE_CLI_MASTER_ROADMAP.md`
   to assign each finding a phase/slice destination.

## Finding taxonomy

| Tag | Meaning |
|---|---|
| **BUG** | Behaviour is wrong as written |
| **INCOMPLETE** | Function or path returns a scaffold/placeholder result |
| **ORPHAN** | Code exists but is not reachable from any registered surface |
| **INTEGRATION_GAP** | Two subsystems should talk but don't |
| **INEFFICIENCY** | Works but with avoidable cost or duplicated work |
| **MISSING_TEST** | Public surface lacks direct test coverage |
| **DOC_DRIFT** | Docs or changelog claim a behaviour that the code does not implement |
| **CONVENTION** | Stylistic deviation that complicates future automation (no `__all__`, etc.) |

Each finding has: id, tag, severity (`info/warning/error/blocked`),
location, summary, additive remediation, blast radius, target slice.

---

## Findings

### F-001 — `cmd_prune` is a scaffold-only stub

| Field | Value |
|---|---|
| Tag | INCOMPLETE |
| Severity | warning |
| Location | `mythic_vibe_cli/commands.py:2757-2762` |
| Summary | The `prune` command prints a "Prune ritual scaffold ready" message and tells the user to run their own linter/dead-code tool. It does not perform any pruning. |
| Additive remediation | Implement an additive `prune` that walks `mythic/` for stale check-ins, expired packets, orphaned plunder caches, and offers a `--dry-run` listing followed by an explicit user-approved removal. Never deletes user-authored docs. |
| Blast radius | low — scoped to `mythic/` artefacts |
| Target slice | PH-13 Drift Detection & Self-Healing, slice 13.3 (`heal v2` pattern reusable for `prune`) |

### F-002 — `cmd_heal` is a scaffold-only stub

| Field | Value |
|---|---|
| Tag | INCOMPLETE |
| Severity | warning |
| Location | `mythic_vibe_cli/commands.py:2765-2772` |
| Summary | The `heal` command prints "Heal ritual scaffold ready" and tells the user to reproduce-failure / patch / rerun. It does not perform any healing. |
| Additive remediation | Connect `heal --failing-test <id>` to `verify` so it generates a Skald-role packet describing the failure and proposed additive fix. Implementation should be the Forge agent in PH-03 + the policy gate in PH-14. |
| Blast radius | low |
| Target slice | PH-03 multi-agent forge + PH-13 self-healing |

### F-003 — `cmd_workflow_run` non-dry-run path is intentionally disabled

| Field | Value |
|---|---|
| Tag | INCOMPLETE |
| Severity | info (intentional gate) |
| Location | `mythic_vibe_cli/commands.py:2779-2781` |
| Summary | `workflow run` returns `UNSAFE_OPERATION_BLOCKED` with the message "Real workflow execution is not enabled yet. Re-run with `--dry-run` to preview the role sequence." |
| Additive remediation | This is the slot Phase 3 fills with the multi-agent `forge` command. Keep the gate until the provider-backed forge ships in slice 3.5. |
| Blast radius | none until enabled |
| Target slice | PH-03 slice 3.5 |

### F-004 — `cmd_oath` records nothing to disk

| Field | Value |
|---|---|
| Tag | INCOMPLETE |
| Severity | warning |
| Location | `mythic_vibe_cli/commands.py:1982-1987` |
| Summary | The `oath` command prints the AI-review oath text. With `--yes` it prints "Oath accepted." It does not persist the acceptance, timestamp, or constraint anywhere. |
| Additive remediation | When `--yes` is given, append a record to `mythic/oaths.jsonl` with timestamp, oath text hash, and the operator name (best-effort). Surface accepted oaths in `policy report` (PH-14). |
| Blast radius | low — adds one new artefact file |
| Target slice | PH-14 Policy Engine, slice 14.1 (constraint store) |

### F-005 — `cmd_weave` is thin

| Field | Value |
|---|---|
| Tag | INCOMPLETE |
| Severity | info |
| Location | `mythic_vibe_cli/commands.py:2735-2754` |
| Summary | `weave` invokes `MythicWorkflow.check_in("reflect", update="Ran mythic weave doc synchronization checkpoint.")` and reports the resulting status/devlog files. It does not actually weave anything (no docs/code drift reconciliation). |
| Additive remediation | Once the knowledge graph (PH-05) and drift detector (PH-13) ship, route `weave` to surface drift findings before recording the check-in. Until then, the current behaviour is acceptable as a check-in marker. |
| Blast radius | none today |
| Target slice | PH-13 slice 13.3 |

### F-006 — `cmd_slash_dispatch` returns `USER_INPUT_ERROR` silently for unknown subcommands

| Field | Value |
|---|---|
| Tag | BUG |
| Severity | warning |
| Location | `mythic_vibe_cli/commands.py:3035-3038` |
| Summary | `cmd_slash_dispatch` only handles `args.slash_command == "list"`. Any other value (or `None`) returns `USER_INPUT_ERROR (2)` without printing an error message — the user sees nothing, just exit code 2. |
| Additive remediation | Add an explicit `write_error(f"Unknown slash subcommand: {args.slash_command!r}. Try `slash list`.")` before the return. Same shape as other dispatchers (`cmd_ai_dispatch` has the same silent-fall-through pattern at line 3071). |
| Blast radius | trivial |
| Target slice | PH-01 slice 1.3 (quick-fix sweep) |

### F-007 — `cmd_ai_dispatch` returns `USER_INPUT_ERROR` silently for unknown subcommands

| Field | Value |
|---|---|
| Tag | BUG |
| Severity | warning |
| Location | `mythic_vibe_cli/commands.py:3062-3071` |
| Summary | Same shape as F-006. Unknown `ai_command` values return exit code 2 with no message. |
| Additive remediation | Same as F-006 — write a structured error before returning. |
| Blast radius | trivial |
| Target slice | PH-01 slice 1.3 |

### F-008 — TUI plugin/extension/skill/prompt entries explicitly inert

| Field | Value |
|---|---|
| Tag | INTEGRATION_GAP |
| Severity | info (declared deferred in CHANGELOG) |
| Location | `mythic_vibe_cli/tui/picker.py:146` |
| Summary | The slash-command picker preview shows "(plugin dispatch not yet implemented; press Esc to return.)" for non-builtin entries. Plugin-contributed slash commands cannot run from the TUI yet. |
| Additive remediation | Phase 2 slice 2.6 ("Plugin-contributed slash commands") wires the dispatcher across CLI/REPL/TUI. Phase 4 slice 4.7 then exposes the full keymap. |
| Blast radius | none — feature gap |
| Target slice | PH-02 slice 2.6 + PH-04 slice 4.7 |

### F-009 — `tui/runner.py` calls `subprocess.Popen` directly

| Field | Value |
|---|---|
| Tag | INTEGRATION_GAP |
| Severity | warning |
| Location | `mythic_vibe_cli/tui/runner.py:127` |
| Summary | The TUI command runner spawns subprocesses with `subprocess.Popen` directly instead of going through `runtime.exec`. This is justified by the live-polling/cancellable use case, but breaks the master-roadmap invariant that all subprocess work flows through `runtime.exec`. |
| Additive remediation | Either (a) extend `runtime.exec` with a streaming/polling variant (`exec_streaming(...)` returning a context manager with `poll()` / `terminate()` / `read_tail()`) and migrate the TUI runner to use it, or (b) document the exception in ADR-0005. Option (a) is preferred. |
| Blast radius | medium — `runtime.exec` API addition |
| Target slice | PH-18 slice 18.1 (Round 1: boundary & error paths) |

### F-010 — Silent JSON sidecar parse failure on packet ingest

| Field | Value |
|---|---|
| Tag | INEFFICIENCY |
| Severity | info |
| Location | `mythic_vibe_cli/codex_bridge.py:278-283` |
| Summary | When `_load_source` reads a `.json` packet sidecar and `json.loads` raises `JSONDecodeError`, the exception is silently swallowed and the metadata falls back to the in-text parse. A user with a malformed sidecar gets no warning. |
| Additive remediation | Replace `pass` with a `write_verbose(...)` line via `mythic_vibe_cli.output` (already used elsewhere in `codex_bridge`) to surface the parse failure when running with `--verbose`. |
| Blast radius | trivial |
| Target slice | PH-01 slice 1.3 |

### F-011 — Public surface implicit on ~44 of 56 modules

| Field | Value |
|---|---|
| Tag | CONVENTION |
| Severity | info |
| Location | `mythic_vibe_cli/**/*.py` (only 12 modules declare `__all__`) |
| Summary | Only 12 of 56 modules declare `__all__`. The other 44 have implicit public surfaces, which complicates the PH-18 round 3 work that requires every subpackage to expose a typed module-level API. |
| Additive remediation | When a module is touched in any future slice, add `__all__` if it has more than two public names. Don't sweep across all 44 in one PR — that would dilute review. |
| Blast radius | none |
| Target slice | PH-18 slice 18.3 (Round 3: internal API surfaces) |

### F-012 — `cmd_verify_dispatch` is a one-line passthrough

| Field | Value |
|---|---|
| Tag | INEFFICIENCY |
| Severity | info |
| Location | `mythic_vibe_cli/commands.py:3074-3075` |
| Summary | `cmd_verify_dispatch` is `return cmd_verify(args)` — there is no real subcommand routing here. The dispatch indirection is a leftover from a deferred design. |
| Additive remediation | Either remove the indirection (registering `cmd_verify` directly) — but that's destructive — or wire real subcommands (`verify run` / `verify show` / `verify history`) under it. Prefer the latter so the dispatcher pattern earns its keep. |
| Blast radius | low |
| Target slice | PH-08 slice 8.4 (verify gets verb subcommands consistent with `ai`/`workflow`/`packet`) |

### F-013 — `prune`, `heal`, `weave`, `oath` lack dedicated tests

| Field | Value |
|---|---|
| Tag | MISSING_TEST |
| Severity | info |
| Location | `tests/` |
| Summary | None of `prune`/`heal`/`weave`/`oath` have a dedicated test module. Behaviour is currently exercised only by indirect coverage in `test_cli_kernel.py`. As these grow into real implementations (F-001/2/4/5), they'll need direct tests. |
| Additive remediation | Add `tests/test_ritual_commands.py` covering the current scaffold-print behaviour, then expand the test as the real behaviour is implemented in PH-13/14. |
| Blast radius | tests-only |
| Target slice | PH-01 slice 1.4 (coverage hygiene) |

### F-014 — Three `pass` exception handlers are intentional but undocumented

| Field | Value |
|---|---|
| Tag | CONVENTION |
| Severity | info |
| Location | `mythic_vibe_cli/output.py:32-33`; `mythic_vibe_cli/runtime/event_log.py:145-146`; `mythic_vibe_cli/tui/runner.py:122-123` |
| Summary | Each of these is a deliberate "best-effort" path: rich import fallback, event-log persistence error, and child process teardown after exit. The plugin dispatcher already documents this with a `# noqa: BLE001 - ... is best-effort` comment. The other three sites should follow the same convention. |
| Additive remediation | Add `# noqa: BLE001 - <reason>` comments to the three sites for consistency. Tests unaffected. |
| Blast radius | trivial |
| Target slice | PH-01 slice 1.3 |

### F-015 — `cmd_workflow_run` error message references `--dry-run` only

| Field | Value |
|---|---|
| Tag | DOC_DRIFT |
| Severity | info |
| Location | `mythic_vibe_cli/commands.py:2780` |
| Summary | The error message tells the user to "Re-run with `--dry-run` to preview the role sequence." Once provider-backed forge lands (PH-03 slice 3.5), this message will be misleading. |
| Additive remediation | Update the message in slice 3.5 to point at the new `forge` command. No change today. |
| Blast radius | none today |
| Target slice | PH-03 slice 3.5 |

### F-016 — `mythic_data.py` and `method_excerpt.py` have no shared base type

| Field | Value |
|---|---|
| Tag | INTEGRATION_GAP |
| Severity | info |
| Location | `mythic_vibe_cli/mythic_data.py` (376 lines), `mythic_vibe_cli/method_excerpt.py` (120 lines) |
| Summary | These two modules both reason over the imported method corpus, but they don't share a typed model of "method section". Future work that needs to walk the corpus (Phase 5 retriever, Phase 13 drift detector) will have to choose between them. |
| Additive remediation | Add a `core/method.py` typed model that both modules can import, without changing either's external behaviour. |
| Blast radius | medium |
| Target slice | PH-05 slice 5.1 (schema design touches the method corpus) |

### F-017 — `cli.py` and `app.py` ownership boundary is implicit

| Field | Value |
|---|---|
| Tag | CONVENTION |
| Severity | info |
| Location | `mythic_vibe_cli/cli.py`, `mythic_vibe_cli/app.py` (712 lines) |
| Summary | `cli.py` is a thin router that delegates to `app.main()`. `app.py` carries 712 lines of argparse construction + command wiring. New contributors aren't told which file owns what. |
| Additive remediation | Add a one-paragraph header docstring to each file describing the ownership boundary. No code change. |
| Blast radius | none |
| Target slice | PH-01 slice 1.3 |

### F-018 — Untracked `research_data/vibe_research_part1_tier1a.md` lingers

| Field | Value |
|---|---|
| Tag | DOC_DRIFT |
| Severity | info |
| Location | repo root (untracked, present since before this audit) |
| Summary | The `git status` snapshot at task open recorded this file as untracked. The project status memory flags it as "obsolete Phase 1 partial". |
| Additive remediation | Either commit it as a research artefact under `research_data/` with a clear "obsolete partial" header, or add it to `.gitignore` if it should never be tracked. Decision needed from Volmarr. |
| Blast radius | none |
| Target slice | PH-01 slice 1.3 (decision-required — flag for human) |

### F-019 — `mythic_vibe_cli/runtime/event_log.py` cap is hardcoded

| Field | Value |
|---|---|
| Tag | INEFFICIENCY |
| Severity | info |
| Location | `mythic_vibe_cli/runtime/event_log.py:159` (cap of 200 entries baked in) |
| Summary | The 200-entry cap on the bounded event log is a literal, not a configurable. Larger projects with many plugin emits per minute may want a larger or smaller cap. |
| Additive remediation | Read `MYTHIC_EVENT_LOG_LIMIT` from env (default 200) the same way `MYTHIC_TIMING` is read. Falls back cleanly if unset. |
| Blast radius | trivial |
| Target slice | PH-01 slice 1.3 |

### F-020 — No structured-log layer separate from user-facing output

| Field | Value |
|---|---|
| Tag | INTEGRATION_GAP |
| Severity | warning |
| Location | repo-wide |
| Summary | All output goes through `output.py` (`write_line`, `write_error`, `write_json`). There is no machine-readable structured log of every command run with `run_id`, `duration_ms`, `result`, `artifacts_written`. The 2026 Roadmap specifically calls for this. |
| Additive remediation | Add `mythic_vibe_cli/runtime/structured_log.py` that writes one JSON line per command run to `~/.mythic-vibe/logs/` (cross-platform via `pathlib.Path.home()`). Wire it from `app.main()` after the existing timings primitive. |
| Blast radius | low |
| Target slice | PH-16 slice 16.4 (OpenTelemetry exporter) — the structured log is the prerequisite |

---

## Severity tally

| Severity | Count |
|---|---|
| blocked | 0 |
| error | 0 |
| warning | 6 (F-001, F-002, F-004, F-006, F-007, F-009, F-020 → recount: 7) |
| info | 13 |

Corrected: **0 errors, 7 warnings, 13 info**. Zero findings would block
a release today; the project is in healthy shape — the warnings
represent feature gaps rather than broken behaviour.

## Slice destination summary

| Phase | Slice | Findings landed there |
|---|---|---|
| PH-01 | 1.3 quick-fix sweep | F-006, F-007, F-010, F-014, F-017, F-018, F-019 |
| PH-01 | 1.4 coverage hygiene | F-013 |
| PH-02 | 2.6 plugin-contributed slash | F-008 |
| PH-03 | 3.5 provider-backed forge | F-003, F-015 |
| PH-03 | (forge agent owns it) | F-002 |
| PH-04 | 4.7 full keymap | F-008 |
| PH-05 | 5.1 schema design | F-016 |
| PH-08 | 8.4 verify subcommands | F-012 |
| PH-13 | 13.3 heal v2 / drift | F-001, F-005 |
| PH-14 | 14.1 constraint store | F-004 |
| PH-16 | 16.4 OTEL exporter prereq | F-020 |
| PH-18 | 18.1 Round 1 | F-009 |
| PH-18 | 18.3 Round 3 | F-011 |

## What this audit deliberately did not do

- It did not rewrite or delete any code.
- It did not run lint/type/test analysis beyond the baseline check
  (270 passed, ruff clean, mypy clean) recorded in the front-matter.
- It did not exhaustively enumerate every public function — the
  taxonomy is already large enough to drive Phase 1 slice 1.3 without
  a full call-graph dump.
- It did not survey dormant islands. Their status is governed by
  `REPO_BOUNDARY.md`; only PH-09 work touches them.

## Closing notes

The CLI is in a structurally sound state. The four "ritual" commands
(`prune`, `heal`, `weave`, `oath`) are the most visible gaps, but
each has a clear future home in the master roadmap rather than
needing emergency reshaping now. The TUI integration gap (F-008,
F-009) is the most architecturally interesting — the dispatcher
contract works, but the TUI surface hasn't grown to match yet.

Slice 1.2 (issue triage) and slice 1.3 (quick-fix sweep) follow this
audit. Slice 1.3 is the first slice in this roadmap that lands a code
change, and only on the trivial (info-severity, additive) findings:
F-006, F-007, F-010, F-014, F-017, F-018, F-019.
