# TASK — Pi Plunder Slice 2: Output Guard (Stdout Cleanliness)

**Opened:** 2026-04-29
**Owner:** Runa
**TODO source:** Item #15 — second plunder slice from Pi.
**Plundering guide:** `Pi_Coding_Agent_Plundering_Guide.md`
**Predecessor slice:** `549c8a1` — file-mutation-queue (established the legal pattern)

---

## Why this primitive next

From the Pi guide section 6.9:

> *"A guard that protects stdout cleanliness — important because pi runs in modes where stdout is the protocol surface (print/JSON, RPC). The dedicated `stdout-cleanliness.test.ts` enforces it. Mythic already has output policies (`output.py`); this guard pattern is worth borrowing before any provider call can pollute stdout."*

Mythic already has `--json` flags on many commands and a documented contract that JSON output must be machine-parseable. Right now nothing prevents accidental `print()` calls (or noisy library imports) from corrupting that JSON surface. The guard makes pollution structurally impossible: any non-protocol writer routes to stderr automatically.

Like the file-mutation-queue, this primitive is plumbing first — it stays unused by `cmd_*` until a follow-on slice wires it into JSON-mode entry points. Landing it now means the safety primitive is ready when V2 Phase 4 (provider execution) or any RPC mode arrives.

## Goal

Land:

1. `mythic_vibe_cli/runtime/output_guard.py` — Python port of pi's `src/core/output-guard.ts`
2. Update `mythic_vibe_cli/runtime/__init__.py` to re-export the public surface
3. `tests/test_output_guard.py` — unit tests on the primitive (subprocess integration test deferred)
4. Append a row to the plunder map in `THIRD_PARTY_NOTICES.md`
5. Per-file Pi attribution header on the new module
6. CHANGELOG Unreleased entry
7. DEVLOG entry with continuity thread

## Public surface (Python translation)

| pi (TS) | mythic (Py) | Notes |
|---|---|---|
| `takeOverStdout()` | `take_over_stdout()` | Replaces `sys.stdout` with a stderr-routing proxy; idempotent if already taken over |
| `restoreStdout()` | `restore_stdout()` | Restores the original `sys.stdout`; no-op if not taken over |
| `isStdoutTakenOver()` | `is_stdout_taken_over()` | Returns the current state |
| `writeRawStdout(text)` | `write_raw_stdout(text)` | Always writes to the real stdout (bypassing the takeover) |
| `flushRawStdout()` | `flush_raw_stdout()` | Sync flush of the real stdout |

The async `flushRawStdout()` becomes a sync `flush_raw_stdout()` because Python file flush is sync and we have no asyncio elsewhere in the codebase.

## Out of scope

- Wiring the guard into `--json` entry points or RPC mode — follow-on slice
- A subprocess integration test à la pi's `stdout-cleanliness.test.ts` — needs the wiring above to be meaningful
- Any changes to `output.py` — the guard is a complement, not a replacement

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/runtime/output_guard.py` | NEW (Python port + Pi attribution header) |
| `mythic_vibe_cli/runtime/__init__.py` | Re-export new public surface |
| `tests/test_output_guard.py` | NEW (unit tests on the primitive) |
| `THIRD_PARTY_NOTICES.md` | Append plunder map row |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New 2026-04-29 entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [x] Port output_guard to Python (sys.stdout proxy + module-level state)
- [x] Update runtime __init__ re-exports
- [x] Port tests (10 unit tests; subprocess integration deferred per task spec)
- [x] `pytest -q` green — 151 passed, 14 subtests passed
- [x] `ruff check mythic_vibe_cli tests` green
- [x] `mypy mythic_vibe_cli` green — 55 source files
- [x] Update THIRD_PARTY_NOTICES plunder map
- [x] Per-file Pi attribution header
- [x] CHANGELOG entry
- [x] DEVLOG entry with continuity thread
- [x] Memory snapshot updated
- [x] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. Port `output_guard.py` mirroring pi's API but using `sys.stdout` reassignment.
3. The takeover proxy should be a small class with `write()` and `flush()` that delegate to `sys.__stderr__` (the original stderr) so that even if `sys.stderr` is also reassigned later, the route stays correct.
4. The `_state` module-level slot mirrors pi's `stdoutTakeoverState` — keep both `original_stdout` and a callable for raw stdout writes.
5. Tests should verify: takeover routes stdout to stderr, restore reinstates stdout, write_raw_stdout always writes to the real stdout regardless of takeover state, idempotent takeover, no-op restore when not taken over.
