"""Web terminal surface (PH-17 Slice 17.1).

Stdlib HTTP server that exposes the CLI behind a token-protected
endpoint. The browser front-end uses xterm.js (loaded from a
CDN — operators can swap to a local copy by editing the served
HTML).

Endpoints:

- ``GET /`` — serves the xterm.js front-end HTML.
- ``GET /static/app.js`` — small client script wiring xterm.js
  to ``/api/run``.
- ``POST /api/run`` — JSON ``{token, command, argv}``; returns
  ``{exit_code, stdout, stderr}``.
- ``GET /api/status`` — server health (no auth required so
  reverse proxies can health-check).

**Security defaults:**
- Bind to ``127.0.0.1`` only (loopback). Operators wishing to
  expose externally must explicitly pass ``--bind 0.0.0.0`` and
  layer their own TLS reverse proxy.
- Token is a 32-byte URL-safe secret; auto-generated when not
  provided.
- Token is compared with :func:`secrets.compare_digest` to
  defeat timing attacks.

Cross-platform: pure stdlib (``http.server`` + ``json`` +
``secrets``).
"""

from __future__ import annotations

import io
import json
import logging
import secrets
import socket
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

# Phase 19.0 / BS-1 (2026-05-02 audit remediation): bound the
# acceptable JSON request body size + per-connection socket timeout
# to defend against DoS via a malicious / misbehaving client that
# advertises a huge ``Content-Length`` (e.g. ``1073741824``). Without
# these caps, ``ThreadingHTTPServer`` spawns a thread per connection
# that blocks in ``rfile.read(length)`` until the byte budget arrives
# or the connection drops — exhausting the server's thread pool and /
# or its memory.
#
# 64 KiB is generous for any legitimate ``/api/run`` JSON payload
# (token + command + argv list); the largest plausible argv list
# for a CLI is well under 4 KiB.
MAX_REQUEST_BODY_BYTES = 65_536

# 30s per-connection socket timeout. Caps the time a stalled client
# can hold a server thread. Operators behind a slow link can override
# via ``WebTerminalConfig.socket_timeout_seconds``.
DEFAULT_SOCKET_TIMEOUT_SECONDS = 30.0


_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Mythic Vibe CLI — Web Terminal</title>
<link rel="stylesheet"
      href="https://unpkg.com/xterm@5.3.0/css/xterm.css" />
