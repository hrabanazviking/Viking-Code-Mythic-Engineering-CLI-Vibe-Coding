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
import os
import shlex
import urllib.error
import urllib.parse
import urllib.request
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Trigger prefix for chat-bridge command messages. Anything not
# starting with this prefix is ignored.
COMMAND_PREFIX = "/cmd"


# Phase E.0 2026-05-02 (audit remediation, finding #2): master env
# gate for the chat-bridge surface. The bridge stays default-off
# until the operator explicitly opts in by setting this to a truthy
# value. Matches the durable rule for default-off feature gates and
# mirrors ``MYTHIC_VOICE_TTS_ENABLED`` from PH-07.
CHAT_BRIDGE_ENABLED_ENV = "MYTHIC_CHAT_BRIDGE_ENABLED"

# Sentinel value an operator must set explicitly in
# ``MYTHIC_CHAT_*_ALLOWED_*`` env vars (or the equivalent file
# field) to opt into broadcast listening — i.e. accept commands from
# any room / chat / user. Without this, the validate() method
# refuses to start the bridge.
ALLOWLIST_BROADCAST = "*"

_TRUTHY = {"1", "true", "yes", "on"}


def is_chat_bridge_enabled() -> bool:
    """Read :data:`CHAT_BRIDGE_ENABLED_ENV`. Empty / unset / falsy
    values return ``False``. The bridge stays default-off until the
    operator explicitly opts in."""
    raw = os.environ.get(CHAT_BRIDGE_ENABLED_ENV, "").strip().lower()
    return raw in _TRUTHY


class ChatBridgeConfigError(ValueError):
    """Raised by :meth:`MatrixConfig.validate` /
    :meth:`TelegramConfig.validate` when required fields are missing
    or no allowlist was set. Carries a human-readable message
    operators can act on."""


def _parse_csv_allowlist(raw: str) -> tuple[str, ...]:
    """Parse a comma-separated allowlist string into a tuple. The
    broadcast sentinel ``*`` (alone or anywhere in the list) yields
    ``(ALLOWLIST_BROADCAST,)``; empty / whitespace-only input yields
    ``()``. Surrounding whitespace on each entry is stripped;
    duplicates are de-duped while preserving order."""
    cleaned = (raw or "").strip()
    if not cleaned:
        return ()
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    if any(p == ALLOWLIST_BROADCAST for p in parts):
        return (ALLOWLIST_BROADCAST,)
    seen: set[str] = set()
    deduped: list[str] = []
    for part in parts:
        if part not in seen:
            seen.add(part)
            deduped.append(part)
    return tuple(deduped)


