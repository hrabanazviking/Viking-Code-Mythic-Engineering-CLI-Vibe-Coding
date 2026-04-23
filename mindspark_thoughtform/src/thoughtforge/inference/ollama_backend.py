"""Ollama HTTP backend for ThoughtForge."""

from __future__ import annotations

import json
import logging
import time
from typing import Callable

import requests

from thoughtforge.inference.unified_backend import (
    GenerationRequest,
    GenerationResponse,
    UnifiedBackend,
)

logger = logging.getLogger(__name__)


class OllamaBackend(UnifiedBackend):
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:3b",
        timeout: int = 120,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def backend_name(self) -> str:
        return f"ollama:{self.model}"

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        start = time.monotonic()
        try:
            messages = _build_messages(request)
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens,
                },
            }
            if request.stop:
                payload["options"]["stop"] = request.stop  # type: ignore[index]

            resp = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            text: str = data.get("message", {}).get("content", "")
            finish_reason = "stop" if data.get("done") else "length"
            tokens_gen: int = data.get("eval_count", 0)

            return GenerationResponse(
                text=text,
                tokens_generated=tokens_gen,
                finish_reason=finish_reason,
                backend_used=self.backend_name(),
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as exc:
            logger.error("OllamaBackend.generate error: %s", exc)
            return GenerationResponse(
                text="",
                error=str(exc),
                finish_reason="error",
                backend_used=self.backend_name(),
                latency_ms=(time.monotonic() - start) * 1000,
            )

    def health_check(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def list_local_models(self) -> list[str]:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            logger.warning("OllamaBackend.list_local_models failed: %s", exc)
            return []

    def pull_model(
        self,
        model_name: str,
        progress_callback: Callable[[str], None] | None = None,
    ) -> bool:
        """
        Pull a model from the Ollama library.
        Streams progress lines; calls progress_callback(status) for each one if supplied.
        """
        try:
            resp = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name, "stream": True},
                stream=True,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                try:
                    line_data = json.loads(raw_line)
                    status: str = line_data.get("status", "")
                    if progress_callback and status:
                        progress_callback(status)
                    if line_data.get("error"):
                        logger.error("Ollama pull error: %s", line_data["error"])
                        return False
                except json.JSONDecodeError:
                    pass
            return True
        except Exception as exc:
            logger.error("OllamaBackend.pull_model failed: %s", exc)
            return False


def _build_messages(request: GenerationRequest) -> list[dict]:
    """Return the messages list, building from system_prompt + prompt when needed."""
    if request.messages:
        return request.messages

    msgs: list[dict] = []
    if request.system_prompt:
        msgs.append({"role": "system", "content": request.system_prompt})
    msgs.append({"role": "user", "content": request.prompt})
    return msgs
