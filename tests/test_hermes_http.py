"""Hermes HTTP API tests.

Mostly exercises the pure ``handle_*`` routing functions
without binding a port. One end-to-end live-server test is
included to verify the full HTTP path is wired correctly
(token auth, body cap, JSON envelopes).
"""

from __future__ import annotations

import json
import secrets
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from mythic_vibe_cli.agent_api import (
    HermesHttpConfig,
    build_default_agent,
    build_default_http_server,
)
from mythic_vibe_cli.agent_api.http_api import (
    check_token,
    handle_events,
    handle_health,
    handle_invoke,
    handle_list_artifacts,
    handle_list_tools,
    handle_read_artifact,
    handle_state,
)


def _config(token: str = "secret") -> HermesHttpConfig:
    """Build a config bound to a default agent's core."""
    agent = build_default_agent(root=tempfile.gettempdir())
    return HermesHttpConfig(core=agent.core, token=token)


class CheckTokenTests(unittest.TestCase):
    def test_correct_token_passes(self) -> None:
        config = _config(token="abc")
        self.assertTrue(check_token("abc", config))

    def test_wrong_token_fails(self) -> None:
        config = _config(token="abc")
        self.assertFalse(check_token("xyz", config))

    def test_empty_token_fails(self) -> None:
        config = _config(token="abc")
        self.assertFalse(check_token("", config))
        self.assertFalse(check_token(None, config))


class HandleHealthTests(unittest.TestCase):
    def test_payload_shape(self) -> None:
        config = _config()
        payload = handle_health(config)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "mythic-vibe-hermes")
        self.assertGreater(payload["tool_count"], 0)


class HandleListToolsTests(unittest.TestCase):
    def test_returns_curated_tool_list(self) -> None:
        config = _config()
        payload = handle_list_tools(config)
        self.assertTrue(payload["ok"])
        names = {t["name"] for t in payload["value"]["tools"]}
        for required in ("status", "doctor", "checkin", "verify"):
            self.assertIn(required, names)


class HandleInvokeTests(unittest.TestCase):
    def test_invoke_status(self) -> None:
        config = _config()
        payload = handle_invoke({"tool": "status"}, config)
        self.assertTrue(payload["ok"])
        result = payload["value"]
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["tool"], "status")
        self.assertIn("summary", result["value"])

    def test_invoke_unknown_tool(self) -> None:
        config = _config()
        payload = handle_invoke({"tool": "nonexistent"}, config)
        self.assertTrue(payload["ok"])  # envelope is OK; result inside is unknown_tool
        result = payload["value"]
        self.assertEqual(result["status"], "unknown_tool")

    def test_invoke_validation_error(self) -> None:
        config = _config()
        payload = handle_invoke(
            {"tool": "checkin", "args": {}},  # missing required phase + update
            config,
        )
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["value"]["status"], "validation_error")

    def test_invoke_missing_tool_field(self) -> None:
        config = _config()
        payload = handle_invoke({"args": {}}, config)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "bad_request")

    def test_invoke_payload_must_be_object(self) -> None:
        config = _config()
        payload = handle_invoke([], config)  # type: ignore[arg-type]
        self.assertFalse(payload["ok"])

    def test_invoke_args_must_be_object(self) -> None:
        config = _config()
        payload = handle_invoke({"tool": "status", "args": []}, config)
        self.assertFalse(payload["ok"])

    def test_request_id_round_trips(self) -> None:
        config = _config()
        payload = handle_invoke(
            {"tool": "status", "request_id": "req-42"},
            config,
        )
        self.assertEqual(payload["value"]["request_id"], "req-42")


class HandleStateTests(unittest.TestCase):
    def test_returns_envelope_with_state_show_result(self) -> None:
        config = _config()
        payload = handle_state(config)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["value"]["tool"], "state_show")


class HandleListArtifactsTests(unittest.TestCase):
    def test_default_lists_mythic_dir(self) -> None:
        config = _config()
        payload = handle_list_artifacts({}, config)
        self.assertTrue(payload["ok"])
        # The tempdir has no mythic/ — so exists is False but envelope ok.
        self.assertEqual(payload["value"]["status"], "ok")

    def test_invalid_limit_returns_bad_request(self) -> None:
        config = _config()
        payload = handle_list_artifacts({"limit": ["not-a-number"]}, config)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "bad_request")