def _read_config_file(path: Path) -> dict[str, Any]:
    """Read a JSON config file used by ``from_file`` classmethods.
    Returns the parsed top-level object (expected to contain
    ``matrix`` and/or ``telegram`` sub-sections). Raises ``OSError``
    on filesystem errors and ``ValueError`` on parse errors —
    caller wraps both in :class:`ChatBridgeConfigError`."""
    text = Path(path).read_text(encoding="utf-8")
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError(f"Chat bridge config root must be an object, got {type(parsed).__name__}")
    return parsed


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
    room_id: str  # legacy default-room for matrix_send_message
    sync_timeout_ms: int = 30_000
    # Phase E.0 2026-05-02 (audit remediation, finding #2): additive
    # fields supporting the long-poll loop (E.1). All have safe
    # defaults so legacy three-arg constructions remain valid.
    user_id: str = ""  # bot's own MXID, e.g. "@mybot:matrix.org" — used for echo prevention
    allowed_rooms: tuple[str, ...] = ()  # rooms the bridge listens in; empty = no allowlist (validate() refuses unless ALLOWLIST_BROADCAST)

    # ---- Phase E.0: classmethods for env / file / merged construction --
    @classmethod
    def from_env(cls) -> "MatrixConfig":
        """Construct a :class:`MatrixConfig` from environment variables.

        Recognised env vars (all under the ``MYTHIC_CHAT_MATRIX_`` prefix):
          - ``HOMESERVER`` (default: ``https://matrix.org``)
          - ``ACCESS_TOKEN`` (required for ``validate()`` to succeed)
          - ``USER_ID`` (the bot's MXID; required for echo prevention)
          - ``ALLOWED_ROOMS`` (comma-separated list of room IDs;
            ``*`` opts into broadcast)
          - ``ROOM_ID`` (legacy default-room; falls back to first
            allowed room if not set)
          - ``SYNC_TIMEOUT_MS`` (default: 30000)
        """
        env = os.environ
        allowed_raw = env.get("MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS", "").strip()
        allowed = _parse_csv_allowlist(allowed_raw)
        room_id = env.get("MYTHIC_CHAT_MATRIX_ROOM_ID", "").strip()
        if not room_id and allowed and allowed[0] != ALLOWLIST_BROADCAST:
            room_id = allowed[0]
        try:
            sync_timeout_ms = int(
                env.get("MYTHIC_CHAT_MATRIX_SYNC_TIMEOUT_MS", "30000").strip()
                or 30000
            )
        except (TypeError, ValueError):
            sync_timeout_ms = 30_000
        return cls(
            homeserver=env.get("MYTHIC_CHAT_MATRIX_HOMESERVER", "https://matrix.org").strip()
            or "https://matrix.org",
            access_token=env.get("MYTHIC_CHAT_MATRIX_ACCESS_TOKEN", "").strip(),
            room_id=room_id,
            sync_timeout_ms=sync_timeout_ms,
            user_id=env.get("MYTHIC_CHAT_MATRIX_USER_ID", "").strip(),
            allowed_rooms=allowed,
        )

    @classmethod
    def from_file(cls, path: Path) -> "MatrixConfig":
        """Read a JSON config file and return its ``matrix`` section
        as a :class:`MatrixConfig`. The file may carry both
        ``matrix`` and ``telegram`` sections; only ``matrix`` is
        consumed here. Missing fields take dataclass defaults."""
        payload = _read_config_file(path)
        section = payload.get("matrix") if isinstance(payload, dict) else None
        if not isinstance(section, dict):
            section = {}
        allowed_raw = section.get("allowed_rooms", [])
        if isinstance(allowed_raw, str):
            allowed = _parse_csv_allowlist(allowed_raw)
        elif isinstance(allowed_raw, (list, tuple)):
            allowed = tuple(str(x).strip() for x in allowed_raw if str(x).strip())
        else:
            allowed = ()
        room_id = str(section.get("room_id", "") or "").strip()
        if not room_id and allowed and allowed[0] != ALLOWLIST_BROADCAST:
            room_id = allowed[0]
        return cls(
            homeserver=str(section.get("homeserver", "https://matrix.org") or "https://matrix.org").strip(),
            access_token=str(section.get("access_token", "") or "").strip(),
            room_id=room_id,
            sync_timeout_ms=int(section.get("sync_timeout_ms", 30_000) or 30_000),
            user_id=str(section.get("user_id", "") or "").strip(),
            allowed_rooms=allowed,
        )

    @classmethod
    def from_sources(cls, *, config_path: Path | None = None) -> "MatrixConfig":
        """Merge env vars and an optional config file. **File values
        win over env values when both are set** (file is the more
        specific source); env supplies defaults for fields the file
        omits. When ``config_path`` is None, behaves like
        :meth:`from_env`."""
        env_cfg = cls.from_env()
        if config_path is None:
            return env_cfg
        try:
            file_cfg = cls.from_file(config_path)
        except (OSError, ValueError) as exc:
            raise ChatBridgeConfigError(
                f"Could not read Matrix config file {config_path}: {exc}"
            ) from exc
        # File overrides env where the file value is non-empty / set.
        return cls(
            homeserver=file_cfg.homeserver or env_cfg.homeserver,
            access_token=file_cfg.access_token or env_cfg.access_token,
            room_id=file_cfg.room_id or env_cfg.room_id,
            sync_timeout_ms=file_cfg.sync_timeout_ms or env_cfg.sync_timeout_ms,
            user_id=file_cfg.user_id or env_cfg.user_id,
            allowed_rooms=file_cfg.allowed_rooms or env_cfg.allowed_rooms,
        )

    def validate(self) -> None:
        """Raise :class:`ChatBridgeConfigError` if the config is not
        safe to start a long-poll loop against. Required fields:
        ``access_token``. Required allowlist: ``allowed_rooms`` must
        be set (set to ``("*",)`` to opt into broadcast — strongly
        not recommended)."""
        problems: list[str] = []
        if not self.access_token:
            problems.append(
                "Matrix access_token is required (MYTHIC_CHAT_MATRIX_ACCESS_TOKEN)"
            )
        if not self.homeserver:
            problems.append("Matrix homeserver is required")
        if not self.allowed_rooms:
            problems.append(
                "Matrix allowed_rooms must be set (MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS) — "
                f"set to '{ALLOWLIST_BROADCAST}' to opt into broadcast (not recommended)"
            )
        if problems:
            raise ChatBridgeConfigError(
                "Matrix config invalid: " + "; ".join(problems)
            )

    def is_room_allowed(self, room_id: str) -> bool:
        """Return True if ``room_id`` is on this config's allowlist
        (or the allowlist is the broadcast sentinel)."""
        if not self.allowed_rooms:
            return False
        if ALLOWLIST_BROADCAST in self.allowed_rooms:
            return True
        return room_id in self.allowed_rooms


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
    room_id: str | None = None,
) -> dict[str, Any]:
    """Send ``text`` as an ``m.room.message`` to a room. Returns the
    Matrix response payload.

    Phase E.0 2026-05-02 (audit remediation): the ``room_id`` keyword
    was added so the long-poll loop can reply to whichever room the
    incoming command came from. Existing callers that pass only
    ``config`` + ``text`` continue to use ``config.room_id`` (legacy
    semantic preserved)."""
    import secrets as _secrets

    target_room = (room_id or config.room_id or "").strip()
    if not target_room:
        raise ChatBridgeConfigError(
            "matrix_send_message requires either a room_id keyword "
            "argument or config.room_id to be set"
        )
    txn = txn_id or f"mvc-{_secrets.token_hex(6)}"
    return _matrix_request(
        config,
        "PUT",
        f"/_matrix/client/v3/rooms/{urllib.parse.quote(target_room)}/send/m.room.message/{urllib.parse.quote(txn)}",
        body={"msgtype": "m.text", "body": text, "format": "org.matrix.custom.html"},
    )


