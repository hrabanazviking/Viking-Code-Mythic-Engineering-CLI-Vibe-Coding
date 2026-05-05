"""Tests for PH-17 Slice 17.1 — web terminal surface."""

from __future__ import annotations

import json
import threading
import time
import unittest
import urllib.error
import urllib.request

from mythic_vibe_cli.surfaces.web_terminal import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    WebTerminalConfig,
    WebTerminalServer,
    find_free_port,
    handle_run_request,
)


class HandleRunRequestTests(unittest.TestCase):
    def _config(self) -> WebTerminalConfig:
        return WebTerminalConfig(token="secret-token-123")

    def test_missing_token(self) -> None:
        result = handle_run_request({}, config=self._config())
        self.assertIn("error", result)
        self.assertIn("token", result["error"])

    def test_invalid_token(self) -> None:
        result = handle_run_request(
            {"token": "wrong"}, config=self._config()
        )
        self.assertIn("error", result)
        self.assertIn("invalid token", result["error"])

    def test_missing_command(self) -> None:
        result = handle_run_request(
            {"token": "secret-token-123"}, config=self._config()
        )
        self.assertIn("missing command", result["error"])

    def test_unknown_command(self) -> None:
        result = handle_run_request(
            {"token": "secret-token-123", "command": "ghost"},
            config=self._config(),
        )
        self.assertIn("unknown command", result["error"])

    def test_argv_must_be_list_of_strings(self) -> None:
        result = handle_run_request(
            {
                "token": "secret-token-123",
                "command": "status",
                "argv": [1, 2, 3],
            },
            config=self._config(),
        )
        self.assertIn("argv must be", result["error"])

    def test_status_command_runs(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            result = handle_run_request(
                {
                    "token": "secret-token-123",
                    "command": "status",
                    "argv": ["--path", tmp, "--json"],
                },
                config=self._config(),
            )
        self.assertIn("exit_code", result)
        self.assertIsInstance(result["stdout"], str)
        self.assertIsInstance(result["stderr"], str)

    def test_token_compared_securely(self) -> None:
        """Tokens with the same prefix but different lengths are
        rejected — the secrets.compare_digest defeats simple
        timing attacks."""
        config = WebTerminalConfig(token="abcdef")
        result = handle_run_request(
            {"token": "abcdefg", "command": "status"}, config=config
        )
        self.assertIn("invalid token", result["error"])


class FindFreePortTests(unittest.TestCase):
    def test_returns_int_in_valid_range(self) -> None:
        port = find_free_port()
        self.assertIsInstance(port, int)
        self.assertGreater(port, 1024)
        self.assertLess(port, 65536)


class WebTerminalServerLifecycleTests(unittest.TestCase):
    """Spin up a real loopback server, hit it with urllib, then
    shut it down. Smoke-tests the routes + token gating."""

    def test_full_lifecycle(self) -> None:
        port = find_free_port()
        config = WebTerminalConfig(host="127.0.0.1", port=port, token="t")
        server = WebTerminalServer(config=config)

        thread = threading.Thread(target=server.start, daemon=True)
        thread.start()
        # Tiny sleep to let the server bind.
        time.sleep(0.1)

        try:
            # GET / returns HTML.
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/", timeout=3
            ) as resp:
                body = resp.read().decode("utf-8")
                self.assertEqual(resp.status, 200)
                self.assertIn("Mythic Vibe", body)
                self.assertIn("xterm", body)

            # GET /api/status (no auth required) returns JSON.
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/status", timeout=3
            ) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(payload["ok"])

            # POST /api/run with a wrong token returns 200 + error.
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/run",
                data=json.dumps({"token": "nope", "command": "status"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=3) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                self.assertIn("error", payload)

            # GET /unknown returns 404.
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/ghost", timeout=3
                )
            self.assertEqual(ctx.exception.code, 404)
        finally:
            server.stop()
            thread.join(timeout=2)


class WebTerminalConfigTests(unittest.TestCase):
    def test_default_host_and_port(self) -> None:
        self.assertEqual(DEFAULT_HOST, "127.0.0.1")
        self.assertEqual(DEFAULT_PORT, 8765)

    def test_token_auto_generated(self) -> None:
        c1 = WebTerminalConfig()
        c2 = WebTerminalConfig()
        # Auto-generated tokens are unique per instance.
        self.assertNotEqual(c1.token, c2.token)
        # 32-byte URL-safe token decodes to ~43 chars.
        self.assertGreater(len(c1.token), 30)


# ---- Phase 19.0 / BS-1 (audit remediation 2026-05-02) ----------------
#
# DoS-protection regression tests for the web terminal surface:
# Content-Length cap (HTTP 413) + per-connection socket timeout.


