"""Hermes HTTP API — token-protected JSON endpoints (v1.0).

Stdlib HTTP wrapper around :class:`HermesCore`. Endpoints:

- ``GET  /api/health`` — no-auth health check (for reverse-proxy probes).
- ``GET  /api/tools`` — list registered tools as JSON Schema (auth).
- ``POST /api/invoke`` — invoke a tool (auth).
- ``GET  /api/state`` — convenience for the most common state query (auth).
- ``GET  /api/artifacts?under=…&glob=…`` — list project artifacts (auth).
- ``GET  /api/artifacts/<relpath>`` — read one artifact (auth).
- ``GET  /api/events?limit=…`` — recent event-log entries (auth).

**Security model** (mirrors PH-19.0 / BS-1 hardening on
``surfaces/web_terminal.py``):

- Default bind ``127.0.0.1`` (loopback). Operators wishing to
  expose externally must explicitly pass ``--bind 0.0.0.0`` and
  layer their own TLS reverse proxy.
- 32-byte URL-safe token compared via :func:`secrets.compare_digest`.
  Token can be passed via the ``X-Hermes-Token`` header OR as
  a top-level ``token`` field in POST JSON bodies.
- ``MAX_REQUEST_BODY_BYTES = 65536`` cap on POST bodies.
- 30 s per-connection socket timeout.
- ``handle_*`` functions are pure (no socket I/O) so the test
  suite can exercise routing without binding a port.

Cross-platform: pure stdlib (``http.server``, ``json``, ``secrets``).
"""

from __future__ import annotations

import json
import logging
import secrets
import socket
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .core import HermesCore, Invocation, InvocationResult


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8770
"""Distinct from web_terminal's 8765 so an operator can run both."""

MAX_REQUEST_BODY_BYTES = 65_536

DEFAULT_SOCKET_TIMEOUT_SECONDS = 30.0


# ---------------------------------------------------------------------------
# Config + server
# ---------------------------------------------------------------------------


@dataclass
class HermesHttpConfig:
    """One Hermes HTTP server instance's configuration."""

    core: HermesCore
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    socket_timeout_seconds: float = DEFAULT_SOCKET_TIMEOUT_SECONDS
    max_request_body_bytes: int = MAX_REQUEST_BODY_BYTES


@dataclass
class HermesHttpServer:
    config: HermesHttpConfig
    httpd: ThreadingHTTPServer | None = None

    def start(self) -> None:
        """Bind + serve_forever. Blocking; call from a worker thread
        if you need non-blocking behaviour. ``stop()`` is safe from
        another thread."""
        handler_cls = _make_handler(self.config)
        self.httpd = ThreadingHTTPServer(
            (self.config.host, self.config.port), handler_cls
        )
        if self.config.socket_timeout_seconds > 0.0:
            self.httpd.socket.settimeout(self.config.socket_timeout_seconds)
        self.httpd.serve_forever()

    def stop(self) -> None:
        if self.httpd is None:
            return
        try:
            self.httpd.shutdown()
        except (OSError, RuntimeError):
            pass
        try:
            self.httpd.server_close()
        except OSError:
            pass

    @property
    def bound_address(self) -> tuple[str, int] | None:
        if self.httpd is None:
            return None
        try:
            return self.httpd.server_address[:2]  # type: ignore[return-value]
        except (AttributeError, IndexError):
            return None


# ---------------------------------------------------------------------------
# Pure routing handlers — testable without a socket
# ---------------------------------------------------------------------------


def _ok_envelope(value: Any) -> dict[str, Any]:
    return {"ok": True, "value": value}


def _err_envelope(error: str, *, code: str = "error") -> dict[str, Any]:
    return {"ok": False, "code": code, "error": error}


def handle_health(config: HermesHttpConfig) -> dict[str, Any]:
    """No-auth health probe."""
    return {
        "ok": True,
        "service": "mythic-vibe-hermes",
        "host": config.host,
        "port": config.port,
        "tool_count": len(config.core.list_tools()),
    }


def handle_list_tools(config: HermesHttpConfig) -> dict[str, Any]:
    return _ok_envelope({
        "tools": [spec.to_dict() for spec in config.core.list_tools()],
    })


