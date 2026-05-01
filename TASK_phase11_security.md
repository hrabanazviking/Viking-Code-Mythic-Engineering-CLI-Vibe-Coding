# TASK — PH-11 Security, Sandbox & Permissions Layer + 10.2 wire-in

**Created:** 2026-05-01
**Branch:** `development`
**Operator:** Volmarr
**Resume from:** HEAD `2be051f` (PH-10 finale)

PH-11 treats the CLI as a security-sensitive tool: approval
modes, redaction, secret scanning, sandbox execution, dangerous-
pattern detection, privacy mode, and a top-level
`mythic-vibe security audit` command — all opt-in by default,
never silent.

This TASK also covers the **deferred sandbox wire-in** from PH-10
slice 10.2 — wrapping `PluginHookDispatcher.emit`'s per-handler
invocation in `sandbox.safe_call` so plugin hooks inherit the
exception isolation + opt-in timing budget the sandbox layer
already exposes.

**Master roadmap dependency:** `[PH-01]` — closed.

---

## 0. Sandbox wire-in (deferred from PH-10 Slice 10.2)

**Goal:** route `PluginHookDispatcher.emit` per-handler calls
through `sandbox.safe_call` so:
- Exceptions inside plugin hooks land in the bus's existing
  log path (already best-effort) AND are surfaced via a typed
  `SandboxResult` for diagnostics.
- The `MYTHIC_PLUGIN_TIMEOUT_SEC` env var actually enforces a
  soft deadline on hook invocations.

**Files:**
- `mythic_vibe_cli/plugins/dispatcher.py` — replace direct hook
  invocation in `_subscribe_plugin` with a sandbox-wrapped
  closure.
- `tests/test_plugin_dispatcher.py` — add tests for
  exception isolation + timing budget.

**Acceptance:** existing 11 dispatcher tests still pass.
`MYTHIC_PLUGIN_TIMEOUT_SEC` enforces the deadline.

**Progress:** [ ] not started

---

## Slice 11.1 — Approval modes

**Goal:** three approval modes for sensitive operations:
- `suggest` (prompt every action)
- `auto-approve` (run without prompting)
- `partial` (allow read, prompt for write)

Configured per-project via `mythic/security.toml` + per-command
override (`--approval suggest|auto|partial`).

**Files:**
- `mythic_vibe_cli/security/approval.py` (new) — typed
  `ApprovalMode` enum + `resolve_approval(mode, action) ->
  ApprovalDecision`. Stdlib stdin prompt fallback; tests inject
  a fake responder.
- `mythic_vibe_cli/security/__init__.py` (new package).
- Tests.

**Default:** `suggest` mode in interactive TTYs; `auto-approve`
in non-TTY (CI). The default is conservative but operators see
no prompts in scripted flows.

**Progress:** [ ] not started

---

## Slice 11.2 — Redaction engine

**Goal:** extend the existing `ai/providers/base.py:redact_text`
into a configurable engine that also default-denies `.env`,
`*.pem`, `*.key`, `*.token` paths from being read into provider
prompts.

**Files:**
- `mythic_vibe_cli/security/redaction.py` (new) — defines
  `DEFAULT_FORBIDDEN_PATHS`, `DEFAULT_REDACTION_PATTERNS`,
  `RedactionEngine` class with `redact_text(s)`,
  `is_path_forbidden(path)`, `redact_payload(payload)`.
- Re-uses the existing `SECRET_PATTERNS` from `ai/providers/base.py`
  so the engine is the new home for the regex set.
- Tests.

**Progress:** [ ] not started

---

## Slice 11.3 — Secret scanner

**Goal:** pre-packet check that scans candidate text + files for
hardcoded API keys, credentials, tokens. Surfaces findings before
the packet ships to a provider.

**Files:**
- `mythic_vibe_cli/security/secret_scanner.py` (new) —
  `scan_text(text)` + `scan_paths(paths, root)`. Returns typed
  `SecretFinding` records with severity / pattern / location.
- Reuses `redaction.DEFAULT_REDACTION_PATTERNS` for the regex
  set; this slice only adds the orchestration over it.
- Tests.

**Progress:** [ ] not started

---

## Slice 11.4 — Sandbox execution

**Goal:** extend `runtime.exec_command` (already runs
`shell=False` per existing slice) with directory restriction and
network-disabled mode guarded by `sandbox.enabled=true` in the
project config.

**Files:**
- `mythic_vibe_cli/runtime/exec_sandbox.py` (new helper) — wraps
  `exec_command` with cwd-restriction + network-disabled flags.
- `mythic_vibe_cli/security/exec_policy.py` — read
  `mythic/security.toml` to determine if sandbox is enabled.
- Tests.

**Cross-platform notes:**
- Network disabling is best-effort cross-platform. Linux:
  `unshare -n` (requires CAP_SYS_ADMIN). Otherwise reported as
  "advisory only".
- Directory restriction: refuse to spawn subprocesses whose cwd
  resolves outside the project root.

**Progress:** [ ] not started

---

## Slice 11.5 — Dangerous-pattern detection

**Goal:** scan code for `eval`, `exec`, shell injection,
unparameterised SQL — surface as warnings, not failures.

**Files:**
- `mythic_vibe_cli/security/dangerous_patterns.py` (new) —
  `DANGEROUS_PATTERNS` list of regex + severity, `scan_code(text,
  language=None)` returns typed findings.
- Tests.

**Progress:** [ ] not started

---

## Slice 11.6 — Privacy mode

**Goal:** when privacy mode is on, no provider call includes any
code outside an explicit allow-list (configured via
`mythic/security.toml:privacy.allow_paths`).

**Files:**
- `mythic_vibe_cli/security/privacy.py` (new) —
  `is_privacy_enabled(root)`, `filter_payload(payload, root)`.
- `mythic_vibe_cli/ai/providers/base.py` — call
  `filter_payload` before any provider write.
- Tests.

**Progress:** [ ] not started

---

## Slice 11.7 — `mythic-vibe security audit`

**Goal:** top-level command that runs all slice 11.2/11.3/11.5
checks across the repo, returns severity-tagged findings.

**Files:**
- `mythic_vibe_cli/commands.py` — `cmd_security_audit`.
- `mythic_vibe_cli/app.py` — argparse subcommand.
- Tests.

**Progress:** [ ] not started

---

## Phase finale

After everything ships:

- `PHASE11_FINALE_CLOSEOUT.md` — summary memo.
- Update memory + status file.
- Push.

---

## Operational notes

- ME laws: stdlib-first, optional deps via try-import, default-
  off feature gates, cross-platform.
- All security checks must be **opt-in by default**. Existing
  flows must keep working with no changes for projects that
  don't enable security.toml.
- Configuration lives in `mythic/security.toml` for per-project
  policy. CLI flags override per-invocation.
- After each slice: update memory + status file immediately.