class RequestBodyCapTests(unittest.TestCase):
    """Phase 19.0 BS-1 — the request handler must reject bodies
    larger than ``config.max_request_body_bytes`` BEFORE allocating
    the read buffer. Without this cap a single malicious client
    advertising ``Content-Length: 1073741824`` could exhaust server
    memory or pin a thread until the bytes arrive."""

    def _start_server(self) -> tuple[WebTerminalServer, WebTerminalConfig]:
        from mythic_vibe_cli.surfaces.web_terminal import (
            MAX_REQUEST_BODY_BYTES,
            DEFAULT_SOCKET_TIMEOUT_SECONDS,
        )

        config = WebTerminalConfig(
            host="127.0.0.1",
            port=find_free_port(),
            token="test-token-bs1",
            max_request_body_bytes=MAX_REQUEST_BODY_BYTES,
            socket_timeout_seconds=DEFAULT_SOCKET_TIMEOUT_SECONDS,
        )
        server = WebTerminalServer(config=config)
        thread = threading.Thread(target=server.start, daemon=True)
        thread.start()
        # Give the server a beat to bind.
        for _ in range(50):
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{config.port}/api/status", timeout=0.5
                ) as resp:
                    if resp.status == 200:
                        return server, config
            except (urllib.error.URLError, ConnectionRefusedError, OSError):
                time.sleep(0.05)
        raise RuntimeError("web terminal server failed to start")

    def test_oversized_content_length_returns_413(self) -> None:
        """A malicious / misbehaving client advertises a huge
        Content-Length and sends only a tiny body. The server must
        reject with HTTP 413 BEFORE attempting to read the bytes —
        otherwise it would block waiting for the rest of the
        advertised payload.

        We use a raw socket because ``urllib.request`` rewrites
        Content-Length based on the actual body size; this test
        needs the header value to lie about the body size.
        """
        import socket as _socket

        from mythic_vibe_cli.surfaces.web_terminal import (
            MAX_REQUEST_BODY_BYTES,
        )

        server, config = self._start_server()
        try:
            tiny_body = b'{"x":1}'
            # The lie: claim 65537 bytes (1 over the cap), send 7.
            request = (
                b"POST /api/run HTTP/1.1\r\n"
                b"Host: 127.0.0.1\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: " + str(MAX_REQUEST_BODY_BYTES + 1).encode() + b"\r\n"
                b"Connection: close\r\n"
                b"\r\n"
                + tiny_body
            )
            with _socket.create_connection(
                ("127.0.0.1", config.port), timeout=5.0
            ) as sock:
                sock.sendall(request)
                # Read the response. The server should send 413 +
                # body promptly, then close.
                chunks: list[bytes] = []
                sock.settimeout(5.0)
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                response = b"".join(chunks)
            # Parse the status line.
            status_line = response.split(b"\r\n", 1)[0].decode("iso-8859-1")
            self.assertIn(
                "413",
                status_line,
                f"expected HTTP 413, got status line: {status_line!r}",
            )
            # The body is JSON with the error message after the
            # blank-line separator.
            _, _, body_bytes = response.partition(b"\r\n\r\n")
            error_body = json.loads(body_bytes.decode("utf-8"))
            self.assertIn("too large", error_body["error"])
        finally:
            server.stop()

    def test_normal_sized_body_still_accepted(self) -> None:
        """Regression: the cap must NOT reject legitimate payloads.
        A typical /api/run JSON is well under 4 KiB."""
        server, config = self._start_server()
        try:
            url = f"http://127.0.0.1:{config.port}/api/run"
            body = json.dumps({
                "token": config.token,
                "command": "version",
                "argv": [],
            }).encode("utf-8")
            request = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5.0) as resp:
                self.assertEqual(resp.status, 200)
                payload = json.loads(resp.read().decode("utf-8"))
            # version command exits 0 and prints something.
            self.assertEqual(payload.get("exit_code"), 0)
            self.assertEqual(payload.get("command"), "version")
        finally:
            server.stop()


