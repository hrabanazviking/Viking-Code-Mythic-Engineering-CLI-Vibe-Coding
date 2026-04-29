# TASK — Wire Timings into `app.main()` Startup

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `a40fb39` — timings primitive port.

---

## Why this slice

The timings primitive is plumbing nobody calls. Wiring it into `app.main()` turns the env var `MYTHIC_TIMING=1` into a real profiling switch — operators can diagnose slow startup or slow commands without code changes.

## Goal

Add four timing calls to `app.main()`:

1. `reset_timings()` at the very top — clears prior state, baselines the clock
2. `record("argparse")` after `build_parser()` + `parse_args()`
3. `record("configure_output")` after the first `configure_output()` call
4. `record(f"handler:{args.command}")` after the handler returns
5. `print_timings()` in a `finally` block so it fires on success, on exception, and on `SystemExit` (e.g., from argparse `--help`)

When the env var is unset, every call is a no-op and the function behaves exactly as before.

## Out of scope

- Sprinkling timings into individual commands (single-emitter scope)
- Changing the timings public API
- Wiring timings into long-running paths (workflow run is still always-blocked)

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/app.py` | Add timing calls; restructure with try/finally |
| `tests/test_cli_kernel.py` | Add 2 integration tests (env on prints; env off silent) |
| `docs/plugins.md` (or `docs/api.md`) | Add a short note about the env var |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New 2026-04-29 entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Wire timings into `app.main()` with try/finally
- [ ] Integration tests (env on / env off)
- [ ] `pytest -q` green
- [ ] `ruff` + `mypy` green
- [ ] Doc note about MYTHIC_TIMING
- [ ] CHANGELOG entry
- [ ] DEVLOG entry
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. The `print_timings()` call must be in `finally` so it fires on `SystemExit` (argparse `--help` raises this).
3. Use `record(f"handler:{args.command}")` so the label includes the command name.
4. The env-var-off path must NOT add any user-visible output — `print_timings()` is itself a no-op when the env var is unset.
