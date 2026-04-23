#!/usr/bin/env python3
"""
Local AI Provider Support (v4.6.0 — hardened)
===============================================
Provides local LLM backends as drop-in replacements for
OpenRouter.

Robustness features
-------------------
- **Jittered exponential backoff** on retries (prevents
  thundering-herd on restart).
- **Defensive JSON parsing** — malformed API responses never
  crash the game.
- **Connection-loss detection** with actionable error messages.
- **Auto-reconnect** — ``check_health()`` validates the server
  and ``complete()`` retries on transient failures.
- **Input sanitisation** — Message content is always stringified.
- **Safe model listing** — ``list_models()`` returns ``[]``
  instead of raising.

Supported providers:
- Ollama (default port 11434)
- LM Studio (OpenAI-compatible, default port 1234)
- Any OpenAI-compatible API (KoboldCpp, text-gen-webui, etc.)

Usage in config.yaml::

    ai_provider: "ollama"
    local_ai:
        provider: "ollama"
        base_url: "http://localhost:11434"
        model: "llama3.1:8b"
        temperature: 0.8
        max_tokens: 4096
"""

import json
import logging
import random
import time
import traceback
import threading
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Import Message and CompletionResponse from existing module
from ai.openrouter import Message, CompletionResponse


class LocalAIError(Exception):
    """Exception raised by local AI providers."""

    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_base_url(base_url: str, provider: str) -> str:
    """Normalise local endpoints so config mistakes
    do not break inference.
    """
    clean = (base_url or "").strip().rstrip("/")
    if not clean:
        return clean
    if provider == "ollama" and clean.endswith("/v1"):
        clean = clean[:-3].rstrip("/")
    if provider in {"lmstudio", "openai_compat"} and clean.endswith("/v1"):
        clean = clean[:-3].rstrip("/")
    return clean


def _with_retries(
    operation: Callable[[], Any],
    attempts: int = 3,
    jitter: bool = True,
) -> Any:
    """Retry loop with jittered exponential backoff.

    Raises the last exception after all attempts are exhausted.
    """
    last_error: Optional[Exception] = None
    for attempt in range(1, max(1, attempts) + 1):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
            if attempt >= attempts:
                break
            delay = min(1.5 * attempt, 6.0)
            if jitter:
                delay += random.uniform(0, delay * 0.3)
            logger.debug(
                "Retry %d/%d after %.1fs: %s",
                attempt,
                attempts,
                delay,
                exc,
            )
            time.sleep(delay)
    if last_error:
        raise last_error
    raise LocalAIError("Local provider failed with unknown retry error")


def _safe_json(response: Any) -> Dict[str, Any]:
    """Parse JSON from a requests Response. Never raises."""
    try:
        data = response.json()
        if isinstance(data, dict):
            return data
        return {"_raw": data}
    except Exception:
        try:
            text = response.text[:2000]
            return {"_raw_text": text}
        except Exception:
            return {}


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert *value* to int, returning *default* on error."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Ollama Client
# ---------------------------------------------------------------------------