# ---- Telegram client --------------------------------------------------


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: int | str  # legacy default-chat for telegram_send_message
    api_root: str = "https://api.telegram.org"
    # Phase E.0 2026-05-02 (audit remediation, finding #2): additive
    # fields supporting the long-poll loop (E.2). All have safe
    # defaults so legacy two-arg constructions remain valid.
    allowed_chats: tuple[str, ...] = ()  # chat IDs the bridge listens in
    allowed_users: tuple[str, ...] = ()  # user IDs the bridge accepts commands from
    poll_timeout_s: int = 30  # long-poll timeout for getUpdates

    @classmethod
    def from_env(cls) -> "TelegramConfig":
        """Construct a :class:`TelegramConfig` from environment variables.

        Recognised env vars (all under the ``MYTHIC_CHAT_TELEGRAM_`` prefix):
          - ``BOT_TOKEN`` (required for ``validate()`` to succeed)
          - ``CHAT_ID`` (legacy default-chat; falls back to first
            allowed chat if not set)
          - ``ALLOWED_CHATS`` (comma-separated list of chat IDs;
            ``*`` opts into broadcast)
          - ``ALLOWED_USERS`` (comma-separated list of user IDs)
          - ``API_ROOT`` (default: ``https://api.telegram.org``)
          - ``POLL_TIMEOUT_S`` (default: 30)
        """
        env = os.environ
        allowed_chats = _parse_csv_allowlist(
            env.get("MYTHIC_CHAT_TELEGRAM_ALLOWED_CHATS", "")
        )
        allowed_users = _parse_csv_allowlist(
            env.get("MYTHIC_CHAT_TELEGRAM_ALLOWED_USERS", "")
        )
        chat_id_raw = env.get("MYTHIC_CHAT_TELEGRAM_CHAT_ID", "").strip()
        chat_id: int | str
        if chat_id_raw:
            try:
                chat_id = int(chat_id_raw)
            except ValueError:
                chat_id = chat_id_raw
        elif allowed_chats and allowed_chats[0] != ALLOWLIST_BROADCAST:
            try:
                chat_id = int(allowed_chats[0])
            except ValueError:
                chat_id = allowed_chats[0]
        else:
            chat_id = ""
        try:
            poll_timeout_s = int(
                env.get("MYTHIC_CHAT_TELEGRAM_POLL_TIMEOUT_S", "30").strip()
                or 30
            )
        except (TypeError, ValueError):
            poll_timeout_s = 30
        return cls(
            bot_token=env.get("MYTHIC_CHAT_TELEGRAM_BOT_TOKEN", "").strip(),
            chat_id=chat_id,
            api_root=env.get("MYTHIC_CHAT_TELEGRAM_API_ROOT", "https://api.telegram.org").strip()
            or "https://api.telegram.org",
            allowed_chats=allowed_chats,
            allowed_users=allowed_users,
            poll_timeout_s=poll_timeout_s,
        )

    @classmethod
    def from_file(cls, path: Path) -> "TelegramConfig":
        """Read a JSON config file and return its ``telegram`` section
        as a :class:`TelegramConfig`."""
        payload = _read_config_file(path)
        section = payload.get("telegram") if isinstance(payload, dict) else None
        if not isinstance(section, dict):
            section = {}
        allowed_chats_raw = section.get("allowed_chats", [])
        allowed_users_raw = section.get("allowed_users", [])
        if isinstance(allowed_chats_raw, str):
            allowed_chats = _parse_csv_allowlist(allowed_chats_raw)
        elif isinstance(allowed_chats_raw, (list, tuple)):
            allowed_chats = tuple(str(x).strip() for x in allowed_chats_raw if str(x).strip())
        else:
            allowed_chats = ()
        if isinstance(allowed_users_raw, str):
            allowed_users = _parse_csv_allowlist(allowed_users_raw)
        elif isinstance(allowed_users_raw, (list, tuple)):
            allowed_users = tuple(str(x).strip() for x in allowed_users_raw if str(x).strip())
        else:
            allowed_users = ()
        chat_id_raw = section.get("chat_id", "")
        chat_id: int | str
        if isinstance(chat_id_raw, int):
            chat_id = chat_id_raw
        elif isinstance(chat_id_raw, str) and chat_id_raw.strip():
            try:
                chat_id = int(chat_id_raw.strip())
            except ValueError:
                chat_id = chat_id_raw.strip()
        elif allowed_chats and allowed_chats[0] != ALLOWLIST_BROADCAST:
            try:
                chat_id = int(allowed_chats[0])
            except ValueError:
                chat_id = allowed_chats[0]
        else:
            chat_id = ""
        return cls(
            bot_token=str(section.get("bot_token", "") or "").strip(),
            chat_id=chat_id,
            api_root=str(section.get("api_root", "https://api.telegram.org") or "https://api.telegram.org").strip(),
            allowed_chats=allowed_chats,
            allowed_users=allowed_users,
            poll_timeout_s=int(section.get("poll_timeout_s", 30) or 30),
        )

    @classmethod
    def from_sources(cls, *, config_path: Path | None = None) -> "TelegramConfig":
        """Merge env vars and an optional config file (file wins)."""
        env_cfg = cls.from_env()
        if config_path is None:
            return env_cfg
        try:
            file_cfg = cls.from_file(config_path)
        except (OSError, ValueError) as exc:
            raise ChatBridgeConfigError(
                f"Could not read Telegram config file {config_path}: {exc}"
            ) from exc
        return cls(
            bot_token=file_cfg.bot_token or env_cfg.bot_token,
            chat_id=file_cfg.chat_id or env_cfg.chat_id,
            api_root=file_cfg.api_root or env_cfg.api_root,
            allowed_chats=file_cfg.allowed_chats or env_cfg.allowed_chats,
            allowed_users=file_cfg.allowed_users or env_cfg.allowed_users,
            poll_timeout_s=file_cfg.poll_timeout_s or env_cfg.poll_timeout_s,
        )

    def validate(self) -> None:
        """Raise :class:`ChatBridgeConfigError` if the config is not
        safe to start a long-poll loop against. Required:
        ``bot_token`` + at least ``allowed_chats`` (set to
        ``ALLOWLIST_BROADCAST`` to opt into broadcast)."""
        problems: list[str] = []
        if not self.bot_token:
            problems.append(
                "Telegram bot_token is required (MYTHIC_CHAT_TELEGRAM_BOT_TOKEN)"
            )
        if not self.allowed_chats:
            problems.append(
                "Telegram allowed_chats must be set (MYTHIC_CHAT_TELEGRAM_ALLOWED_CHATS) — "
                f"set to '{ALLOWLIST_BROADCAST}' to opt into broadcast (not recommended)"
            )
        if problems:
            raise ChatBridgeConfigError(
                "Telegram config invalid: " + "; ".join(problems)
            )

    def is_chat_allowed(self, chat_id: int | str) -> bool:
        """Return True if ``chat_id`` is on this config's allowlist."""
        if not self.allowed_chats:
            return False
        if ALLOWLIST_BROADCAST in self.allowed_chats:
            return True
        return str(chat_id) in self.allowed_chats

    def is_user_allowed(self, user_id: int | str) -> bool:
        """Return True if ``user_id`` is on this config's user
        allowlist. Empty allowed_users means **no user filter** —
        any user in an allowed chat may issue commands. Set
        explicit user IDs to lock down further."""
        if not self.allowed_users:
            return True
        if ALLOWLIST_BROADCAST in self.allowed_users:
            return True
        return str(user_id) in self.allowed_users


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


