"""Long-poll loops for the chat bridge surface (Phase E, 2026-05-02).

Background
==========

The first 2026-05-02 audit (`AUDIT_FAKE_TEMP_CODE_2026-05-02.md`,
finding #2, **High** severity) caught the slice-17.4 chat bridge as
**scaffolding-and-exit only** — `mythic-vibe surface chat --backend
matrix|telegram` printed a notice and returned without polling
anything. Phase E ships the actually-running bridge: long-poll loops
for both Matrix (`/sync`) and Telegram (`getUpdates`) that:

- Listen on **allowlisted rooms / chats** only (config refuses to
  start without an explicit allowlist; ``"*"`` is the
  opt-in-broadcast sentinel and is strongly discouraged).
- Dispatch each `/cmd <name> <argv>` message through
  :func:`chat_bridge.handle_message` (the existing pure-dispatch
  layer; reused without modification).
- Reply to **the originating room / chat** via the new
  ``room_id`` / ``chat_id`` keyword overrides on
  ``matrix_send_message`` / ``telegram_send_message``.
- **Skip the bot's own messages** to prevent reply loops (echo
  prevention).
- **Reconnect with exponential backoff** on transient HTTP errors
  (5xx, network resets); fail fast on 4xx (likely auth — not
  transient).
- **Honour ``stop_event``** between sync calls for clean shutdown
  (used by SIGINT / SIGTERM handlers in ``cmd_surface_chat``).

Both loops are pure-stdlib (urllib + threading + time + json) and
fully testable via injected ``transport`` / ``clock_sleep`` callables.

Cross-platform: Windows / macOS / Linux behave identically.
"""

from __future__ import annotations