def handle_invoke(
    payload: dict[str, Any],
    config: HermesHttpConfig,
) -> dict[str, Any]:
    """Invoke a tool. Payload shape:
    ``{"tool": "<name>", "args": {...}, "request_id": "<optional>"}``.
    Returns the full :class:`InvocationResult` in the envelope.
    """
    if not isinstance(payload, dict):
        return _err_envelope("payload must be a JSON object", code="bad_request")
    tool = payload.get("tool")
    if not isinstance(tool, str) or not tool.strip():
        return _err_envelope("'tool' field is required (string)", code="bad_request")
    args = payload.get("args", {})
    if not isinstance(args, dict):
        return _err_envelope("'args' must be an object", code="bad_request")
    request_id = payload.get("request_id")
    if request_id is not None and not isinstance(request_id, str):
        return _err_envelope("'request_id' must be a string when supplied", code="bad_request")
    invocation = Invocation(tool=tool, args=args, request_id=request_id)
    result: InvocationResult = config.core.invoke(invocation)
    return _ok_envelope(result.to_dict())


def handle_state(config: HermesHttpConfig) -> dict[str, Any]:
    """Convenience — equivalent to ``invoke('state_show')`` for the
    common ``GET /api/state`` query pattern."""
    if not config.core.has_tool("state_show"):
        return _err_envelope("state_show tool is not registered", code="not_implemented")
    result = config.core.invoke(Invocation(tool="state_show"))
    return _ok_envelope(result.to_dict())


def handle_list_artifacts(
    query: dict[str, list[str]],
    config: HermesHttpConfig,
) -> dict[str, Any]:
    if not config.core.has_tool("list_artifacts"):
        return _err_envelope("list_artifacts tool is not registered", code="not_implemented")
    args: dict[str, Any] = {}
    if "under" in query:
        args["under"] = query["under"][0]
    if "glob" in query:
        args["glob"] = query["glob"][0]
    if "limit" in query:
        try:
            args["limit"] = int(query["limit"][0])
        except (TypeError, ValueError):
            return _err_envelope("'limit' must be an integer", code="bad_request")
    result = config.core.invoke(Invocation(tool="list_artifacts", args=args))
    return _ok_envelope(result.to_dict())


def handle_read_artifact(
    relpath: str,
    query: dict[str, list[str]],
    config: HermesHttpConfig,
) -> dict[str, Any]:
    if not config.core.has_tool("read_artifact"):
        return _err_envelope("read_artifact tool is not registered", code="not_implemented")
    args: dict[str, Any] = {"path": relpath}
    if "max_bytes" in query:
        try:
            args["max_bytes"] = int(query["max_bytes"][0])
        except (TypeError, ValueError):
            return _err_envelope("'max_bytes' must be an integer", code="bad_request")
    result = config.core.invoke(Invocation(tool="read_artifact", args=args))
    return _ok_envelope(result.to_dict())


def handle_events(
    query: dict[str, list[str]],
    config: HermesHttpConfig,
) -> dict[str, Any]:
    if not config.core.has_tool("recent_events"):
        return _err_envelope("recent_events tool is not registered", code="not_implemented")
    args: dict[str, Any] = {}
    if "limit" in query:
        try:
            args["limit"] = int(query["limit"][0])
        except (TypeError, ValueError):
            return _err_envelope("'limit' must be an integer", code="bad_request")
    result = config.core.invoke(Invocation(tool="recent_events", args=args))
    return _ok_envelope(result.to_dict())


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------


def check_token(supplied: str | None, config: HermesHttpConfig) -> bool:
    """Constant-time token compare. ``supplied`` may be None / empty."""
    if not supplied:
        return False
    expected = config.token.encode("utf-8")
    actual = supplied.encode("utf-8")
    return secrets.compare_digest(expected, actual)


# ---------------------------------------------------------------------------
# Handler factory (binds config via closure)
# ---------------------------------------------------------------------------