def telegram_send_message(
    config: TelegramConfig,
    text: str,
    *,
    chat_id: int | str | None = None,
) -> dict[str, Any]:
    """Post ``text`` to a Telegram chat. Returns the Bot API response
    payload.

    Phase E.0 2026-05-02 (audit remediation): the ``chat_id`` keyword
    was added so the long-poll loop can reply to whichever chat the
    incoming command came from. Existing callers that pass only
    ``config`` + ``text`` continue to use ``config.chat_id`` (legacy
    semantic preserved)."""
    target_chat = chat_id if chat_id not in (None, "") else config.chat_id
    if target_chat in (None, ""):
        raise ChatBridgeConfigError(
            "telegram_send_message requires either a chat_id keyword "
            "argument or config.chat_id to be set"
        )
    return _telegram_request(
        config,
        "sendMessage",
        body={
            "chat_id": target_chat,
            "text": text,
            "parse_mode": "Markdown",
        },
    )


__all__ = [
    "ALLOWLIST_BROADCAST",
    "CHAT_BRIDGE_ENABLED_ENV",
    "COMMAND_PREFIX",
    "ChatBridgeConfigError",
    "ChatResponse",
    "MatrixConfig",
    "ParsedCommand",
    "TelegramConfig",
    "handle_message",
    "is_chat_bridge_enabled",
    "matrix_send_message",
    "parse_command",
    "telegram_send_message",
]
