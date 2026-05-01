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


if __name__ == "__main__":
    unittest.main()
