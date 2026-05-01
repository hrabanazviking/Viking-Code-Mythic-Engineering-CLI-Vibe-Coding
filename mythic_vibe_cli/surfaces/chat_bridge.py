"""Chat bridge surface (PH-17 Slice 17.4).

Thin adapters that poll a chat backend and run CLI commands in
response to ``/cmd <name> <argv>`` messages. Two backends:

- **Matrix** — first-class, well-documented stdlib HTTP REST
  API. The bridge uses :func:`urllib.request` for sync calls to
  ``/_matrix/client/v3/sync`` (with a long-poll timeout).
- **Telegram** — second-class, simpler Bot API via
  ``api.telegram.org``. Same urllib approach.

Both backends are open-source-friendly: Matrix is the canonical
open-source choice; Telegram's Bot API is open even though the
client is closed.

The bridge is intentionally **stateless** — each poll cycle
runs whatever commands arrived since the last sync, then
returns. Operators run the bridge as a long-lived loop via
``mythic-vibe surface chat``; tests call ``handle_message`` /
``parse_command`` in isolation.

Cross-platform: pure stdlib (``urllib.request`` + ``json``).
"""

from __future__ import annotations

import io
import json
import shlex
import urllib.error
import urllib.parse
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from typing import Any


# Trigger prefix for chat-bridge command messages. Anything not
# starting with this prefix is ignored.
COMMAND_PREFIX = "/cmd"


@dataclass(frozen=True)
class ParsedCommand:
    """Result of parsing a chat message into a command + argv.
    ``valid=False`` records a parse failure with a reason."""

    valid: bool
    command: str = ""
    argv: tuple[str, ...] = ()
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "command": self.command,
            "argv": list(self.argv),
            "reason": self.reason,
        }


@dataclass
class ChatResponse:
    """Result of dispatching a parsed command. The bridge sends
    ``rendered`` back to the chat channel."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    rendered: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "rendered": self.rendered,
        }


def parse_command(message: str) -> ParsedCommand:
    """Parse a chat message into a typed command + argv. Messages
    that don't start with the trigger prefix are returned as
    ``valid=False`` with a reason."""
    text = (message or "").strip()
    if not text.startswith(COMMAND_PREFIX):
        return ParsedCommand(valid=False, reason="missing /cmd prefix")
    body = text[len(COMMAND_PREFIX):].strip()
    if not body:
        return ParsedCommand(valid=False, reason="empty command body")
    try:
        tokens = shlex.split(body)
    except ValueError as exc:
        return ParsedCommand(
            valid=False, reason=f"shlex error: {exc}"
        )
    if not tokens:
        return ParsedCommand(valid=False, reason="empty token list")
    command = tokens[0]
    argv = tuple(tokens[1:])
    return ParsedCommand(valid=True, command=command, argv=argv)


def handle_message(message: str) -> ChatResponse | None:
    """Pure dispatch: parse + run + render. Returns ``None`` when
    the message wasn't a command (so the bridge stays silent on
    chitchat). Always returns a :class:`ChatResponse` for valid
    ``/cmd`` lines, even on errors — operators see exit codes."""
    from ..app import build_parser
    from ..commands import COMMAND_HANDLERS

    parsed = parse_command(message)
    if not parsed.valid:
        return None

    if parsed.command not in COMMAND_HANDLERS:
        return ChatResponse(
            command=parsed.command,
            exit_code=2,
            stdout="",
            stderr=f"unknown command: {parsed.command}",
            rendered=f"❌ unknown command: {parsed.command}",
        )

    parser = build_parser()
    try:
        ns = parser.parse_args([parsed.command, *parsed.argv])
    except SystemExit as exc:
        return ChatResponse(
            command=parsed.command,
            exit_code=2,
            stdout="",
            stderr=f"argparse rejected argv: exit={exc.code}",
            rendered=(
                f"❌ {parsed.command}: argparse rejected argv "
                f"(exit={exc.code})"
            ),
        )

    handler = COMMAND_HANDLERS[parsed.command]
    out = io.StringIO()
    err = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            exit_code = int(handler(ns) or 0)
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 1
    except Exception as exc:  # noqa: BLE001 — never propagate
        exit_code = 1
        err.write(f"{type(exc).__name__}: {exc}\n")

    rendered = _render_chat_block(parsed.command, exit_code, out.getvalue(), err.getvalue())
    return ChatResponse(
        command=parsed.command,
        exit_code=exit_code,
        stdout=out.getvalue(),
        stderr=err.getvalue(),
        rendered=rendered,
    )


def _render_chat_block(
    command: str, exit_code: int, stdout: str, stderr: str
) -> str:
    """Compose a chat-friendly response. We use a fenced code
    block so Matrix / Telegram render the output in monospace.
    Truncated at 1500 chars total (keeps under typical chat
    message limits)."""
    icon = "✅" if exit_code == 0 else "❌"
    parts: list[str] = [f"{icon} `{command}` (exit {exit_code})"]
    body = ""
    if stdout:
        body += stdout
    if stderr:
        body += ("\n--- stderr ---\n" if body else "") + stderr
    if not body:
        body = "(no output)"
    if len(body) > 1500:
        body = body[:1497] + "..."
    parts.append("```\n" + body.rstrip("\n") + "\n```")
    return "\n".join(parts)


# ---- Matrix client ----------------------------------------------------


@dataclass
class MatrixConfig:
    homeserver: str  # e.g. "https://matrix.org"
    access_token: str
    room_id: str
    sync_timeout_ms: int = 30_000


def _matrix_request(
    config: MatrixConfig,
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call a Matrix REST endpoint via stdlib urllib. Returns the
    parsed JSON body. Raises :class:`urllib.error.URLError` /
    :class:`urllib.error.HTTPError` on transport failures —
    callers handle those for the long-poll loop."""
    url = config.homeserver.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    data: bytes | None = None
    headers = {
        "Authorization": f"Bearer {config.access_token}",
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=config.sync_timeout_ms / 1000 + 5) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def matrix_send_message(
    config: MatrixConfig,
    text: str,
    *,
    txn_id: str | None = None,
) -> dict[str, Any]:
    """Send ``text`` as an ``m.room.message`` to the configured
    room. Returns the Matrix response payload."""
    import secrets as _secrets

    txn = txn_id or f"mvc-{_secrets.token_hex(6)}"
    return _matrix_request(
        config,
        "PUT",
        f"/_matrix/client/v3/rooms/{urllib.parse.quote(config.room_id)}/send/m.room.message/{urllib.parse.quote(txn)}",
        body={"msgtype": "m.text", "body": text, "format": "org.matrix.custom.html"},
    )


# ---- Telegram client --------------------------------------------------


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: int | str
    api_root: str = "https://api.telegram.org"


def _telegram_request(
    config: TelegramConfig,
    method_name: str,
    *,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{config.api_root}/bot{urllib.parse.quote(config.bot_token)}/{method_name}"
    data = json.dumps(body or {}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def telegram_send_message(config: TelegramConfig, text: str) -> dict[str, Any]:
    """Post ``text`` to the configured Telegram chat."""
    return _telegram_request(
        config,
        "sendMessage",
        body={
            "chat_id": config.chat_id,
            "text": text,
            "parse_mode": "Markdown",
        },
    )


__all__ = [
    "COMMAND_PREFIX",
    "ChatResponse",
    "MatrixConfig",
    "ParsedCommand",
    "TelegramConfig",
    "handle_message",
    "matrix_send_message",
    "parse_command",
    "telegram_send_message",
]