def _make_handler(config: HermesHttpConfig) -> type[BaseHTTPRequestHandler]:
    class HermesHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A002
            logging.getLogger("mythic_vibe_cli.hermes_http").debug(fmt, *args)

        # ---- Routing ----------------------------------------

        def do_GET(self) -> None:  # noqa: N802
            url = urlsplit(self.path)
            query = parse_qs(url.query)
            path = url.path

            if path == "/api/health":
                self._send_json(handle_health(config))
                return

            if not self._authenticated(query=query):
                self._send_json(_err_envelope("invalid or missing token", code="unauthorized"), status=401)
                return

            if path == "/api/tools":
                self._send_json(handle_list_tools(config))
                return
            if path == "/api/state":
                self._send_json(handle_state(config))
                return
            if path == "/api/artifacts":
                self._send_json(handle_list_artifacts(query, config))
                return
            if path == "/api/events":
                self._send_json(handle_events(query, config))
                return
            if path.startswith("/api/artifacts/"):
                relpath = path[len("/api/artifacts/"):]
                self._send_json(handle_read_artifact(relpath, query, config))
                return

            self._send_json(_err_envelope("not found", code="not_found"), status=404)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/invoke":
                self._send_json(_err_envelope("not found", code="not_found"), status=404)
                return
            payload = self._read_json_body()
            if payload is None:
                return  # error already sent
            # Token in body OR header — both accepted.
            body_token = payload.pop("token", None) if isinstance(payload, dict) else None
            if not self._authenticated(body_token=body_token):
                self._send_json(_err_envelope("invalid or missing token", code="unauthorized"), status=401)
                return
            self._send_json(handle_invoke(payload, config))

        # ---- Helpers ----------------------------------------

        def _authenticated(
            self,
            *,
            body_token: str | None = None,
            query: dict[str, list[str]] | None = None,
        ) -> bool:
            header_token = self.headers.get("X-Hermes-Token")
            if header_token and check_token(header_token, config):
                return True
            if body_token and check_token(body_token, config):
                return True
            if query and "token" in query:
                if check_token(query["token"][0], config):
                    return True
            return False

        def _read_json_body(self) -> Any:
            length_header = self.headers.get("Content-Length")
            try:
                length = int(length_header or "0")
            except ValueError:
                self._send_json(_err_envelope("invalid Content-Length", code="bad_request"), status=400)
                return None
            if length < 0 or length > config.max_request_body_bytes:
                self._send_json(
                    _err_envelope(
                        f"request body too large (max {config.max_request_body_bytes} bytes)",
                        code="payload_too_large",
                    ),
                    status=413,
                )
                return None
            try:
                raw = self.rfile.read(length) if length else b""
            except (socket.timeout, OSError):
                self._send_json(_err_envelope("read timeout", code="timeout"), status=408)
                return None
            if not raw:
                return {}
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as exc:
                self._send_json(_err_envelope(f"invalid JSON: {exc}", code="bad_request"), status=400)
                return None
            return payload

        def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
            body = json.dumps(payload).encode("utf-8")
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, OSError):
                # Client closed before we could finish — nothing
                # to do but swallow.
                return

    return HermesHandler


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------


def build_default_http_server(
    root: Path | str = ".",
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    token: str | None = None,
) -> HermesHttpServer:
    """Build a Hermes HTTP server bound to the curated default
    tool registry. Operators rarely need this — the surface CLI
    command (``mythic-vibe surface hermes``) is the normal entry
    point. Useful for tests + programmatic launches."""
    from .tcl import build_default_agent

    agent = build_default_agent(root=root)
    config = HermesHttpConfig(
        core=agent.core,
        host=host,
        port=port,
        token=token if token is not None else secrets.token_urlsafe(32),
    )
    return HermesHttpServer(config=config)


__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_SOCKET_TIMEOUT_SECONDS",
    "MAX_REQUEST_BODY_BYTES",
    "HermesHttpConfig",
    "HermesHttpServer",
    "build_default_http_server",
    "check_token",
    "handle_events",
    "handle_health",
    "handle_invoke",
    "handle_list_artifacts",
    "handle_list_tools",
    "handle_read_artifact",
    "handle_state",
]
