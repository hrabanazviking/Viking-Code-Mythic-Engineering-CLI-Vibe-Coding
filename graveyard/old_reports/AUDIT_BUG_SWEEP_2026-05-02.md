# Mythic Vibe CLI — Pre-PH-19 Bug Sweep
Date: 2026-05-02
HEAD swept: ba3e1aa
Auditor: Sólrún Hvítmynd
Scope: Full production codebase — `mythic_vibe_cli/` (138 source files, 135 inspected directly)
Environment: Python 3.x, Windows 11, branch `development`

---

## Verdict

The codebase is **functionally sound at its tested paths**. Mypy passes clean (0 errors, 138 files), ruff passes clean, and the test suite holds at 1875 passed / 1 skipped — baseline confirmed. No data-corruption-level bugs were found in the primary persistence layer (`json_store.py`). The findings are concentrated in three clusters: (1) missing upper bounds on I/O that enables DoS conditions, (2) a logic error in the Telegram backoff that causes persistent spin on `ok=false` states, and (3) untimed subprocesses on multiple call-paths that can hang the CLI indefinitely. No cryptographic weaknesses, no secrets in logs, no shell injection vectors, no unsafe deserialization. Distribution is safe to begin under PH-19 with the High findings resolved first.

---

## Severity Summary

| Severity | Count | Category |
|---|---|---|
| High    | 3 | DoS via unbounded I/O; MCP readline hang; subprocess timeouts |
| Medium  | 3 | Telegram backoff spin; forge_ledger non-atomic write; cross-process ledger race |
| Low     | 4 | Dead `"succeeded"` sentinel; dead `narrow_layout` export; test weakness; `test_elapsed_ms_recorded` fragility |

---

## Findings

### Category 1 — Crash-Prone / Hang Code Paths

---

**[HIGH] web_terminal.py:267 — Unbounded `rfile.read(length)` enables memory exhaustion / thread starvation**

File: `mythic_vibe_cli/surfaces/web_terminal.py`, line 256–275, function `_read_json_body`

```python
length = int(length_header)   # no upper-bound check
# ...
raw = self.rfile.read(length).decode("utf-8")   # reads entire client-declared length into RAM
```

A caller (or attacker who can reach the port) sends:
```
POST /api/run HTTP/1.1
Content-Length: 1073741824
```

`ThreadingHTTPServer` spawns a thread per connection. Each thread blocks in `rfile.read(1073741824)`, either consuming 1 GiB of RAM or blocking indefinitely waiting for bytes that never arrive. The server has no per-connection timeout either. A handful of such requests exhaust all threads.

Default bind is loopback (`127.0.0.1`), which limits exposure to local processes. Exposure becomes real with `--bind 0.0.0.0`.

**Recommendation:** Add a `MAX_REQUEST_BODY = 65_536` constant and reject `length > MAX_REQUEST_BODY` with HTTP 413 before calling `read`. Add a `ThreadingHTTPServer` socket timeout (`self.httpd.socket.settimeout(30.0)`).

---

**[HIGH] protocols/mcp_client.py:112 — Unbounded `while True` loop + blocking `readline()` with no timeout**

File: `mythic_vibe_cli/protocols/mcp_client.py`, lines 80–123, method `call`

```python
def _read_one(self) -> JsonRpcMessage:
    with self._read_lock:
        raw = self.stdout.readline()   # no read timeout
    # ...

def call(self, method, ...):
    # ...
    while True:
        response = self._read_one()
        if response.get("id") != request_id:
            continue   # loops on notification spam indefinitely
```

Two distinct hang vectors:
1. `readline()` on a subprocess stdout pipe blocks forever if the MCP server stalls without closing its stdout.
2. The `while True` loop discards messages with non-matching `id`. An MCP server that sends an unbounded stream of notifications will spin the calling thread forever.

No tests exercise these paths. Coverage report shows `mcp_client.py` call-path lines are untested in the real-subprocess case.

**Recommendation:** Add a `max_discard` counter (e.g. 1000 iterations) to the `while True` loop and raise `McpClientError` on excess. For `readline()` timeout: switch to `proc.communicate(timeout=N)` pattern or set the pipe to non-blocking with a threading timeout wrapper.

