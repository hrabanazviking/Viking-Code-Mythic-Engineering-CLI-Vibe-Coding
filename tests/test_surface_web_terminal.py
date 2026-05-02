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


if __name__ == "__main__":
    unittest.main()
