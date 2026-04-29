# TASK — Pi Plunder Slice 7: Exec Subprocess Primitive

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `06ded12` — runtime operator guide.

---

## Why this primitive next

The runtime subpackage holds six primitives — four wired, two foundation. Tools, custom command runners, and any future provider/agent paths will need to spawn subprocesses. Pi's `core/exec.ts` is a clean 2.4KB wrapper around `child_process.spawn` with timeout, abort signal, and a graceful SIGTERM → SIGKILL fallback. Porting it gives Mythic a uniform subprocess primitive instead of letting `subprocess.run(...)` calls scatter across the codebase with inconsistent timeout / kill / capture conventions.

## Goal

Land:

1. `mythic_vibe_cli/runtime/exec.py` — Python port of pi's `core/exec.ts`
2. Update `mythic_vibe_cli/runtime/__init__.py` re-exports
3. `tests/test_exec.py` — unit tests covering happy path, exit code, stderr capture, timeout kill, cancel event kill, missing command
4. Update `docs/runtime.md` to add a §11 for the primitive (keep §12 = "See also")
5. Plunder map row in `THIRD_PARTY_NOTICES.md`
6. Per-file Pi attribution header on the new module
7. CHANGELOG Unreleased entry
8. DEVLOG entry

## Public surface (Python translation)

| pi (TS) | mythic (Py) | Notes |
|---|---|---|
| `ExecOptions` interface | keyword-only args on `exec_command` | `timeout`, `cwd`, `cancel_event` |
| `ExecResult` interface | `ExecResult` frozen dataclass | `stdout`, `stderr`, `code`, `killed` |
| `execCommand(command, args, cwd, options)` | `exec_command(command, args, cwd, *, timeout, cancel_event)` | snake_case rename |
| `AbortSignal` | `threading.Event` | Python's natural async-cancellation primitive in a sync codebase |
| Pi's `waitForChildProcess` Node-stdio quirk handler | not needed | Python's `subprocess.Popen.communicate()` handles this natively |

## Out of scope

- Async wrapper (codebase is sync)
- Stream-based stdout/stderr (full capture only, matching pi)
- Shell-execution mode (pi explicitly disables `shell: true`; we keep `shell=False`)
- Wiring the primitive into existing call sites (separate slice when a consumer arrives)

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/runtime/exec.py` | NEW (port + Pi attribution header) |
| `mythic_vibe_cli/runtime/__init__.py` | Re-export `ExecResult`, `exec_command` |
| `tests/test_exec.py` | NEW |
| `docs/runtime.md` | Add §11 covering exec; renumber See also to §12 |
| `THIRD_PARTY_NOTICES.md` | Append plunder map rows (production + test) |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Port `exec.py` (Popen + Timer for timeout + threading.Event watcher for cancel)
- [ ] Re-export from `runtime/__init__.py`
- [ ] Write tests (happy path, non-zero exit, stderr capture, timeout kill, cancel event, missing command)
- [ ] `pytest -q` green
- [ ] `ruff` + `mypy` green
- [ ] Add §11 to `docs/runtime.md`
- [ ] Plunder map rows added
- [ ] Per-file Pi attribution header
- [ ] CHANGELOG entry
- [ ] DEVLOG entry
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. Use `subprocess.Popen` (not `subprocess.run`) so the cancel-event watcher thread can kill the process while it's running.
3. Match pi's SIGTERM → SIGKILL fallback: `proc.terminate()` then `proc.wait(timeout=5.0)` then `proc.kill()`.
4. Tests should use `sys.executable -c "..."` for cross-platform commands rather than `echo` / `sleep` shell builtins.
5. Don't catch exceptions other than `subprocess.TimeoutExpired` and `FileNotFoundError`; let them propagate so callers see real bugs.
