# Threat Model — Mythic Vibe CLI

**Version:** 1.0 (Phase 19.5, audit remediation cycle 2026-05-02)
**Owner:** Mythic Vibe Contributors
**Scope:** the installable `mythic_vibe_cli` package and every
surface it exposes (terminal, web terminal, chat bridges, plugin
sandbox, AI providers, file persistence, voice). Out of scope:
the operator's host OS, third-party AI provider infrastructure,
and the user's project repository contents (we treat those as
trust boundaries we cross — see §3).

---

## 1. Purpose

This document lists the assets the CLI protects, the attackers
those assets must be protected from, and the mitigations the
codebase actually implements (with file:line references where
material). It is **descriptive, not aspirational** — every
mitigation listed here points to extant runtime behavior. Gaps
between intent and implementation are called out explicitly in
§5 ("Known limitations") rather than papered over.

The goal is to give operators, security reviewers, and future
contributors:

- A single canonical answer to "what does this tool defend
  against, and what doesn't it defend against?"
- A grounded baseline so any new attack surface can be slotted
  into the existing matrix without re-deriving the whole model.
- Evidence to show during code review or audit that the design
  has been thought through, not improvised.

---

## 2. Assets

The five categories of value the CLI must keep intact:

| ID | Asset | Where it lives | Why it matters |
|----|-------|----------------|----------------|
| A1 | Operator project state | `mythic/status.json`, `mythic/backups/*`, `mythic/handoffs/*`, `mythic/forge/ledger.jsonl` | Workflow truth — corruption loses operator history |
| A2 | AI provider credentials | env vars (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.) and operator config | Direct billing / abuse risk if leaked |
| A3 | Source files in the operator repo | the repository the CLI is invoked against | A buggy mutation can wipe / corrupt user code |
| A4 | Web terminal endpoint | `surfaces/web_terminal.py` HTTP server when started | Remote command execution if exposed |
| A5 | Chat bridge endpoint | `surfaces/chat_bridge.py` Matrix / Telegram polling clients | Remote command execution + provider impersonation |

Secondary assets (defended in transit by the same controls):
plugin packages and their sandboxed execution context
(`plugins/sandbox.py`); local file-lock state under
`mythic/*.lock`; cached method-source fixtures under
`mythic_data` cache.

---

## 3. Trust Boundaries

The CLI sits on the boundary between several trust zones. Each
boundary crossing is explicit and enforced at a well-defined
chokepoint:

| Boundary | Direction | Chokepoint | Enforcement |
|----------|-----------|------------|-------------|
| Operator shell ↔ CLI process | bidirectional | `cli.py:main` / `app.py` argparse | argparse type validation, exit-code policy in `exit_codes.py` |
| CLI ↔ user repository files | write | `runtime/atomic_write.py`, `persistence/json_store.py:JsonStateStore.write_state` | atomic write-tmp + replace, FileLock, cross-process lock opt-in |
| CLI ↔ third-party AI provider | outbound | `ai/router.py` + per-provider modules | provider-specific API key isolation, no raw credential logging |
| CLI ↔ remote operator (web terminal) | inbound | `surfaces/web_terminal.py` | loopback default bind, token via `secrets.compare_digest`, request-body cap, socket timeout |
| CLI ↔ chat platform | inbound | `surfaces/chat_bridge.py` | command parser whitelist, no arbitrary shell exec from chat |
| CLI ↔ plugin code | inbound | `plugins/sandbox.py:safe_call` | timeout enforcement, exception isolation, no privileged context handed to plugins |

---

## 4. Attacker Profiles

We model four attacker personas. Each row in the threat matrix
in §5 names which personas it applies to.

| ID | Persona | Capability | Motive |
|----|---------|------------|--------|
| T1 | Local unprivileged process | Same UID as operator, can read `~/.mythic` config and env (via `/proc/<pid>/environ` on Linux) | Credential theft, state corruption |
| T2 | Network attacker | Can reach the loopback / LAN interface where the operator runs surfaces | RCE via web terminal, command-injection via chat bridge |
| T3 | Hostile plugin author | Can publish a Mythic plugin (entry-point or local install) that the operator chooses to load | Code execution inside the operator's CLI invocation |
| T4 | Compromised AI provider response | Returns malicious tool-call JSON / shell-snippet text the operator pastes verbatim | Trick operator into executing harmful local commands |

We deliberately exclude:

- **Kernel-level / root attackers (T0).** Anyone with root on
  the operator's machine can already exfiltrate everything; the
  CLI cannot defend against that and does not pretend to.
- **Supply-chain attacks against the Python interpreter or
  stdlib.** Those are the operator's package manager's problem
  (Linux distro / Homebrew / Scoop / pip — see §6 for SBOM).

---

## 5. Threat Matrix