---

**[HIGH] All `exec_command` call-sites pass no `timeout` — subprocess can hang CLI indefinitely**

Files:
- `mythic_vibe_cli/context/scanner.py:377`
- `mythic_vibe_cli/handoff.py:89`
- `mythic_vibe_cli/verify/git_diff.py:25`
- `mythic_vibe_cli/verify/test_runner.py:56`

```python
# Every call site:
result = exec_command("git", ["-C", str(root), *args], cwd=root)
# timeout= parameter is never passed; defaults to None → no timeout.
```

`exec_command` in `runtime/exec.py` documents `timeout: float | None = None` and explicitly handles it — but all four callers omit it. A slow or hung git process (e.g., waiting for SSH passphrase on a misconfigured remote, or an NFS-mounted repo) will block the CLI thread with no escape except Ctrl-C.

`test_runner.py:56` is especially exposed: it runs the user's full pytest suite with no timeout.

**Recommendation:** Set sensible defaults per call-site — e.g. 30s for git commands in `scanner.py`, `handoff.py`, `git_diff.py`; expose `--timeout` on `mythic-vibe test` for `test_runner.py`.

---

### Category 2 — Race Conditions / Concurrency

---

**[MEDIUM] forge_ledger.py:281 — Non-atomic write; process-kill mid-write produces corrupt ledger**

File: `mythic_vibe_cli/forge_ledger.py`, line 281, `_write_entries`

```python
target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
```

`json_store.py` (the status store) writes atomically: it creates a `.tmp` file, populates it, then calls `os.replace(tmp, target)`. The forge ledger does not. If the process is killed between the OS truncating the file and finishing the write, the ledger is left with partial JSON — unrecoverable without restoring from a backup.

The `load()` method handles this defensively (returns `[]` on JSON error), so a corrupt ledger does not crash the CLI. But it silently discards all ledger history.

**Recommendation:** Adopt the same write-to-tmp-then-replace pattern used in `json_store.py`. Three lines of change.

---

**[MEDIUM] forge_ledger.py — `file_mutation_queue` serializes within-process only; cross-process ledger writes race**

File: `mythic_vibe_cli/forge_ledger.py` docstring (line 25–27) + `runtime/file_mutation_queue.py`

The docstring claims:
> "Concurrent writes to the same ledger file are serialised through `file_mutation_queue` so two simultaneous forge runs cannot corrupt each other's writes."

`file_mutation_queue` uses `threading.Lock` — it serializes threads **within one Python process**. Two separate `mythic-vibe forge` invocations (two separate processes) do not share the lock and can interleave their read-load-rewrite cycles, resulting in the later writer silently overwriting the earlier writer's entries.

Evidence: `runtime/file_mutation_queue.py:38` — `_locks: dict[str, _QueueEntry] = {}` is process-local. No cross-process IPC mechanism exists.

**Recommendation:** Replace `file_mutation_queue` in the ledger append path with the `FileLock` (`os.O_CREAT|O_EXCL`) primitive already present in `json_store.py`, which works cross-process. Or document the limitation explicitly and accept it.

---

### Category 3 — Logic Errors

---

**[MEDIUM] chat_bridge_loop.py:406–410 — Telegram `ok=false` backoff reset: persistent failures spin at base delay forever**

File: `mythic_vibe_cli/surfaces/chat_bridge_loop.py`, lines 406–411, function `run_telegram_loop`

```python
bo.reset()                          # line 406: always resets attempt counter on any successful HTTP response
if not payload.get("ok", True):     # line 407: ok=false check follows the reset
    _log("telegram", f"getUpdates returned ok=false: {payload!r}")
    clock_sleep(bo.next_delay())    # line 410: bo.attempt was just reset to 0 → always returns base=1.0s
    continue
```

When `getUpdates` HTTP succeeds (200 OK) but returns `{"ok": false}`, `bo.reset()` zeroes the attempt counter before `next_delay()` is called. Every iteration with `ok=false` thus produces the same 1.0s wait regardless of how many consecutive failures have occurred. Exponential backoff never accumulates for this failure mode.

