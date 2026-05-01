"""MCP server runtime (PH-16 Slice 16.1).

Stdlib-only JSON-RPC 2.0 server speaking Anthropic's Model
Context Protocol over stdio. Each request/response is one JSON
object per line. No LSP-style headers — MCP framing is plain
NDJSON.

Implemented methods:

- ``initialize`` — protocol handshake. Returns server info +
  declared capabilities (``tools`` only — the minimum surface).
- ``notifications/initialized`` — accepts the post-init
  notification, returns nothing.
- ``tools/list`` — returns the catalogue from
  :mod:`mcp_tools`.
- ``tools/call`` — invokes a CLI handler with the request's
  ``arguments.argv`` array. Stdout / stderr are captured and
  returned as ``content`` + ``isError`` fields.

Cross-platform: pure stdlib. Tests drive the server through
in-process JSON dicts; the production CLI binds it to real
stdin/stdout via :func:`run_stdio_server`.
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from typing import Any, Callable, IO

from .mcp_tools import McpTool, build_tool_catalogue


PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "mythic-vibe"
SERVER_VERSION = "0.1.0"


JsonRpcRequest = dict[str, Any]
JsonRpcResponse = dict[str, Any]


# ---- Error codes (subset of JSON-RPC 2.0 standard) -------------------


PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


@dataclass
class McpServer:
    """In-process MCP server. Pure data; tests drive it via
    :meth:`handle_request`. Production code runs the stdio
    pump via :func:`run_stdio_server`."""

    name: str = SERVER_NAME
    version: str = SERVER_VERSION
    tools: list[McpTool] = field(default_factory=build_tool_catalogue)
    initialized: bool = False

    # ---- Public API ----------------------------------------------------

    def handle_request(self, payload: JsonRpcRequest) -> JsonRpcResponse | None:
        """Dispatch one JSON-RPC request. Returns the response
        dict or ``None`` for notifications (no response required).
        """
        if not isinstance(payload, dict):
            return _error_response(None, INVALID_REQUEST, "request must be a JSON object")

        method = payload.get("method")
        if not isinstance(method, str) or not method:
            return _error_response(
                payload.get("id"), INVALID_REQUEST, "missing method"
            )

        params = payload.get("params") or {}
        if not isinstance(params, dict):
            return _error_response(
                payload.get("id"), INVALID_PARAMS, "params must be an object"
            )

        request_id = payload.get("id")
        is_notification = "id" not in payload

        try:
            handler = self._method_handler(method)
        except KeyError:
            if is_notification:
                return None
            return _error_response(
                request_id, METHOD_NOT_FOUND, f"unknown method {method!r}"
            )

        try:
            result = handler(params)
        except Exception as exc:  # noqa: BLE001 — never crash the server
            if is_notification:
                return None
            return _error_response(
                request_id, INTERNAL_ERROR, f"{type(exc).__name__}: {exc}"
            )

        if is_notification:
            return None
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result,
        }

    # ---- Method handlers ----------------------------------------------

    def _method_handler(self, method: str) -> Callable[[dict[str, Any]], Any]:
        if method == "initialize":
            return self._handle_initialize
        if method == "notifications/initialized":
            return self._handle_notifications_initialized
        if method == "tools/list":
            return self._handle_tools_list
        if method == "tools/call":
            return self._handle_tools_call
        if method == "ping":
            return self._handle_ping
        raise KeyError(method)

    def _handle_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        self.initialized = True
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": self.name, "version": self.version},
        }

    def _handle_notifications_initialized(self, params: dict[str, Any]) -> None:
        # Notification — clients send this after `initialize`. No
        # response required. Server can use this signal to start
        # serving real requests.
        return None

    def _handle_tools_list(self, params: dict[str, Any]) -> dict[str, Any]:
        return {"tools": [tool.to_dict() for tool in self.tools]}

    def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("tools/call requires a string `name`")
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise ValueError("tools/call `arguments` must be an object")
        argv = arguments.get("argv") or []
        if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
            raise ValueError("tools/call `arguments.argv` must be a list of strings")

        if not name.startswith("mythic_vibe."):
            raise ValueError(
                f"unknown tool {name!r} — names must be prefixed `mythic_vibe.`"
            )
        command = name.removeprefix("mythic_vibe.")
        return _invoke_command(command, argv)

    def _handle_ping(self, params: dict[str, Any]) -> dict[str, Any]:
        return {}


def _error_response(
    request_id: Any,
    code: int,
    message: str,
    *,
    data: Any = None,
) -> JsonRpcResponse:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": error,
    }


def _invoke_command(command: str, argv: list[str]) -> dict[str, Any]:
    """Run a Mythic Vibe CLI command and return its
    ``tools/call`` result envelope.

    The MCP `content` array carries one or more text blocks; we
    use a single block with the captured stdout. ``isError`` is
    True when the command's exit code is non-zero. stderr is
    appended for diagnostics.
    """
    from ..app import build_parser
    from ..commands import COMMAND_HANDLERS

    if command not in COMMAND_HANDLERS:
        return {
            "isError": True,
            "content": [
                {"type": "text", "text": f"unknown command: {command!r}"}
            ],
        }

    parser = build_parser()
    full_argv = [command, *argv]
    try:
        namespace = parser.parse_args(full_argv)
    except SystemExit as exc:
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": f"argparse rejected argv {full_argv!r}: exit={exc.code}",
                },
            ],
        }

    handler = COMMAND_HANDLERS[command]
    out = io.StringIO()
    err = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            exit_code = handler(namespace)
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 1
    except Exception as exc:  # noqa: BLE001 — never propagate to the JSON-RPC layer
        exit_code = 1
        err.write(f"{type(exc).__name__}: {exc}\n")

    stdout_text = out.getvalue()
    stderr_text = err.getvalue()
    is_error = exit_code != 0
    text_block = stdout_text
    if stderr_text:
        text_block = (text_block + "\n--- stderr ---\n" + stderr_text).lstrip("\n")
    if not text_block:
        text_block = f"command exited with code {exit_code}"
    return {
        "isError": is_error,
        "content": [{"type": "text", "text": text_block}],
        "_meta": {"exitCode": exit_code, "command": command},
    }


# ---- Stdio pump -------------------------------------------------------


def run_stdio_server(
    *,
    server: McpServer | None = None,
    stdin: IO[str] | None = None,
    stdout: IO[str] | None = None,
) -> int:
    """Read JSON-RPC messages from stdin and write responses to
    stdout until stdin closes. One request/response per line.
    Returns the process exit code (always 0 — server doesn't
    fail unless stdin / stdout do)."""
    server = server or McpServer()
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
            _write_message(out_stream, response)
            continue
        response = server.handle_request(payload)
        if response is None:
            continue
        _write_message(out_stream, response)
    return 0


def _write_message(stream: IO[str], payload: JsonRpcResponse) -> None:
    try:
        stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        stream.flush()
    except (OSError, ValueError):
        pass


__all__ = [
    "INTERNAL_ERROR",
    "INVALID_PARAMS",
    "INVALID_REQUEST",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "METHOD_NOT_FOUND",
    "McpServer",
    "PARSE_ERROR",
    "PROTOCOL_VERSION",
    "SERVER_NAME",
    "SERVER_VERSION",
    "run_stdio_server",
]
