"""LM Studio / generic OpenAI-compatible HTTP backend for ThoughtForge.

Works with LM Studio, vLLM, text-generation-webui, Oobabooga, LocalAI, and any
server that implements the /v1/chat/completions endpoint.
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


class LMStudioBackend(UnifiedBackend):
    def __init__(
        self,
        base_url: str = "http://localhost:1234",
        model: str = "",
        api_key: str = "lm-studio",
        timeout: int = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def backend_name(self) -> str:
        label = self.model or "lmstudio"
        return f"lmstudio:{label}"

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        start = time.monotonic()
        try:
            messages = _build_messages(request)
            payload: dict = {
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "stream": False,
            }
            if self.model:
                payload["model"] = self.model
            if request.stop:
                payload["stop"] = request.stop

            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            choice = data.get("choices", [{}])[0]
            text: str = choice.get("message", {}).get("content", "")
            finish_reason: str = choice.get("finish_reason") or "stop"
            usage = data.get("usage", {})
            tokens_gen: int = usage.get("completion_tokens", 0)

            return GenerationResponse(
                text=text,
                tokens_generated=tokens_gen,
                finish_reason=finish_reason,
                backend_used=self.backend_name(),
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as exc:
            logger.error("LMStudioBackend.generate error: %s", exc)
            return GenerationResponse(
                text="",
                error=str(exc),
                finish_reason="error",
                backend_used=self.backend_name(),
                latency_ms=(time.monotonic() - start) * 1000,
            )

    def health_check(self) -> bool:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(
                f"{self.base_url}/v1/models",
                headers=headers,
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = requests.get(
                f"{self.base_url}/v1/models",
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception as exc:
            logger.warning("LMStudioBackend.list_models failed: %s", exc)
            return []


def _build_messages(request: GenerationRequest) -> list[dict]:
    if request.messages:
        return request.messages

    msgs: list[dict] = []
    if request.system_prompt:
        msgs.append({"role": "system", "content": request.system_prompt})
    msgs.append({"role": "user", "content": request.prompt})
    return msgs
