# TASK — Pi Plunder Slice 4: Timings Primitive

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor slices:** `549c8a1` (file-mutation-queue), `0ae9d54` (output-guard), `0acf784` (event-bus), `c150359` (wiring), `0c5a9bb` (plugin docs).

---

## Why this primitive next

The runtime subpackage holds three Pi-derived primitives so far. `timings.ts` is a tiny single-file utility for elapsed-time instrumentation — useful for startup profiling, slow-command diagnosis, and anywhere you want to know where the CLI spent its milliseconds. Single file, clear contract, mechanical port.

## Goal

Land:

1. `mythic_vibe_cli/runtime/timings.py` — Python port of pi's `src/core/timings.ts`
2. Update `mythic_vibe_cli/runtime/__init__.py` to re-export the public surface
3. `tests/test_timings.py` — unit tests covering enabled/disabled/reset/format paths
4. Plunder map row in `THIRD_PARTY_NOTICES.md`
5. Per-file Pi attribution header on the new module
6. CHANGELOG Unreleased entry
7. DEVLOG entry with continuity thread

## Public surface (Python translation)

| pi (TS) | mythic (Py) | Notes |
|---|---|---|
| `process.env.PI_TIMING === "1"` constant | `_is_enabled()` lazy reader of `MYTHIC_TIMING` env var | Lazy read keeps tests clean (no module reloading) |
| `resetTimings()` | `reset_timings()` | Clears the in-memory list, resets the elapsed baseline |
| `time(label)` | `record(label)` | Renamed to avoid shadowing the `time` stdlib module in callers |
| `printTimings()` | `print_timings()` | Prints to stderr, totals at the bottom |
| `Date.now()` (ms precision) | `time.perf_counter()` (sub-ms precision; output rounded to ms) | Better resolution; same output format |

Env var: `MYTHIC_TIMING` accepts `1`, `true`, `yes`, `on` (matches the existing `_parse_bool_env` pattern in `config.py`). Default disabled.

## Out of scope

- Wiring `record(...)` into existing CLI startup paths (separate slice if useful)
- Async / threaded timing
- Persistent timing logs (the primitive is in-memory only)
- Histograms or aggregate stats — pi's primitive just records labelled deltas

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/runtime/timings.py` | NEW (Python port + Pi attribution header) |
| `mythic_vibe_cli/runtime/__init__.py` | Re-export `reset_timings`, `record`, `print_timings` |
| `tests/test_timings.py` | NEW (no upstream unit-test analog) |
| `THIRD_PARTY_NOTICES.md` | Append plunder map row |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New 2026-04-29 entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Port `timings.py`
- [ ] Update `runtime/__init__.py` re-exports
- [ ] Write tests (enabled/disabled/reset/format)
- [ ] `pytest -q` green
- [ ] `ruff` + `mypy` green
- [ ] Plunder map row added
- [ ] Per-file Pi attribution header
- [ ] CHANGELOG entry
- [ ] DEVLOG entry
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. Use lazy env-var read (`_is_enabled()` function) instead of module-level constant — tests stay clean.
3. Use `time.perf_counter()` for the clock; format output in milliseconds rounded to one or two decimals.
4. Output goes to `sys.stderr` (matching pi's `console.error`).
5. The primitive is plumbing only in this slice — wiring into CLI startup paths is a separate decision.
