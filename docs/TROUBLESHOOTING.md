# Troubleshooting

The most common issues operators hit when running Mythic Vibe CLI, organised by symptom. Skim the table of contents, find your symptom, follow the recipe.

If nothing here matches your issue, see [`docs/SUPPORT.md`](SUPPORT.md) for how to file a bug report or a feature request, and [`SECURITY.md`](../SECURITY.md) for security-sensitive issues.

---

## Table of contents

1. [Install + first-run](#1-install--first-run)
2. [Doctor errors](#2-doctor-errors)
3. [AI provider issues](#3-ai-provider-issues)
4. [Plugin issues](#4-plugin-issues)
5. [TUI issues](#5-tui-issues)
6. [Chat-bridge issues](#6-chat-bridge-issues)
7. [Hermes Agent HTTP issues](#7-hermes-agent-http-issues)
8. [Cross-platform quirks](#8-cross-platform-quirks)
9. [Test / CI issues](#9-test--ci-issues)
10. [Release verification issues](#10-release-verification-issues)

---

## 1) Install + first-run

### `pipx: command not found`
Pipx is the recommended user installer but it's not bundled with Python. Install it once:

```bash
python -m pip install --user pipx
python -m pipx ensurepath
```

Then restart your shell so the new `~/.local/bin` (or platform equivalent) is on `PATH`. After that, `pipx install mythic-vibe-cli` works.

### `mythic-vibe: command not found` after `pipx install`
Pipx installs binaries to a per-user bin directory that may not be on `PATH`. Run:

```bash
pipx ensurepath
```

Restart your shell. If you still don't see it, run `pipx list` — the entry shows the exact install path.

### `ImportError: No module named 'textual'` when running `mythic-vibe tui`
The TUI is an opt-in extra. Install it:

```bash
pipx inject mythic-vibe-cli textual rich
# or, for a fresh install:
pipx install "mythic-vibe-cli[tui]"
```

### `ImportError: No module named 'anthropic'` (or `openai` / `google`)
AI provider SDKs are opt-in extras. Install the one you need:

```bash
pipx inject mythic-vibe-cli "mythic-vibe-cli[ai]"
```

For just one provider, the upstream package name is acceptable too: `pipx inject mythic-vibe-cli anthropic`.

### Standalone binary is "damaged and can't be opened" on macOS
This is Gatekeeper rejecting an un-notarized binary. The project ships un-notarized by design (no Apple Developer account required). Override per-binary:

```bash
xattr -d com.apple.quarantine ./mythic-vibe-macos-arm64
```

Or right-click the binary in Finder → **Open** → confirm the dialog. Subsequent runs work without prompting.

### Standalone binary triggers Windows SmartScreen
Same root cause — un-signed binary. Click **More info** → **Run anyway**. SmartScreen learns over time; after enough operators run the binary, the warning goes away.

### Launcher (`packaging/launcher`) hangs on first run
The launcher downloads `python-build-standalone` (~30-60 MB) on first invocation. The progress bar (PH-23.6) shows the download state. If the bar isn't moving, check:

- **Network reachable?** `curl -I https://github.com/astral-sh/python-build-standalone/releases/latest` should return 200/302.
- **Behind a corporate proxy?** Set `MYTHIC_LAUNCHER_MIRRORS=https://internal.artifactory/...` to an internal mirror.
- **DNS issue?** The launcher uses `ureq` which respects standard DNS — the same fix that works for `curl` works here.

To pin a strict integrity check, set `MYTHIC_LAUNCHER_REQUIRE_SHA=1` — this fails fast if the SHA256 doesn't match the embedded table.

---

## 2) Doctor errors

### `Missing required file: SYSTEM_VISION.md` when running on a non-Mythic project
You're running `mythic-vibe doctor` against a directory that hasn't been initialized. Either:

```bash
mythic-vibe init --goal "Your project goal"
```

Or run doctor against the right directory: `mythic-vibe doctor --path /path/to/mythic-project`.

### `Legacy docs/index2.md is still present` warning
The original docs entry point was `docs/index2.md`; v1.x moved it to `docs/INDEX.md`. The legacy file is kept for any operator who hardcoded the path; the warning is informational, not blocking.

### Doctor reports JSON parse errors on `mythic/status.json`
Likely a partial-write from a crashed earlier session. Mitigations:

- **Check the backup**: `ls -la mythic/status.json*` — older `.bak` snapshots may exist.
- **Re-run init**: `mythic-vibe init --goal "..." --force` rebuilds the file.
- **Restore from git**: if the project is under version control, `git restore mythic/status.json`.

PH-19 introduced atomic write + cross-process locking on this file (see `runtime/atomic_write.py` + `runtime/cross_process_lock.py`), so the partial-write window is now sub-millisecond.

---

## 3) AI provider issues

### `ANTHROPIC_API_KEY is required`
Set the env var: `export ANTHROPIC_API_KEY=sk-ant-...`. Verify with `mythic-vibe ai providers --json` — the `configured` flag should be true for the provider you set.

### `ConnectionError: Ollama daemon unreachable`
Start the daemon: `ollama serve` (or your platform's equivalent — systemd unit on Linux, launchd plist on macOS, NSSM service on Windows). Verify with `curl http://localhost:11434/api/tags`.

If the daemon runs on a non-default host:port, set `OLLAMA_HOST=remote.host:11434`.

### `ProviderListingError: HTTP 401` on `mythic-vibe ai models --provider anthropic --remote`
The API key is valid for the messages endpoint but missing the `models:read` scope. Anthropic API keys carry different scopes; regenerate at the console with the right permissions.

### Daily cost cap blocks every call
Check `MYTHIC_DAILY_COST_CAP_USD` — if set, every provider call estimates cost and blocks if the running total would exceed the cap. Either raise the cap, switch to a cheaper model, or unset the env var.

```bash
unset MYTHIC_DAILY_COST_CAP_USD
# or temporarily raise:
export MYTHIC_DAILY_COST_CAP_USD=10.00
```

### Provider call succeeds but redacts the response in logs
The provider-call log applies secret redaction to anything matching common API-key patterns (`sk-...`, `AIza...`, `ghp_...`). If your AI response legitimately contains a string matching one of those patterns, the log will show `[REDACTED]`. The CLI's stdout output is not redacted — only the persisted log file at `mythic/ai/provider_calls.jsonl`.

---

## 4) Plugin issues

### Plugin doesn't appear in `mythic-vibe plugin list`
The plugin must be `pip install`ed (or `pipx inject`ed into the same env) and declare an entry point in its `pyproject.toml`:

```toml
[project.entry-points."mythic_vibe_cli.plugins"]
my_plugin = "my_package.plugin:Plugin"
```

After install, `mythic-vibe plugin list` discovers it via `importlib.metadata.entry_points`. If still missing, run `pipx list --include-injected` and check the env you targeted.

### `Plugin breaker tripped: <name>`
The plugin failed `MYTHIC_PLUGIN_BREAKER_THRESHOLD` consecutive invocations (default 3). The breaker auto-resets after `MYTHIC_PLUGIN_BREAKER_COOLDOWN_S` seconds. To clear it manually:

```bash
mythic-vibe plugin doctor --reset-breakers
```

### `Plugin sandbox: capability denied`
The plugin requested a capability that's not granted. See the plugin's declared capabilities (`mythic-vibe plugin doctor`) and your local allow-list. Capability denials are deliberate — `docs/PLUGIN_AUTHORING_GUIDE.md` explains the model.

---

## 5) TUI issues

### TUI shows garbled characters / no colors
Your terminal doesn't support full UTF-8 / 256-color. Workarounds:

- **Switch terminals**: Windows Terminal / iTerm2 / Alacritty / Kitty / Wezterm all work.
- **Force narrow layout**: `MYTHIC_TUI_NARROW=1 mythic-vibe tui`.
- **Disable rich rendering**: `MYTHIC_RICH=0` falls back to plain text.

### TUI panics with `RuntimeError: no running event loop`
Textual requires an asyncio loop. If you're invoking the TUI from inside a Jupyter notebook or another already-running loop, that's not supported — run the TUI from a fresh shell.

### Keyboard shortcuts don't work
The bindings table is rendered by the help overlay (`?` from any TUI screen). If a key registers in some shells but not others, your terminal multiplexer (tmux / screen) is intercepting it before Textual sees it. Most multiplexers support a passthrough escape (e.g. tmux's prefix-prefix).

---

## 6) Chat-bridge issues

### `Chat bridge is not enabled` on `mythic-vibe surface chat --run`
Set the master gate: `export MYTHIC_CHAT_BRIDGE_ENABLED=1`. The default-off design means a misconfigured chat surface can't accidentally start polling.

### Matrix bridge connects but never receives messages
Common causes:

- **Room not in allow-list**: `MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS` defaults to just the primary `MYTHIC_CHAT_MATRIX_ROOM_ID`. Add other rooms explicitly.
- **Bot not joined**: the user behind `MYTHIC_CHAT_MATRIX_USER_ID` must be a member of every allow-listed room. Joining from another client (Element / fluffychat) is the simplest fix.
- **Sync timeout too low**: `MYTHIC_CHAT_MATRIX_SYNC_TIMEOUT_MS=30000` is the default. Lower values can hide messages on flaky networks.

### Telegram bridge replies to wrong chat
The bot replies into the chat the message came from, not `MYTHIC_CHAT_TELEGRAM_CHAT_ID`. The chat-id env var only sets which chats are *allowed* to receive replies; allow-list determines *which messages get processed*. If you want all replies to go to a single channel, configure that at the bot side (BotFather).

### Bridge logs show "transient error" repeatedly
Network glitch + the exponential-backoff loop is doing its job. PH-19.0 / BS-4 fixed a real bug here where the backoff reset prematurely; if you see `attempt=0` over and over, you're on a pre-PH-19 build and should upgrade.

---

## 7) Hermes Agent HTTP issues

### `401 invalid or missing token`
The token must be supplied via:

- `X-Hermes-Token: <token>` HTTP header, OR
- `?token=<token>` query string (GET), OR
- `{"token": "..."}` field in the POST body for `/api/invoke`

The token is auto-generated when you start the surface — copy it from the start-up banner or the `mythic/hermes/token.txt` file. Constant-time comparison means timing attacks won't help.

### `413 payload too large`
The default cap is 65536 bytes (`MAX_REQUEST_BODY_BYTES` in `agent_api/http_api.py`). For legitimate large payloads, run a separate Hermes instance with a custom config — the cap is intentional to prevent memory exhaustion.

### `404 not found` on `/api/state`
The `state_show` tool isn't registered in your Hermes core. The default agent (`build_default_agent`) wires all 18 tools; if you're using a custom HermesCore, register the tool yourself.

---

## 8) Cross-platform quirks

### Permission denied on POSIX writing to `~/.mythic-vibe/`
The directory is created with the operator's own umask. If you're running as a different user (sudo, container, CI), point `MYTHIC_HOME` somewhere writable:

```bash
export MYTHIC_HOME=/tmp/mythic-runtime
```

### Windows path-too-long errors
Windows MAX_PATH is 260 characters by default. Mythic doesn't trip this for normal usage, but a deeply-nested project with long packet IDs might. Enable Windows long-path support (system-wide registry change, requires admin):

```
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1
```

### File contents differ between Windows and POSIX checkout
PH-24.4 fixed the runtime side of this — every persistent on-disk artifact is now byte-stable across platforms. If you still see differences, check **Git** itself: `git config core.autocrlf` defaults to `true` on Windows, which mangles line endings on checkout. Set it to `input` or `false`:

```bash
git config --global core.autocrlf input
```

### Termux: `pip install` fails to compile a C extension
Termux's Python is fine; the issue is usually missing build tooling. Install the meta-package:

```bash
pkg install python python-pip clang make
```

The base CLI is stdlib-only so this only matters for optional extras (`[ai]` pulls Cython-based deps).

---

## 9) Test / CI issues

### Tests fail with `Absolute-path-leak guard tripped`
A test left debris under the repo root that matches a known absolute-path leak pattern (Users / private / var / tmp / AppData / ProgramData). Look at the failing test's path-handling logic — it's almost always treating `tempfile.gettempdir()` as a relative path. The guard is at `tests/conftest.py`.

To temporarily disable while debugging:

```bash
MYTHIC_LEAK_GUARD_DISABLED=1 pytest tests/your_test.py
```

### `pytest-cov` reports lower coverage than expected
Coverage is union-of-tests — running a subset of tests will report lower aggregate coverage than the full suite. Always run the full suite for the canonical number:

```bash
pytest tests/ --cov=mythic_vibe_cli
```

### CI fails on Windows but works on Linux/macOS
The most common culprit is path separators. PH-24.4 hardened the runtime; if you find a regression, file a bug — the test suite at `tests/test_cross_platform_invariants.py` is your guard.

### CI takes too long
The full test suite runs in ~2 minutes locally. CI overhead (checkout, dep install, matrix sharding) brings it to ~5-8 min per OS. If a single PR takes >20 min, check for flakes — `pytest --lf` reruns just the last failures.

---

## 10) Release verification issues

### `cosign verify` fails with "no matching signatures"
You're verifying against the wrong cert identity. The expected identity is the GitHub Actions OIDC subject — see [`docs/security/verifying_artifacts.md`](security/verifying_artifacts.md) for the per-channel exact strings. The most common mistake is forgetting the workflow ref (`@refs/tags/vX.Y.Z`).

### `slsa-verifier` reports "expected source repo doesn't match"
You're using a token from one repo to verify an artifact from another. Verify against the original `hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding` repo regardless of where you cloned to.

### Sigstore bundle download is 404
The bundle is a separate asset on the GitHub Release. For PyPI artifacts, the `.sigstore` lives next to the `.whl` / `.tar.gz` — `pip download mythic-vibe-cli` doesn't fetch it. Use the GitHub Release page or `gh release download v1.0.0 --pattern '*.sigstore'`.

---

## Still stuck?

- Check the [issue tracker](https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/issues) — your issue may already be filed.
- Read the relevant operator-facing doc:
  - [Quickstart](quickstart.md)
  - [Install Guide](INSTALL.md)
  - [Hermes Agent](HERMES_AGENT.md)
  - [Plugin Authoring Guide](PLUGIN_AUTHORING_GUIDE.md)
  - [Verifying Artifacts](security/verifying_artifacts.md)
- File a new issue with: version, channel, OS, full reproduction. The issue template walks you through the structure.

Last updated: 2026-05-06.
