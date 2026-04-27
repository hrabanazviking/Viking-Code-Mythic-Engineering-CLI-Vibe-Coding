from __future__ import annotations

import os
import tempfile
import unittest

from mythic_vibe_cli.ai.registry import ProviderRegistry


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


if __name__ == "__main__":
    unittest.main()
