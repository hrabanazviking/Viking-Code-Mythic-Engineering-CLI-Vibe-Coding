# PH-11 — Phase Finale Close-out (2026-05-01)

**Branch:** `development`
**Final HEAD:** `488696a` (this memo will land the next commit)
**Resume from:** `2be051f` (PH-10 finale)

PH-11 treats the CLI as a security-sensitive tool: approval
modes, redaction, secret scanning, sandbox execution, dangerous-
pattern detection, privacy mode, and a top-level
`mythic-vibe security audit` — all opt-in by default, never
silent. This phase also closed the deferred sandbox wire-in from
PH-10 slice 10.2, so plugin hooks now run through the
`safe_call` exception isolation + opt-in timing budget.

All 7 slices + the wire-in shipped in order; working tree clean,
every commit pushed, every existing test still passes (after two
expected updates for the new `security` command in registry-
inventory tests).

---

## What landed

| Slice | Title | Commit | Net |
|---|---|---|---|
| TASK file | — | `a5f756a` | +202 lines |
| Wire-in (10.2 deferred) | sandbox.safe_call → PluginHookDispatcher | `b36329e` | +168/-27 lines, +2 tests |
| 11.1 | Approval modes | `b73c377` | new package + 24 tests |
| 11.2 | Redaction engine | `e9c33cd` | +24 tests |
| 11.3 | Secret scanner | `beb60e6` | +20 tests |
| 11.4-11.6 | exec_policy + dangerous_patterns + privacy (bundled) | `98fbcfe` | +55 tests |
| 11.7 | `security audit` command | `488696a` | +11 tests |

**Test delta:** 1233 → 1369 (+136 net across the wire-in + 7 slices).
**Coverage:** 76% (held).
**Lint / type:** clean throughout.

---

## Capability summary

### Wire-in (PH-10 Slice 10.2 follow-up)

`PluginHookDispatcher._wrap_handler()` now wraps every plugin
hook call through `sandbox.safe_call`. Plugin exceptions land in
typed `SandboxResult`s rather than the bus's catch-all log;
`MYTHIC_PLUGIN_TIMEOUT_SEC` actually enforces a soft deadline.
Sandbox internals reworked from `ThreadPoolExecutor` (which
blocks on `__exit__`) to a daemon `Thread` + `Thread.join(
timeout=...)` so timeouts truly return immediately.

### Slice 11.1 — Approval modes

`mythic_vibe_cli/security/approval.py`. Three modes:
- `"suggest"` — prompt before every action.
- `"auto"` — run without prompting (CI-friendly).
- `"partial"` — allow read; prompt for write/exec.

Resolution: CLI override → `mythic/security.toml [approval]
mode = "..."` → TTY-aware default (TTY → suggest, non-TTY →
auto). Empty / unknown stdin answer ⇒ not approved (conservative
default).

### Slice 11.2 — Redaction engine

`mythic_vibe_cli/security/redaction.py`. Configurable
`RedactionEngine` with default-deny path globs (.env, .env.*,
*.pem, *.key, *.token, *.p12, *.pfx, id_rsa, id_ecdsa,
id_ed25519, credentials.json, service_account.json) and the
existing AI provider `SECRET_PATTERNS` as the regex base.
Operators extend via `[redaction] extra_patterns` /
`forbidden_paths` / `placeholder` in security.toml.

### Slice 11.3 — Secret scanner

`mythic_vibe_cli/security/secret_scanner.py`. `scan_text(text)`
+ `scan_paths(paths, root)` return typed `SecretFinding` /
`ScanResult` records with severity heuristic (sk-/AIza →
critical, bearer/api_key → high, secret/token/password →
medium). Files matching forbidden-path globs are listed in
`forbidden_paths` but **never opened** — the scanner refuses to
read secrets out of explicitly secret-bearing files.

### Slice 11.4 — Sandbox execution policy

`mythic_vibe_cli/security/exec_policy.py`. `SandboxPolicy` with
`directory_restriction` (refuse cwd outside project root) and
`network_disabled` (best-effort `unshare -n` wrap on Linux,
advisory-only elsewhere with a clear note). Helpers
`enforce_directory_restriction` and
`wrap_argv_for_network_disabled` give callers clean
`(allowed, reason)` tuples and argv-wrapping respectively.

