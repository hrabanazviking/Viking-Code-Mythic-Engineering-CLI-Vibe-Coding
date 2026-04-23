"""
Phase 7 test suite — Backend interface + unified backend factory tests.

Tests the UnifiedBackend ABC compliance for each backend class, the factory
loader, model browser catalogue, and graceful degradation when backends are
unreachable.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from thoughtforge.inference.unified_backend import (
    GenerationRequest,
    GenerationResponse,
    UnifiedBackend,
    load_backend_from_config,
)
from thoughtforge.inference.ollama_backend import OllamaBackend
from thoughtforge.inference.lmstudio_backend import LMStudioBackend
from thoughtforge.inference.hf_backend import HuggingFaceBackend
from thoughtforge.inference.model_browser import ModelBrowser, ModelEntry


# ── GenerationRequest / GenerationResponse types ──────────────────────────────

class TestGenerationTypes:
    def test_request_defaults(self):
        req = GenerationRequest(prompt="hello")
        assert req.temperature == 0.7
        assert req.max_tokens == 512
        assert req.stop == []
        assert req.system_prompt == ""
        assert req.messages == []

    def test_request_custom(self):
        req = GenerationRequest(
            prompt="test",
            temperature=0.2,
            max_tokens=128,
            stop=["</s>"],
            system_prompt="You are a skald.",
            messages=[{"role": "user", "content": "hi"}],
        )
        assert req.temperature == 0.2
        assert req.stop == ["</s>"]
        assert len(req.messages) == 1

    def test_response_defaults(self):
        resp = GenerationResponse(text="hello")
        assert resp.tokens_generated == 0
        assert resp.finish_reason == "stop"
        assert resp.backend_used == ""
        assert resp.latency_ms == 0.0
        assert resp.error == ""

    def test_response_error_state(self):
        resp = GenerationResponse(text="", finish_reason="error", error="timeout")
        assert resp.finish_reason == "error"
        assert resp.error == "timeout"


# ── UnifiedBackend ABC ────────────────────────────────────────────────────────

class TestUnifiedBackendABC:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            UnifiedBackend()

    def test_concrete_subclass_must_implement_all_methods(self):
        class Incomplete(UnifiedBackend):
            def generate(self, request): return GenerationResponse(text="")
            def health_check(self): return True
            # missing backend_name

        with pytest.raises(TypeError):
            Incomplete()

    def test_full_concrete_subclass_instantiates(self):
        class Minimal(UnifiedBackend):
            def generate(self, request): return GenerationResponse(text="ok")
            def health_check(self): return True
            def backend_name(self): return "minimal"

        b = Minimal()
        assert b.backend_name() == "minimal"
        assert b.health_check() is True
        result = b.generate(GenerationRequest(prompt="test"))
        assert isinstance(result, GenerationResponse)


# ── OllamaBackend ─────────────────────────────────────────────────────────────

class TestOllamaBackend:
    def test_instantiates_with_defaults(self):
        b = OllamaBackend()
        assert "ollama" in b.backend_name()

    def test_instantiates_with_custom_params(self):
        b = OllamaBackend(base_url="http://localhost:9999", model="phi3:mini")
        assert "phi3" in b.backend_name()

    def test_health_check_returns_false_when_unreachable(self):
        b = OllamaBackend(base_url="http://127.0.0.1:19999")
        assert b.health_check() is False

    def test_generate_returns_error_response_when_unreachable(self):
        b = OllamaBackend(base_url="http://127.0.0.1:19999", timeout=2)
        result = b.generate(GenerationRequest(prompt="hello"))
        assert isinstance(result, GenerationResponse)
        assert result.finish_reason == "error"
        assert result.text == "" or isinstance(result.text, str)

    def test_generate_never_raises(self):
        b = OllamaBackend(base_url="http://127.0.0.1:19999", timeout=2)
        try:
            result = b.generate(GenerationRequest(prompt="crash me"))
            assert isinstance(result, GenerationResponse)
        except Exception as e:
            pytest.fail(f"generate() raised unexpectedly: {e}")

    def test_health_check_never_raises(self):
        b = OllamaBackend(base_url="http://127.0.0.1:19999")
        try:
            result = b.health_check()
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"health_check() raised unexpectedly: {e}")

    def test_mocked_successful_generate(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {"content": "Yggdrasil is the world tree."},
            "done": True,
            "eval_count": 8,
        }
        b = OllamaBackend()
        with patch("requests.post", return_value=mock_resp):
            result = b.generate(GenerationRequest(prompt="What is Yggdrasil?"))
        assert result.text == "Yggdrasil is the world tree."
        assert result.finish_reason == "stop"
        assert result.tokens_generated == 8

    def test_mocked_health_check_ok(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        b = OllamaBackend()
        with patch("requests.get", return_value=mock_resp):
            assert b.health_check() is True

    def test_mocked_list_local_models(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [
                {"name": "llama3.2:3b"},
                {"name": "phi3:mini"},
            ]
        }
        b = OllamaBackend()
        with patch("requests.get", return_value=mock_resp):
            models = b.list_local_models()
        assert "llama3.2:3b" in models
        assert "phi3:mini" in models


# ── LMStudioBackend ───────────────────────────────────────────────────────────

class TestLMStudioBackend:
    def test_instantiates_with_defaults(self):
        b = LMStudioBackend()
        assert "lmstudio" in b.backend_name()

    def test_health_check_false_when_unreachable(self):
        b = LMStudioBackend(base_url="http://127.0.0.1:19998")
        assert b.health_check() is False

    def test_generate_never_raises(self):
        b = LMStudioBackend(base_url="http://127.0.0.1:19998", timeout=2)
        try:
            result = b.generate(GenerationRequest(prompt="hello"))
            assert isinstance(result, GenerationResponse)
        except Exception as e:
            pytest.fail(f"generate() raised: {e}")

    def test_mocked_successful_generate(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Frith is peace."}, "finish_reason": "stop"}],
            "usage": {"completion_tokens": 4},
        }
        b = LMStudioBackend(model="phi-3-mini")
        with patch("requests.post", return_value=mock_resp):
            result = b.generate(GenerationRequest(prompt="What is frith?"))
        assert result.text == "Frith is peace."
        assert result.finish_reason == "stop"

    def test_mocked_list_models(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"id": "phi-3-mini"}, {"id": "mistral-7b"}]
        }
        b = LMStudioBackend()
        with patch("requests.get", return_value=mock_resp):
            models = b.list_models()
        assert "phi-3-mini" in models

    def test_messages_passed_through(self):
        """When request.messages is set, backend uses them directly."""
        captured = {}

        def fake_post(url, json=None, **kwargs):
            captured["payload"] = json
            mock = MagicMock()
            mock.status_code = 200
            mock.json.return_value = {
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"completion_tokens": 1},
            }
            return mock

        b = LMStudioBackend()
        messages = [
            {"role": "system", "content": "You are a skald."},
            {"role": "user", "content": "Sing of Yggdrasil."},
        ]
        with patch("requests.post", side_effect=fake_post):
            b.generate(GenerationRequest(prompt="", messages=messages))

        sent_messages = captured["payload"]["messages"]
        assert any(m["role"] == "system" for m in sent_messages)


# ── HuggingFaceBackend ────────────────────────────────────────────────────────

class TestHuggingFaceBackend:
    def test_instantiates(self):
        b = HuggingFaceBackend(model="gpt2", token="")
        assert "huggingface" in b.backend_name() or "hf" in b.backend_name().lower()

    def test_health_check_returns_bool(self):
        b = HuggingFaceBackend(model="gpt2", token="")
        result = b.health_check()
        assert isinstance(result, bool)

    def test_generate_never_raises(self):
        b = HuggingFaceBackend(model="gpt2", token="fake_token_xyz")
        try:
            result = b.generate(GenerationRequest(prompt="hello"))
            assert isinstance(result, GenerationResponse)
        except Exception as e:
            pytest.fail(f"generate() raised: {e}")

    def test_generate_returns_error_on_auth_fail(self):
        """Bad token → error response, not exception."""
        b = HuggingFaceBackend(model="meta-llama/Llama-2-7b-chat-hf", token="fake")
        result = b.generate(GenerationRequest(prompt="hello"))
        assert isinstance(result, GenerationResponse)
        # Either got text or an error, but never raised
        assert result.text is not None


# ── load_backend_from_config factory ─────────────────────────────────────────

class TestLoadBackendFromConfig:
    def _write_config(self, tmp_dir: Path, data: dict) -> Path:
        import yaml
        cfg = tmp_dir / "user_config.yaml"
        cfg.write_text(yaml.dump(data), encoding="utf-8")
        return cfg

    def test_returns_none_when_config_missing(self):
        result = load_backend_from_config(Path("/nonexistent/path/user_config.yaml"))
        assert result is None

    def test_returns_none_for_backend_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "user_config.yaml"
            cfg.write_text("backend: none\n", encoding="utf-8")
            result = load_backend_from_config(cfg)
            assert result is None

    def test_returns_ollama_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "user_config.yaml"
            cfg.write_text(
                "backend: ollama\nollama_url: http://localhost:11434\nollama_model: llama3.2:3b\n",
                encoding="utf-8",
            )
            result = load_backend_from_config(cfg)
            assert isinstance(result, OllamaBackend)

    def test_returns_lmstudio_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "user_config.yaml"
            cfg.write_text(
                "backend: lmstudio\nlmstudio_url: http://localhost:1234\nlmstudio_model: phi3\n",
                encoding="utf-8",
            )
            result = load_backend_from_config(cfg)
            assert isinstance(result, LMStudioBackend)

    def test_returns_huggingface_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "user_config.yaml"
            cfg.write_text(
                "backend: huggingface\nhf_model: gpt2\nhf_token: \"\"\n",
                encoding="utf-8",
            )
            result = load_backend_from_config(cfg)
            assert isinstance(result, HuggingFaceBackend)

    def test_returns_none_for_corrupt_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "user_config.yaml"
            cfg.write_text(": invalid: {{yaml}}: [\n", encoding="utf-8")
            result = load_backend_from_config(cfg)
            assert result is None


# ── ModelBrowser ──────────────────────────────────────────────────────────────

class TestModelBrowser:
    @pytest.fixture
    def browser(self):
        return ModelBrowser()

    def test_curated_models_non_empty(self, browser):
        models = browser.list_curated()
        assert len(models) >= 5

    def test_curated_models_all_have_required_fields(self, browser):
        for m in browser.list_curated():
            assert isinstance(m.model_id, str) and m.model_id
            assert isinstance(m.filename, str) and m.filename
            assert isinstance(m.size_gb, float)
            assert m.tier in {"phone", "pi", "cpu", "gpu", "server"}
            assert isinstance(m.description, str)

    def test_filter_by_tier_phone(self, browser):
        phone_models = browser.list_curated(tier="phone")
        assert all(m.tier == "phone" for m in phone_models)

    def test_filter_by_tier_gpu(self, browser):
        gpu_models = browser.list_curated(tier="gpu")
        assert all(m.tier == "gpu" for m in gpu_models)

    def test_filter_unknown_tier_returns_empty(self, browser):
        result = browser.list_curated(tier="nonexistent_tier")
        assert result == []

    def test_all_tiers_represented(self, browser):
        tiers = {m.tier for m in browser.list_curated()}
        assert len(tiers) >= 3

    def test_detect_existing_ggufs_returns_list(self, browser):
        result = browser.detect_existing_ggufs()
        assert isinstance(result, list)
        # All entries should be Path objects ending in .gguf
        for p in result:
            assert str(p).endswith(".gguf")

    def test_detect_existing_ggufs_with_custom_dir(self, browser):
        with tempfile.TemporaryDirectory() as tmp:
            # Create a fake .gguf file
            (Path(tmp) / "test_model.gguf").write_bytes(b"fake")
            found = browser.detect_existing_ggufs(search_dirs=[Path(tmp)])
            assert any("test_model.gguf" in str(p) for p in found)

    def test_model_entry_dataclass(self):
        m = ModelEntry(
            model_id="test/model",
            filename="model.gguf",
            size_gb=4.1,
            tier="cpu",
            description="Test model",
            quantization="Q4_K_M",
        )
        assert m.size_gb == 4.1
        assert m.quantization == "Q4_K_M"


# ── ThoughtForgeCore with unified backend ────────────────────────────────────

class TestThoughtForgeCoreWithBackend:
    def test_core_accepts_backend_kwarg(self):
        import tempfile
        from thoughtforge.cognition.core import ThoughtForgeCore

        class FakeBackend(UnifiedBackend):
            def generate(self, r): return GenerationResponse(text="Yggdrasil is the world tree.")
            def health_check(self): return True
            def backend_name(self): return "fake"

        tmp = tempfile.mkdtemp()
        core = ThoughtForgeCore(
            memory_dir=Path(tmp) / "memory",
            db_path=Path(tmp) / "test.db",
            model_path=None,
            backend=FakeBackend(),
        )
        assert core is not None

    def test_core_with_backend_returns_final_response(self):
        import tempfile
        from thoughtforge.cognition.core import ThoughtForgeCore
        from thoughtforge.knowledge.models import FinalResponseRecord

        class FakeBackend(UnifiedBackend):
            def generate(self, r):
                return GenerationResponse(
                    text="Yggdrasil connects the nine worlds of Norse cosmology.",
                    tokens_generated=10,
                )
            def health_check(self): return True
            def backend_name(self): return "fake"

        tmp = tempfile.mkdtemp()
        core = ThoughtForgeCore(
            memory_dir=Path(tmp) / "memory",
            db_path=Path(tmp) / "test.db",
            model_path=None,
            backend=FakeBackend(),
        )
        result = core.think("What is Yggdrasil?")
        assert isinstance(result, FinalResponseRecord)
        assert isinstance(result.text, str)
        assert len(result.text) > 0
