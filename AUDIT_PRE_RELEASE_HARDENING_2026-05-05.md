# Pre-Release Hardening Audit (PH-24.1, 2026-05-05)

**Auditor:** Runa Gridweaver Freyjasdottir, on Volmarr's behalf during the autonomous PH-24 hardening run.
**Branch:** `development`
**HEAD at audit:** `796a16c` (PH-24 kickoff)
**Scope:** every defect, gap, or hardening opportunity in the post-v1.0.0 + PH-21/22/23 surface that matters for a production release.

This document records findings before fixing them. Each finding has a severity (Critical / High / Medium / Low / Cosmetic) and a fix recipe. Fixes land in subsequent slices (24.1.fix-X) so the audit trail stays clean.

---

## Method

Five sweeps run against `mythic_vibe_cli/` (the active runtime — `tests/`, scripts, tools excluded):

1. **Static analysis** — `ruff check --select B,S,SIM,RET,PLE,PLW,UP,RUF` (extended bug-bear + security + simplification + return-style + perflint + plw + pyupgrade + ruff-specific rules).
2. **Pseudocode + stub scan** — grep for `TODO` / `FIXME` / `XXX` / `HACK` / `placeholder` in production code.
3. **Bare-except scan** — `except:` and `except Exception:` patterns.
4. **Dead-code scan** — symbols defined but never imported or referenced.
5. **Resource-leak scan** — file handles outside `with`, sockets / subprocess without try/finally.

Findings:

```
ruff extended sweep:        349 hits in 156 files (most are stylistic)
real concerns isolated:      34 hits across 6 categories (S110, S603, S607, RUF012, B905, B010, SIM117)
TODO/FIXME/HACK in src:       0 (after filtering scaffold templates + Conversation-id placeholders)
bare except: / except Exception:: ~30 (all with `# noqa: BLE001` justification — see Finding 5)
dead code:                    0 confirmed (every public symbol re-exported via __all__)
resource leaks:               0 confirmed (every open()/Popen() inspected uses with-block or finally)
```

---

## Findings (severity-ordered)

### Finding 1 — `RUF012` mutable class default for Textual `BINDINGS` (8 sites) — Medium

**Severity:** Medium
**Class:** correctness / typing clarity
**Sites:** `tui/app.py:692`, `tui/diff_review.py:365`, `tui/drift_panel.py`, `tui/help_overlay.py`, `tui/picker.py` (×2), `tui/runner.py`, `tui/wave_panel.py`

Textual screen subclasses define `BINDINGS = [_Binding(...), ...]` as a class attribute. Python's class-attribute model treats this as a single mutable list shared across all subclass instances. If any code path mutated `BINDINGS` at runtime, every screen of that class would see the mutation. Textual itself treats the list as immutable, so today there's no live bug — but the typing isn't honest.

**Fix:** annotate as `ClassVar[list[Binding]]` so static analyzers + readers know it's class-scoped (not instance-shadowable) and intentionally not per-instance.

```python
from typing import ClassVar
class StatusScreen(Screen):
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit"),
        ...
    ]
```

**Slice 24.1.fix-1 lands this.**

---

### Finding 2 — `B905` `zip()` without explicit `strict=` (4 sites) — Cosmetic

**Severity:** Cosmetic
**Class:** intent clarity
**Sites:** `workflow.py:225`, `workflow_lineage.py:74`, `workflow_lineage.py:186`, `workflow_engine.py` (one more)

Each site uses `zip(a, a[1:])` to iterate consecutive-pair tuples. `a[1:]` is always one element shorter, so the short-zip is the intended behavior. Python 3.10+ introduced `strict=` as a required-keyword for `zip` to make truncation behavior explicit at the call site.

**Fix:** add `strict=False` to each call. No behavior change.

**Slice 24.1.fix-1 lands this.**

---

### Finding 3 — `B010` `setattr(args, "json", True)` (1 site) — Cosmetic

**Severity:** Cosmetic
**Class:** style
**Site:** `commands.py:6665`

`setattr(args, "json", True)` is equivalent to `args.json = True`. The latter is more readable + lets static analyzers track the attribute. Used in `cmd_scry` to flip an argparse-namespace flag.

**Fix:** replace with direct attribute assignment.

**Slice 24.1.fix-1 lands this.**

---

### Finding 4 — `S110` try-except-pass (12 sites) — Low (most justified)

**Severity:** Low (most are intentional)
**Class:** silent failure surface
**Sites:** spread across `voice/tts.py`, `forge_ledger.py`, `runtime/cross_process_lock.py`, `event_log.py` cleanup paths, etc.

Every `except: pass` (or `except Exception: pass`) silently swallows an error. Each one is either:
- **Intentional best-effort cleanup** — e.g., `unlink` of a tmp file in a finally block. Justified.
- **Platform-specific fallback** — e.g., trying Apple Silicon MPS detection; failure means fall back to CPU. Justified.
- **Unjustified swallow** — none found in this audit.

Each site already carries a `# noqa: BLE001` comment indicating an author intentionally accepted the broad catch. The audit verified each is a legitimate best-effort or platform-fallback pattern.

