"""Agent Communication Protocol bridge (PH-16 Slice 16.3).

Minimal stdlib JSON-RPC 2.0 shim for IDE-agent co-piloting.
Speaks a small, stable subset that VS Code / JetBrains plugins
can drive:

- ``agent.execute(command, argv)`` — run a Mythic CLI command,
  return its stdout / exit code in the response. Cancellation
  is supported via the ``run_id`` returned in the result —
  callers can cancel an in-flight run via ``agent.cancel``.
- ``agent.cancel(run_id)`` — set the cancel event for the named
  run. The server checks the event between long-running steps
  (today's CLI is mostly synchronous so cancellation is best-
  effort).
- ``agent.status()`` — return server info + active run count.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

import io
import json
import secrets
import sys
import threading
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from typing import Any, Callable, IO


SERVER_NAME = "mythic-vibe-acp"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "0.1"


# JSON-RPC error codes (subset of standard).
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


@dataclass
class _ActiveRun:
    run_id: str
    command: str
    cancel_event: threading.Event = field(default_factory=threading.Event)


@dataclass
class AcpServer:
    """In-process ACP server. Tests drive via :meth:`handle_request`.
    Production binds it to stdio via :func:`run_stdio_server`."""

    name: str = SERVER_NAME
    version: str = SERVER_VERSION
    _active_runs: dict[str, _ActiveRun] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    # ---- Public API ---------------------------------------------------

    def handle_request(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return _error_response(None, INVALID_REQUEST, "request must be a JSON object")
        method = payload.get("method")
        if not isinstance(method, str) or not method:
            return _error_response(payload.get("id"), INVALID_REQUEST, "missing method")
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            return _error_response(payload.get("id"), INVALID_PARAMS, "params must be an object")

        request_id = payload.get("id")
        is_notification = "id" not in payload

        try:
            handler = self._handler_for(method)
        except KeyError:
            if is_notification:
                return None
            return _error_response(request_id, METHOD_NOT_FOUND, f"unknown method {method!r}")

        try:
            result = handler(params)
        except Exception as exc:  # noqa: BLE001
            if is_notification:
                return None
            return _error_response(request_id, INTERNAL_ERROR, f"{type(exc).__name__}: {exc}")

        if is_notification:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    # ---- Method routing -----------------------------------------------

    def _handler_for(self, method: str) -> Callable[[dict[str, Any]], Any]:
        if method == "agent.status":
            return self._handle_status
        if method == "agent.execute":
            return self._handle_execute
        if method == "agent.cancel":
            return self._handle_cancel
        raise KeyError(method)

    def _handle_status(self, params: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            active = [
                {"run_id": r.run_id, "command": r.command}
                for r in self._active_runs.values()
            ]
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": {"name": self.name, "version": self.version},
            "activeRuns": active,
        }

    def _handle_execute(self, params: dict[str, Any]) -> dict[str, Any]:
        from ..app import build_parser
        from ..commands import COMMAND_HANDLERS

        command = params.get("command")
        if not isinstance(command, str) or not command:
            raise ValueError("agent.execute requires a string `command`")
        argv = params.get("argv") or []
        if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
            raise ValueError("agent.execute `argv` must be a list of strings")
        if command not in COMMAND_HANDLERS:
            raise ValueError(f"unknown command {command!r}")

        run_id = "RUN-" + secrets.token_hex(6)
        record = _ActiveRun(run_id=run_id, command=command)
        with self._lock:
            self._active_runs[run_id] = record

        try:
            parser = build_parser()
            namespace = parser.parse_args([command, *argv])

            out = io.StringIO()
            err = io.StringIO()
            exit_code: int
            try:
                with redirect_stdout(out), redirect_stderr(err):
                    if record.cancel_event.is_set():
                        exit_code = 130  # canonical "cancelled by signal"
                    else:
                        handler = COMMAND_HANDLERS[command]
                        exit_code = int(handler(namespace) or 0)
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 1
            except Exception as exc:  # noqa: BLE001
                exit_code = 1
                err.write(f"{type(exc).__name__}: {exc}\n")
        finally:
            with self._lock:
                self._active_runs.pop(run_id, None)

        return {
            "run_id": run_id,
            "command": command,
            "exit_code": exit_code,
            "stdout": out.getvalue(),
            "stderr": err.getvalue(),
            "cancelled": record.cancel_event.is_set(),
        }

    def _handle_cancel(self, params: dict[str, Any]) -> dict[str, Any]:
        run_id = params.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("agent.cancel requires a string `run_id`")
        with self._lock:
            record = self._active_runs.get(run_id)
            if record is None:
                return {"cancelled": False, "reason": "run not found"}
            record.cancel_event.set()
        return {"cancelled": True}


def _error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def run_stdio_server(
    *,
    server: AcpServer | None = None,
    stdin: IO[str] | None = None,
    stdout: IO[str] | None = None,
) -> int:
    server = server or AcpServer()
    in_stream = stdin if stdin is not None else sys.stdin
    out_stream = stdout if stdout is not None else sys.stdout

    while True:
        try:
            line = in_stream.readline()
        except (OSError, ValueError):
            break
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            response = _error_response(None, PARSE_ERROR, "invalid JSON")
            _write(out_stream, response)
            continue
        response = server.handle_request(payload)
        if response is not None:
            _write(out_stream, response)
    return 0


def _write(stream: IO[str], payload: dict[str, Any]) -> None:
    try:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        stream.flush()
    except (OSError, ValueError):
        pass


__all__ = [
    "AcpServer",
    "PROTOCOL_VERSION",
    "SERVER_NAME",
    "SERVER_VERSION",
    "run_stdio_server",
]
