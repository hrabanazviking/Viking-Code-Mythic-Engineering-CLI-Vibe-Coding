"""Tests for `mythic-vibe ai models` (PH-06 slice 6.3)."""

from __future__ import annotations

import argparse
import io
import json
import os
import threading
import unittest
from contextlib import contextmanager, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from unittest import mock

from mythic_vibe_cli.ai.ollama_health import OLLAMA_HOST_ENV, OllamaHealth
from mythic_vibe_cli.app import build_parser
from mythic_vibe_cli.exit_codes import OPERATIONAL_FAILURE, SUCCESS, USER_INPUT_ERROR


# ---- Stub Ollama daemon for /api/tags --------------------------------


class _TagsHandler(BaseHTTPRequestHandler):
    payload: dict[str, Any] = {"models": []}

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/tags":
            body = json.dumps(self.payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


@contextmanager
def _stub_daemon(payload: dict[str, Any]):
    """Spin up a stub /api/tags server on an ephemeral port and
    point OLLAMA_HOST at it for the duration of the block."""

    class Handler(_TagsHandler):
        pass

    Handler.payload = payload
    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    saved = os.environ.get(OLLAMA_HOST_ENV)
    os.environ[OLLAMA_HOST_ENV] = f"127.0.0.1:{port}"
    try:
        yield
    finally:
        if saved is None:
            os.environ.pop(OLLAMA_HOST_ENV, None)
        else:
            os.environ[OLLAMA_HOST_ENV] = saved
        server.shutdown()
        thread.join(timeout=2.0)


# ---- argparse ----------------------------------------------------------


class AiModelsArgparseTests(unittest.TestCase):
    def test_parses_with_provider(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["ai", "models", "--provider", "ollama"])
        self.assertEqual(ns.command, "ai")
        self.assertEqual(ns.ai_command, "models")
        self.assertEqual(ns.provider, "ollama")

    def test_provider_required(self) -> None:
        parser = build_parser()
        from contextlib import redirect_stderr

        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                parser.parse_args(["ai", "models"])


# ---- cmd_ai_models -----------------------------------------------------


class CmdAiModelsOllamaTests(unittest.TestCase):
    def test_unreachable_daemon_returns_operational_failure(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_models

        ns = argparse.Namespace(provider="ollama", json=True, path=".")
        with mock.patch(
            "mythic_vibe_cli.ai.ollama_health.check_ollama_health",
            return_value=OllamaHealth(
                reachable=False,
                endpoint="http://127.0.0.1:11434",
                latency_ms=0.0,
                error="connection refused",
                details=["could not reach http://127.0.0.1:11434"],
            ),
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_ai_models(ns)
        self.assertEqual(exit_code, OPERATIONAL_FAILURE)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["command"], "ai models")
        self.assertEqual(payload["provider"], "ollama")
        self.assertFalse(payload["health"]["reachable"])
        self.assertEqual(payload["models"], [])

    def test_reachable_daemon_lists_models_json(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_models

        models_payload = {
            "models": [
                {"name": "llama3.2:3b", "size": 1234},
                {
                    "name": "qwen2.5:7b",
                    "size": 5678,
                    "details": {"family": "qwen"},
                },
            ]
        }
        ns = argparse.Namespace(provider="ollama", json=True, path=".")
        with _stub_daemon(models_payload):
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_ai_models(ns)
        self.assertEqual(exit_code, SUCCESS)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["health"]["reachable"])
        self.assertEqual(len(payload["models"]), 2)
        names = {m["name"] for m in payload["models"]}
        self.assertEqual(names, {"llama3.2:3b", "qwen2.5:7b"})

    def test_reachable_daemon_text_output(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_models

        ns = argparse.Namespace(provider="ollama", json=False, path=".")
        with _stub_daemon(
            {
                "models": [
                    {"name": "llama3.2:3b", "size": 999},
                    {"name": "qwen2.5:7b", "details": {"family": "qwen"}},
                ]
            }
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_models(ns)
        rendered = buf.getvalue()
        self.assertIn("llama3.2:3b", rendered)
        self.assertIn("qwen2.5:7b", rendered)
        self.assertIn("size=999", rendered)
        self.assertIn("family=qwen", rendered)

    def test_reachable_but_no_models_explains_pull(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_models

        ns = argparse.Namespace(provider="ollama", json=False, path=".")
        with _stub_daemon({"models": []}):
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_ai_models(ns)
        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("no models installed", buf.getvalue())
        self.assertIn("ollama pull", buf.getvalue())


class CmdAiModelsNonOllamaTests(unittest.TestCase):
    def test_other_provider_returns_not_implemented_note(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_models

        ns = argparse.Namespace(provider="anthropic", json=True, path=".")
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_ai_models(ns)
        self.assertEqual(exit_code, SUCCESS)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["provider"], "anthropic")
        self.assertEqual(payload["models"], [])
        self.assertIn("not implemented", payload["note"])

    def test_unknown_provider_returns_user_input_error(self) -> None:
        # cmd_ai_models is dispatched directly here (not via main)
        # with a bogus provider name that argparse would have caught;
        # we still want a clean USER_INPUT_ERROR if the dispatcher
        # is bypassed.
        from mythic_vibe_cli.commands import cmd_ai_models

        ns = argparse.Namespace(provider="not-a-provider", json=True, path=".")
        self.assertEqual(cmd_ai_models(ns), USER_INPUT_ERROR)


# ---- Dispatcher --------------------------------------------------------


class AiDispatchTests(unittest.TestCase):
    def test_models_routed_through_dispatch(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_dispatch, cmd_ai_models

        with mock.patch(
            "mythic_vibe_cli.commands.cmd_ai_models",
            wraps=cmd_ai_models,
        ) as wrapped:
            ns = argparse.Namespace(
                ai_command="models",
                provider="anthropic",
                json=True,
                path=".",
            )
            with redirect_stdout(io.StringIO()):
                cmd_ai_dispatch(ns)
            wrapped.assert_called_once_with(ns)

    def test_unknown_subcommand_includes_models_in_help(self) -> None:
        from contextlib import redirect_stderr

        from mythic_vibe_cli.commands import cmd_ai_dispatch

        ns = argparse.Namespace(ai_command="bogus", json=True)
        buf = io.StringIO()
        with redirect_stderr(buf):
            exit_code = cmd_ai_dispatch(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)
        self.assertIn("models", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
