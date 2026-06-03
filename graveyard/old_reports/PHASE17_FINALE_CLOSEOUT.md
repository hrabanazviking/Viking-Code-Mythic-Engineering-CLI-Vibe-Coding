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

---

## Update Notice — 2026-05-02 (additive)

A later audit (`AUDIT_FAKE_TEMP_CODE_2026-05-02.md`, HEAD `e0953b6`) re-measured the project on 2026-05-02. The original closeout above is preserved unchanged; this notice is purely additive.

- **Coverage:** the figure above recorded as **"76% (held)"** was a stale carry-over. Live measurement (`pytest --cov=mythic_vibe_cli --cov-report=term-missing`) on 2026-05-02 reports **82%** branch+line coverage on the production package (1694 passed, 1 skipped, 14 subtests). Current coverage is ~6 points higher than recorded.

### Caveat on slice 17.4 — Chat bridge scaffolding

The line `17.4 Chat bridge scaffolding ✓` in the table above remains accurate as written: the **scaffolding** is shipped (`parse_command`, `handle_message`, `MatrixConfig`, `TelegramConfig`, urllib HTTP client primitives, and a `surface chat` entry-point that exits with a notice). The footnote at line 91–93 already discloses that the long-poll loop is deferred. This caveat amplifies that disclosure for any reader who skims the checkmark table only:

⚠ **Operator caveat:** the long-poll loop (Matrix `/sync`, Telegram `getUpdates`) is **deferred to a future PR**. `mythic-vibe surface chat --backend matrix|telegram` is currently a scaffolding-and-exit surface, **not** a running bridge. For a live bridge today, an operator must wrap the exported primitives (`matrix_send_message`, `telegram_send_message`, `parse_command`, `handle_message`) in their own loop until the deferred work lands.

This caveat does **not** retract the checkmark — the slice contract was "scaffolding," and scaffolding shipped — but it ensures readers do not over-read the table.

— *Sólrún Hvítmynd & Runa, additive correction*

---

## Update Notice — 2026-05-02 Phase E (additive, audit remediation **closed**)

The 2026-05-02 caveat block above is now **historical**. Phase E of
the audit remediation shipped a fully-featured running chat bridge
for both Matrix and Telegram. Operators can now run
`mythic-vibe surface chat --backend matrix --run` (or
`--backend telegram --run`) with credentials in env vars (or a
`--config <path>` JSON file) and the bridge actually polls + replies +
reconnects on transient errors + shuts down cleanly on
SIGINT / SIGTERM.

**Phase E shipped — six logical sub-phases, one cohesive commit:**

- **E.0** Config + master gate + allowlist refusal:
  `MatrixConfig` and `TelegramConfig` gained `from_env`,
  `from_file`, `from_sources`, `validate`, `is_room_allowed` /
  `is_chat_allowed` / `is_user_allowed` classmethods. Master env
  gate `MYTHIC_CHAT_BRIDGE_ENABLED=1` (default off — durable rule).
  `validate()` **refuses to start** without an explicit allowlist
  (operators must opt into broadcast with `*` — strongly
  discouraged). `ChatBridgeConfigError` is a typed exception for
  config errors. `_parse_csv_allowlist` and `_read_config_file`
  helpers added.

- **E.1** Matrix `/sync` long-poll loop:
  `surfaces/chat_bridge_loop.py` — new module. `run_matrix_loop()`
  drives a `/sync?since=<token>&timeout=<ms>` long-poll, dispatches
  `m.room.message`/`m.text` events through `parse_command` +
  `handle_message`, replies via `matrix_send_message(...,
  room_id=originating_room)` to the originating room. Allowlist
  filtering, echo prevention (skip messages where `sender ==
  config.user_id`), exponential backoff with cap on transient HTTP
  errors (5xx / URLError / 408 / 429), terminal raise on 4xx
  (auth — fail fast). Honours `stop_event` between sync calls.

- **E.2** Telegram `getUpdates` long-poll loop: same shape.
  `run_telegram_loop()`. Allowlist on **both** `chat_id` and
  `user_id` (empty `allowed_users` = "any user in an allowed
  chat"). `offset` advances per update. Same backoff + stop_event
  semantics.

- **E.3** `--run` + `--config` + signal handling on
  `cmd_surface_chat`: argparse gained `--run`, `--config <path>`,
  `--max-iterations <N>` (test guard). The legacy
  scaffolding-and-exit body is **preserved verbatim** when `--run`
  is absent (additive). With `--run`: master gate check →
  `ChatBridgeConfigError` USER_INPUT_ERROR → SIGINT/SIGTERM
  handlers set the stop_event → loop runs to clean shutdown.

- **E.4** Tests (3 new files, 80 net new tests):
  - `tests/test_chat_bridge_config.py` (38 tests) — env / file /
    sources / validate / allowlist semantics for both backends.
  - `tests/test_chat_bridge_http_client.py` (11 tests) — exercises
    the four HTTP client functions previously flagged as untested
    (`_matrix_request`, `matrix_send_message`, `_telegram_request`,
    `telegram_send_message`) plus the new `room_id` / `chat_id`
    keyword overrides. **Closes audit finding #7 as a
    side-effect.**
  - `tests/test_chat_bridge_loop.py` (31 tests) — `_Backoff`,
    `_is_transient_http_error`, `_matrix_extract_messages`,
    `_telegram_extract_messages`, both loops' happy paths,
    allowlist filtering, echo prevention, transient backoff
    recovery, terminal-error raise-through, validate refusal,
    `cmd_surface_chat --run` master-gate / config-error / happy /
    legacy-preservation.

- **E.5** Deployment guide:
  `docs/CHAT_BRIDGE_DEPLOYMENT.md` — security model (master gate
  + allowlist refusal + echo prevention), env-var reference,
  systemd unit (Linux), NSSM service (Windows), launchd plist
  (macOS), TLS notes, rate-limit guidance, troubleshooting
  matrix, JSON `--config` file shape.

**Audit findings closed by Phase E:**
- **#2 (High)** Chat-bridge poll loop missing — closed.
- **#7 (Low)** chat_bridge HTTP client untested — closed (4
  previously-untested functions now have 11 tests).

Test count: 1783 → 1863 (+80). Coverage still ≥ 82%. Lint + mypy
clean. Working tree clean and pushed.

— *Sólrún Hvítmynd & Runa, additive correction*