<style>
  body {{ background:#0c0c10; color:#e7e7ee; font-family:ui-monospace, monospace; margin:0; }}
  header {{ padding:0.6rem 1rem; background:#13131a; border-bottom:1px solid #25252e; }}
  #term {{ height: calc(100vh - 60px); padding: 0.5rem; }}
  input {{ background:#1c1c25; color:#e7e7ee; border:1px solid #2c2c38; padding:.4rem; }}
</style>
</head>
<body>
<header>
  Mythic Vibe CLI · Web Terminal
  &nbsp;&nbsp;
  Token: <input id="tok" type="password" placeholder="paste --token here" />
</header>
<div id="term"></div>
<script src="https://unpkg.com/xterm@5.3.0/lib/xterm.js"></script>
<script src="/static/app.js"></script>
</body>
</html>
"""


_APP_JS = """\
const term = new Terminal({
  fontSize: 14,
  theme: { background: '#0c0c10', foreground: '#e7e7ee' },
});
term.open(document.getElementById('term'));
term.writeln('Mythic Vibe CLI — Web Terminal (PH-17 Slice 17.1)');
term.writeln('Type a command and press Enter. Example: status --json');
term.writeln('');
term.write('$ ');

let line = '';
term.onKey(({ key, domEvent }) => {
  const code = domEvent.keyCode;
  if (code === 13) {
    term.writeln('');
    runCommand(line.trim());
    line = '';
  } else if (code === 8) {
    if (line.length > 0) {
      line = line.slice(0, -1);
      term.write('\\b \\b');
    }
  } else if (key.length === 1) {
    line += key;
    term.write(key);
  }
});

async function runCommand(cmdLine) {
  if (!cmdLine) { term.write('$ '); return; }
  const tok = document.getElementById('tok').value;
  const parts = cmdLine.split(/\\s+/);
  const command = parts.shift();
  try {
    const resp = await fetch('/api/run', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ token: tok, command, argv: parts }),
    });
    const data = await resp.json();
    if (data.error) {
      term.writeln('error: ' + data.error);
    } else {
      if (data.stdout) term.write(data.stdout.replace(/\\n/g, '\\r\\n'));
      if (data.stderr) {
        term.writeln('');
        term.writeln('--- stderr ---');
        term.write(data.stderr.replace(/\\n/g, '\\r\\n'));
      }
      term.writeln('');
      term.writeln('[exit ' + data.exit_code + ']');
    }
  } catch (e) {
    term.writeln('fetch failed: ' + e.message);
  }
  term.write('$ ');
}
"""


@dataclass
class WebTerminalConfig:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    # Phase 19.0 / BS-1 (additive 2026-05-02): per-connection socket
    # timeout. ``0.0`` means "no timeout" (legacy behaviour); the
    # default applies a sensible 30s cap. Operators behind very slow
    # links can override.
    socket_timeout_seconds: float = DEFAULT_SOCKET_TIMEOUT_SECONDS
    # Phase 19.0 / BS-1: max bytes accepted in a single JSON request
    # body. Requests exceeding this are rejected with HTTP 413 before
    # any bytes are read. Default 64 KiB; operators with unusual needs
    # can raise it but should NOT remove the cap.
    max_request_body_bytes: int = MAX_REQUEST_BODY_BYTES


@dataclass
class WebTerminalServer:
    config: WebTerminalConfig
    httpd: ThreadingHTTPServer | None = None

    def start(self) -> None:
        handler_cls = _make_handler(self.config)
        self.httpd = ThreadingHTTPServer(
            (self.config.host, self.config.port), handler_cls
        )
        # Phase 19.0 / BS-1 (additive 2026-05-02): apply a per-connection
        # socket timeout so a stalled client can't hold a server thread
        # indefinitely. ``0.0`` disables (legacy behaviour); any positive
        # value caps the read at that many seconds.
        if self.config.socket_timeout_seconds > 0.0:
            self.httpd.socket.settimeout(self.config.socket_timeout_seconds)
        self.httpd.serve_forever()

    def stop(self) -> None:
        if self.httpd is not None:
            try:
                self.httpd.shutdown()
            except OSError:
                pass
            try:
                self.httpd.server_close()
            except OSError:
                pass


# ---- Handler factory -------------------------------------------------


def _make_handler(config: WebTerminalConfig) -> type[BaseHTTPRequestHandler]:
    """Build a request-handler class bound to a config. We use a
    factory because BaseHTTPRequestHandler instantiates per
    request; the config has to be captured via closure."""

    class WebTerminalHandler(BaseHTTPRequestHandler):
        # Quiet default access logging — operators get noise via
        # their own reverse proxy.
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            logging.getLogger("mythic_vibe_cli.web_terminal").debug(
                format, *args
            )

        # ---- Routing ---------------------------------------------

        def do_GET(self) -> None:  # noqa: N802 — http.server requires this name
            if self.path == "/" or self.path == "/index.html":
                self._send_html(_INDEX_HTML)
                return
            if self.path == "/static/app.js":
                self._send_javascript(_APP_JS)
                return
            if self.path == "/api/status":
                self._send_json(
                    {
                        "ok": True,
                        "service": "mythic-vibe-web-terminal",
                        "host": config.host,
                        "port": config.port,
                    }
                )
                return
            self._send_status(404, "not found")

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/run":
                self._send_status(404, "not found")
                return
            payload = self._read_json_body()
            if payload is None:
                return  # error already sent
            response = handle_run_request(payload, config=config)
            self._send_json(response)

        # ---- Helpers ---------------------------------------------

        def _send_status(self, code: int, message: str) -> None:
            body = json.dumps({"error": message}).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _send_javascript(self, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header(
                "Content-Type", "application/javascript; charset=utf-8"
            )
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _read_json_body(self) -> dict | None:
            length_header = self.headers.get("Content-Length", "0")
            try:
                length = int(length_header)
            except (TypeError, ValueError):
                self._send_status(400, "Content-Length missing or invalid")
                return None
            if length <= 0:
                self._send_status(400, "empty body")
                return None
            # Phase 19.0 / BS-1 (additive 2026-05-02 audit remediation):
            # reject oversized request bodies with HTTP 413 BEFORE
            # calling rfile.read(). A malicious client advertising
            # Content-Length: 1073741824 used to block a server thread
            # forever waiting for those bytes; capping at
            # config.max_request_body_bytes (default 64 KiB) defeats
            # that DoS vector while keeping legitimate /api/run JSON
            # payloads well under the limit (token + command + argv is
            # typically < 4 KiB).
            if length > config.max_request_body_bytes:
                self._send_status(
                    413,
                    f"request body too large: {length} bytes "
                    f"(max {config.max_request_body_bytes})",
                )
                return None
            try:
                raw = self.rfile.read(length).decode("utf-8")
                payload = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_status(400, "invalid JSON body")
                return None
            if not isinstance(payload, dict):
                self._send_status(400, "JSON body must be an object")
                return None
            return payload

    return WebTerminalHandler


# ---- Pure command dispatch ---------------------------------------------


def handle_run_request(
    payload: dict, *, config: WebTerminalConfig
) -> dict:
    """Pure function — used by the handler AND the tests. Validates
    token, parses argv, dispatches to a Mythic CLI handler, and
    returns the structured response.

    Returns a dict with one of:
    - ``{error: str}`` when validation fails (auth, payload shape).
    - ``{exit_code, stdout, stderr, command}`` on a successful
      dispatch.
    """
    from ..app import build_parser
    from ..commands import COMMAND_HANDLERS

    token = payload.get("token", "")
    if not isinstance(token, str) or not token:
        return {"error": "missing token"}
    if not secrets.compare_digest(token, config.token):
        return {"error": "invalid token"}

    command = payload.get("command", "")
    if not isinstance(command, str) or not command:
        return {"error": "missing command"}
    if command not in COMMAND_HANDLERS:
        return {"error": f"unknown command: {command}"}

    raw_argv = payload.get("argv", [])
    if not isinstance(raw_argv, list) or not all(
        isinstance(a, str) for a in raw_argv
    ):
        return {"error": "argv must be a list of strings"}

    parser = build_parser()
    try:
        ns = parser.parse_args([command, *raw_argv])
    except SystemExit as exc:
        return {
            "error": f"argparse rejected argv: exit={exc.code}",
        }

    handler = COMMAND_HANDLERS[command]
    out = io.StringIO()
    err = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            exit_code = int(handler(ns) or 0)
    except SystemExit as exc:
        exit_code = exc.code if isinstance(exc.code, int) else 1
    except Exception as exc:  # noqa: BLE001 — never propagate to HTTP
        exit_code = 1
        err.write(f"{type(exc).__name__}: {exc}\n")
    return {
        "exit_code": exit_code,
        "stdout": out.getvalue(),
        "stderr": err.getvalue(),
        "command": command,
    }


# ---- Free-port helper for tests --------------------------------------


def find_free_port(host: str = "127.0.0.1") -> int:
    """Open + immediately close a socket to claim an OS-assigned
    port. Tests use this to launch a server on a port the host
    hasn't allocated."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "WebTerminalConfig",
    "WebTerminalServer",
    "find_free_port",
    "handle_run_request",
]