class OllamaClient:
    """Client for Ollama (https://ollama.ai).

    Ollama runs models locally and exposes them via REST API.
    Default endpoint: http://localhost:11434
    """

    def __init__(
        self,
        model: str = "llama3.1:8b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.8,
        max_tokens: int = 4096,
        timeout: int = 120,
        **kwargs: Any,
    ):
        self.model = str(model)
        self.base_url = _normalize_base_url(str(base_url), "ollama")
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self.timeout = int(timeout)
        self._consecutive_failures = 0
        self._last_health: Optional[bool] = None
        self._model_ready: bool = False
        self._pull_attempted: bool = False
        self._pull_lock = threading.Lock()

        logger.info(
            "OllamaClient initialised: %s @ %s",
            self.model,
            self.base_url,
        )

    def _is_model_installed(self) -> bool:
        """Check whether configured model is present in local Ollama registry."""
        try:
            target = self.model.strip().lower()
            if not target:
                return False
            for name in self.list_models():
                normalized = str(name).strip().lower()
                if normalized == target or normalized.startswith(f"{target}:"):
                    return True
            return False
        except Exception:
            return False

    def _pull_model_with_progress(self, timeout_s: int = 1800) -> bool:
        """Pull configured model from Ollama and log progress updates."""
        import requests

        endpoint = f"{self.base_url}/api/pull"
        payload = {"name": self.model, "stream": True}
        logger.info("Ollama model missing; downloading '%s' from %s", self.model, endpoint)

        try:
            with requests.post(endpoint, json=payload, stream=True, timeout=(10, timeout_s)) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except Exception:
                        logger.debug("Ollama pull raw: %s", line)
                        continue

                    if evt.get("error"):
                        logger.warning("Ollama pull error: %s", evt.get("error"))
                        continue

                    status = str(evt.get("status", "")).strip()
                    completed = _safe_int(evt.get("completed", 0), 0)
                    total = _safe_int(evt.get("total", 0), 0)
                    if total > 0:
                        pct = max(0.0, min(100.0, (completed / total) * 100.0))
                        logger.info("Ollama pull progress for %s: %.1f%% (%s/%s)", self.model, pct, completed, total)
                    elif status:
                        logger.info("Ollama pull status for %s: %s", self.model, status)
        except Exception as exc:
            logger.warning("Ollama pull request failed for %s: %s", self.model, exc)
            return False

        installed = self._is_model_installed()
        if installed:
            logger.info("Ollama model ready: %s", self.model)
        return installed

    def ensure_model_available(self, max_attempts: int = 3) -> bool:
        """Ensure configured Ollama model exists locally; self-heal with pull retries."""
        with self._pull_lock:
            if self._model_ready:
                return True

            if self._is_model_installed():
                self._model_ready = True
                return True

            self._pull_attempted = True
            if not self.check_health():
                logger.warning("Ollama unavailable while ensuring model '%s'; skipping auto-pull.", self.model)
                return False

            for attempt in range(1, max(1, max_attempts) + 1):
                if self._pull_model_with_progress():
                    self._model_ready = True
                    return True
                backoff = min(2.0 * attempt, 10.0)
                logger.warning(
                    "Ollama model pull attempt %d/%d failed for %s; retrying in %.1fs",
                    attempt,
                    max_attempts,
                    self.model,
                    backoff,
                )
                time.sleep(backoff)

            logger.warning(
                "Ollama model '%s' is still unavailable after retries; engine will continue with fallbacks.",
                self.model,
            )
            return False

    # ---- completions -------------------------------------------------------

    def complete(self, messages: List[Message], **kwargs: Any) -> CompletionResponse:
        """Send messages to Ollama's chat endpoint.

        Compatible with the SyncOpenRouterClient interface.
        """
        import requests

        # Huginn confirms the model rune is carved before seeking omens.
        self.ensure_model_available(max_attempts=1)

        # Sanitise messages
        msg_dicts: List[Dict[str, str]] = []
        for msg in messages:
            try:
                role = str(getattr(msg, "role", "user"))
                content = str(getattr(msg, "content", ""))
            except Exception:
                role, content = "user", ""
            msg_dicts.append({"role": role, "content": content})

        payload = {
            "model": self.model,
            "messages": msg_dicts,
            "stream": False,
            "options": {
                "temperature": float(kwargs.get("temperature", self.temperature)),
                "num_predict": int(kwargs.get("max_tokens", self.max_tokens)),
            },
        }

        try:

            def _request_chat() -> Dict[str, Any]:
                resp = requests.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                return _safe_json(resp)

            data = _with_retries(_request_chat, attempts=3, jitter=True)

            # Extract content defensively
            content = ""
            msg_data = data.get("message")
            if isinstance(msg_data, dict):
                content = str(msg_data.get("content", ""))
            if not content:
                fallback = data.get("response", "")
                if isinstance(fallback, str):
                    content = fallback

            # Extract usage defensively
            usage = {
                "prompt_tokens": _safe_int(data.get("prompt_eval_count", 0)),
                "completion_tokens": _safe_int(data.get("eval_count", 0)),
                "total_tokens": (
                    _safe_int(data.get("prompt_eval_count", 0))
                    + _safe_int(data.get("eval_count", 0))
                ),
            }

            self._consecutive_failures = 0
            return CompletionResponse(
                content=content,
                model=self.model,
                usage=usage,
                finish_reason="stop",
                raw_response=data,
            )

        except requests.exceptions.ConnectionError:
            self._consecutive_failures += 1
            raise LocalAIError(
                f"Cannot connect to Ollama at "
                f"{self.base_url}. "
                f"Is Ollama running? Start with: "
                f"ollama serve "
                f"(failures: "
                f"{self._consecutive_failures})"
            )
        except requests.exceptions.Timeout:
            self._consecutive_failures += 1
            raise LocalAIError(
                f"Ollama request timed out after "
                f"{self.timeout}s. "
                f"Model may be loading or prompt "
                f"too long."
            )
        except LocalAIError:
            self._consecutive_failures += 1
            raise
        except Exception as exc:
            self._consecutive_failures += 1
            logger.error(
                "Ollama unexpected error: %s\n%s",
                exc,
                traceback.format_exc(),
            )
            raise LocalAIError(f"Ollama error: {exc}")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Compatibility helper for subsystems expecting generate(prompt=...)."""
        messages = [Message(role="user", content=str(prompt))]
        response = self.complete(messages, **kwargs)
        return str(getattr(response, "content", "")).strip()

    # ---- model listing -----------------------------------------------------

    def list_models(self) -> List[str]:
        """List available Ollama models. Never raises."""
        import requests

        try:

            def _fetch() -> List[str]:
                resp = requests.get(
                    f"{self.base_url}/api/tags",
                    timeout=10,
                )
                resp.raise_for_status()
                data = _safe_json(resp)
                models = data.get("models", [])
                if not isinstance(models, list):
                    return []
                result = []
                for m in models:
                    if isinstance(m, dict):
                        name = m.get("name", "")
                        if name:
                            result.append(str(name))
                return result

            return _with_retries(_fetch, attempts=2, jitter=True)
        except Exception as exc:
            logger.warning("Could not list Ollama models: %s", exc)
            return []

    # ---- health check ------------------------------------------------------

    def check_health(self) -> bool:
        """Ping Ollama server to verify reachability.

        Caches the result so callers can check
        ``self._last_health``.
        """
        import requests

        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            healthy = resp.status_code < 500
            self._last_health = healthy
            return healthy
        except Exception:
            self._last_health = False
            return False


# ---------------------------------------------------------------------------
# LM Studio / OpenAI-compatible Client
# ---------------------------------------------------------------------------


class LMStudioClient:
    """Client for LM Studio and any OpenAI-compatible API.

    Works with LM Studio, KoboldCpp,
    text-generation-webui, etc.
    """

    def __init__(
        self,
        model: str = "local-model",
        base_url: str = "http://localhost:1234",
        temperature: float = 0.8,
        max_tokens: int = 4096,
        timeout: int = 120,
        api_key: str = "not-needed",
        **kwargs: Any,
    ):
        self.model = str(model)
        self.base_url = _normalize_base_url(str(base_url), "lmstudio")
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self.timeout = int(timeout)
        self.api_key = str(api_key)
        self._consecutive_failures = 0

        logger.info(
            "LMStudioClient initialised: %s @ %s",
            self.model,
            self.base_url,
        )

    def complete(self, messages: List[Message], **kwargs: Any) -> CompletionResponse:
        """Send messages to an OpenAI-compatible endpoint."""
        import requests

        msg_dicts: List[Dict[str, str]] = []
        for msg in messages:
            try:
                role = str(getattr(msg, "role", "user"))
                content = str(getattr(msg, "content", ""))
            except Exception:
                role, content = "user", ""
            msg_dicts.append({"role": role, "content": content})

        payload = {
            "model": self.model,
            "messages": msg_dicts,
            "temperature": float(kwargs.get("temperature", self.temperature)),
            "max_tokens": int(kwargs.get("max_tokens", self.max_tokens)),
            "stream": False,
        }

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.api_key and self.api_key != "not-needed":
            headers["Authorization"] = f"Bearer {self.api_key}"

        endpoint = f"{self.base_url}/v1/chat/completions"

        try:

            def _request_chat() -> Dict[str, Any]:
                resp = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                return _safe_json(resp)

            data = _with_retries(_request_chat, attempts=3, jitter=True)

            choices = data.get("choices", [])
            if not isinstance(choices, list):
                choices = []

            if not choices:
                # Recovery: retry with shorter max_tokens
                retry_payload = dict(payload)
                retry_payload["max_tokens"] = max(
                    256,
                    int(payload.get("max_tokens", self.max_tokens) * 0.5),
                )

                def _request_short() -> Dict[str, Any]:
                    resp = requests.post(
                        endpoint,
                        json=retry_payload,
                        headers=headers,
                        timeout=self.timeout,
                    )
                    resp.raise_for_status()
                    return _safe_json(resp)

                data = _with_retries(_request_short, attempts=2, jitter=True)
                choices = data.get("choices", [])
                if not isinstance(choices, list):
                    choices = []

            if not choices:
                raise LocalAIError("No choices in response after recovery attempts")

            first = choices[0] if isinstance(choices[0], dict) else {}
            msg = first.get("message", {})
            content = str(msg.get("content", "")) if isinstance(msg, dict) else ""
            finish = str(first.get("finish_reason", "stop"))

            raw_usage = data.get("usage", {})
            usage = {
                "prompt_tokens": _safe_int(raw_usage.get("prompt_tokens", 0)),
                "completion_tokens": _safe_int(raw_usage.get("completion_tokens", 0)),
                "total_tokens": _safe_int(raw_usage.get("total_tokens", 0)),
            }

            self._consecutive_failures = 0
            return CompletionResponse(
                content=content,
                model=data.get("model", self.model),
                usage=usage,
                finish_reason=finish,
                raw_response=data,
            )

        except requests.exceptions.ConnectionError:
            self._consecutive_failures += 1
            raise LocalAIError(
                f"Cannot connect to local AI at "
                f"{self.base_url}. "
                f"Is your local server running?"
            )
        except requests.exceptions.Timeout:
            self._consecutive_failures += 1
            raise LocalAIError(
                f"Local AI timed out after "
                f"{self.timeout}s. "
                f"Model may be loading or prompt "
                f"too long."
            )
        except LocalAIError:
            self._consecutive_failures += 1
            raise
        except Exception as exc:
            self._consecutive_failures += 1
            logger.error(
                "LMStudio unexpected error: %s\n%s",
                exc,
                traceback.format_exc(),
            )
            raise LocalAIError(f"Local AI error: {exc}")

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Compatibility helper for subsystems expecting generate(prompt=...)."""
        messages = [Message(role="user", content=str(prompt))]
        response = self.complete(messages, **kwargs)
        return str(getattr(response, "content", "")).strip()

    def check_health(self) -> bool:
        """Ping the server to verify reachability."""
        import requests

        try:
            resp = requests.get(
                f"{self.base_url}/v1/models",
                timeout=5,
            )
            return resp.status_code < 500
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_local_client(config: Dict[str, Any]) -> Any:
    """Factory function to create the appropriate local AI
    client.

    Returns an OllamaClient or LMStudioClient based on
    ``config['local_ai']['provider']``.
    """
    local_config = {}
    if isinstance(config, dict):
        local_config = config.get("local_ai", {})
    if not isinstance(local_config, dict):
        local_config = {}

    provider = str(local_config.get("provider", "ollama")).lower().strip()

    common_args: Dict[str, Any] = {
        "model": str(local_config.get("model", "")),
        "base_url": str(local_config.get("base_url", "")),
        "temperature": float(local_config.get("temperature", 0.8)),
        "max_tokens": int(local_config.get("max_tokens", 4096)),
        "timeout": int(local_config.get("timeout", 120)),
    }

    if provider == "ollama":
        if not common_args["base_url"]:
            common_args["base_url"] = "http://localhost:11434"
        if not common_args["model"]:
            common_args["model"] = "llama3.1:8b"
        return OllamaClient(**common_args)

    elif provider in (
        "lmstudio",
        "openai_compat",
        "openai_compatible",
        "koboldcpp",
        "local",
    ):
        if not common_args["base_url"]:
            common_args["base_url"] = "http://localhost:1234"
        if not common_args["model"]:
            common_args["model"] = "local-model"
        common_args["api_key"] = str(local_config.get("api_key", "not-needed"))
        return LMStudioClient(**common_args)

    else:
        raise LocalAIError(
            f"Unknown local AI provider: '{provider}'. "
            f"Supported: ollama, lmstudio, openai_compat"
        )