The test `test_ok_false_triggers_backoff_continue` (test_chat_bridge_loop.py:572) only asserts `len(sleeps) >= 1`, which passes even with the bug. The test does not verify the wait is increasing.

**Recommendation:** Move `bo.reset()` to after the `ok=false` guard, or handle `ok=false` as a separate `_Backoff` instance that is not reset on HTTP-level success.

---

### Category 4 — Dead / Misleading Code

---

**[LOW] forge_verifier.py:173 — `"succeeded"` is a dead sentinel; the verify layer never writes this value**

File: `mythic_vibe_cli/forge_verifier.py`, line 173

```python
if result_value not in {"pass", "succeeded"}:
```

`VerificationArtifact.result` (verified in `verify/__init__.py:20`) takes only `"pass"`, `"fail"`, or `"blocked"`. The string `"succeeded"` is never assigned anywhere in the production codebase (grep of `result.*=.*"succ"` returns no hits in `mythic_vibe_cli/`). The branch is dead code that will never match.

The functional impact is zero (the gate correctly accepts `"pass"`), but the dead arm misleads readers about valid result vocabulary.

**Recommendation:** Remove `"succeeded"` from the set, or if it was intended for future use, document that intention.

---

**[LOW] surfaces/narrow_layout.py:75 — `should_use_narrow_layout` exported in `__all__` but never imported by production code**

File: `mythic_vibe_cli/surfaces/narrow_layout.py`, line 75 (`__all__`)

`grep -rn "should_use_narrow_layout" mythic_vibe_cli/ --include="*.py"` returns only matches within `narrow_layout.py` itself and `surfaces/__init__.py` documentation. No command, TUI component, or other module imports it. The function is tested but its production integration point is absent.

**Recommendation:** Either wire it into the TUI startup path (its stated purpose) or note in a comment that integration is deferred to PH-19/PH-22.

---

**[LOW] test_plugin_sandbox.py:96 — `test_elapsed_ms_recorded` uses machine-speed-dependent threshold**

File: `tests/test_plugin_sandbox.py`, line 96

```python
result = safe_call(time.sleep, 0.01)
self.assertGreaterEqual(result.elapsed_ms, 5.0)
```

`sleep(0.01)` = 10ms expected. Asserts `>= 5.0ms`. On Windows with coarse timer resolution (~15ms granularity), a 10ms sleep may measure as 0ms or 15ms depending on when it fires. The assertion would survive the latter but theoretically could fail if the timer granularity rounds down and the implementation returns 0. Previously noted as a flake candidate in the MEMORY.md.

**Recommendation:** Lower threshold to `>= 0.0` and add a separate test for the "elapsed is plausible" case, or mock the clock.

---

**[LOW] Multiple `write_text()` calls on artifact files are non-atomic**

Files (representative sample):
- `mythic_vibe_cli/verify/__init__.py:81,83` — verification artifacts + `latest.json`
- `mythic_vibe_cli/handoff.py:260–263` — handoff records
- `mythic_vibe_cli/forge_reflection.py:386,388` — reflection artifacts

These use `Path.write_text()` directly — not write-to-tmp + `os.replace`. A process kill during write leaves the file truncated. None of these files are read by the primary state machine (they are observational artifacts), so the impact is data loss of a single artifact rather than corruption of project state. Acceptable at current maturity level but worth upgrading before v1.0.

**Recommendation:** Add a `_atomic_write(path, text)` helper (3 lines: mkstemp + write + os.replace) and route artifact writes through it in PH-19/20.

---

## Security Audit — No Blockers Found

- **Token comparison** (`secrets.compare_digest`): confirmed at `web_terminal.py:301`. Timing-safe. ✓
- **Shell injection**: no `shell=True` in production code. All subprocess calls pass argv as lists. ✓
- **Pickle / eval / exec**: not present in production paths. ✓
- **Secret logging**: `HTTPError.__repr__` (confirmed via source inspection) emits only code+msg, not URL. `URLError` repr does not embed the request URL. Telegram bot token appears in the URL at construction (line 295) but is not logged — only the exception repr is logged, which is safe. ✓
- **Path traversal**: `cmd_plunder_plan` resolves relative `dest` under `root`. `cmd_packet_ingest` accepts arbitrary `source` path — acceptable for a CLI where the operator controls the shell. ✓
- **Token in stdout**: web terminal prints its auth token to stdout intentionally (operator needs it). This is correct behavior but should be documented as a risk in CI environments. ✓
- **CORS/CSP on web terminal**: no CORS headers, no `Content-Security-Policy`. Low risk at loopback-only default. Should add headers before exposing externally. Noted, not a blocker.
- **Allowlist bypass in chat bridge**: `validate()` refuses to start without an explicit allowlist. `"*"` is the only broadcast sentinel. Room/chat/user checks are layered. No bypass path found. ✓

