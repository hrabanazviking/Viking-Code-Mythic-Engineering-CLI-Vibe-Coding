"""MCP client (PH-16 Slice 16.2).

Stdlib JSON-RPC 2.0 client that spawns an MCP server subprocess
and invokes its tools. Used by forge plugins (and slice 16.1
self-tests) to integrate external MCPs.

Cross-platform: pure stdlib through ``runtime.exec.spawn_process`` plus
``json`` and ``threading``.
"""

from __future__ import annotations

import itertools
import json
import os
import queue
import threading
from dataclasses import dataclass, field
from subprocess import TimeoutExpired
from typing import Any, IO

from ..runtime.exec import spawn_process


JsonRpcMessage = dict[str, Any]


# Phase 19.0 / BS-2 (2026-05-02 audit remediation): bounds for the
# JSON-RPC pump so a stalled or notification-spamming MCP server
# can't hang the calling thread forever.
#
# - ``DEFAULT_READ_TIMEOUT_SECONDS`` caps how long ``_read_one`` will
#   wait for the next line from the server's stdout. After this it
#   raises :class:`McpClientError`. Set to ``0.0`` to disable the
#   timeout (legacy behaviour — readline blocks forever).
# - ``DEFAULT_MAX_DISCARD`` caps how many non-matching responses the
#   ``call()`` discard loop will skip before bailing with
#   :class:`McpClientError`. Defends against an MCP server that
#   emits an unbounded stream of notifications.
#
# Both are env-var configurable so operators can tune without code
# changes:
#   - ``MYTHIC_MCP_READ_TIMEOUT``  (float seconds, ``0`` disables)
#   - ``MYTHIC_MCP_MAX_DISCARD``   (positive int)
DEFAULT_READ_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_DISCARD = 1000


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class McpClientError(RuntimeError):
    """Raised when an MCP client call fails (server returned an
    error envelope, subprocess died, malformed JSON, read timed
    out, discard-loop overflow, etc.)."""


_EOF_SENTINEL = object()


