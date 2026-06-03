from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from mythic_vibe_cli import app
from mythic_vibe_cli.ai.providers.base import write_provider_log
from mythic_vibe_cli.ai.registry import ProviderRegistry
from mythic_vibe_cli.exit_codes import SUCCESS


class _FakeHTTPResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class AIProviderTests(unittest.TestCase):
    def test_registry_exposes_expected_providers(self) -> None:
        providers = ProviderRegistry().providers()
        self.assertEqual(
            set(providers),
            {
                "copy-paste",
                "local",
                "openai",
                "anthropic",
                "gemini",
                "openrouter",
                # PH-06 slice 6.1 — local Ollama daemon adapter.
                "ollama",
                # PH-09 slice 9.1 — Yggdrasil island adapter.
                "yggdrasil",
                # PH-09 slice 9.2 — MindSpark ThoughtForge adapter.
                "mindspark",
            },
        )

    def test_api_key_validation_reflects_environment(self) -> None:
        registry = ProviderRegistry().providers()
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"):
            old = os.environ.get(key)
            try:
                os.environ.pop(key, None)
                status = registry[key.split("_")[0].lower() if key != "OPENROUTER_API_KEY" else "openrouter"].validate_config()
                self.assertFalse(status.configured)
            finally:
                if old is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old

    def test_copy_paste_provider_is_always_available(self) -> None:
        provider = ProviderRegistry().providers()["copy-paste"]
        status = provider.validate_config()
        self.assertTrue(status.configured)

        estimate = provider.estimate("hello world")
        response = provider.run("hello world")
        self.assertGreaterEqual(estimate.input_tokens, 1)
        self.assertEqual(response.packet_id, "manual")
        self.assertIn("estimated_cost_usd", response.metadata)
        self.assertEqual(response.metadata["estimated_cost_usd"], 0.0)

    def test_openai_provider_executes_and_redacts_provider_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider = ProviderRegistry(root=root).providers()["openai"]
            old = os.environ.get("OPENAI_API_KEY")
            os.environ["OPENAI_API_KEY"] = "sk-test1234567890"
            try:
                def fake_urlopen(request, timeout=0):  # noqa: ANN001 - signature mirrors urllib for the patch.
                    self.assertIn("api.openai.com/v1/chat/completions", request.full_url)
                    payload = json.dumps(
                        {
                            "choices": [
                                {
                                    "message": {
                                        "content": "done with sk-secret1234567890",
                                    }
                                }
                            ]
                        }
                    ).encode("utf-8")
                    return _FakeHTTPResponse(payload)

                with patch("mythic_vibe_cli.ai.providers.base.urllib_request.urlopen", side_effect=fake_urlopen):
                    response = provider.run(
                        {
                            "text": "use api key sk-secret1234567890",
                            "packet_id": "PKT-000123",
                        },
                        dry_run=False,
                    )

                self.assertFalse(response.dry_run)
                self.assertEqual(response.packet_id, "PKT-000123")
                self.assertIn("sk-secret1234567890", response.content)
                self.assertIn("input_tokens", response.usage)
                self.assertIn("observed_cost_usd", response.metadata)
                self.assertGreaterEqual(response.metadata["estimated_cost_usd"], 0.0)

                log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
                self.assertTrue(log_path.exists())
                log_text = log_path.read_text(encoding="utf-8")
                self.assertNotIn("sk-secret1234567890", log_text)
                self.assertIn("[REDACTED]", log_text)
            finally:
                if old is None:
                    os.environ.pop("OPENAI_API_KEY", None)
                else:
                    os.environ["OPENAI_API_KEY"] = old

    def test_provider_log_serializes_non_json_payload_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            write_provider_log(root, {"bad": object()})

            log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
            payload = json.loads(log_path.read_text(encoding="utf-8"))
            self.assertEqual(
                payload["provider_log_error"],
                "payload was not JSON serializable",
            )

    def test_provider_log_concurrent_writes_remain_valid_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def worker(index: int) -> None:
                write_provider_log(root, {"provider": "test", "index": index})

            threads = [threading.Thread(target=worker, args=(index,)) for index in range(25)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=3.0)

            log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
            lines = log_path.read_text(encoding="utf-8").splitlines()
            entries = [json.loads(line) for line in lines]

            self.assertEqual(len(entries), 25)
            self.assertEqual({entry["index"] for entry in entries}, set(range(25)))

    def test_ai_test_resolves_packet_id_from_project_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "tasks").mkdir(parents=True, exist_ok=True)
            (root / "mythic").mkdir(parents=True, exist_ok=True)
            (root / "docs" / "ARCHITECTURE.md").write_text("# Architecture\n", encoding="utf-8")
            (root / "tasks" / "current_GOALS.md").write_text("Ship packets\n", encoding="utf-8")
            (root / "mythic" / "plan.md").write_text("# Plan\n", encoding="utf-8")
            (root / "mythic" / "loop.md").write_text("# Loop\n", encoding="utf-8")

            create_output = io.StringIO()
            with redirect_stdout(create_output):
                create_code = app.main(
                    [
                        "packet",
                        "create",
                        "--task",
                        "wire provider resolution",
                        "--phase",
                        "build",
                        "--path",
                        str(root),
                        "--json",
                    ]
                )

            self.assertEqual(create_code, SUCCESS)

            test_output = io.StringIO()
            with redirect_stdout(test_output):
                test_code = app.main(
                    [
                        "ai",
                        "test",
                        "--path",
                        str(root),
                        "--provider",
                        "copy-paste",
                        "--packet",
                        "PKT-000001",
                        "--json",
                    ]
                )

            payload = json.loads(test_output.getvalue())
            self.assertEqual(test_code, SUCCESS)
            self.assertEqual(payload["packet"]["packet_id"], "PKT-000001")
            self.assertEqual(payload["response"]["packet_id"], "PKT-000001")
            self.assertTrue(payload["response"]["dry_run"])
            self.assertIn("usage", payload["response"])
            self.assertIn("metadata", payload["response"])


