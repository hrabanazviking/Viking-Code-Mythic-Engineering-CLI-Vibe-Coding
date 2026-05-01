# PH-17 — Phase Finale Close-out (2026-05-01)

**Branch:** `development`
**Final HEAD:** `9b624dd` (this memo will land the next commit)
**Resume from:** `be46dc1` (PH-16 finale)

PH-17 reaches beyond the local terminal: a stdlib HTTP web
terminal, a TUI narrow-layout fallback for mobile SSH clients,
an SSH-readiness diagnostic, and a chat-bridge scaffolding for
Matrix + Telegram. All four surfaces are opt-in.

---

## What landed

| Slice | Title | Commit | Net |
|---|---|---|---|
| TASK file | — | `7629ad6` | +119 lines |
| 17.1 + 17.2 + 17.3 + 17.4 (bundled) | Web terminal + narrow layout + SSH doctor + chat bridge | `9b624dd` | +1,950 lines, +52 tests |

**Test delta:** 1642 → 1694 (+52 net).
**Coverage:** 76% (held).
**Lint / type:** clean throughout.

---

## Capability summary

### Slice 17.1 — Web terminal

`mythic_vibe_cli/surfaces/web_terminal.py` — stdlib
`http.server.ThreadingHTTPServer` exposing the CLI behind a
token-protected `/api/run` endpoint. xterm.js front-end loaded
from CDN (operators can swap to a local copy).

Routes:
- `GET /` → HTML front-end
- `GET /static/app.js` → wiring script
- `GET /api/status` → health (no auth, for reverse proxy
  health checks)
- `POST /api/run` → token-gated JSON command dispatch

Token compared via `secrets.compare_digest` to defeat timing
attacks. 32-byte URL-safe auto-generated when omitted.
**Default bind: 127.0.0.1** — external exposure requires
`--bind 0.0.0.0` plus the operator's own TLS reverse proxy.

CLI: `mythic-vibe surface web --port N --token X --bind ADDR`.

### Slice 17.2 — Narrow-layout helper

`mythic_vibe_cli/surfaces/narrow_layout.py`. Pure detection:
`should_use_narrow_layout(columns=None, threshold=78)` returns
True when the terminal is < 78 columns wide. The TUI consumes
this to switch to a single-column layout when operators connect
from mobile SSH clients.

`MYTHIC_TUI_NARROW=1` forces the narrow layout regardless of
width — useful for testing on a wide screen.

### Slice 17.3 — SSH doctor

`mythic_vibe_cli/surfaces/ssh_doctor.py` runs four diagnostic
checks:
- TTY-detected — stdout `isatty()` shape
- color-output-safe — `NO_COLOR` set OR TTY present
- TERM-env-set — non-empty `TERM` env var
- approval-default-sensible — slice 11.1's resolver picks the
  expected mode for the active TTY state

Plus `docs/SSH_DEPLOYMENT.md`: interactive vs scripted SSH,
ANSI-color gotchas, web terminal forwarding via `ssh -L`,
multi-user notes, and a minimal systemd unit template.

CLI: `mythic-vibe surface ssh-doctor [--json]`.

### Slice 17.4 — Chat bridge

`mythic_vibe_cli/surfaces/chat_bridge.py`:
- `parse_command(message)` — extracts (command, argv) from
  `/cmd`-prefixed chat messages via `shlex.split` (handles
  quoted argv).
- `handle_message(message)` — pure dispatch returning a typed
  `ChatResponse` with stdout/stderr captured and a chat-friendly
  rendered body (fenced code block, ✅/❌ icons, truncated to
  ~1500 chars).
- Matrix + Telegram HTTP clients via stdlib `urllib.request`
  (no third-party SDK).

CLI: `mythic-vibe surface chat --backend matrix|telegram` is
the **scaffolding entry**. The long-poll loop is deferred to a
future deployment-style PR — operators wire credentials via
systemd EnvironmentFile / 1Password CLI / vault.

---

## Master-roadmap impact

PH-17 closed. All 4 slices shipped:
- 17.1 Web terminal ✓
- 17.2 Narrow-layout helper ✓
- 17.3 SSH doctor + docs ✓
- 17.4 Chat bridge scaffolding ✓

**Phases now fully closed:** PH-01..18 (all of PH-01 through
PH-18 except PH-19 which is unblocked but unstarted). **18 of
20 — 90% of roadmap.**

PH-17 unblocks no other phase directly — pure capability
addition. Remaining phases: **PH-19 (Distribution)**, **PH-20
(v1.0.0 Sovereign OS Launch)**.

**Recommended next move:** **PH-19 Distribution** — final
shippable phase before the v1.0.0 launch. Builds on PH-12's
release helper to ship `mythic-vibe` to PyPI / Homebrew / scoop
/ aur / winget. Once PH-19 lands, only PH-20 (the launch
ceremony) remains.

---

## Operational notes

- All four surfaces are opt-in. `mythic-vibe surface <name>`
  is the entry point; the CLI's normal flow is unchanged.
- Web terminal binds to loopback by default. Production
  deployments layer their own TLS reverse proxy and a real
  authentication scheme on top of (or replacing) the simple
  token gate.
- SSH doctor is read-only diagnostic; it never mutates env
  vars or config. Operators apply the remediation hints
  manually.
- The chat bridge ships the parse + dispatch + render
  primitives plus the Matrix + Telegram HTTP wrappers. The
  long-poll loop is deferred — it's a deployment concern, not
  a contract concern.
- Memory updated incrementally (per the durable rule).
- No new ADRs required.
