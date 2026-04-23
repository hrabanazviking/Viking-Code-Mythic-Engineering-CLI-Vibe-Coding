"""HuggingFace Inference API backend for ThoughtForge.

Uses huggingface_hub.InferenceClient when installed; falls back to raw requests.
Handles 503 "model loading" responses with a single retry after a short wait.
"""

from __future__ import annotations

import logging
import time

import requests

from thoughtforge.inference.unified_backend import (
    GenerationRequest,
    GenerationResponse,
    UnifiedBackend,
)

logger = logging.getLogger(__name__)

_HF_API_BASE = "https://api-inference.huggingface.co/models"
_MODEL_LOADING_RETRY_WAIT = 20  # seconds


class HuggingFaceBackend(UnifiedBackend):
    def __init__(
        self,
        model: str = "mistralai/Mistral-7B-Instruct-v0.3",
        token: str = "",
    ) -> None:
        self.model = model
        self.token = token
        self._client = self._try_build_client()

    def backend_name(self) -> str:
        return f"huggingface:{self.model}"

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        start = time.monotonic()
        try:
            if self._client is not None:
                return self._generate_via_client(request, start)
            return self._generate_via_requests(request, start)
        except Exception as exc:
            logger.error("HuggingFaceBackend.generate unexpected error: %s", exc)
            return GenerationResponse(
                text="",
                error=str(exc),
                finish_reason="error",
                backend_used=self.backend_name(),
                latency_ms=(time.monotonic() - start) * 1000,
            )

    def health_check(self) -> bool:
        try:
            headers = self._auth_headers()
            # Hit the model info endpoint — fast and doesn't load the model
            resp = requests.get(
                f"https://huggingface.co/api/models/{self.model}",
                headers=headers,
                timeout=8,
            )
            return resp.status_code < 500
        except Exception:
            return False

    # ── Private helpers ────────────────────────────────────────────────────────

    def _try_build_client(self):
        """Return an InferenceClient if huggingface_hub is installed, else None."""
        try:
            from huggingface_hub import InferenceClient
            return InferenceClient(model=self.model, token=self.token or None)
        except ImportError:
            logger.debug("huggingface_hub not installed — using raw requests fallback")
            return None

    def _generate_via_client(self, request: GenerationRequest, start: float) -> GenerationResponse:
        prompt = _build_prompt(request)
        try:
            result = self._client.text_generation(  # type: ignore[union-attr]
                prompt,
                temperature=request.temperature,
                max_new_tokens=request.max_tokens,
                stop_sequences=request.stop or None,
            )
            text: str = result if isinstance(result, str) else str(result)
            return GenerationResponse(
                text=text,
                tokens_generated=len(text.split()),  # approximate; client doesn't always return counts
                finish_reason="stop",
                backend_used=self.backend_name(),
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as exc:
            # Retry logic handled by falling through to raw requests on hard failure
            logger.warning("InferenceClient call failed (%s) — falling back to raw requests", exc)
            self._client = None
            return self._generate_via_requests(request, start)

    def _generate_via_requests(
        self,
        request: GenerationRequest,
        start: float,
        _retry: bool = True,
    ) -> GenerationResponse:
        prompt = _build_prompt(request)
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": request.temperature,
                "max_new_tokens": request.max_tokens,
            },
        }
        if request.stop:
            payload["parameters"]["stop"] = request.stop  # type: ignore[index]

        try:
            resp = requests.post(
                f"{_HF_API_BASE}/{self.model}",
                json=payload,
                headers=self._auth_headers(),
                timeout=60,
            )

            # 503 = model is still loading on HF side — retry once
            if resp.status_code == 503 and _retry:
                wait = resp.json().get("estimated_time", _MODEL_LOADING_RETRY_WAIT)
                logger.info("HF model loading, waiting %.0fs then retrying…", wait)
                time.sleep(float(wait))
                return self._generate_via_requests(request, start, _retry=False)

            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list):
                text = data[0].get("generated_text", "") if data else ""
            else:
                text = data.get("generated_text", "")

            return GenerationResponse(
                text=text,
                tokens_generated=len(text.split()),
                finish_reason="stop",
                backend_used=self.backend_name(),
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as exc:
            logger.error("HuggingFaceBackend raw request failed: %s", exc)
            return GenerationResponse(
                text="",
                error=str(exc),
                finish_reason="error",
                backend_used=self.backend_name(),
                latency_ms=(time.monotonic() - start) * 1000,
            )

    def _auth_headers(self) -> dict[str, str]:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}


def _build_prompt(request: GenerationRequest) -> str:
    """Flatten messages or build a simple prompt string for text-generation endpoints."""
    if request.messages:
        parts: list[str] = []
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"[SYSTEM] {content}")
            elif role == "assistant":
                parts.append(f"[ASSISTANT] {content}")
            else:
                parts.append(f"[USER] {content}")
        return "\n".join(parts) + "\n[ASSISTANT]"

    if request.system_prompt:
        return f"[SYSTEM] {request.system_prompt}\n[USER] {request.prompt}\n[ASSISTANT]"

    return request.prompt