# ---------------------------------------------------------------------------
# PH-24.2 coverage push — exercise the run() paths of the Anthropic + Gemini
# providers (network is mocked via the same urlopen patch the OpenAI test
# uses). Goal: take both modules from ~57% to ~90%+.
# ---------------------------------------------------------------------------


class AnthropicProviderRunTests(unittest.TestCase):
    """Cover :class:`AnthropicProvider.run` — dry_run + live + missing-key."""

    def test_dry_run_returns_estimate_and_writes_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider = ProviderRegistry(root=root).providers()["anthropic"]
            response = provider.run(
                {"text": "hello", "packet_id": "PKT-DRY-001"},
                dry_run=True,
            )
            self.assertTrue(response.dry_run)
            self.assertEqual(response.packet_id, "PKT-DRY-001")
            self.assertEqual(response.content, "hello")
            self.assertIn("input_tokens", response.usage)
            self.assertIn("estimated_cost_usd", response.metadata)
            log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
            self.assertTrue(log_path.exists())

    def test_live_run_executes_and_redacts_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider = ProviderRegistry(root=root).providers()["anthropic"]
            old = os.environ.get("ANTHROPIC_API_KEY")
            os.environ["ANTHROPIC_API_KEY"] = "sk-anttestsecret9999999999"
            try:
                def fake_urlopen(request, timeout=0):  # noqa: ANN001
                    self.assertIn("api.anthropic.com/v1/messages", request.full_url)
                    payload = json.dumps(
                        {
                            "id": "msg_test_42",
                            "content": [{"type": "text", "text": "ok with sk-anttestsecret9999999999"}],
                            "usage": {"input_tokens": 4, "output_tokens": 5},
                        }
                    ).encode("utf-8")
                    return _FakeHTTPResponse(payload)

                with patch(
                    "mythic_vibe_cli.ai.providers.base.urllib_request.urlopen",
                    side_effect=fake_urlopen,
                ):
                    response = provider.run(
                        {"text": "use sk-anttestsecret9999999999", "packet_id": "PKT-LIVE-002"},
                        dry_run=False,
                    )
                self.assertFalse(response.dry_run)
                self.assertEqual(response.packet_id, "PKT-LIVE-002")
                self.assertIn("ok", response.content)
                self.assertEqual(response.usage["input_tokens"], 4)
                self.assertEqual(response.usage["output_tokens"], 5)
                self.assertIn("observed_cost_usd", response.metadata)

                log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
                log_text = log_path.read_text(encoding="utf-8")
                self.assertNotIn("sk-anttestsecret9999999999", log_text)
                self.assertIn("[REDACTED]", log_text)
            finally:
                if old is None:
                    os.environ.pop("ANTHROPIC_API_KEY", None)
                else:
                    os.environ["ANTHROPIC_API_KEY"] = old

    def test_live_run_without_api_key_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = ProviderRegistry(root=Path(tmp)).providers()["anthropic"]
            old = os.environ.get("ANTHROPIC_API_KEY")
            os.environ.pop("ANTHROPIC_API_KEY", None)
            try:
                with self.assertRaises(ValueError) as cm:
                    provider.run({"text": "hi", "packet_id": "PKT-NOKEY"}, dry_run=False)
                self.assertIn("ANTHROPIC_API_KEY", str(cm.exception))
            finally:
                if old is not None:
                    os.environ["ANTHROPIC_API_KEY"] = old

    def test_live_run_falls_back_to_estimated_usage_when_missing(self) -> None:
        """If the API response omits usage, the provider populates from estimate."""
        with tempfile.TemporaryDirectory() as tmp:
            provider = ProviderRegistry(root=Path(tmp)).providers()["anthropic"]
            old = os.environ.get("ANTHROPIC_API_KEY")
            os.environ["ANTHROPIC_API_KEY"] = "sk-ant-key"
            try:
                def fake_urlopen(request, timeout=0):  # noqa: ANN001
                    payload = json.dumps(
                        {"content": [{"type": "text", "text": "hi"}]}
                    ).encode("utf-8")
                    return _FakeHTTPResponse(payload)

                with patch(
                    "mythic_vibe_cli.ai.providers.base.urllib_request.urlopen",
                    side_effect=fake_urlopen,
                ):
                    response = provider.run(
                        {"text": "hello", "packet_id": "PKT-NOUSAGE"}, dry_run=False
                    )
                self.assertIn("input_tokens", response.usage)
                self.assertIn("output_tokens", response.usage)
            finally:
                if old is None:
                    os.environ.pop("ANTHROPIC_API_KEY", None)
                else:
                    os.environ["ANTHROPIC_API_KEY"] = old

    def test_validate_config_reports_detected_when_key_present(self) -> None:
        provider = ProviderRegistry().providers()["anthropic"]
        old = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-x"
        try:
            status = provider.validate_config()
            self.assertTrue(status.configured)
            self.assertTrue(any("detected" in line for line in status.details))
        finally:
            if old is None:
                os.environ.pop("ANTHROPIC_API_KEY", None)
            else:
                os.environ["ANTHROPIC_API_KEY"] = old

    def test_estimate_returns_token_estimate_for_packet(self) -> None:
        provider = ProviderRegistry().providers()["anthropic"]
        estimate = provider.estimate({"text": "a longer hello world packet"})
        self.assertGreaterEqual(estimate.input_tokens, 1)


