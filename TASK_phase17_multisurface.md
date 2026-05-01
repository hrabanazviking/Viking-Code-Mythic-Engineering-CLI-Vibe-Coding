# TASK — PH-17 Multi-Surface Access

**Created:** 2026-05-01
**Branch:** `development`
**Operator:** Volmarr
**Resume from:** HEAD `be46dc1` (PH-16 finale)

PH-17 reaches beyond the local terminal: web bridge, mobile-
friendly TUI fallback, SSH-ready packaging, and a chat-bridge
adapter (Matrix-first, Telegram-second). All opt-in, all open-
source-only.

**Master roadmap dependency:** `[PH-04, PH-16]` — both closed.

---

## Slice 17.1 — Web terminal

**Goal:** new `mythic_vibe_cli/surfaces/` package +
`web_terminal.py`. Stdlib HTTP server that wraps the CLI
behind a token-protected endpoint. Browser-side fronted by
xterm.js (linked from CDN in the served HTML; not bundled).

**Files:**
- `mythic_vibe_cli/surfaces/__init__.py` (new package).
- `mythic_vibe_cli/surfaces/web_terminal.py` — stdlib
  `http.server` + token validation + JSON command dispatch.
- `mythic_vibe_cli/commands.py` — `cmd_surface_web`.
- `mythic_vibe_cli/app.py` — `mythic-vibe surface web` argparse.
- Tests.

**Default behaviour:** disabled. Operators run
`mythic-vibe surface web --port 8765 --token <random>` to
launch.

**Cross-platform notes:** stdlib http.server is
single-threaded; for production deployments operators wrap it
behind their own reverse proxy. xterm.js is loaded from
unpkg.com (operators can edit the served HTML to point at a
local copy).

**Progress:** [ ] not started

---

## Slice 17.2 — Mobile-friendly TUI narrow-layout

**Goal:** detect terminal column count < 80 and switch the TUI
to a single-column layout. Sidebar collapses; the artifact /
events / packet panels stack vertically.

**Files:**
- `mythic_vibe_cli/tui/app.py` — `_should_use_narrow_layout` +
  CSS branch.
- Tests via headless TUI rendering with a forced narrow size.

**Progress:** [ ] not started

---

## Slice 17.3 — SSH-ready surface check

**Goal:** `mythic-vibe surface ssh-doctor` runs a small set of
checks that confirm the CLI is suitable for SSH usage:
- Are interactive prompts present? (would block under SSH)
- Are color codes present without a TTY? (need `NO_COLOR`)
- Is the user's terminal type detected?
- Is the slice 11.1 approval default sensible (auto in non-TTY)?

Plus `docs/SSH_DEPLOYMENT.md` documenting the canonical SSH
workflow.

**Files:**
- `mythic_vibe_cli/surfaces/ssh_doctor.py` (new).
- `mythic_vibe_cli/commands.py` — `cmd_surface_ssh_doctor`.
- `docs/SSH_DEPLOYMENT.md` (new).
- Tests.

**Progress:** [ ] not started

---

## Slice 17.4 — Chat bridge (Matrix + Telegram)

**Goal:** thin adapters that poll a chat backend and run CLI
commands in response to `/cmd <name> <argv>` messages. Matrix
first (well-documented stdlib HTTP REST API), Telegram second
(simpler Bot API).

**Files:**
- `mythic_vibe_cli/surfaces/chat_bridge.py` (new) —
  per-backend adapters + a small dispatcher.
- `mythic_vibe_cli/commands.py` — `cmd_surface_chat`.
- Tests (against fake HTTP responses).

**Progress:** [ ] not started

---

## Phase finale

After all 4 slices ship:
- `PHASE17_FINALE_CLOSEOUT.md` — summary memo.
- Update memory + status file.
- Push.
- PH-17 closed; **PH-19 + PH-20 remain**.

---

## Operational notes

- ME laws: stdlib-first (no WebSocket / async libs), default-
  off, cross-platform, open-source only.
- All four surfaces are **opt-in** — invoke via
  `mythic-vibe surface <name>`.
- Token-based auth on the web surface (32-byte secret); chat
  bridges authenticate via the backend's standard mechanism
  (Matrix access token / Telegram bot token).
- Memory updated incrementally.