import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .chat_bridge import (
    ChatResponse,
    MatrixConfig,
    TelegramConfig,
    _matrix_request,
    handle_message,
    matrix_send_message,
    telegram_send_message,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


@dataclass
class _Backoff:
    """Exponential-with-cap backoff for transient HTTP failures.

    First failure waits ``base`` seconds; each subsequent failure
    multiplies by ``factor`` up to ``cap``. Successful operations
    reset the attempt counter."""

    base: float = 1.0
    factor: float = 2.0
    cap: float = 60.0
    attempt: int = 0

    def next_delay(self) -> float:
        delay = min(self.base * (self.factor ** self.attempt), self.cap)
        self.attempt += 1
        return delay

    def reset(self) -> None:
        self.attempt = 0


def _log(prefix: str, message: str) -> None:
    """Write a single timestamped line to stderr — the chat-bridge
    loops' diagnostic channel. Operators capture this via systemd /
    NSSM / launchd journals. Best-effort; never raises."""
    try:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        print(f"[{ts}] [{prefix}] {message}", file=sys.stderr, flush=True)
    except Exception:  # noqa: BLE001 - logging must never crash the loop
        pass


def _is_transient_http_error(exc: BaseException) -> bool:
    """Classify an HTTP / network exception as transient (worth
    retrying) or terminal (auth / config — fail fast). 5xx and
    connection-level errors are transient; 4xx is terminal."""
    if isinstance(exc, urllib.error.HTTPError):
        # 408 Request Timeout, 429 Too Many Requests, 5xx — transient.
        # All other 4xx (auth / not-found / forbidden) — terminal.
        return exc.code in (408, 429) or 500 <= exc.code < 600
    if isinstance(exc, urllib.error.URLError):
        return True  # network-level, retry
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    return False


# ---------------------------------------------------------------------------
# Matrix /sync loop
# ---------------------------------------------------------------------------


def _matrix_sync(
    config: MatrixConfig,
    *,
    since: str | None = None,
    transport: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """One Matrix ``/sync`` call. ``transport`` defaults to the
    module-level :func:`chat_bridge._matrix_request`; tests inject
    a stub. Honours the config's sync_timeout_ms."""
    params: dict[str, Any] = {"timeout": config.sync_timeout_ms}
    if since:
        params["since"] = since
    request_fn = transport if transport is not None else _matrix_request
    return request_fn(
        config,
        "GET",
        "/_matrix/client/v3/sync",
        params=params,
    )


def _matrix_extract_messages(
    sync_payload: dict[str, Any],
) -> list[tuple[str, str, str, str]]:
    """Pull text-message events out of a /sync payload. Returns a
    list of ``(room_id, sender, event_id, body)`` tuples — one per
    ``m.room.message`` of msgtype ``m.text``. Non-text events,
    edits, and structural noise are filtered out."""
    out: list[tuple[str, str, str, str]] = []
    rooms = sync_payload.get("rooms")
    if not isinstance(rooms, dict):
        return out
    join = rooms.get("join")
    if not isinstance(join, dict):
        return out
    for room_id, room_data in join.items():
        if not isinstance(room_data, dict):
            continue
        timeline = room_data.get("timeline")
        if not isinstance(timeline, dict):
            continue
        events = timeline.get("events") or []
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, dict):
                continue
            if event.get("type") != "m.room.message":
                continue
            content = event.get("content")
            if not isinstance(content, dict):
                continue
            if content.get("msgtype") != "m.text":
                continue
            sender = str(event.get("sender") or "")
            event_id = str(event.get("event_id") or "")
            body = str(content.get("body") or "")
            if not body:
                continue
            out.append((str(room_id), sender, event_id, body))
    return out


def run_matrix_loop(
    config: MatrixConfig,
    *,
    stop_event: threading.Event | None = None,
    max_iterations: int | None = None,
    transport: Callable[..., dict[str, Any]] | None = None,
    sender: Callable[..., dict[str, Any]] | None = None,
    handler: Callable[[str], ChatResponse | None] | None = None,
    clock_sleep: Callable[[float], None] = time.sleep,
    backoff: _Backoff | None = None,
) -> int:
    """Run the Matrix long-poll loop against ``config``.

    Returns the number of dispatched messages (0 means no commands
    arrived during the run).

    The function blocks until one of:
      - ``stop_event`` is set (clean shutdown);
      - a non-transient HTTP error fires (auth / config — terminal);
      - ``max_iterations`` is reached (test guard).

    Injection points (tests):
      - ``transport``: replaces ``_matrix_request`` for ``/sync``
        and the legacy reply path.
      - ``sender``: replaces ``matrix_send_message`` (so tests can
        capture replies without HTTP).
      - ``handler``: replaces :func:`handle_message` (so tests can
        assert dispatch shape without running the full CLI).
      - ``clock_sleep``: replaces ``time.sleep`` (tests pass a no-op).
      - ``backoff``: pre-built ``_Backoff`` (tests pass a tight one).
    """
    config.validate()  # raises ChatBridgeConfigError if not safe to start

    stop = stop_event or threading.Event()
    send = sender if sender is not None else matrix_send_message
    dispatch = handler if handler is not None else handle_message
    bo = backoff if backoff is not None else _Backoff()
    next_batch: str | None = None
    dispatched = 0
    iterations = 0

    _log("matrix", f"loop start (allowlist={list(config.allowed_rooms)})")

    while not stop.is_set():
        if max_iterations is not None and iterations >= max_iterations:
            _log("matrix", f"max_iterations reached ({max_iterations})")
            break
        iterations += 1
        try:
            payload = _matrix_sync(config, since=next_batch, transport=transport)
        except Exception as exc:  # noqa: BLE001 - classified below
            if not _is_transient_http_error(exc):
                _log("matrix", f"terminal error: {exc!r}")
                raise
            delay = bo.next_delay()
            _log(
                "matrix",
                f"transient error {exc!r}; backoff {delay:.1f}s",
            )
            clock_sleep(delay)
            continue

        bo.reset()
        new_batch = payload.get("next_batch")
        if isinstance(new_batch, str) and new_batch:
            next_batch = new_batch

        for room_id, sender_id, event_id, body in _matrix_extract_messages(payload):
            if not config.is_room_allowed(room_id):
                continue
            # Echo prevention: skip our own messages.
            if config.user_id and sender_id == config.user_id:
                continue
            response = dispatch(body)
            if response is None:
                continue
            try:
                send(config, response.rendered, room_id=room_id)
                dispatched += 1
                _log(
                    "matrix",
                    f"dispatched {response.command!r} to {room_id} "
                    f"(exit={response.exit_code}, event={event_id})",
                )
            except Exception as exc:  # noqa: BLE001 - reply errors mustn't crash loop
                _log(
                    "matrix",
                    f"reply error in {room_id} ({event_id}): {exc!r}",
                )

    _log("matrix", f"loop stop (dispatched={dispatched}, iterations={iterations})")
    return dispatched


# ---------------------------------------------------------------------------
# Telegram getUpdates loop
# ---------------------------------------------------------------------------


def _telegram_get_updates(
    config: TelegramConfig,
    *,
    offset: int | None = None,
    transport: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """One Telegram ``getUpdates`` call. ``transport`` defaults to
    a thin urllib GET against the Bot API; tests inject a stub."""
    if transport is not None:
        return transport(config, offset)
    params: list[tuple[str, Any]] = [
        ("timeout", config.poll_timeout_s),
    ]
    if offset is not None:
        params.append(("offset", offset))
    url = (
        f"{config.api_root.rstrip('/')}"
        f"/bot{urllib.parse.quote(config.bot_token)}"
        f"/getUpdates?{urllib.parse.urlencode(params, doseq=True)}"
    )
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=config.poll_timeout_s + 5) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    if not raw:
        return {}
    import json as _json

    try:
        parsed = _json.loads(raw)
    except _json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _telegram_extract_messages(
    payload: dict[str, Any],
) -> list[tuple[int, int | str, int | str, str]]:
    """Extract ``(update_id, chat_id, user_id, text)`` tuples from
    a getUpdates payload. Drops non-message updates, edits, and
    messages without a text body."""
    out: list[tuple[int, int | str, int | str, str]] = []
    result = payload.get("result")
    if not isinstance(result, list):
        return out
    for update in result:
        if not isinstance(update, dict):
            continue
        try:
            update_id = int(update.get("update_id"))
        except (TypeError, ValueError):
            continue
        message = update.get("message")
        if not isinstance(message, dict):
            continue
        text = message.get("text")
        if not isinstance(text, str) or not text:
            continue
        chat = message.get("chat")
        chat_id: int | str = ""
        if isinstance(chat, dict):
            raw_chat_id = chat.get("id")
            if isinstance(raw_chat_id, (int, str)):
                chat_id = raw_chat_id
        from_user = message.get("from")
        user_id: int | str = ""
        if isinstance(from_user, dict):
            raw_user_id = from_user.get("id")
            if isinstance(raw_user_id, (int, str)):
                user_id = raw_user_id
        out.append((update_id, chat_id, user_id, text))
    return out


def run_telegram_loop(
    config: TelegramConfig,
    *,
    stop_event: threading.Event | None = None,
    max_iterations: int | None = None,
    transport: Callable[..., dict[str, Any]] | None = None,
    sender: Callable[..., dict[str, Any]] | None = None,
    handler: Callable[[str], ChatResponse | None] | None = None,
    clock_sleep: Callable[[float], None] = time.sleep,
    backoff: _Backoff | None = None,
) -> int:
    """Run the Telegram long-poll loop against ``config``.

    Same shape as :func:`run_matrix_loop`. Allowlist is enforced on
    BOTH ``chat_id`` and ``user_id`` — a chat being allowed is not
    enough; if ``allowed_users`` is set, the sender must also match.
    Empty ``allowed_users`` means "any user in an allowed chat".
    """
    config.validate()

    stop = stop_event or threading.Event()
    send = sender if sender is not None else telegram_send_message
    dispatch = handler if handler is not None else handle_message
    bo = backoff if backoff is not None else _Backoff()
    offset: int | None = None
    dispatched = 0
    iterations = 0

    _log(
        "telegram",
        f"loop start (allowlist_chats={list(config.allowed_chats)}, "
        f"allowlist_users={list(config.allowed_users)})",
    )

    while not stop.is_set():
        if max_iterations is not None and iterations >= max_iterations:
            _log("telegram", f"max_iterations reached ({max_iterations})")
            break
        iterations += 1
        try:
            payload = _telegram_get_updates(
                config, offset=offset, transport=transport
            )
        except Exception as exc:  # noqa: BLE001 - classified below
            if not _is_transient_http_error(exc):
                _log("telegram", f"terminal error: {exc!r}")
                raise
            delay = bo.next_delay()
            _log(
                "telegram",
                f"transient error {exc!r}; backoff {delay:.1f}s",
            )
            clock_sleep(delay)
            continue

        # Phase 19.0 / BS-4 (additive 2026-05-02 audit remediation):
        # ``bo.reset()`` is gated behind the ok=true check so a
        # persistent ``ok=false`` response (e.g. Bot API rate-limit
        # or auth issue) produces an exponentially-growing backoff
        # rather than a flat 1.0s spin. Pre-fix the reset ran
        # unconditionally — every iteration started at attempt=0,
        # so next_delay() always returned the base. The audit
        # ``test_ok_false_triggers_backoff_continue`` covering this
        # asserted only ``len(sleeps) >= 1``, which the spin
        # behaviour also satisfied; the assertion has since been
        # tightened to require monotonically-increasing delays.
        if not payload.get("ok", True):
            # Bot API returned ok=false — likely 4xx-shaped, log + continue
            # WITHOUT resetting the backoff counter. Each consecutive
            # ok=false grows the next sleep until the cap.
            delay = bo.next_delay()
            _log(
                "telegram",
                f"getUpdates returned ok=false: {payload!r}; backoff {delay:.1f}s",
            )
            clock_sleep(delay)
            continue
        # ok=true — reset the backoff counter. Real recovery.
        bo.reset()

        messages = _telegram_extract_messages(payload)
        for update_id, chat_id, user_id, text in messages:
            offset = max(offset or 0, update_id + 1)
            if not config.is_chat_allowed(chat_id):
                continue
            if not config.is_user_allowed(user_id):
                continue
            response = dispatch(text)
            if response is None:
                continue
            try:
                send(config, response.rendered, chat_id=chat_id)
                dispatched += 1
                _log(
                    "telegram",
                    f"dispatched {response.command!r} to chat={chat_id} "
                    f"user={user_id} (exit={response.exit_code}, update={update_id})",
                )
            except Exception as exc:  # noqa: BLE001
                _log(
                    "telegram",
                    f"reply error to chat={chat_id} (update={update_id}): {exc!r}",
                )

    _log(
        "telegram",
        f"loop stop (dispatched={dispatched}, iterations={iterations})",
    )
    return dispatched


__all__ = [
    "run_matrix_loop",
    "run_telegram_loop",
]