class GeminiProviderRunTests(unittest.TestCase):
    """Cover :class:`GeminiProvider.run` — dry_run + live + missing-key."""

    def test_dry_run_returns_estimate_and_writes_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider = ProviderRegistry(root=root).providers()["gemini"]
            response = provider.run(
                {"text": "hello gemini", "packet_id": "PKT-G-DRY"},
                dry_run=True,
            )
            self.assertTrue(response.dry_run)
            self.assertEqual(response.packet_id, "PKT-G-DRY")
            self.assertEqual(response.content, "hello gemini")
            self.assertIn("input_tokens", response.usage)
            log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
            self.assertTrue(log_path.exists())

    def test_live_run_executes_and_redacts_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            provider = ProviderRegistry(root=root).providers()["gemini"]
            old = os.environ.get("GEMINI_API_KEY")
            os.environ["GEMINI_API_KEY"] = "AIzaSyTESTKEY1234567890"
            try:
                def fake_urlopen(request, timeout=0):  # noqa: ANN001
                    self.assertIn("generativelanguage.googleapis.com", request.full_url)
                    self.assertIn("key=AIzaSyTESTKEY1234567890", request.full_url)
                    payload = json.dumps(
                        {
                            "candidates": [
                                {
                                    "content": {
                                        "parts": [{"text": "ok with AIzaSyTESTKEY1234567890"}]
                                    }
                                }
                            ],
                            "usageMetadata": {
                                "promptTokenCount": 6,
                                "candidatesTokenCount": 4,
                            },
                        }
                    ).encode("utf-8")
                    return _FakeHTTPResponse(payload)

                with patch(
                    "mythic_vibe_cli.ai.providers.base.urllib_request.urlopen",
                    side_effect=fake_urlopen,
                ):
                    response = provider.run(
                        {
                            "text": "use AIzaSyTESTKEY1234567890",
                            "packet_id": "PKT-G-LIVE",
                        },
                        dry_run=False,
                    )
                self.assertFalse(response.dry_run)
                self.assertEqual(response.packet_id, "PKT-G-LIVE")
                self.assertIn("ok", response.content)
                self.assertIn("input_tokens", response.usage)
                self.assertIn("observed_cost_usd", response.metadata)

                log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
                log_text = log_path.read_text(encoding="utf-8")
                self.assertNotIn("AIzaSyTESTKEY1234567890", log_text)
            finally:
                if old is None:
                    os.environ.pop("GEMINI_API_KEY", None)
                else:
                    os.environ["GEMINI_API_KEY"] = old

    def test_live_run_without_api_key_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            provider = ProviderRegistry(root=Path(tmp)).providers()["gemini"]
            old = os.environ.get("GEMINI_API_KEY")
            os.environ.pop("GEMINI_API_KEY", None)
            try:
                with self.assertRaises(ValueError) as cm:
                    provider.run({"text": "hi", "packet_id": "PKT-G-NOKEY"}, dry_run=False)
                self.assertIn("GEMINI_API_KEY", str(cm.exception))
            finally:
                if old is not None:
                    os.environ["GEMINI_API_KEY"] = old

    def test_live_run_handles_response_without_candidates(self) -> None:
        """An empty candidates list yields content="" but still produces a log."""
        with tempfile.TemporaryDirectory() as tmp:
            provider = ProviderRegistry(root=Path(tmp)).providers()["gemini"]
            old = os.environ.get("GEMINI_API_KEY")
            os.environ["GEMINI_API_KEY"] = "AIza-x"
            try:
                def fake_urlopen(request, timeout=0):  # noqa: ANN001
                    return _FakeHTTPResponse(json.dumps({"candidates": []}).encode("utf-8"))

                with patch(
                    "mythic_vibe_cli.ai.providers.base.urllib_request.urlopen",
                    side_effect=fake_urlopen,
                ):
                    response = provider.run(
                        {"text": "ping", "packet_id": "PKT-G-EMPTY"},
                        dry_run=False,
                    )
                self.assertEqual(response.content, "")
                self.assertIn("input_tokens", response.usage)
            finally:
                if old is None:
                    os.environ.pop("GEMINI_API_KEY", None)
                else:
                    os.environ["GEMINI_API_KEY"] = old

    def test_validate_config_reports_detected_when_key_present(self) -> None:
        provider = ProviderRegistry().providers()["gemini"]
        old = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "AIza-x"
        try:
            status = provider.validate_config()
            self.assertTrue(status.configured)
        finally:
            if old is None:
                os.environ.pop("GEMINI_API_KEY", None)
            else:
                os.environ["GEMINI_API_KEY"] = old

    def test_list_models_remote_picks_up_google_api_key_fallback(self) -> None:
        """When ``remote=True`` and ``GEMINI_API_KEY`` is unset, the provider
        should fall through to ``GOOGLE_API_KEY`` (Google's canonical name)."""
        provider = ProviderRegistry().providers()["gemini"]
        old_g = os.environ.get("GEMINI_API_KEY")
        old_goog = os.environ.get("GOOGLE_API_KEY")
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ["GOOGLE_API_KEY"] = "AIza-fallback"
        captured: dict[str, str | None] = {}
        try:
            def fake_catalog(name, *, remote, api_key=None):  # noqa: ANN001
                captured["name"] = name
                captured["api_key"] = api_key
                from mythic_vibe_cli.ai.providers.model_catalog import ModelListing
                return ModelListing(family=name, models=[], source="static")

            with patch(
                "mythic_vibe_cli.ai.providers.gemini._catalog_list_models",
                side_effect=fake_catalog,
            ):
                provider.list_models(remote=True)
            self.assertEqual(captured["api_key"], "AIza-fallback")
        finally:
            if old_g is not None:
                os.environ["GEMINI_API_KEY"] = old_g
            if old_goog is None:
                os.environ.pop("GOOGLE_API_KEY", None)
            else:
                os.environ["GOOGLE_API_KEY"] = old_goog


if __name__ == "__main__":
    unittest.main()