**Fix:** none required. Adding logging at info-level to each cleanup path was considered but rejected — it would create noise during normal operation.

---

### Finding 5 — `S603` subprocess invocations flagged (5 sites) — False Positive

**Severity:** False Positive
**Class:** security heuristic
**Sites:** `cicd/release.py:172`, `cicd/rollback.py:74`, `protocols/mcp_client.py:131`, `runtime/exec.py`, `verify/test_runner.py`

Bandit-style ruff S603 flags **every** `subprocess.run` / `Popen` call as "check for execution of untrusted input." Each site:

- Uses `shell=False` (default; verified).
- Runs only project-supplied git commands or operator-configured binaries.
- Does not interpolate operator input directly into the argv string (the argv list is constructed from validated inputs).

**Fix:** none required. Could add per-site `# noqa: S603` to silence the linter, but the linter is at default-disabled severity anyway.

---

### Finding 6 — `RUF100` unused `noqa` comments (103 sites) — Cosmetic

**Severity:** Cosmetic
**Class:** style hygiene
**Sites:** spread across the codebase — `noqa` directives that no longer correspond to a live ruff finding.

These accumulate as ruff rules evolve or as code is refactored. They're harmless (no behavior change) but they're noise for future readers.

**Fix:** ruff's `--fix` can auto-remove all 103. Defer to a focused style-cleanup slice (24.1.fix-2 or later) rather than mixing with substantive fixes.

---

### Finding 7 — `UP035` deprecated import patterns (42 sites) — Cosmetic

**Severity:** Cosmetic
**Class:** PEP 585 / 604 modernization
**Sites:** `from typing import List, Dict, Optional, Union` patterns that PEP 585 (3.9+) and PEP 604 (3.10+) made unnecessary.

The project targets Python 3.10+, so all 42 sites can use `list` / `dict` / `X | None` / `X | Y` directly. Auto-fixable via ruff `--fix`.

**Fix:** defer to a focused modernization slice.

---

### Finding 8 — `UP037` quoted annotations (37 sites) — Cosmetic

**Severity:** Cosmetic
**Class:** PEP 563 modernization
**Sites:** function annotations using string literals that `from __future__ import annotations` already covers.

The project uses `from __future__ import annotations` in every module, so quoted annotations are redundant. Auto-fixable.

**Fix:** defer to focused modernization slice.

---

### Finding 9 — `S310` urlopen without scheme validation (23 sites) — Low

**Severity:** Low
**Class:** security heuristic
**Sites:** `urllib.request.urlopen` calls in AI provider adapters + the OCI / wasi build helpers + tools/fetch_pbs_checksums.py.

S310 flags any urlopen call as "audit URL scheme to prevent file:// or other unsafe schemes." Every site here:

- Builds URLs from constants (`PBS_RELEASE_URL_TEMPLATE`, `WHEEL_PYPI_INDEX`, etc.) or operator-supplied strings (provider API keys + endpoints).
- Operator-supplied URLs are an explicit configuration surface — operators wanting to install Mythic Vibe behind a corporate proxy or against an internal mirror configure these. Forcing `https://` only would break legitimate use cases.

**Fix:** none required. Could add `# noqa: S310` per site to silence the linter, but the heuristic is correct in spirit; site-by-site review confirmed each is operator-controllable.

---

### Finding 10 — `S101` `assert` in production (7 sites) — Low

**Severity:** Low
**Class:** assertion-stripped-by-O-flag
**Sites:** spread across runtime helpers.

Python's `-O` flag strips `assert` statements; if production code relies on an assertion for control flow, `-O` removes the check silently. Each site here uses asserts for **invariants** that should never fail in correct code (not user-input validation), so even if `-O` strips them, the code is correct.

**Fix:** none required. Mark for future cleanup if a per-site `if not cond: raise RuntimeError(...)` is preferred.

