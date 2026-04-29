# TASK — Wire `exec_command` into Existing Subprocess Call Sites

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `0ee8291` — exec primitive port.

---

## Why this slice

The exec primitive landed yesterday with full tests but no consumers. Four `subprocess.run` callers exist in the codebase today. Migrating them gives:

1. Uniform result shape (`ExecResult`) across the codebase
2. Graceful missing-binary handling (`code=127` instead of unhandled `FileNotFoundError`)
3. A foundation for future timeout / cancel-event wiring without per-site refactor

This is a wiring slice — no new plunder, no new tests for the primitive itself. Behavior at the call-site level is preserved.

## Migration sites

| File | Helper | Migration |
|---|---|---|
| `mythic_vibe_cli/verify/test_runner.py` | `run_command` | `subprocess.run` → `exec_command`; map `.returncode` → `.code` into `CommandResult` |
| `mythic_vibe_cli/verify/git_diff.py` | `_git` | Return `ExecResult`; update 2 callers (`returncode` → `code`) |
| `mythic_vibe_cli/handoff.py` | `_git` | Return `ExecResult`; update all internal callers (`returncode` → `code`) |
| `mythic_vibe_cli/context/scanner.py` | `_run_git` | Replace `try / except (OSError, CalledProcessError)` with `if result.code != 0: return None` |

## Behavior preservation

- `test_runner.py`: `CommandResult` shape is unchanged; only the inner type swaps.
- `git_diff.py`: `_git` is a private helper; callers in same file get rewritten; external callers unaffected.
- `handoff.py`: same — `_git` is private to the module.
- `scanner.py`: `_run_git` is private; the failure path now triggers via `code != 0` instead of exception, but the externally observable return (`None`) is identical. Missing-`git` case remains `None` (was `FileNotFoundError` → caught → `None`; now `code=127` → `None`). Net behavior unchanged.

## Side benefits

- `verify/test_runner.py` and the others used to raise `FileNotFoundError` if `git` or `pytest` were missing on the host. After migration, they return `code=127` cleanly. For `verify/test_runner.py` this means a missing `pytest` becomes a verification *failure* (graceful) instead of an unhandled exception (crash).
- The `subprocess` import becomes unused in `verify/git_diff.py`, `handoff.py`, and `verify/test_runner.py` — removing those imports tightens the dependency surface.

## Out of scope

- Adding `timeout` or `cancel_event` arguments to any wired call site (separate slice if/when callers want them)
- Migrating subprocess invocations in tests (test code can stay on stdlib)
- Refactoring the `_git` helpers to share a common implementation across `git_diff.py` / `handoff.py` / `scanner.py` (separate slice if it becomes a maintenance pain)

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/verify/test_runner.py` | Replace `subprocess.run`; remove unused import |
| `mythic_vibe_cli/verify/git_diff.py` | Replace `subprocess.run`; update `.returncode` → `.code` callers; remove unused import |
| `mythic_vibe_cli/handoff.py` | Same pattern |
| `mythic_vibe_cli/context/scanner.py` | Replace `subprocess.run`; rewrite error path; remove unused imports |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Migrate `verify/test_runner.py`
- [ ] Migrate `verify/git_diff.py`
- [ ] Migrate `handoff.py`
- [ ] Migrate `context/scanner.py`
- [ ] `pytest -q` green
- [ ] `ruff` + `mypy` green
- [ ] CHANGELOG entry
- [ ] DEVLOG entry
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. Migrate one site at a time, run tests between sites.
3. The `subprocess` import becomes unused in three of four files — remove cleanly so ruff stays green.
4. Behavior preservation is the contract — no test should change as a result of this slice.
