from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mythic_vibe_cli import app
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
            {"copy-paste", "local", "openai", "anthropic", "gemini", "openrouter"},
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


if __name__ == "__main__":
    unittest.main()