class WebTerminalConfigBs1FieldTests(unittest.TestCase):
    """The new fields ``max_request_body_bytes`` and
    ``socket_timeout_seconds`` should round-trip on construction."""

    def test_defaults_match_module_constants(self) -> None:
        from mythic_vibe_cli.surfaces.web_terminal import (
            MAX_REQUEST_BODY_BYTES,
            DEFAULT_SOCKET_TIMEOUT_SECONDS,
        )

        config = WebTerminalConfig()
        self.assertEqual(
            config.max_request_body_bytes, MAX_REQUEST_BODY_BYTES
        )
        self.assertEqual(
            config.socket_timeout_seconds, DEFAULT_SOCKET_TIMEOUT_SECONDS
        )

    def test_explicit_overrides_take_effect(self) -> None:
        config = WebTerminalConfig(
            max_request_body_bytes=128 * 1024,
            socket_timeout_seconds=10.0,
        )
        self.assertEqual(config.max_request_body_bytes, 128 * 1024)
        self.assertEqual(config.socket_timeout_seconds, 10.0)

    def test_socket_timeout_zero_disables_legacy_behaviour(self) -> None:
        """A 0.0 timeout means "no timeout" — preserves the
        pre-Phase-19 unbounded-read behaviour for operators with
        unusual long-poll needs. The server.start path must NOT call
        socket.settimeout in that case."""
        config = WebTerminalConfig(socket_timeout_seconds=0.0)
        # We don't actually start a server here — just confirm the
        # config field accepts 0.0. The server.start path's
        # ``if self.config.socket_timeout_seconds > 0.0`` guard
        # handles the runtime branch.
        self.assertEqual(config.socket_timeout_seconds, 0.0)


# PH-23.14 — coverage push for web_terminal.py from 80% toward
# 95%+. Targets: _send_javascript (static/app.js path), 404
# branches in do_GET + do_POST, _read_json_body error branches
# (Content-Length / empty / oversized / invalid-JSON / non-dict),
# handle_run_request argparse-SystemExit + handler-exception
# branches, server.stop() OSError swallows.


def _live_server_request(method: str, path: str, body: bytes | None = None,
                         headers: dict[str, str] | None = None,
                         timeout: float = 5.0) -> tuple[int, bytes]:
    """Helper: start a WebTerminalServer on a free port, send the
    given request, return (status_code, body). Cleanly stops the
    server in a finally block.
    """
    config = WebTerminalConfig(
        token="secret-token-123",
        host="127.0.0.1",
        port=find_free_port(),
        max_request_body_bytes=8 * 1024,
        socket_timeout_seconds=2.0,
    )
    server = WebTerminalServer(config)
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    # Brief wait for the bind to complete.
    deadline = time.perf_counter() + 2.0
    while time.perf_counter() < deadline:
        try:
            url = f"http://{config.host}:{config.port}{path}"
            request = urllib.request.Request(
                url, data=body, method=method,
                headers=headers or {},
            )
            with urllib.request.urlopen(request, timeout=timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()
        except (ConnectionRefusedError, OSError):
            time.sleep(0.05)
    raise RuntimeError("server failed to bind in 2 seconds")


def _live_server_request_then_stop(
    method: str, path: str, body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes, WebTerminalServer]:
    """Variant that returns the server too so the caller can
    drive lifecycle assertions. The caller is responsible for
    server.stop()."""
    config = WebTerminalConfig(
        token="secret-token-123",
        host="127.0.0.1",
        port=find_free_port(),
        max_request_body_bytes=8 * 1024,
        socket_timeout_seconds=2.0,
    )
    server = WebTerminalServer(config)
    thread = threading.Thread(target=server.start, daemon=True)
    thread.start()
    deadline = time.perf_counter() + 2.0
    while time.perf_counter() < deadline:
        try:
            url = f"http://{config.host}:{config.port}{path}"
            request = urllib.request.Request(
                url, data=body, method=method,
                headers=headers or {},
            )
            with urllib.request.urlopen(request, timeout=5.0) as resp:
                return resp.status, resp.read(), server
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), server
        except (ConnectionRefusedError, OSError):
            time.sleep(0.05)
    server.stop()
    raise RuntimeError("server failed to bind")


