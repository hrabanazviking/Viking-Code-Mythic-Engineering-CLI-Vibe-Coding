# Chat Bridge Deployment Guide

**Phase E** of the 2026-05-02 audit remediation shipped a real,
runnable Matrix + Telegram chat bridge. This guide tells operators
how to deploy it safely on Linux (systemd), Windows (NSSM), and
macOS (launchd), with the security caveats they need to honour.

---

## Quick start

```bash
# 1) Master gate (default off — durable rule).
export MYTHIC_CHAT_BRIDGE_ENABLED=1

# 2) Backend credentials + allowlist (Matrix shown).
export MYTHIC_CHAT_MATRIX_HOMESERVER=https://matrix.org
export MYTHIC_CHAT_MATRIX_ACCESS_TOKEN=<your-bot-access-token>
export MYTHIC_CHAT_MATRIX_USER_ID="@mybot:matrix.org"
export MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS="!abc:matrix.org,!def:matrix.org"

# 3) Run.
mythic-vibe surface chat --backend matrix --run
```

The bridge listens on the rooms in `MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS`
for messages starting with `/cmd <name> <argv>`, runs each command,
and replies with the output. Press `Ctrl+C` to stop cleanly.

---

## Security model — read this first

The chat bridge runs **arbitrary CLI commands** in response to chat
messages. Misconfigured, it is a remote code execution surface.
The bridge enforces **three layers** of safety, all of which are
load-bearing:

1. **Master env gate** — `MYTHIC_CHAT_BRIDGE_ENABLED=1` is required.
   Default off; the `--run` flag refuses to start without it.
   This prevents the bridge from being accidentally launched in
   environments where it shouldn't run.

2. **Allowlist refusal** — the bridge **refuses to start** unless an
   explicit room / chat allowlist is set. To opt into broadcast
   listening (any room / chat), set the allowlist literally to
   `*` (the `ALLOWLIST_BROADCAST` sentinel) — **strongly
   discouraged**. Always pin to specific room / chat IDs in
   production.

3. **Echo prevention** — Matrix messages whose `sender` matches
   `MYTHIC_CHAT_MATRIX_USER_ID` are skipped, preventing reply loops
   when the bot's own outputs are themselves valid `/cmd` lines.
   On Telegram, the Bot API doesn't return our own messages by
   default; the user-allowlist provides analogous protection.

**Set `MYTHIC_CHAT_<BACKEND>_USER_ID` (Matrix) or
`MYTHIC_CHAT_TELEGRAM_ALLOWED_USERS` (Telegram) in production.**

---

## Configuration reference

### Matrix env vars

| Variable                                | Required? | Description |
|-----------------------------------------|-----------|-------------|
| `MYTHIC_CHAT_BRIDGE_ENABLED`            | yes       | `1` to enable the bridge surface (master gate) |
| `MYTHIC_CHAT_MATRIX_HOMESERVER`         | no        | Matrix homeserver URL (default `https://matrix.org`) |
| `MYTHIC_CHAT_MATRIX_ACCESS_TOKEN`       | **yes**   | Long-lived bot access token (from `/_matrix/client/v3/login` or your homeserver admin) |
| `MYTHIC_CHAT_MATRIX_USER_ID`            | strongly recommended | Bot's MXID, e.g. `@mythicbot:matrix.org` — used for echo prevention |
| `MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS`      | **yes**   | Comma-separated list of room IDs the bridge listens in. Use `*` to broadcast (not recommended) |
| `MYTHIC_CHAT_MATRIX_ROOM_ID`            | no        | Legacy default-room for `matrix_send_message` calls without an explicit `room_id`; falls back to the first allowed room |
| `MYTHIC_CHAT_MATRIX_SYNC_TIMEOUT_MS`    | no        | Long-poll `/sync` timeout (default `30000`) |

### Telegram env vars

| Variable                                  | Required? | Description |
|-------------------------------------------|-----------|-------------|
| `MYTHIC_CHAT_BRIDGE_ENABLED`              | yes       | `1` to enable the bridge surface (master gate) |
| `MYTHIC_CHAT_TELEGRAM_BOT_TOKEN`          | **yes**   | Token from `@BotFather` |
| `MYTHIC_CHAT_TELEGRAM_ALLOWED_CHATS`      | **yes**   | Comma-separated list of chat IDs (numeric or `@channelname`). Use `*` to broadcast (not recommended) |
| `MYTHIC_CHAT_TELEGRAM_ALLOWED_USERS`      | strongly recommended | Comma-separated list of user IDs. Empty = any user in an allowed chat may issue commands |
| `MYTHIC_CHAT_TELEGRAM_CHAT_ID`            | no        | Legacy default-chat; falls back to first allowed chat |
| `MYTHIC_CHAT_TELEGRAM_API_ROOT`           | no        | API root (default `https://api.telegram.org`) |
| `MYTHIC_CHAT_TELEGRAM_POLL_TIMEOUT_S`     | no        | Long-poll `getUpdates` timeout (default `30`) |