class HandleReadArtifactTests(unittest.TestCase):
    def test_reads_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "hello.txt"
            target.write_text("hi", encoding="utf-8")
            agent = build_default_agent(root=tmp)
            config = HermesHttpConfig(core=agent.core, token="t")
            payload = handle_read_artifact("hello.txt", {}, config)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["value"]["status"], "ok")
        self.assertEqual(payload["value"]["value"]["content"], "hi")

    def test_path_escape_attempt_returns_error_status(self) -> None:
        config = _config()
        payload = handle_read_artifact("../../../etc/passwd", {}, config)
        self.assertTrue(payload["ok"])  # envelope ok
        self.assertEqual(payload["value"]["status"], "error")


class HandleEventsTests(unittest.TestCase):
    def test_invokes_recent_events_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            agent.status()  # produce one event
            config = HermesHttpConfig(core=agent.core, token="t")
            payload = handle_events({"limit": ["5"]}, config)
        self.assertTrue(payload["ok"])
        result = payload["value"]
        self.assertEqual(result["status"], "ok")
        self.assertGreater(result["value"]["count"], 0)


# ---------------------------------------------------------------------------
# Live-server end-to-end smoke
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Pick an unused localhost port for the test server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class HermesHttpLiveServerTests(unittest.TestCase):
    """One end-to-end test that binds a port and hits real
    endpoints. Verifies the auth / routing / body-cap wiring."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.token = secrets.token_urlsafe(16)
        self.port = _free_port()
        self.server = build_default_http_server(
            root=self.tmpdir.name,
            host="127.0.0.1",
            port=self.port,
            token=self.token,
        )
        self.thread = threading.Thread(target=self.server.start, daemon=True)
        self.thread.start()
        # Tiny wait for server to bind.
        for _ in range(50):
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.1):
                    break
            except OSError:
                continue

    def tearDown(self) -> None:
        self.server.stop()
        self.thread.join(timeout=2.0)
        self.tmpdir.cleanup()

    def _get(self, path: str, *, headers: dict[str, str] | None = None) -> tuple[int, dict]:
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                code = resp.status
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            code = exc.code
            payload = json.loads(exc.read().decode("utf-8"))
        return code, payload

    def _post(self, path: str, body: dict, *, headers: dict[str, str] | None = None) -> tuple[int, dict]:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                code = resp.status
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            code = exc.code
            payload = json.loads(exc.read().decode("utf-8"))
        return code, payload

    def test_health_endpoint_no_auth(self) -> None:
        code, payload = self._get("/api/health")
        self.assertEqual(code, 200)
        self.assertEqual(payload["service"], "mythic-vibe-hermes")

    def test_tools_requires_auth(self) -> None:
        code, payload = self._get("/api/tools")
        self.assertEqual(code, 401)
        self.assertFalse(payload["ok"])

    def test_tools_with_header_token(self) -> None:
        code, payload = self._get(
            "/api/tools",
            headers={"X-Hermes-Token": self.token},
        )
        self.assertEqual(code, 200)
        self.assertTrue(payload["ok"])
        names = {t["name"] for t in payload["value"]["tools"]}
        self.assertIn("status", names)

    def test_invoke_with_body_token(self) -> None:
        code, payload = self._post(
            "/api/invoke",
            {"token": self.token, "tool": "status"},
        )
        self.assertEqual(code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["value"]["tool"], "status")

    def test_invoke_rejects_wrong_token(self) -> None:
        code, payload = self._post(
            "/api/invoke",
            {"token": "wrong", "tool": "status"},
        )
        self.assertEqual(code, 401)
        self.assertFalse(payload["ok"])

    def test_unknown_endpoint_returns_404(self) -> None:
        code, _ = self._get(
            "/api/nope",
            headers={"X-Hermes-Token": self.token},
        )
        self.assertEqual(code, 404)


# ---------------------------------------------------------------------------
# PH-24.2 coverage push — error-path coverage for the HTTP layer:
# missing tools (state_show / list_artifacts / read_artifact / recent_events
# absent from the registry), bad query-param shapes, server lifecycle.
# Goal: take ``agent_api/http_api.py`` from ~73% to 90%+.
# ---------------------------------------------------------------------------


from mythic_vibe_cli.agent_api.core import HermesCore  # noqa: E402
from mythic_vibe_cli.agent_api.http_api import (  # noqa: E402
    HermesHttpServer,
    _err_envelope,
    _ok_envelope,
)


def _bare_core_config() -> HermesHttpConfig:
    """Build a config whose core has no tools — exercises the
    ``not_implemented`` branches in handle_state/list_artifacts/etc."""
    with tempfile.TemporaryDirectory() as tmp:
        core = HermesCore(root=Path(tmp))
        return HermesHttpConfig(core=core, token="t")


class HandleStateMissingToolTests(unittest.TestCase):
    def test_returns_not_implemented_when_state_show_absent(self) -> None:
        config = _bare_core_config()
        payload = handle_state(config)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "not_implemented")


class HandleListArtifactsErrorTests(unittest.TestCase):
    def test_not_implemented_when_tool_absent(self) -> None:
        config = _bare_core_config()
        payload = handle_list_artifacts({}, config)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "not_implemented")

    def test_glob_query_passes_through(self) -> None:
        config = _config()
        payload = handle_list_artifacts({"glob": ["*.txt"], "under": ["mythic"]}, config)
        self.assertTrue(payload["ok"])

    def test_invalid_limit_returns_bad_request(self) -> None:
        config = _config()
        payload = handle_list_artifacts({"limit": ["not-an-int"]}, config)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "bad_request")


class HandleReadArtifactErrorTests(unittest.TestCase):
    def test_not_implemented_when_tool_absent(self) -> None:
        config = _bare_core_config()
        payload = handle_read_artifact("any.txt", {}, config)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "not_implemented")

    def test_invalid_max_bytes_returns_bad_request(self) -> None:
        config = _config()
        payload = handle_read_artifact("x.txt", {"max_bytes": ["nan"]}, config)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "bad_request")


class HandleEventsErrorTests(unittest.TestCase):
    def test_not_implemented_when_tool_absent(self) -> None:
        config = _bare_core_config()
        payload = handle_events({}, config)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "not_implemented")

    def test_invalid_limit_returns_bad_request(self) -> None:
        config = _config()
        payload = handle_events({"limit": ["bad"]}, config)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "bad_request")


class HandleInvokeRequestIdValidationTests(unittest.TestCase):
    def test_request_id_must_be_string_when_supplied(self) -> None:
        config = _config()
        payload = handle_invoke({"tool": "status", "request_id": 42}, config)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["code"], "bad_request")
        self.assertIn("request_id", payload["error"])


class EnvelopeHelperTests(unittest.TestCase):
    def test_ok_envelope_marks_value(self) -> None:
        self.assertEqual(_ok_envelope({"a": 1}), {"ok": True, "value": {"a": 1}})

    def test_err_envelope_includes_code(self) -> None:
        env = _err_envelope("nope", code="bad_request")
        self.assertFalse(env["ok"])
        self.assertEqual(env["code"], "bad_request")
        self.assertEqual(env["error"], "nope")

    def test_err_envelope_default_code(self) -> None:
        env = _err_envelope("nope")
        self.assertEqual(env["code"], "error")


class HermesHttpServerLifecycleTests(unittest.TestCase):
    """Cover server start/stop/bound_address — the wrapper around
    ThreadingHTTPServer that earlier tests instantiated indirectly."""

    def test_bound_address_is_none_before_start(self) -> None:
        config = _config()
        server = HermesHttpServer(config=config)
        self.assertIsNone(server.bound_address)

    def test_stop_is_idempotent_when_never_started(self) -> None:
        config = _config()
        server = HermesHttpServer(config=config)
        # Should not raise even with httpd is None.
        server.stop()

    def test_start_then_stop_returns_bound_address(self) -> None:
        """A live-server-like start/stop sequence on an ephemeral port,
        wrapped in a thread so the blocking serve_forever() returns
        when stop() is called."""
        agent = build_default_agent(root=tempfile.gettempdir())
        config = HermesHttpConfig(
            core=agent.core, host="127.0.0.1", port=0, token="t"
        )
        server = HermesHttpServer(config=config)
        thread = threading.Thread(target=server.start, daemon=True)
        thread.start()
        # Wait until httpd is bound.
        deadline = 5.0
        step = 0.02
        elapsed = 0.0
        while server.httpd is None and elapsed < deadline:
            import time
            time.sleep(step)
            elapsed += step
        try:
            self.assertIsNotNone(server.httpd)
            addr = server.bound_address
            self.assertIsNotNone(addr)
            self.assertEqual(addr[0], "127.0.0.1")
            self.assertGreater(addr[1], 0)
        finally:
            server.stop()
            thread.join(timeout=5.0)


if __name__ == "__main__":
    unittest.main()
