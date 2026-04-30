"""Tests for the Ollama provider + daemon discovery (PH-06 slices 6.1 + 6.2)."""

from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from unittest import mock

from mythic_vibe_cli.ai.ollama_health import (
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_PORT,
    OLLAMA_HOST_ENV,
    OllamaHealth,
    _resolve_endpoint,
    check_ollama_health,
    is_ollama_daemon_up,
    list_models,
)
from mythic_vibe_cli.ai.providers.ollama import (
    DEFAULT_MODEL,
    OLLAMA_MODEL_ENV,
    OllamaProvider,
)
from mythic_vibe_cli.ai.registry import ProviderRegistry


# ---- Helpers ----------------------------------------------------------


@contextmanager
def _scrub_env(*names: str):
    """Temporarily delete environment variables, restoring on exit."""
    saved: dict[str, str] = {}
    for name in names:
        if name in os.environ:
            saved[name] = os.environ.pop(name)
    try:
        yield
    finally:
        for name, value in saved.items():
            os.environ[name] = value


class _StubHandler(BaseHTTPRequestHandler):
    """Configurable HTTP handler injected per-test via class attrs."""

    tags_payload: dict[str, Any] = {"models": []}
    generate_payload: dict[str, Any] = {"response": "stub reply"}

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return  # silence

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/tags":
            body = json.dumps(self.tags_payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/generate":
            length = int(self.headers.get("Content-Length", "0") or "0")
            _ = self.rfile.read(length)
            body = json.dumps(self.generate_payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


@contextmanager
def _stub_daemon(
    *,
    tags_payload: dict[str, Any] | None = None,
    generate_payload: dict[str, Any] | None = None,
):
    """Spin up a one-shot HTTP server on an ephemeral port mimicking
    Ollama's /api/tags and /api/generate endpoints. Sets OLLAMA_HOST
    so the adapter targets the stub for the duration of the block."""

    class Handler(_StubHandler):
        pass

    Handler.tags_payload = tags_payload or {"models": []}
    Handler.generate_payload = generate_payload or {"response": "stub reply"}

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    saved = os.environ.get(OLLAMA_HOST_ENV)
    os.environ[OLLAMA_HOST_ENV] = f"127.0.0.1:{port}"
    try:
        yield port
    finally:
        if saved is None:
            os.environ.pop(OLLAMA_HOST_ENV, None)
        else:
            os.environ[OLLAMA_HOST_ENV] = saved
        server.shutdown()
        thread.join(timeout=2.0)


# ---- _resolve_endpoint -------------------------------------------------


class ResolveEndpointTests(unittest.TestCase):
    def test_defaults_when_env_unset(self) -> None:
        with _scrub_env(OLLAMA_HOST_ENV):
            host, port = _resolve_endpoint(None, None)
        self.assertEqual(host, DEFAULT_OLLAMA_HOST)
        self.assertEqual(port, DEFAULT_OLLAMA_PORT)

    def test_explicit_args_override_env(self) -> None:
        try:
            os.environ[OLLAMA_HOST_ENV] = "evil.example:9999"
            host, port = _resolve_endpoint("override.local", 1234)
        finally:
            os.environ.pop(OLLAMA_HOST_ENV, None)
        self.assertEqual(host, "override.local")
        self.assertEqual(port, 1234)

    def test_env_host_only(self) -> None:
        try:
            os.environ[OLLAMA_HOST_ENV] = "myserver"
            host, port = _resolve_endpoint(None, None)
        finally:
            os.environ.pop(OLLAMA_HOST_ENV, None)
        self.assertEqual(host, "myserver")
        self.assertEqual(port, DEFAULT_OLLAMA_PORT)

    def test_env_host_port(self) -> None:
        try:
            os.environ[OLLAMA_HOST_ENV] = "host.local:55555"
            host, port = _resolve_endpoint(None, None)
        finally:
            os.environ.pop(OLLAMA_HOST_ENV, None)
        self.assertEqual(host, "host.local")
        self.assertEqual(port, 55555)

    def test_env_url_form(self) -> None:
        try:
            os.environ[OLLAMA_HOST_ENV] = "http://host.local:7777"
            host, port = _resolve_endpoint(None, None)
        finally:
            os.environ.pop(OLLAMA_HOST_ENV, None)
        self.assertEqual(host, "host.local")
        self.assertEqual(port, 7777)

    def test_garbage_port_falls_back(self) -> None:
        try:
            os.environ[OLLAMA_HOST_ENV] = "host.local:not-a-port"
            host, port = _resolve_endpoint(None, None)
        finally:
            os.environ.pop(OLLAMA_HOST_ENV, None)
        self.assertEqual(host, "host.local")
        self.assertEqual(port, DEFAULT_OLLAMA_PORT)


# ---- daemon liveness probes -------------------------------------------


class DaemonLivenessTests(unittest.TestCase):
    def test_unreachable_endpoint_returns_false(self) -> None:
        # Bind a socket and immediately close it — port is then free,
        # so connect attempts get refused.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        # Outside the with-block: socket is closed, port is free.
        self.assertFalse(
            is_ollama_daemon_up("127.0.0.1", port, timeout=0.2)
        )

    def test_check_ollama_health_unreachable(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        health = check_ollama_health("127.0.0.1", port, timeout=0.2)
        self.assertIsInstance(health, OllamaHealth)
        self.assertFalse(health.reachable)
        self.assertEqual(health.endpoint, f"http://127.0.0.1:{port}")
        self.assertTrue(health.error)
        self.assertTrue(any("could not reach" in d for d in health.details))

    def test_reachable_endpoint(self) -> None:
        with _stub_daemon() as port:
            self.assertTrue(
                is_ollama_daemon_up("127.0.0.1", port, timeout=2.0)
            )
            health = check_ollama_health("127.0.0.1", port, timeout=2.0)
            self.assertTrue(health.reachable)
            self.assertEqual(health.endpoint, f"http://127.0.0.1:{port}")
            self.assertGreaterEqual(health.latency_ms, 0.0)


# ---- list_models -------------------------------------------------------


class ListModelsTests(unittest.TestCase):
    def test_unreachable_returns_empty_with_unhealthy(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        models, health = list_models("127.0.0.1", port, timeout=0.2)
        self.assertEqual(models, [])
        self.assertFalse(health.reachable)

    def test_returns_models_from_stub(self) -> None:
        payload = {
            "models": [
                {"name": "llama3.2:3b", "size": 1234},
                {"name": "qwen2.5:7b", "size": 5678},
            ]
        }
        with _stub_daemon(tags_payload=payload) as _port:
            models, health = list_models(timeout=2.0)
        self.assertTrue(health.reachable)
        self.assertEqual(len(models), 2)
        self.assertEqual(
            sorted(m["name"] for m in models),
            ["llama3.2:3b", "qwen2.5:7b"],
        )


# ---- OllamaProvider ----------------------------------------------------


class OllamaProviderConfigTests(unittest.TestCase):
    def test_validate_config_unreachable(self) -> None:
        provider = OllamaProvider()
        with mock.patch(
            "mythic_vibe_cli.ai.providers.ollama.check_ollama_health",
            return_value=OllamaHealth(
                reachable=False,
                endpoint="http://127.0.0.1:11434",
                latency_ms=0.0,
                error="connection refused",
                details=[
                    "could not reach http://127.0.0.1:11434",
                    "start the daemon with `ollama serve` (or your platform's equivalent)",
                ],
            ),
        ):
            status = provider.validate_config()
        self.assertFalse(status.configured)
        self.assertTrue(any("endpoint:" in d for d in status.details))
        self.assertTrue(any("error:" in d for d in status.details))

    def test_validate_config_reachable(self) -> None:
        provider = OllamaProvider()
        with mock.patch(
            "mythic_vibe_cli.ai.providers.ollama.check_ollama_health",
            return_value=OllamaHealth(
                reachable=True,
                endpoint="http://127.0.0.1:11434",
                latency_ms=1.5,
                details=["connected in 1.5 ms"],
            ),
        ):
            status = provider.validate_config()
        self.assertTrue(status.configured)

    def test_default_model_resolution(self) -> None:
        with _scrub_env(OLLAMA_MODEL_ENV):
            provider = OllamaProvider()
            self.assertEqual(provider._resolved_model(), DEFAULT_MODEL)

    def test_env_overrides_default_model(self) -> None:
        try:
            os.environ[OLLAMA_MODEL_ENV] = "qwen2.5:7b"
            provider = OllamaProvider()
            self.assertEqual(provider._resolved_model(), "qwen2.5:7b")
        finally:
            os.environ.pop(OLLAMA_MODEL_ENV, None)

    def test_explicit_model_wins_over_env(self) -> None:
        try:
            os.environ[OLLAMA_MODEL_ENV] = "qwen2.5:7b"
            provider = OllamaProvider(model="explicit:7b")
            self.assertEqual(provider._resolved_model(), "explicit:7b")
        finally:
            os.environ.pop(OLLAMA_MODEL_ENV, None)


class OllamaProviderRunTests(unittest.TestCase):
    def test_dry_run_skips_network(self) -> None:
        provider = OllamaProvider()
        with tempfile.TemporaryDirectory() as tmp:
            provider.root = Path(tmp)
            with mock.patch(
                "mythic_vibe_cli.ai.providers.ollama.check_ollama_health"
            ) as health_call:
                response = provider.run({"text": "hi", "packet_id": "PKT-1"}, dry_run=True)
                health_call.assert_not_called()
        self.assertTrue(response.dry_run)
        self.assertEqual(response.provider, "ollama")
        self.assertEqual(response.content, "hi")
        self.assertGreater(response.usage["total_tokens"], 0)

    def test_unreachable_daemon_raises_connection_error(self) -> None:
        provider = OllamaProvider()
        with tempfile.TemporaryDirectory() as tmp:
            provider.root = Path(tmp)
            with mock.patch(
                "mythic_vibe_cli.ai.providers.ollama.check_ollama_health",
                return_value=OllamaHealth(
                    reachable=False,
                    endpoint="http://127.0.0.1:11434",
                    latency_ms=0.0,
                    error="connection refused",
                ),
            ):
                with self.assertRaises(ConnectionError) as ctx:
                    provider.run({"text": "hi", "packet_id": "PKT-1"})
            self.assertIn("Ollama daemon unreachable", str(ctx.exception))
            self.assertIn("ollama serve", str(ctx.exception))

    def test_real_call_against_stub_records_latency_and_returns_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with _stub_daemon(
                generate_payload={
                    "response": "the model reply",
                    "prompt_eval_count": 5,
                    "eval_count": 9,
                    "total_duration": 123456789,
                    "load_duration": 1234,
                    "eval_duration": 4567,
                    "done_reason": "stop",
                }
            ):
                provider = OllamaProvider(model="llama3.2:3b", root=Path(tmp))
                response = provider.run({"text": "hello world", "packet_id": "PKT-X"})
            self.assertFalse(response.dry_run)
            self.assertEqual(response.content, "the model reply")
            self.assertEqual(response.usage["input_tokens"], 5)
            self.assertEqual(response.usage["output_tokens"], 9)
            self.assertEqual(response.usage["total_tokens"], 14)
            self.assertEqual(response.metadata["done_reason"], "stop")
            # Telemetry written to provider_calls.jsonl with latency_ms.
            log_path = Path(tmp) / "mythic" / "ai" / "provider_calls.jsonl"
            self.assertTrue(log_path.is_file())
            entries = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["provider"], "ollama")
            self.assertIn("latency_ms", entries[0])
            self.assertGreaterEqual(entries[0]["latency_ms"], 0.0)


# ---- Registry --------------------------------------------------------


class RegistryRegistrationTests(unittest.TestCase):
    def test_registry_includes_ollama(self) -> None:
        registry = ProviderRegistry()
        providers = registry.providers()
        self.assertIn("ollama", providers)
        self.assertIsInstance(providers["ollama"], OllamaProvider)

    def test_argparse_choices_include_ollama(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(
            ["ai", "run", "--provider", "ollama", "--packet", "hello", "--dry-run"]
        )
        self.assertEqual(ns.provider, "ollama")


if __name__ == "__main__":
    unittest.main()