### File-based config (`--config <path>`)

A JSON file with optional `matrix` and `telegram` sections. **File
values override env-var values** when both are set; env supplies
defaults for fields the file omits.

```json
{
  "matrix": {
    "homeserver": "https://matrix.org",
    "access_token": "<token>",
    "user_id": "@mythicbot:matrix.org",
    "allowed_rooms": ["!abc:matrix.org", "!def:matrix.org"],
    "room_id": "!abc:matrix.org",
    "sync_timeout_ms": 30000
  },
  "telegram": {
    "bot_token": "<token>",
    "allowed_chats": [-100123456789, -100987654321],
    "allowed_users": [4242, 5353],
    "chat_id": -100123456789,
    "poll_timeout_s": 30
  }
}
```

Pass with `--config /etc/mythic/chat_bridge.json`. Recommended file
permissions: `chmod 0600` (owner read/write only).

---

## Linux — systemd unit

**`/etc/systemd/system/mythic-chat-bridge-matrix.service`:**

```ini
[Unit]
Description=Mythic Vibe Chat Bridge (Matrix)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=mythic
Group=mythic
EnvironmentFile=/etc/mythic/chat_bridge.env
ExecStart=/usr/local/bin/mythic-vibe surface chat --backend matrix --run
Restart=on-failure
RestartSec=10
# Hardening — adjust to your filesystem layout.
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/mythic
NoNewPrivileges=true
PrivateTmp=true
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**`/etc/mythic/chat_bridge.env` (chmod 0600):**

```env
MYTHIC_CHAT_BRIDGE_ENABLED=1
MYTHIC_CHAT_MATRIX_HOMESERVER=https://matrix.org
MYTHIC_CHAT_MATRIX_ACCESS_TOKEN=<token>
MYTHIC_CHAT_MATRIX_USER_ID=@mythicbot:matrix.org
MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS=!abc:matrix.org,!def:matrix.org
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mythic-chat-bridge-matrix.service
sudo journalctl -u mythic-chat-bridge-matrix.service -f
```

---

## Windows — NSSM (Non-Sucking Service Manager)

```powershell
# Install NSSM, then:
nssm install MythicChatBridgeMatrix
# In the GUI dialog:
#   Path:        C:\Python\Scripts\mythic-vibe.exe
#   Arguments:   surface chat --backend matrix --run
#   Startup:     Automatic
# In the Environment tab, paste:
#   MYTHIC_CHAT_BRIDGE_ENABLED=1
#   MYTHIC_CHAT_MATRIX_HOMESERVER=https://matrix.org
#   MYTHIC_CHAT_MATRIX_ACCESS_TOKEN=<token>
#   MYTHIC_CHAT_MATRIX_USER_ID=@mythicbot:matrix.org
#   MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS=!abc:matrix.org,!def:matrix.org

nssm start MythicChatBridgeMatrix
nssm status MythicChatBridgeMatrix
```

Logs land in the Windows Event Log + the NSSM-configured stdout /
stderr files (set in the **I/O** tab).

---

## macOS — launchd

**`~/Library/LaunchAgents/com.mythic.chatbridge.matrix.plist`:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.mythic.chatbridge.matrix</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/mythic-vibe</string>
    <string>surface</string>
    <string>chat</string>
    <string>--backend</string>
    <string>matrix</string>
    <string>--run</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>MYTHIC_CHAT_BRIDGE_ENABLED</key>
    <string>1</string>
    <key>MYTHIC_CHAT_MATRIX_HOMESERVER</key>
    <string>https://matrix.org</string>
    <key>MYTHIC_CHAT_MATRIX_ACCESS_TOKEN</key>
    <string><token></string>
    <key>MYTHIC_CHAT_MATRIX_USER_ID</key>
    <string>@mythicbot:matrix.org</string>
    <key>MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS</key>
    <string>!abc:matrix.org,!def:matrix.org</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/usr/local/var/log/mythic-chatbridge-matrix.log</string>
  <key>StandardErrorPath</key>
  <string>/usr/local/var/log/mythic-chatbridge-matrix.log</string>
</dict>
</plist>
```

