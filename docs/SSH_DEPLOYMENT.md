# SSH Deployment Guide

How to run the Mythic Vibe CLI under an SSH session — both interactive and scripted.

> **v1.0 threat-model context.** The web-terminal surface (asset
> **A4** in [`docs/security/threat_model.md`](security/threat_model.md))
> binds to `127.0.0.1` by default; SSH forwarding is the supported
> remote-access path. The PH-19.0 hardening sweep added explicit
> request-body caps + per-connection socket timeouts (BS-1) — the
> bridge no longer hangs on a misbehaving client that advertises a
> huge `Content-Length`.

## Interactive SSH

The default config works out of the box. SSH inherits a TTY, so:

- `mythic-vibe shell` opens the REPL.
- `mythic-vibe tui` renders the four-panel interface (auto-falls back to the PH-17 narrow layout when the remote terminal is < 78 columns wide).
- `mythic-vibe oath` and other commands that gate through PH-14's policy gate prompt the operator on stdin.

Run the surface check before relying on the SSH workflow:

```bash
ssh user@host -- mythic-vibe surface ssh-doctor
```

A clean exit code means the CLI is ready. Each finding includes a remediation hint.

## Scripted / non-interactive SSH

When SSH runs without a TTY (`ssh user@host -- mythic-vibe ...`), the CLI auto-adapts:

- Slice 11.1 approval mode flips to `auto` — no prompts on stdin.
- Slice 6.1 voice TTS stays disabled (no `MYTHIC_VOICE_TTS_ENABLED`).
- Slice 4.4 status-bar / TUI cues are not rendered (TUI requires `mythic-vibe tui`, which itself requires a TTY).

Common gotchas:

1. **ANSI color leaks** — set `NO_COLOR=1` in the remote shell to suppress ANSI codes when redirecting output to log files. The `ssh-doctor` check warns when `NO_COLOR` isn't set in a non-TTY context.
2. **Bare `TERM`** — many SSH sessions inherit `TERM=dumb`. Set `TERM=xterm-256color` (or your local equivalent) before invoking `mythic-vibe tui`.
3. **Long-running commands** — slice 6.4 streaming + slice 8.3 fallback both honour `threading.Event` cancellation. SSH `Ctrl-C` propagates as `SIGINT`; the CLI's signal handlers convert it into a cooperative cancel.

## Forwarding the web terminal over SSH

Want the slice 17.1 web terminal exposed to your laptop without opening a port on the remote host? Use SSH local forwarding:

```bash
# On the remote host:
mythic-vibe surface web --port 8765 --token "$TOKEN"

# From your laptop:
ssh -L 8765:localhost:8765 user@host
# Then open http://localhost:8765 in your browser.
```

The web terminal binds to `127.0.0.1` only by default — SSH forwarding is the only ingress.

## Multi-user SSH

The CLI keeps per-project state in `mythic/`. If multiple operators SSH into the same machine and run commands against the same project root, the v1.0 hardening covers:

- **Intra-process** writes serialize via `runtime/file_mutation_queue.py` (per-realpath `threading.Lock`).
- **Cross-process** writes can serialize via `runtime/cross_process_lock.py` (POSIX `fcntl.flock` / Windows `msvcrt.locking`) — opt-in for callers, wired into `forge_ledger.py` and into `JsonStateStore.FileLock(cross_process=True)`.

These cover concurrent-write races on shared files. Operator-level concurrency at the workflow layer (two operators running `mythic-vibe ai run` simultaneously against the same packet) is still not coordinated above the file-lock layer.

For multi-operator setups, one of:

1. Each operator works in their own checkout under their own home dir.
2. Operators coordinate out-of-band (chat, ticket).
3. Wrap the bridge in tmux and share via `tmux attach -t mythic`.

## Running as a systemd service

The PH-17 surfaces (web terminal, chat bridge) are designed to run unattended. A minimal systemd unit:

```ini
[Unit]
Description=Mythic Vibe CLI — web terminal
After=network-online.target

[Service]
Type=simple
User=mythic
WorkingDirectory=/srv/mythic-project
Environment=NO_COLOR=1
Environment=TERM=xterm-256color
ExecStart=/usr/local/bin/mythic-vibe surface web --port 8765 --token "%i"
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

The `%i` template parameter pairs with `systemctl start mythic-web@<token>`. Alternatively store the token in a file and reference it via `EnvironmentFile=`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Prompt freezes on `Y/n` | TTY detection wrong | Run with `--approval auto` flag explicitly |
| Garbled colors in piped output | No-color not set | `export NO_COLOR=1` |
| TUI layout looks broken | Narrow terminal | The narrow layout activates automatically below 78 columns; force with `MYTHIC_TUI_NARROW=1` |
| Web terminal returns 401 | Token mismatch | Verify the URL-safe token; the field is case-sensitive |
| `mythic-vibe ai stream` hangs | Stdin not closed | Pipe `< /dev/null` for non-interactive runs |