---

## Test / Lint / Mypy Baseline at Sweep Time

| Tool | Command | Result |
|---|---|---|
| pytest | `python -m pytest tests/ -q --tb=no` | **1875 passed, 1 skipped** in 93.06s |
| ruff | `python -m ruff check mythic_vibe_cli/ tests/` | **All checks passed** |
| mypy | `python -m mypy mythic_vibe_cli/ --ignore-missing-imports` | **Success: no issues found in 138 source files** |

Coverage for high-risk modules (from `--cov` run):

| Module | Coverage |
|---|---|
| `commands.py` | 68% |
| `forge.py` | 71% |
| `surfaces/chat_bridge_loop.py` | 79% |
| `surfaces/web_terminal.py` | 78% |
| `runtime/exec.py` | 88% |
| `persistence/json_store.py` | 81% |
| `policy/policy_gate.py` | 95% |
| `persistence/migrations.py` | 91% |
| TOTAL | 82% |

The 68% on `commands.py` is the dominant gap. The missing lines are concentrated in error paths, edge branches in less-frequently-used commands, and the chat bridge / voice paths. None of the uncovered branches appear to contain the bug classes described above — the bugs found were in covered code.

---

## Recommendations for Plan Integration

### Should block PH-19 kickoff

**None are strict blockers** if PH-19 distribution work is package-only (PyPI/Homebrew/Scoop). However, the following should be resolved before the v1.0 tag:

1. **[HIGH] web_terminal.py body size limit** — Any `--bind 0.0.0.0` usage or SSH tunnel will expose this DoS vector. Recommend folding into **PH-19.5 (Hardening)** or a new PH-19.6 slice "Security Hardening."
2. **[HIGH] exec_command timeouts** — Affects all git-calling paths and the test runner. Recommend folding into **PH-19.5 (Hardening)**.
3. **[HIGH] mcp_client.py hang** — Affects `mythic-vibe protocols mcp` path. Recommend folding into **PH-19.5** or deferring to PH-22 if MCP is not a v1.0 user-facing feature.

### Should fold into PH-19/PH-20 existing slices

4. **[MEDIUM] Telegram ok=false backoff bug** — Simple 2-line fix. Add to **PH-19.5 (Hardening)**. Pair with a corrected test assertion for `test_ok_false_triggers_backoff_continue`.
5. **[MEDIUM] forge_ledger non-atomic write** — Write-to-tmp pattern already exists in `json_store.py`. Copy it. Add to **PH-19.5** or PH-20.
6. **[MEDIUM] forge_ledger cross-process race** — Requires `FileLock` swap. May be acceptable to document as a known limitation in v1.0 and defer to PH-22 if multi-process forge is not a v1.0 use case.

### Can defer to PH-22

7. **[LOW] `"succeeded"` dead sentinel** — 1-line cleanup. Can go in PH-20 final polish.
8. **[LOW] `narrow_layout` dead export** — Wire or remove. PH-20 or PH-22.
9. **[LOW] `test_elapsed_ms_recorded` fragility** — PH-20 test polish.
10. **[LOW] Non-atomic artifact writes** — Add `_atomic_write` helper in PH-20 or PH-22.

### Suggested new PH-19 slice

**PH-19.6 Security + Stability Hardening** (2–3 hours of work):
- `web_terminal.py`: body size cap + socket timeout
- `exec_command` callers: pass `timeout=30` defaults
- `mcp_client.py`: discard limit + readline timeout
- `chat_bridge_loop.py`: backoff reset relocation
- `forge_ledger.py`: atomic write + test for backoff correctness