Each row: an asset, the attackers that threaten it, the
realistic attack, and the mitigations actually present in the
codebase.

### A1 — Operator project state

| # | Threat | Attackers | Mitigation (file:line if applicable) |
|---|--------|-----------|--------------------------------------|
| A1.1 | Concurrent CLI invocations corrupt `status.json` via interleaved writes | T1 (cooperative) | `persistence/json_store.py:FileLock` (legacy O_EXCL, default) + `runtime/cross_process_lock.py` (OS-level fcntl/msvcrt, opt-in via `cross_process=True`) |
| A1.2 | Power loss / process kill mid-write leaves a partial file | environmental | `runtime/atomic_write.py:atomic_write_text` — write-tmp + `os.replace` is atomic on every supported FS; `BaseException` cleanup catches KeyboardInterrupt / SystemExit |
| A1.3 | Antivirus / Windows indexer holds a transient handle over the target during `os.replace` | environmental | `runtime/atomic_write.py:_replace_with_retry` — five exponential-backoff retries on Windows `PermissionError` |
| A1.4 | Stale lock file from a crashed holder blocks all subsequent invocations | T1 | OS-lock mode (`cross_process=True`) auto-releases on process death; legacy O_EXCL mode documented as not auto-recovering — operator deletes stale lockfile manually |
| A1.5 | Silently corrupted JSON (disk error, manual edit) crashes future runs | environmental | `persistence/migrations.py:migrate_project_state` — on `StateStoreError`, copies the file to `mythic/backups/status.json.<stamp>.bak` and bootstraps a fresh state |
| A1.6 | Migration regressions silently change saved state | n/a (regression) | `tests/property/test_state_migrations.py` — six hypothesis-driven invariants (idempotency, schema invariant, validation-clean output, goal preservation, corrupt recovery, missing-file bootstrap) |

### A2 — AI provider credentials

| # | Threat | Attackers | Mitigation |
|---|--------|-----------|------------|
| A2.1 | Credentials echoed into stdout/logs / error messages | T1 (post-hoc log scraping) | `security/redaction.py` — pattern-based redaction of common API-key shapes before any structured output |
| A2.2 | Credentials persisted to project state on disk | n/a (design constraint) | `core/state.py:ProjectState` carries no credential fields; `mythic/status.json` schema explicitly excludes secrets |
| A2.3 | A plugin reads `os.environ` and exfiltrates keys | T3 | Documented limitation: Python plugins run in the same process and CAN read env. Mitigations: operator approval to load (suggest mode), allowlist of approved plugins (`plugins/registry.py`). True isolation requires a subprocess sandbox — tracked as future work in §7 |
| A2.4 | Provider response includes secret-like text that gets re-echoed | T4 | Same `security/redaction.py` pass on outputs — defends against "the LLM returned my API key back to me" loops |

### A3 — Source files in the operator repo

| # | Threat | Attackers | Mitigation |
|---|--------|-----------|------------|
| A3.1 | Buggy mutation overwrites a file the operator wanted to keep | n/a (correctness) | All file mutations route through `runtime/atomic_write.py` (no in-place truncation); `runtime/file_mutation_queue.py` serializes writes per-realpath inside one process |
| A3.2 | Auto-applied AI suggestion clobbers source without operator review | T4 | `security/approval.py` — three-tier mode (`suggest` / `auto` / `partial`) defaults to `suggest` on TTY; write actions prompt operator |
| A3.3 | Malicious / dangerous shell snippet from the AI is executed | T4 | `security/dangerous_patterns.py` flags known-bad shell forms (`rm -rf /`, fork bombs, etc.) and refuses to auto-execute; operator must approve each |

### A4 — Web terminal endpoint (`surfaces/web_terminal.py`)

