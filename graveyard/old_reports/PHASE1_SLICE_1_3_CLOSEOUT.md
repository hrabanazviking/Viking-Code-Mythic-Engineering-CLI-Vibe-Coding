---
title: "Phase 1 — Slice 1.3 Close-out (Quick-Fix Sweep)"
phase: PH-01
slice: 1.3
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 25b177e
head_at_close: 74ffa45
test_baseline_open: 270 + 14 subtests
test_baseline_close: 276 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
---

# Phase 1 Slice 1.3 — Quick-Fix Sweep Close-Out

## Purpose

First code-changing slice of the master roadmap. Apply only the
*additive*, *zero-risk* fixes from `PHASE1_RUNTIME_AUDIT.md` — the
seven info-severity findings flagged for slice 1.3.

Every fix is its own commit. Tests stay green at every step. No
restructuring, no refactors, no scope creep.

## Findings closed (7/7)

### F-006 / F-007 — Silent dispatch fall-through

| Field | Value |
|---|---|
| Commit | `f9c8f38` |
| Files | `mythic_vibe_cli/commands.py`, `tests/test_cli_kernel.py` |
| Tests added | 2 (`test_slash_dispatch_unknown_subcommand_emits_error`, `test_ai_dispatch_unknown_subcommand_emits_error`) |
| Behaviour change | Unknown subcommand now writes a clear error to stderr before returning `USER_INPUT_ERROR (2)`. |
| Note | Argparse currently blocks unknown subcommands at parse time (both subparsers use `required=True` with `choices`), so the fall-through is unreachable via normal CLI invocation. The fix matters for direct programmatic dispatch (REPL, plugins, future tests) and as a regression guard if argparse constraints are ever loosened. |

### F-010 — Silent JSON sidecar parse failure

| Field | Value |
|---|---|
| Commit | `816efbb` |
| Files | `mythic_vibe_cli/codex_bridge.py`, `tests/test_cli_kernel.py` |
| Tests added | 1 (`test_packet_ingest_malformed_sidecar_emits_verbose_warning`) |
| Behaviour change | `PacketBuilder._read_ingest_source` now writes a one-line `write_verbose` warning when a `.json` sidecar fails to parse. Default behaviour unchanged when verbose mode is off. |

### F-014 — Annotate deliberate best-effort pass sites

| Field | Value |
|---|---|
| Commit | `b6e22c3` |
| Files | `mythic_vibe_cli/output.py`, `mythic_vibe_cli/runtime/event_log.py`, `mythic_vibe_cli/tui/runner.py` |
| Tests added | 0 (annotation only) |
| Behaviour change | None. Three sites that swallow exceptions deliberately now carry inline comments — `# noqa: BLE001 - rich import/render is best-effort` on the only true blind-Exception site, and intent-explaining comments on the two `OSError` sites. |
| Audit precision | The original audit summary called all three sites "BLE001 candidates"; only `output.py:32` actually is. Closeout records this for future reference. |

### F-017 — Ownership-boundary docstrings

| Field | Value |
|---|---|
| Commit | `30c9964` |
| Files | `mythic_vibe_cli/cli.py`, `mythic_vibe_cli/app.py` |
| Tests added | 0 (documentation only) |
| Behaviour change | None. Module-level docstrings now spell out the implicit boundary that new contributors had to reverse-engineer: `cli.py` is a stable thin shim (no logic, no imports beyond `app` re-exports), `app.py` owns the full argparse surface and dispatch routing. |

### F-018 — Untracked obsolete research partial

| Field | Value |
|---|---|
| Commit | `7d0a455` |
| Files | `.gitignore` |
| Tests added | 0 (config only) |
| Behaviour change | `research_data/vibe_research_part1_tier1a.md` no longer surfaces as untracked. The file is preserved on disk; a single `.gitignore` line removal undoes the rule. Inline comment in `.gitignore` cross-references this audit. |

### F-019 — `MYTHIC_EVENT_LOG_LIMIT` env-var override

| Field | Value |
|---|---|
| Commit | `74ffa45` |
| Files | `mythic_vibe_cli/runtime/event_log.py`, `mythic_vibe_cli/runtime/__init__.py`, `mythic_vibe_cli/plugins/dispatcher.py`, `tests/test_event_log.py` |
| Tests added | 3 (`test_resolve_max_entries_default_when_env_unset`, `test_resolve_max_entries_honors_positive_env_override`, `test_resolve_max_entries_ignores_invalid_values`) |
| Behaviour change | The 200-entry event-log cap is now configurable via `MYTHIC_EVENT_LOG_LIMIT`. Same pattern as `MYTHIC_TIMING`: positive integer overrides default; non-int / zero / negative / unset all fall back to 200 silently. |
| Public surface | `resolve_max_entries()` and `EVENT_LOG_LIMIT_ENV` are now re-exported from `mythic_vibe_cli.runtime`. |

## Test deltas

| Phase | Tests | Subtests |
|---|---|---|
| Slice 1.3 open (HEAD `25b177e`) | 270 | 14 |
| After F-006/F-007 | 272 | 14 |
| After F-010 | 273 | 14 |
| After F-014 | 273 | 14 |
| After F-017 | 273 | 14 |
| After F-018 | 273 | 14 |
| After F-019 | **276** | 14 |

Net: **+6 tests, 0 regressions, 0 lint warnings, 0 type errors.**

## Commits in slice 1.3

```text
74ffa45 slice 1.3 F-019: MYTHIC_EVENT_LOG_LIMIT env-var override
7d0a455 slice 1.3 F-018: gitignore the obsolete Phase 1 research partial
30c9964 slice 1.3 F-017: ownership-boundary docstrings on cli.py and app.py
b6e22c3 slice 1.3 F-014: annotate three deliberate best-effort pass sites
816efbb slice 1.3 F-010: verbose log on malformed packet sidecar
f9c8f38 slice 1.3 F-006/F-007: error messages on unknown slash/ai subcommands
```

## What this slice deliberately did not do

- Did not touch any warning-severity finding (F-001/2/4/5/9/20). Those
  have phase homes in PH-03/13/14/16/18 and need real implementation,
  not quick-fixes.
- Did not refactor any module structure. The audit's CONVENTION-tagged
  `__all__`-coverage gap (F-011) waits for PH-18 round 3.
- Did not add CLI commands. Slice 1.3 is hygiene; new surfaces wait
  for PH-02 onwards.
- Did not run `pytest --cov` (slice 1.4 owns coverage hygiene).

## Slice 1.3 close

All seven findings closed. Test suite green at 276; ruff and mypy
clean. The audit-found list is now empty for info-severity items.

## Next slice

**Slice 1.4 — coverage hygiene.** Run `pytest --cov=mythic_vibe_cli`,
identify untested public surface, add tests only (no behavioural
changes). Target ≥ 85% line coverage on the active runtime, exclusive
of the TUI (which has its own headless test surface and shouldn't
inflate the metric).
