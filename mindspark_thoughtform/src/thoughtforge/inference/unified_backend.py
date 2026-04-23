"""Unified backend abstraction — abstract base class, shared types, and factory loader."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class GenerationRequest:
    prompt: str
    temperature: float = 0.7
    max_tokens: int = 512
    stop: list[str] = field(default_factory=list)
    system_prompt: str = ""
    # OpenAI chat format; if non-empty, backend should use this directly
    messages: list[dict] = field(default_factory=list)


@dataclass
class GenerationResponse:
    text: str
    tokens_generated: int = 0
    finish_reason: str = "stop"   # "stop" | "length" | "error"
    backend_used: str = ""
    latency_ms: float = 0.0
    error: str = ""


class UnifiedBackend(ABC):
    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResponse: ...

    @abstractmethod
    def health_check(self) -> bool: ...

    @abstractmethod
    def backend_name(self) -> str: ...


def load_backend_from_config(config_path: Path | None = None) -> UnifiedBackend | None:
    """
    Load the backend specified in configs/user_config.yaml.
    Returns None when backend is 'none', missing, or the config file doesn't exist.
    """
    from thoughtforge.utils.paths import get_configs_dir

    if config_path is None:
        config_path = get_configs_dir() / "user_config.yaml"

    if not config_path.exists():
        logger.debug("user_config.yaml not found at %s — no backend loaded", config_path)
        return None

    try:
        import yaml
        with config_path.open("r", encoding="utf-8") as f:
            cfg: dict[str, Any] = yaml.safe_load(f) or {}
    except Exception as exc:
        logger.error("Failed to read user_config.yaml: %s", exc)
        return None

    backend_type: str = (cfg.get("backend") or "none").strip().lower()
    logger.info("Loading backend from config: %s", backend_type)

    if backend_type in ("none", ""):
        return None

    if backend_type == "ollama":
        from thoughtforge.inference.ollama_backend import OllamaBackend
        return OllamaBackend(
            base_url=cfg.get("ollama_url", "http://localhost:11434"),
            model=cfg.get("ollama_model", "llama3.2:3b"),
        )

    if backend_type in ("lmstudio", "openai_compatible"):
        from thoughtforge.inference.lmstudio_backend import LMStudioBackend
        url = cfg.get("lmstudio_url") or cfg.get("openai_base_url") or "http://localhost:1234"
        model = cfg.get("lmstudio_model") or cfg.get("openai_model", "")
        api_key = cfg.get("openai_api_key", "lm-studio")
        return LMStudioBackend(base_url=url, model=model, api_key=api_key or "lm-studio")

    if backend_type == "huggingface":
        from thoughtforge.inference.hf_backend import HuggingFaceBackend
        return HuggingFaceBackend(
            model=cfg.get("hf_model", "mistralai/Mistral-7B-Instruct-v0.3"),
            token=cfg.get("hf_token", ""),
        )

    if backend_type == "turboquant":
        gguf_path = cfg.get("gguf_model_path", "")
        if not gguf_path:
            logger.error("turboquant backend selected but gguf_model_path is empty")
            return None
        # TurboQuantEngine is wrapped lazily to avoid hard llama-cpp-python dependency
        from thoughtforge.inference.turboquant_backend import TurboQuantBackend
        return TurboQuantBackend(model_path=Path(gguf_path))

    logger.warning("Unknown backend type '%s' in user_config.yaml", backend_type)
    return None