### Slice 11.5 — Dangerous-pattern detection

`mythic_vibe_cli/security/dangerous_patterns.py`. Catalogue of
8 entries with severity tags + human-readable remediation:
`python.eval` / `python.exec` (critical), `python.shell_true` /
`python.os_system` / `python.pickle_loads` (high),
`python.yaml_load` (medium), `sql.string_format` (high),
`html.mark_safe_user_input` (medium). Language-aware filtering
keeps python-specific patterns from firing on Go/Rust files.

### Slice 11.6 — Privacy mode

`mythic_vibe_cli/security/privacy.py`. `PrivacyPolicy` with
`enabled` flag + `allow_paths` list. When enabled,
`filter_payload` recursively walks dict / list / tuple payloads
and replaces path-shape strings (slashes, no whitespace, < 256
chars) outside the allow-list with `"[PRIVACY:FILTERED]"`. Empty
allow_paths under enabled=true means "deny everything path-shaped"
— the strongest stance on the security stack.

### Slice 11.7 — `mythic-vibe security audit`

Aggregator command that runs all the slice 11.3 + 11.5 detectors
across the repo and reports the active slice 11.1 + 11.2 + 11.4
+ 11.6 policies in one consolidated payload. Critical + high
findings → exit OPERATIONAL_FAILURE; medium + advisory →
SUCCESS. CLI flag `--approval` overrides for the single run.

Available as both:
- `mythic-vibe security audit` (top-level CLI)
- `/security` (slash command — picker → preview → run loop)

---

## Master-roadmap impact

PH-11 closed. All 7 slices + the deferred wire-in shipped:

- 0 (10.2 deferred) Sandbox wire-in ✓
- 11.1 Approval modes ✓
- 11.2 Redaction engine ✓
- 11.3 Secret scanner ✓
- 11.4 Sandbox execution policy ✓
- 11.5 Dangerous-pattern detection ✓
- 11.6 Privacy mode ✓
- 11.7 `security audit` command ✓

**Phases now fully closed:** PH-01, PH-02, PH-03, PH-04, PH-05,
PH-06 (5/6), PH-07, PH-08, PH-09, PH-10, **PH-11**, PH-13,
PH-15. (13 of 20 — 65% of roadmap.)

PH-11 closure unblocks:
- **PH-14 (Policy Engine)** — depends_on `[PH-11, PH-13]`. PH-13
  was already closed; PH-11 was the gating prerequisite. PH-14
  is now eligible.

Remaining phases: PH-12 (CI/CD), **PH-14 (newly unblocked)**,
PH-16 (MCP/ACP/OpenTelemetry), PH-17 (Multi-Surface Access),
PH-18 (Robustness Sweeps), PH-19 (Distribution), PH-20 (v1.0.0
Sovereign OS Launch).

**Recommended next move:** **PH-14 (Policy Engine & Constraint
Verification)** — newly unblocked, builds directly on the slice
11.x policy machinery (security.toml, the typed `*Policy`
dataclasses, the audit aggregator). Natural follow-on. PH-12
(CI/CD) is the strategic alternative if Volmarr wants to turn
the security audit into a CI gate before extending the policy
surface.

---

## Operational notes

- Every PH-11 capability is **opt-in by default**. Projects
  without `mythic/security.toml` see zero behavioural change
  from before PH-11.
- The `security` package is fully isolated: no PH-11 code
  imports from outside `security/` except the existing
  `ai/providers/base.py:SECRET_PATTERNS` (deliberate single
  source of truth for the regex catalogue) and the slice 3.1
  `workflow_agents` dataclasses.
- Two existing tests updated for the new `security` command +
  slash entry; no other tests touched.
- Memory updated incrementally after each slice (per the
  durable rule about not batching).
- No new ADRs required — PH-11 lives entirely inside the
  active runtime boundary defined by ADR-0001 + ADR-0002.
  Future PH-14 work may add ADR-0009 (Policy Engine) once the
  approach is locked.
