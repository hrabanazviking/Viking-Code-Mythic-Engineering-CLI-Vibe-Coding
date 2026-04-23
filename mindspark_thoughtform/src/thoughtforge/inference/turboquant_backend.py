"""TurboQuant (llama-cpp-python) backend wrapped as a UnifiedBackend.

Bridges the existing TurboQuantEngine — which takes a GGUF model path and
exposes generate(prompt, params) -> GenerationResult — into the UnifiedBackend
ABC used by run_thoughtforge.py and the setup wizard.

The model is loaded lazily on first generate() call so that construction never
blocks or raises for missing model files until inference is actually attempted.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from thoughtforge.inference.unified_backend import (
    GenerationRequest,
    GenerationResponse,
    UnifiedBackend,
)

logger = logging.getLogger(__name__)


class TurboQuantBackend(UnifiedBackend):
    """Thin UnifiedBackend wrapper around TurboQuantEngine."""

    def __init__(self, model_path: Path, profile_id: str = "auto") -> None:
        self.model_path = Path(model_path)
        self.profile_id = profile_id
        self._engine = None   # loaded lazily

    def backend_name(self) -> str:
        return f"turboquant:{self.model_path.name}"

    def health_check(self) -> bool:
        """Returns True if the model file exists and llama-cpp-python is importable."""
        if not self.model_path.exists():
            return False
        try:
            import importlib
            return importlib.util.find_spec("llama_cpp") is not None
        except Exception:
            return False

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        start = time.monotonic()
        try:
            engine = self._get_engine()
        except Exception as exc:
            logger.error("TurboQuantBackend: failed to load engine: %s", exc)
            return GenerationResponse(
                text="",
                error=str(exc),
                finish_reason="error",
                backend_used=self.backend_name(),
                latency_ms=(time.monotonic() - start) * 1000,
            )

        # Build a flat prompt string — TurboQuantEngine expects a single string
        prompt = _flatten_request(request)

        try:
            from thoughtforge.inference.turboquant import GenerationParams
            params = GenerationParams(
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stop=request.stop or [],
            )
            result = engine.generate(prompt, params=params)
            return GenerationResponse(
                text=result.text,
                tokens_generated=result.completion_tokens,
                finish_reason=result.finish_reason or "stop",
                backend_used=self.backend_name(),
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except ImportError:
            # GenerationParams might not be exported; fall back to default params
            result = engine.generate(prompt)
            return GenerationResponse(
                text=result.text,
                tokens_generated=result.completion_tokens,
                finish_reason=result.finish_reason or "stop",
                backend_used=self.backend_name(),
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as exc:
            logger.error("TurboQuantBackend.generate error: %s", exc)
            return GenerationResponse(
                text="",
                error=str(exc),
                finish_reason="error",
                backend_used=self.backend_name(),
                latency_ms=(time.monotonic() - start) * 1000,
            )

    # ── Private ────────────────────────────────────────────────────────────────

    def _get_engine(self):
        if self._engine is not None:
            return self._engine
        from thoughtforge.inference.turboquant import TurboQuantEngine
        engine = TurboQuantEngine(
            model_path=self.model_path,
            profile_id=self.profile_id,
        )
        engine.load()
        self._engine = engine
        return engine


def _flatten_request(request: GenerationRequest) -> str:
    """Convert a GenerationRequest to a single prompt string for TurboQuantEngine."""
    if request.messages:
        parts: list[str] = []
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"[SYSTEM]\n{content}")
            elif role == "assistant":
                parts.append(f"[ASSISTANT]\n{content}")
            else:
                parts.append(f"[USER]\n{content}")
        return "\n\n".join(parts) + "\n\n[ASSISTANT]\n"

    if request.system_prompt:
        return f"[SYSTEM]\n{request.system_prompt}\n\n[USER]\n{request.prompt}\n\n[ASSISTANT]\n"

    return request.prompt