| # | Threat | Attackers | Mitigation (file:line) |
|---|--------|-----------|------------------------|
| A4.1 | Remote attacker hits the endpoint | T2 | Default bind `127.0.0.1` (`web_terminal.py:DEFAULT_HOST`); operator must explicitly pass `--bind 0.0.0.0` and is documented as needing their own TLS reverse proxy |
| A4.2 | Brute-force token guessing | T2 | 32-byte URL-safe token (`secrets.token_urlsafe(32)`); compared via `secrets.compare_digest` (constant-time) — no early return on mismatch |
| A4.3 | DoS via huge `Content-Length` advertising | T2 | `MAX_REQUEST_BODY_BYTES = 65_536` cap and per-connection socket timeout (BS-1 fix, 2026-05-02); `web_terminal.py:50-65` |
| A4.4 | Stalled connection consumes a worker thread forever | T2 | Socket-level read timeout on each handler; thread releases on timeout |
| A4.5 | Cross-site request forgery against the local endpoint | T2 (browser-based) | Token is required in the JSON body, not a cookie — defeats classic CSRF (the attacker page can't read the token) |

### A5 — Chat bridge endpoint (`surfaces/chat_bridge.py`)

| # | Threat | Attackers | Mitigation |
|---|--------|-----------|------------|
| A5.1 | Anyone in a public room sends commands | T2 | Bridge filters to a configured operator allowlist; commands not from allowed senders are dropped |
| A5.2 | Command injection through chat text | T2 | `parse_command` only accepts a fixed verb whitelist; arguments are passed as discrete argv entries, not shelled out |
| A5.3 | Long-poll auth header leakage in logs | T1 | Auth headers redacted via `security/redaction.py` before `logging` emits |

### Plugins (sandbox layer)

| # | Threat | Attackers | Mitigation |
|---|--------|-----------|------------|
| P.1 | Hostile plugin runs forever, hangs the CLI | T3 | `plugins/sandbox.py:safe_call` enforces a per-call timeout |
| P.2 | Hostile plugin raises and crashes the CLI | T3 | `safe_call` catches and structures plugin exceptions; the host stays up |
| P.3 | Hostile plugin imports unexpected modules | T3 | Documented limitation — Python doesn't enforce import boundaries inside one process. Treat plugin loading as equivalent to `pip install`-ing the same code |

---

## 6. Supply-chain integrity

The CLI is distributed via three channels (PH-19.7): PyPI,
Homebrew tap, Scoop bucket. Supply-chain integrity is enforced
at each layer:

| Layer | Mechanism |
|-------|-----------|
| PyPI publish | OIDC trusted publishing from GitHub Actions (no long-lived API token in the repo) — see PH-19.7 release workflow |
| Wheel reproducibility | `python -m build` produces wheels; `twine check dist/*` validates metadata before upload |
| Operator-side verification | SBOM checked into `docs/security/sbom.json` (CycloneDX v1.x); regenerated and committed with every release |
| Dependency floor | `pyproject.toml` pins lower bounds for all extras; runtime base has zero non-stdlib deps |

The SBOM is generated by `cyclonedx-py` at release time and
committed under `docs/security/sbom.json`. Operators or
auditors can diff the SBOM across versions to see exactly which
transitive dependencies changed.

---

## 7. Known limitations

We list these here so an auditor doesn't have to reverse-engineer
the absence of a control:

1. **No in-process plugin isolation** — plugins run in the same
   Python interpreter and share `os.environ`, file handles, and
   `sys.modules`. Mitigation today is "operator chose to load
   it." A subprocess sandbox is a future option but adds
   significant runtime overhead and is not on the v1.0 roadmap.
2. **Web terminal does not bundle TLS** — operators exposing the
   endpoint outside loopback must front it with a reverse proxy.
   Documented in `docs/SSH_DEPLOYMENT.md` and in the surface's
   own docstring.
3. **Legacy O_EXCL lock mode does not auto-recover from holder
   crash** — opt-in to `cross_process=True` for OS-level locks
   that auto-release. Default left as O_EXCL for backwards
   compatibility with existing callers.
4. **No mandatory access control for AI provider keys** — the
   keys are read from the operator's environment as-is. The
   project does not (yet) ship a credential-vault adapter.
5. **No log signing / tamper-evidence on `forge/ledger.jsonl`** —
   the ledger is append-only by convention but not by enforced
   crypto. A malicious local process with write access could
   rewrite history. Out-of-scope for v1.0 (covered by general
   filesystem permissions on the operator's home directory).

---

## 8. Update procedure

This document is required reading for any PR that adds a new
network surface, a new persisted state file, a new credential
input, or a new plugin extension point. The PR must update the
relevant §5 sub-table before merge. CI does not enforce this
mechanically — code review does.

When the SBOM is regenerated (`cyclonedx-py environment
mythic-vibe-cli -o docs/security/sbom.json` after a release),
this file's "Version" header increments and the date in the
header is updated. The mechanical SBOM regeneration is wired
into the release workflow (PH-19.7).

---

## 9. References

- `runtime/atomic_write.py` — atomic write helper.
- `runtime/cross_process_lock.py` — OS-level cross-process lock.
- `runtime/file_mutation_queue.py` — intra-process write
  serialization.
- `persistence/json_store.py` — `JsonStateStore` + `FileLock`.
- `persistence/migrations.py` — `migrate_project_state`.
- `security/approval.py` — three-tier approval modes.
- `security/redaction.py` — output redaction.
- `security/dangerous_patterns.py` — shell-snippet refusal list.
- `surfaces/web_terminal.py` — token-protected HTTP surface.
- `surfaces/chat_bridge.py` — Matrix / Telegram bridge.
- `plugins/sandbox.py` — plugin call sandbox.
- `docs/security/sbom.json` — CycloneDX v1.x dependency manifest.