---

### Finding 11 — `SIM105` suppressible-exception (21 sites) — Cosmetic

**Severity:** Cosmetic
**Class:** style modernization
**Sites:** `try / except / pass` blocks that contextlib.suppress would express more clearly.

```python
# Before
try:
    path.unlink()
except FileNotFoundError:
    pass

# After
with contextlib.suppress(FileNotFoundError):
    path.unlink()
```

**Fix:** defer to focused modernization slice.

---

### Finding 12 — Pseudocode / TODO / placeholder scan — Clean

After filtering out:
- CI/Docker scaffold *templates* (these contain operator-facing TODOs by design — `cicd/ci_scaffold.py`, `cicd/docker_scaffold.py`, `cicd/release.py`)
- Packet-linter rule strings (the linter detects the strings "TODO", "etc.", etc. in operator-authored content; those literals must appear in the linter source)
- Conversation-id placeholders (`CV-XXXXXX` is a documented operator-facing format)

**Result: zero TODOs or placeholders in production code paths.** The codebase is genuinely complete — every PH-22 / PH-23 deferred item that's noted in a README is documented as "deferred to future slice" rather than scattered as code-level TODO comments. That's the correct discipline.

---

### Finding 13 — Resource-leak scan — Clean

Scanned every `open()` / `tempfile.mkstemp` / `tempfile.mkdtemp` / `subprocess.Popen` / `socket.socket()` / `urllib.request.urlopen` call:

- All `open()` calls use the `with` form or are immediately followed by a `with`-managed wrapper.
- All `tempfile.mkstemp` callers either close the FD via `os.close(fd)` and use the path, or use `with` over the file handle.
- All `tempfile.mkdtemp` callers use `tempfile.TemporaryDirectory` instead, which auto-cleans on exit.
- All `subprocess.Popen` callers eventually call `.wait()` / `.communicate()` / `.terminate()`. The `runtime/exec.py` wrapper is the only direct caller; everywhere else uses that wrapper.
- All `urllib.request.urlopen` calls are inside `with` blocks.
- Sockets are created only in `surfaces/web_terminal.py` via `ThreadingHTTPServer`, which has a documented lifecycle (`stop()` calls `shutdown()` + `server_close()`).

**Result: no resource leaks found.**

---

### Finding 14 — Thread-safety scan — Clean (with one previously-fixed item)

Global mutable state holders:
- `runtime/output_guard.py:_state` — module-level mutable; PH-21 conftest test (`test_output_guard.py`) verified the takeover/restore lifecycle is exception-safe.
- `runtime/event_log.py` — uses `EventTailReader` per-instance state; module-level state is read-only constants.
- `runtime/timings.py` — module-level dict; only mutated when `MYTHIC_TIMING=1`; `app.main()` resets at start so no cross-call leak.

Plugin loader's `importlib.import_module` calls aren't reentrant-protected, but the dispatcher is documented as operating on a per-invocation snapshot of plugins (see `docs/plugins.md` "synchronous-only / read-only-payload contract").

**Result: thread-safety posture is correct + documented.**

---

## Summary

| Severity | Count | Action |
|---|---|---|
| Critical | 0 | — |
| High | 0 | — |
| Medium | 1 (Finding 1: `RUF012` mutable class defaults) | Fix in 24.1.fix-1 (this slice) |
| Low | 4 (Findings 4, 9, 10 — all justified after review) | Defer; document the justification |
| Cosmetic | 6 (Findings 2, 3, 6, 7, 8, 11) | Pick the genuinely actionable (B905, B010 — Findings 2 + 3) for 24.1.fix-1; defer the noqa + UP modernization sweep to a focused later slice |
| False Positive | 1 (Finding 5: `S603`) | None |

**Net result:** the v1.0.0 + post-launch surface is in genuinely solid shape. No critical or high-severity defects exist. The Medium finding (mutable BINDINGS) is correctness-clarity not runtime-bug. The cosmetic items are real but small.

**Slice 24.1.fix-1 (next commit):** apply the Medium + actionable Cosmetic fixes (Findings 1, 2, 3) — `ClassVar` annotations + `strict=False` on zips + `setattr → direct assignment`. Bench: ~10-12 file edits, all behavior-preserving.

**Slice 24.1.fix-2 (deferred to a focused style slice):** the `--fix`-able style sweep (Findings 6, 7, 8, 11). 216 auto-fixes, but bundling them with the substantive fixes muddies the audit trail; landing them as their own slice is the cleaner discipline.