@dataclass
class McpClient:
    """Lightweight JSON-RPC 2.0 client. Construct via
    :meth:`spawn` for subprocess-backed servers or
    :meth:`from_streams` for in-process pipes (testing).

    Phase 19.0 / BS-2 (additive 2026-05-02): the JSON-RPC pump now
    runs the blocking ``readline()`` on a daemon reader thread that
    pumps results into a queue; ``_read_one`` does
    ``queue.get(timeout=read_timeout_seconds)`` so a stalled server
    can no longer hang the caller. The discard loop in ``call()``
    is bounded by ``max_discard`` so a notification-spamming server
    can no longer spin the caller forever. Both bounds default to
    sensible production values and are env-var configurable; setting
    ``read_timeout_seconds=0.0`` opts back into the legacy unbounded
    behaviour for callers who genuinely need it.
    """

    stdin: IO[str]
    stdout: IO[str]
    process: Any | None = None
    # Phase 19.0 / BS-2 (additive): bounds on the JSON-RPC pump.
    read_timeout_seconds: float = field(
        default_factory=lambda: _env_float(
            "MYTHIC_MCP_READ_TIMEOUT", DEFAULT_READ_TIMEOUT_SECONDS
        )
    )
    max_discard: int = field(
        default_factory=lambda: _env_int(
            "MYTHIC_MCP_MAX_DISCARD", DEFAULT_MAX_DISCARD
        )
    )
    _id_counter: itertools.count = field(default_factory=lambda: itertools.count(1))
    _read_lock: threading.Lock = field(default_factory=threading.Lock)
    _write_lock: threading.Lock = field(default_factory=threading.Lock)
    _read_queue: queue.Queue = field(default_factory=queue.Queue)
    _reader_thread: threading.Thread | None = field(default=None, repr=False)
    _reader_started: bool = field(default=False, repr=False)
    _close_event: threading.Event = field(default_factory=threading.Event)

    # ---- Construction --------------------------------------------------

    @classmethod
    def spawn(
        cls,
        argv: list[str],
        *,
        read_timeout_seconds: float | None = None,
        max_discard: int | None = None,
    ) -> "McpClient":
        """Spawn the given argv as an MCP server subprocess. Pipes
        stdin / stdout for JSON-RPC framing. stderr is left
        attached to the parent for diagnostic output."""
        if not argv:
            raise ValueError("argv must contain at least the server binary")
        proc = spawn_process(
            argv,
            stdin="pipe",
            stdout="pipe",
            stderr="inherit",
            text=True,
            bufsize=1,
        )
        if proc.stdin is None or proc.stdout is None:  # pragma: no cover — Popen contract
            raise McpClientError("Popen did not provide stdin/stdout pipes")
        kwargs: dict[str, Any] = {
            "stdin": proc.stdin,
            "stdout": proc.stdout,
            "process": proc,
        }
        if read_timeout_seconds is not None:
            kwargs["read_timeout_seconds"] = read_timeout_seconds
        if max_discard is not None:
            kwargs["max_discard"] = max_discard
        return cls(**kwargs)

    @classmethod
    def from_streams(
        cls,
        *,
        stdin: IO[str],
        stdout: IO[str],
        read_timeout_seconds: float | None = None,
        max_discard: int | None = None,
    ) -> "McpClient":
        """In-process construction for tests. Phase 19.0 / BS-2 added
        ``read_timeout_seconds`` and ``max_discard`` keyword args so
        tests can pin tight bounds without env-var setup."""
        kwargs: dict[str, Any] = {"stdin": stdin, "stdout": stdout}
        if read_timeout_seconds is not None:
            kwargs["read_timeout_seconds"] = read_timeout_seconds
        if max_discard is not None:
            kwargs["max_discard"] = max_discard
        return cls(**kwargs)

    # ---- JSON-RPC pump -------------------------------------------------

    def _next_id(self) -> int:
        return next(self._id_counter)

    def _send(self, payload: JsonRpcMessage) -> None:
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        with self._write_lock:
            self.stdin.write(line)
            self.stdin.flush()

    # Phase 19.0 / BS-2 (additive 2026-05-02): reader-thread pump.
    # The thread does the blocking readline() and pushes either a
    # parsed message or a sentinel (EOF / decode error) into the
    # queue. ``_read_one`` then does ``queue.get(timeout=...)`` so
    # a stalled server can't hang the caller.
    def _ensure_reader_started(self) -> None:
        if self._reader_started:
            return
        self._reader_started = True
        if self.read_timeout_seconds <= 0.0:
            # Legacy mode: don't start a reader thread; ``_read_one``
            # falls back to direct readline (will block indefinitely
            # if the server stalls — preserves pre-Phase-19 semantics
            # for callers who explicitly opt in via 0.0 timeout).
            return
        thread = threading.Thread(
            target=self._reader_loop,
            name="McpClient-reader",
            daemon=True,
        )
        thread.start()
        self._reader_thread = thread

    def _reader_loop(self) -> None:
        """Run on a daemon thread. Pulls lines off ``stdout``,
        parses them, and pushes (parsed_dict | exc | EOF sentinel)
        into the queue. Exits when the stream closes or when
        ``_close_event`` is set."""
        try:
            while not self._close_event.is_set():
                try:
                    raw = self.stdout.readline()
                except (OSError, ValueError):
                    # Stream closed mid-read.
                    self._read_queue.put(_EOF_SENTINEL)
                    return
                if not raw:
                    self._read_queue.put(_EOF_SENTINEL)
                    return
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError as exc:
                    self._read_queue.put(
                        McpClientError(f"server returned invalid JSON: {exc}")
                    )
                    continue
                self._read_queue.put(parsed)
        except Exception as exc:  # noqa: BLE001 — never crash the daemon thread
            self._read_queue.put(
                McpClientError(f"reader thread crashed: {type(exc).__name__}: {exc}")
            )

    def _read_one(self) -> JsonRpcMessage:
        # Legacy unbounded path — preserved for callers who set
        # ``read_timeout_seconds=0.0`` to opt back into the
        # pre-Phase-19 semantics.
        if self.read_timeout_seconds <= 0.0:
            with self._read_lock:
                raw = self.stdout.readline()
            if not raw:
                raise McpClientError("server closed stdout before responding")
            try:
                return json.loads(raw)
            except json.JSONDecodeError as exc:
                raise McpClientError(
                    f"server returned invalid JSON: {exc}"
                ) from exc

        # Phase 19.0 / BS-2 path — bounded read via reader thread.
        self._ensure_reader_started()
        try:
            item = self._read_queue.get(timeout=self.read_timeout_seconds)
        except queue.Empty as exc:
            raise McpClientError(
                f"server stdout read timed out after "
                f"{self.read_timeout_seconds:.1f}s "
                f"(set MYTHIC_MCP_READ_TIMEOUT to adjust, or 0 to disable)"
            ) from exc
        if item is _EOF_SENTINEL:
            raise McpClientError("server closed stdout before responding")
        if isinstance(item, McpClientError):
            raise item
        if not isinstance(item, dict):  # pragma: no cover — defensive
            raise McpClientError(
                f"reader pumped unexpected type: {type(item).__name__}"
            )
        return item

    def call(
        self,
        method: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Send a JSON-RPC request and return the ``result``
        field. Raises :class:`McpClientError` on transport or
        protocol errors.

        Phase 19.0 / BS-2 (additive 2026-05-02): the read loop is now
        bounded by ``self.max_discard`` so a server that emits an
        unbounded stream of unrelated messages can no longer spin
        this method forever.
        """
        request_id = self._next_id()
        payload: JsonRpcMessage = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        self._send(payload)

        # Read until we see a response with the matching id; discard
        # notifications / unrelated messages along the way (servers may
        # interleave them). Phase 19.0 / BS-2: bounded by max_discard.
        discarded = 0
        while True:
            response = self._read_one()
            if response.get("id") != request_id:
                discarded += 1
                if discarded >= self.max_discard:
                    raise McpClientError(
                        f"discarded {discarded} unrelated messages without "
                        f"finding response to request id={request_id}; "
                        f"server may be spamming notifications "
                        f"(set MYTHIC_MCP_MAX_DISCARD to adjust)"
                    )
                continue
            error = response.get("error")
            if isinstance(error, dict):
                message = error.get("message", "(no message)")
                code = error.get("code", "?")
                raise McpClientError(
                    f"server error code={code}: {message}"
                )
            return response.get("result")

    def notify(
        self,
        method: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Fire-and-forget notification (no id, no response)."""
        payload: JsonRpcMessage = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)

    # ---- High-level convenience ---------------------------------------

    def initialize(self) -> dict[str, Any]:
        """Send the standard MCP handshake. Returns the server's
        info / capabilities payload."""
        result = self.call(
            "initialize",
            params={
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "mythic-vibe-client", "version": "0.1.0"},
                "capabilities": {},
            },
        )
        # Send the post-init notification per MCP spec.
        self.notify("notifications/initialized")
        if not isinstance(result, dict):
            raise McpClientError("initialize did not return an object")
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        result = self.call("tools/list")
        if not isinstance(result, dict):
            raise McpClientError("tools/list did not return an object")
        tools = result.get("tools", [])
        if not isinstance(tools, list):
            raise McpClientError("tools/list result missing tools array")
        return [t for t in tools if isinstance(t, dict)]

    def call_tool(
        self,
        name: str,
        *,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.call(
            "tools/call",
            params={
                "name": name,
                "arguments": arguments or {},
            },
        )
        if not isinstance(result, dict):
            raise McpClientError("tools/call did not return an object")
        return result

    # ---- Lifecycle ----------------------------------------------------

    def close(self) -> None:
        """Close stdin (signals server shutdown) and reap the
        subprocess if we own one. Phase 19.0 / BS-2: also signals
        the reader thread to exit (best-effort; the daemon thread
        will be reaped at process exit if it's blocked in readline)."""
        self._close_event.set()
        try:
            self.stdin.close()
        except (OSError, ValueError):
            pass
        try:
            self.stdout.close()
        except (OSError, ValueError):
            pass
        if self.process is not None:
            try:
                self.process.wait(timeout=2.0)
            except TimeoutExpired:
                self.process.kill()
            except OSError:
                pass
        if self._reader_thread is not None:
            # Best-effort join — the daemon thread is reaped at
            # process exit if it's still blocked.
            try:
                self._reader_thread.join(timeout=0.5)
            except RuntimeError:  # pragma: no cover — defensive
                pass

    def __enter__(self) -> "McpClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


__all__ = [
    "JsonRpcMessage",
    "McpClient",
    "McpClientError",
]