```bash
launchctl load -w ~/Library/LaunchAgents/com.mythic.chatbridge.matrix.plist
launchctl list | grep mythic
tail -F /usr/local/var/log/mythic-chatbridge-matrix.log
```

---

## TLS / reverse proxy notes

- **Matrix homeservers run on HTTPS by default** (matrix.org and most
  community servers). The bridge uses stdlib `urllib`, which honours
  the system trust store. No special TLS configuration is required.
- **Self-hosted Matrix homeservers behind a TLS-terminating reverse
  proxy** (nginx, Caddy, Traefik): point `MYTHIC_CHAT_MATRIX_HOMESERVER`
  at the proxy URL. The bridge speaks HTTPS to the proxy; the proxy
  speaks HTTP to the homeserver.
- **Telegram Bot API** is HTTPS-only (`https://api.telegram.org`).
  No proxy or special TLS config required.

---

## Rate-limit guidance

- **Matrix**: per-room rate limits vary by homeserver (matrix.org
  defaults to ~1 message / second per room; community servers can
  be tighter). The bridge replies once per `/cmd` invocation, so it
  rarely hits limits unless someone scripts a flood. If you receive
  HTTP 429, the loop's exponential backoff handles it
  automatically (1s → 2s → ... → 60s cap).
- **Telegram**: 30 messages / second across all chats, 1 message /
  second to the same chat. The bridge's reply rate is bounded by
  the rate of incoming `/cmd` messages; in normal use this is well
  under the limit.

---

## Operational diagnostics

The bridge logs structured lines to **stderr** with the prefix
`[YYYY-MM-DDTHH:MM:SSZ] [matrix]` or `[telegram]`. Capture this via
your service manager's standard mechanism:

- **systemd**: `journalctl -u mythic-chat-bridge-matrix -f`
- **NSSM**: configure the I/O tab's stderr file path
- **launchd**: `StandardErrorPath` in the plist (above)

Sample log lines:

```
[2026-05-02T19:43:21Z] [matrix] loop start (allowlist=['!abc:matrix.org'])
[2026-05-02T19:43:52Z] [matrix] dispatched 'status' to !abc:matrix.org (exit=0, event=$abc123)
[2026-05-02T19:44:13Z] [matrix] transient error HTTPError(503); backoff 1.0s
[2026-05-02T19:46:01Z] [matrix] loop stop (dispatched=4, iterations=12)
```

Use `--max-iterations <N>` for test drives — the loop exits cleanly
after N sync calls.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Chat bridge surface is disabled` | `MYTHIC_CHAT_BRIDGE_ENABLED` not set / not truthy | `export MYTHIC_CHAT_BRIDGE_ENABLED=1` |
| `Matrix config invalid: ... access_token is required` | env var missing | set `MYTHIC_CHAT_MATRIX_ACCESS_TOKEN` |
| `Matrix config invalid: ... allowed_rooms must be set` | allowlist refusal — by design | set `MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS=...` (or `*` for broadcast — not recommended) |
| Bridge starts but doesn't reply | Bot lacks send-permission in the room (Matrix) or hasn't been added to the chat (Telegram) | Invite / promote the bot |
| Reply loops (bot replying to itself) | `MYTHIC_CHAT_MATRIX_USER_ID` not set | set it to the bot's MXID |
| `terminal error: HTTPError(401)` | invalid / revoked access token | re-issue the token |
| `transient error HTTPError(5xx); backoff Xs` | upstream homeserver / Bot API issue | bridge retries automatically; investigate the upstream if persistent |

---

## See also

- `mythic_vibe_cli/surfaces/chat_bridge.py` — config classes,
  `parse_command`, `handle_message`, HTTP client functions
- `mythic_vibe_cli/surfaces/chat_bridge_loop.py` — the long-poll
  loops + backoff + echo prevention
- `tests/test_chat_bridge_config.py` / `test_chat_bridge_http_client.py`
  / `test_chat_bridge_loop.py` — comprehensive coverage
- `AUDIT_FAKE_TEMP_CODE_2026-05-02.md` finding #2 — original gap
- `TASK_AUDIT_REMEDIATION_PLAN.md` Phase E — locked scope and
  closeout