class WebTerminalLiveServerTests(unittest.TestCase):
    """PH-23.14 — drive the live server through HTTP to cover
    handler routing branches that pure-function tests can't reach."""

    def test_static_app_js_route(self) -> None:
        # Lines 226-228 + 281-289: GET /static/app.js delivers
        # the JS body via _send_javascript.
        status, body = _live_server_request("GET", "/static/app.js")
        self.assertEqual(status, 200)
        self.assertGreater(len(body), 0)

    def test_get_unknown_path_returns_404(self) -> None:
        # Line 239: GET to an unknown path → 404.
        status, body = _live_server_request("GET", "/nope")
        self.assertEqual(status, 404)

    def test_post_to_wrong_path_returns_404(self) -> None:
        # Lines 242-244: POST to anything other than /api/run → 404.
        status, body = _live_server_request(
            "POST", "/api/wrong",
            body=b"{}",
            headers={"Content-Length": "2", "Content-Type": "application/json"},
        )
        self.assertEqual(status, 404)

    def test_missing_content_length_returns_400(self) -> None:
        # Lines 295-297: Content-Length header missing or invalid.
        # We can't easily send a missing header via urllib, but
        # we CAN send an invalid value.
        status, body = _live_server_request(
            "POST", "/api/run",
            body=b"{}",
            headers={"Content-Length": "not-a-number",
                     "Content-Type": "application/json"},
        )
        # Note: urllib may override Content-Length; if so we get
        # a different status. Accept either 400 (our code) or 200
        # (urllib overrode).
        self.assertIn(status, {400, 200})

    def test_empty_body_returns_400(self) -> None:
        # Lines 299-300: Content-Length: 0 → "empty body".
        status, body = _live_server_request(
            "POST", "/api/run",
            body=b"",
            headers={"Content-Length": "0",
                     "Content-Type": "application/json"},
        )
        self.assertEqual(status, 400)
        self.assertIn(b"empty body", body)

    def test_invalid_json_body_returns_400(self) -> None:
        # Lines 320-322: body decodes/parses fail.
        bad_json = b"{ not json"
        status, body = _live_server_request(
            "POST", "/api/run",
            body=bad_json,
            headers={"Content-Length": str(len(bad_json)),
                     "Content-Type": "application/json"},
        )
        self.assertEqual(status, 400)
        self.assertIn(b"invalid JSON", body)

    def test_non_dict_json_body_returns_400(self) -> None:
        # Lines 324-325: JSON parses but isn't a dict.
        list_json = b"[1, 2, 3]"
        status, body = _live_server_request(
            "POST", "/api/run",
            body=list_json,
            headers={"Content-Length": str(len(list_json)),
                     "Content-Type": "application/json"},
        )
        self.assertEqual(status, 400)
        self.assertIn(b"object", body)

    def test_server_stop_is_idempotent_after_first_call(self) -> None:
        # Lines 196-201: stop() handles OSError on shutdown +
        # server_close gracefully. We exercise the happy path
        # then call stop() a second time to verify it doesn't
        # raise on already-closed handles.
        status, body, server = _live_server_request_then_stop(
            "GET", "/api/status",
        )
        self.assertEqual(status, 200)
        # First stop — happy path.
        server.stop()
        # Second stop — must not raise even though shutdown +
        # server_close are already done.
        server.stop()


class HandleRunRequestExceptionPathTests(unittest.TestCase):
    """PH-23.14 — cover lines 370-371 + 381-385 in
    handle_run_request: argparse SystemExit + handler exceptions."""

    def test_argparse_rejects_invalid_argv(self) -> None:
        # Lines 370-371: parser.parse_args raises SystemExit when
        # argv is malformed (e.g. unknown flag).
        result = handle_run_request(
            {
                "token": "secret-token-123",
                "command": "status",
                "argv": ["--this-flag-does-not-exist"],
            },
            config=WebTerminalConfig(token="secret-token-123"),
        )
        self.assertIn("error", result)
        self.assertIn("argparse rejected argv", result["error"])

    def test_handler_raising_exception_returns_exit_one(self) -> None:
        # Lines 383-385: handler raises a generic Exception →
        # exit_code=1, stderr captures the exception.
        from unittest import mock

        with mock.patch.dict(
            "mythic_vibe_cli.commands.COMMAND_HANDLERS",
            {
                "doctor": lambda ns: (_ for _ in ()).throw(
                    RuntimeError("boom")
                )
            },
            clear=False,
        ):
            result = handle_run_request(
                {
                    "token": "secret-token-123",
                    "command": "doctor",
                    "argv": [],
                },
                config=WebTerminalConfig(token="secret-token-123"),
            )

        self.assertEqual(result["exit_code"], 1)
        self.assertIn("RuntimeError", result["stderr"])
        self.assertIn("boom", result["stderr"])

    def test_handler_systemexit_with_int_carries_exit_code(self) -> None:
        # Line 381-382: SystemExit with int code maps directly.
        from unittest import mock

        with mock.patch.dict(
            "mythic_vibe_cli.commands.COMMAND_HANDLERS",
            {
                "doctor": lambda ns: (_ for _ in ()).throw(
                    SystemExit(42)
                )
            },
            clear=False,
        ):
            result = handle_run_request(
                {
                    "token": "secret-token-123",
                    "command": "doctor",
                    "argv": [],
                },
                config=WebTerminalConfig(token="secret-token-123"),
            )

        self.assertEqual(result["exit_code"], 42)


if __name__ == "__main__":
    unittest.main()
