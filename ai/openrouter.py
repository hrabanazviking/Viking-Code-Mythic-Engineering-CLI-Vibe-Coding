#!/usr/bin/env python3
"""
OpenRouter API Client
=====================
Provides async access to LLMs via OpenRouter API.
Supports multiple models with automatic fallback.

SUPPORTED MODELS:
- DeepSeek (V3, R1, Coder) - Recommended for roleplay
- Anthropic Claude (3.5, 3 Opus)
- OpenAI (GPT-4, GPT-4 Turbo)
- Meta Llama (3.1, 3.2)
- Qwen (2.5, QwQ)
- Yi-Large
- And many more via OpenRouter
"""

import asyncio
import httpx
import json
import logging
import random
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# RECOMMENDED MODELS
# ============================================================================
# These are tested and work well for roleplay/narrative generation.
# Add your own by finding model IDs at https://openrouter.ai/models

RECOMMENDED_MODELS = {
    # ===== CHINESE MODELS (Excellent for creative/roleplay) =====
    "deepseek/deepseek-chat-v3-0324": {
        "name": "DeepSeek V3 (2025-03)",
        "context": 128000,
        "type": "chat",
        "recommended": True,
        "notes": "Best overall - fast, cheap, excellent at roleplay"
    },
    "deepseek/deepseek-chat": {
        "name": "DeepSeek V3",
        "context": 128000,
        "type": "chat",
        "recommended": True,
        "notes": "Latest DeepSeek V3"
    },
    "deepseek/deepseek-r1": {
        "name": "DeepSeek R1",
        "context": 64000,
        "type": "reasoning",
        "notes": "Best for complex reasoning, shows thought process"
    },
    "deepseek/deepseek-r1-distill-llama-70b": {
        "name": "DeepSeek R1 Distill 70B",
        "context": 128000,
        "type": "reasoning",
        "notes": "Faster R1 reasoning on Llama architecture"
    },
    "deepseek/deepseek-coder": {
        "name": "DeepSeek Coder",
        "context": 128000,
        "type": "code",
        "notes": "Optimized for code generation"
    },
    "qwen/qwen-2.5-72b-instruct": {
        "name": "Qwen 2.5 72B",
        "context": 131072,
        "type": "chat",
        "notes": "Alibaba's best model, excellent at Chinese and English"
    },
    "qwen/qwq-32b": {
        "name": "QwQ 32B",
        "context": 32000,
        "type": "reasoning",
        "notes": "Qwen reasoning model"
    },
    "01-ai/yi-large": {
        "name": "Yi-Large",
        "context": 32000,
        "type": "chat",
        "notes": "01.AI's flagship model"
    },
    
    # ===== ANTHROPIC =====
    "anthropic/claude-3.5-sonnet": {
        "name": "Claude 3.5 Sonnet",
        "context": 200000,
        "type": "chat",
        "notes": "Best for nuanced creative writing"
    },
    "anthropic/claude-3-opus": {
        "name": "Claude 3 Opus",
        "context": 200000,
        "type": "chat",
        "notes": "Most capable Claude, higher cost"
    },
    
    # ===== OPENAI =====
    "openai/gpt-4-turbo": {
        "name": "GPT-4 Turbo",
        "context": 128000,
        "type": "chat",
        "notes": "Strong general purpose"
    },
    "openai/gpt-4o": {
        "name": "GPT-4o",
        "context": 128000,
        "type": "chat",
        "notes": "Latest GPT-4"
    },
    
    # ===== META =====
    "meta-llama/llama-3.1-70b-instruct": {
        "name": "Llama 3.1 70B",
        "context": 131072,
        "type": "chat",
        "notes": "Open weights, good for roleplay"
    },
    "meta-llama/llama-3.3-70b-instruct": {
        "name": "Llama 3.3 70B", 
        "context": 131072,
        "type": "chat",
        "notes": "Latest Llama"
    },
}

# Provider preferences (faster providers for certain models)
PROVIDER_PREFERENCES = {
    "deepseek/deepseek-chat": ["DeepInfra", "Together", "Fireworks"],
    "deepseek/deepseek-chat-v3-0324": ["DeepInfra", "Together", "Fireworks"],
    "deepseek/deepseek-r1": ["DeepInfra", "Together"],
    "qwen/qwen-2.5-72b-instruct": ["DeepInfra", "Together", "Fireworks"],
    "meta-llama/llama-3.1-70b-instruct": ["DeepInfra", "Together", "Fireworks"],
}

# Default model - DeepSeek V3 is excellent for roleplay
DEFAULT_MODEL = "deepseek/deepseek-chat-v3-0324"

# Extended context hints for models that are valid but not in RECOMMENDED_MODELS.
KNOWN_MODEL_CONTEXT_WINDOWS: Dict[str, int] = {
    "x-ai/grok-4.1-fast": 2_000_000,
    "x-ai/grok-4": 2_000_000,
    "x-ai/grok-3-mini": 1_000_000,
}


@dataclass
class Message:
    """Chat message structure."""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class CompletionResponse:
    """Response from completion API."""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    raw_response: Dict[str, Any] = field(default_factory=dict)


class OpenRouterError(Exception):
    """Base exception for OpenRouter errors."""
    pass


class OpenRouterClient:
    """
    Async client for OpenRouter API.
    
    Usage:
        client = OpenRouterClient(api_key="your-key")
        response = await client.complete([
            Message(role="system", content="You are a Norse saga narrator."),
            Message(role="user", content="Describe Uppsala at dusk.")
        ])
        print(response.content)
    """
    
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    def __init__(
        self,
        api_key: str,
        model: str = None,  # Now defaults to None, uses DEFAULT_MODEL
        fallback_model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.8,
        top_p: float = 1.0,
        top_k: int = 0,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        timeout: int = 120,
        max_retries: int = 3,
        provider: Optional[str] = None,
        model_context_overrides: Optional[Dict[str, Any]] = None,
        context_budget_factor: float = 0.95,
    ):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key
            model: Primary model to use (default: DeepSeek V3)
            fallback_model: Fallback if primary fails
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-2.0)
            top_p: Nucleus sampling value (0.0-1.0)
            top_k: Top-k token sampling (0 for provider default)
            presence_penalty: Presence penalty (-2.0 to 2.0)
            frequency_penalty: Frequency penalty (-2.0 to 2.0)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            provider: Preferred provider (e.g., "DeepInfra" for faster DeepSeek)
            context_budget_factor: Fraction of the model context window reserved for
                input messages (0.0-1.0).  The remainder is reserved for the
                completion.  Default 0.95 (use 95 % of the window).  Must NOT be
                configured to drop data silently; raise it rather than lower it.
        """
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL
        self.fallback_model = fallback_model or "anthropic/claude-3.5-sonnet"
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = max(0.0, min(1.0, float(top_p)))
        self.top_k = max(0, min(200, int(top_k)))
        self.presence_penalty = max(-2.0, min(2.0, float(presence_penalty)))
        self.frequency_penalty = max(-2.0, min(2.0, float(frequency_penalty)))
        self.timeout = timeout
        self.max_retries = max_retries
        self.provider = provider
        self.model_context_overrides = model_context_overrides or {}
        # Clamp to (0.50, 1.00] so it is never so low as to always truncate.
        self.context_budget_factor = max(0.50, min(1.0, float(context_budget_factor)))
        
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://norse-saga-engine.local",
            "X-Title": "Norse Saga Engine"
        }
        
        self._client: Optional[httpx.AsyncClient] = None
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0
        
        logger.info(f"OpenRouter client initialized with model: {self.model}")
        if self.provider:
            logger.info(f"Preferred provider: {self.provider}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=self.headers
            )
        return self._client

    async def _reset_client(self):
        """Reset the HTTP client after transport-layer failures."""
        if self._client and not self._client.is_closed:
            try:
                await self._client.aclose()
            except Exception as exc:
                logger.warning("Failed closing client during reset: %s", exc)
        self._client = None

    def _sanitize_messages(self, messages: List[Message]) -> List[Message]:
        """Huginn scouts for relevant threads before we ask the oracle."""
        cleaned: List[Message] = []
        for idx, message in enumerate(messages):
            if not isinstance(message, Message):
                logger.warning("Dropping non-Message at index %s: %r", idx, message)
                continue
            role = (message.role or "user").strip().lower()
            if role not in {"system", "user", "assistant"}:
                logger.warning("Invalid role '%s' at index %s, coercing to user", role, idx)
                role = "user"
            content = (message.content or "").strip()
            if not content:
                logger.warning("Skipping empty message content at index %s", idx)
                continue
            cleaned.append(Message(role=role, content=content))
        if not cleaned:
            raise OpenRouterError("No valid messages to send after sanitization")
        return cleaned



    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Approximate token estimation for provider-safe budgeting."""
        return max(1, len(text or "") // 4)

    def _resolve_model_context_limit(self, model_name: str) -> int:
        """Resolve model context window using overrides, known lists, and safe fallback."""
        try:
            override = self.model_context_overrides.get(model_name)
            if override is not None:
                parsed = int(override)
                if parsed > 0:
                    return parsed
        except Exception as exc:
            logger.warning("Invalid model context override for %s: %r (%s)", model_name, override, exc)

        known = RECOMMENDED_MODELS.get(model_name, {})
        if isinstance(known, dict) and known.get("context"):
            return int(known["context"])

        hinted = KNOWN_MODEL_CONTEXT_WINDOWS.get(model_name)
        if hinted:
            return int(hinted)

        # Conservative fallback when model metadata is unknown.
        return 128000

    def _fit_messages_within_budget(
        self, messages: List[Message], context_limit: int
    ) -> List[Message]:
        """Trim oversized message payloads to prevent context-window failures."""
        # Reserve context_budget_factor of the window for input; the rest for output.
        # With large-context models (e.g. Grok 2M) this budget is 1.9M tokens and
        # this function is essentially a no-op in normal operation.
        input_budget = max(2000, int(context_limit * self.context_budget_factor))
        token_count = sum(self._estimate_tokens(m.content) + 8 for m in messages)
        if token_count <= input_budget:
            return messages

        logger.warning(
            "Prompt oversized (%s est tokens > %s budget). Applying emergency compaction.",
            token_count,
            input_budget,
        )

        compacted: List[Message] = [Message(role=m.role, content=m.content) for m in messages]
        # Preserve final user intent and initial system prompt as much as possible.
        preserve = {len(compacted) - 1}
        if len(compacted) > 2:
            preserve.add(0)

        # Pre-compute per-message token counts once; maintain a running total and only
        # re-estimate the specific message that was truncated (O(n) → O(1) per trim step).
        msg_tokens: List[int] = [self._estimate_tokens(m.content) + 8 for m in compacted]

        for idx, msg in enumerate(compacted):
            if idx in preserve:
                continue
            if token_count <= input_budget:
                break
            current_tokens = msg_tokens[idx] - 8  # strip the per-message overhead
            if current_tokens <= 48:
                continue
            target_tokens = max(24, current_tokens // 4)
            max_chars = target_tokens * 4
            msg.content = msg.content[:max_chars] + "\n...[context compacted for budget]"
            new_tokens = self._estimate_tokens(msg.content) + 8
            token_count += new_tokens - msg_tokens[idx]
            msg_tokens[idx] = new_tokens

        if token_count > input_budget and compacted:
            if len(compacted) == 1:
                # Single-message prompts still need compaction, otherwise we can never recover.
                hard_char_budget = max(1024, input_budget * 4)
                compacted[0].content = compacted[0].content[:hard_char_budget] + "\n...[hard-compacted]"
                new_tokens = self._estimate_tokens(compacted[0].content) + 8
                token_count += new_tokens - msg_tokens[0]
                msg_tokens[0] = new_tokens

            # Last-resort trim of the largest message outside preserve.
            candidates = [
                (i, msg_tokens[i] - 8)
                for i in range(len(compacted))
                if i not in preserve
            ]
            candidates.sort(key=lambda x: x[1], reverse=True)
            for idx, _ in candidates:
                if token_count <= input_budget:
                    break
                msg = compacted[idx]
                msg.content = msg.content[:1024] + "\n...[hard-compacted]"
                new_tokens = self._estimate_tokens(msg.content) + 8
                token_count += new_tokens - msg_tokens[idx]
                msg_tokens[idx] = new_tokens

        if token_count > input_budget and compacted:
            # Final emergency pass: trim even preserved entries so the request can proceed.
            for idx, msg in enumerate(compacted):
                if token_count <= input_budget:
                    break
                if len(msg.content) <= 1024:
                    continue
                msg.content = msg.content[-1024:] + "\n...[last-resort tail-preserved]"
                new_tokens = self._estimate_tokens(msg.content) + 8
                token_count += new_tokens - msg_tokens[idx]
                msg_tokens[idx] = new_tokens

        return compacted

    def _safe_output_tokens(self, requested_max_tokens: int, messages: List[Message], model_name: str) -> int:
        """Trust configured max_tokens; only reject unusable values."""
        try:
            requested = int(requested_max_tokens)
            if requested <= 0:
                raise ValueError("must be > 0")
            return requested
        except Exception as exc:
            raise OpenRouterError(
                f"Invalid max_tokens value {requested_max_tokens!r} for model {model_name}: {exc}"
            ) from exc

    def _circuit_is_open(self) -> bool:
        return time.monotonic() < self._circuit_open_until

    def _record_failure(self):
        self._consecutive_failures += 1
        if self._consecutive_failures >= 5:
            cooldown = min(60, 2 ** min(self._consecutive_failures - 5, 5))
            self._circuit_open_until = time.monotonic() + cooldown
            logger.warning("Circuit opened for %.1fs after %s failures", cooldown, self._consecutive_failures)

    def _record_success(self):
        self._consecutive_failures = 0
        self._circuit_open_until = 0.0
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        stop: Optional[List[str]] = None,
        provider: Optional[str] = None,
        **kwargs
    ) -> CompletionResponse:
        """
        Send completion request to OpenRouter.
        
        Args:
            messages: List of chat messages
            model: Override default model
            max_tokens: Deprecated override. Ignored; config-driven client max_tokens is authoritative.
            temperature: Override default temperature
            top_p: Override nucleus sampling
            top_k: Override top-k sampling
            presence_penalty: Override presence penalty
            frequency_penalty: Override frequency penalty
            stop: Stop sequences
            provider: Override default provider
            **kwargs: Additional API parameters
            
        Returns:
            CompletionResponse with generated content
            
        Raises:
            OpenRouterError: On API errors after retries
        """
        use_model = model or self.model
        if max_tokens is not None:
            try:
                per_call_max_tokens = int(max_tokens)
            except Exception:
                per_call_max_tokens = None
            if per_call_max_tokens is not None and per_call_max_tokens != int(self.max_tokens):
                logger.debug(
                    "Per-call max_tokens=%s ignored for model %s; using configured max_tokens=%s",
                    max_tokens,
                    use_model,
                    self.max_tokens,
                )
        max_tokens = self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        top_p = self.top_p if top_p is None else max(0.0, min(1.0, float(top_p)))
        top_k = self.top_k if top_k is None else max(0, min(200, int(top_k)))
        presence_penalty = (
            self.presence_penalty
            if presence_penalty is None
            else max(-2.0, min(2.0, float(presence_penalty)))
        )
        frequency_penalty = (
            self.frequency_penalty
            if frequency_penalty is None
            else max(-2.0, min(2.0, float(frequency_penalty)))
        )
        use_provider = provider or self.provider
        messages = self._sanitize_messages(messages)
        context_limit = self._resolve_model_context_limit(use_model)
        messages = self._fit_messages_within_budget(messages, context_limit)
        max_tokens = self._safe_output_tokens(max_tokens, messages, use_model)

        if self._circuit_is_open():
            raise OpenRouterError("OpenRouter circuit is temporarily open after repeated failures")
        
        # Log the model being used
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{timestamp}] AI Inference - Model: {use_model}" + 
                   (f", Provider: {use_provider}" if use_provider else ""))
        
        payload = {
            "model": use_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "presence_penalty": presence_penalty,
            "frequency_penalty": frequency_penalty,
        }

        # Respect extra kwargs but never allow them to override sanitized core controls.
        for key, value in kwargs.items():
            if key in payload:
                logger.warning("Ignoring unsafe override for '%s' in complete() kwargs", key)
                continue
            payload[key] = value
        
        if stop:
            payload["stop"] = stop
        
        # Add provider preference if specified
        if use_provider:
            payload["provider"] = {
                "order": [use_provider]
            }
        
        # Try primary model
        try:
            return await self._request_with_retry(payload, use_model)
        except OpenRouterError:
            # Try fallback model if available
            if self.fallback_model and use_model != self.fallback_model:
                logger.warning(f"Primary model {use_model} failed, trying fallback: {self.fallback_model}")
                payload["model"] = self.fallback_model
                fallback_context = self._resolve_model_context_limit(self.fallback_model)
                payload_messages = [Message(role=m.role, content=m.content) for m in messages]
                payload_messages = self._fit_messages_within_budget(payload_messages, fallback_context)
                payload["messages"] = [
                    {"role": m.role, "content": m.content} for m in payload_messages
                ]
                payload["max_tokens"] = self._safe_output_tokens(
                    payload.get("max_tokens", max_tokens), payload_messages, self.fallback_model
                )
                # Remove provider preference for fallback
                if "provider" in payload:
                    del payload["provider"]
                return await self._request_with_retry(payload, self.fallback_model)
            raise
    
    async def _request_with_retry(self, payload: Dict[str, Any], model_name: str) -> CompletionResponse:
        """Make request with retry logic."""
        client = await self._get_client()
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = await client.post(self.BASE_URL, json=payload)
                
                if response.status_code == 200:
                    result = self._parse_response(response.json())
                    self._record_success()
                    # Log successful completion
                    logger.info(f"AI Response received - Model: {result.model}, "
                               f"Tokens: {result.usage.get('total_tokens', 'N/A')}")
                    return result
                
                # Handle specific error codes
                if response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited on {model_name}, waiting {wait_time}s...")
                    self._record_failure()
                    await asyncio.sleep(wait_time)
                    continue
                
                if response.status_code == 401:
                    raise OpenRouterError("Invalid API key")
                
                if response.status_code == 402:
                    raise OpenRouterError("Insufficient credits")
                
                if response.status_code >= 500:
                    # Server error - retry
                    wait_time = 2 ** attempt
                    logger.warning(f"Server error {response.status_code} on {model_name}, retrying in {wait_time}s...")
                    self._record_failure()
                    await asyncio.sleep(wait_time)
                    continue
                
                # Other errors
                try:
                    error_data = response.json() if response.content else {}
                except ValueError:
                    error_data = {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                self._record_failure()
                raise OpenRouterError(f"API error: {error_msg}")
                
            except httpx.TimeoutException:
                last_error = OpenRouterError(f"Request timed out for {model_name}")
                logger.warning(f"Timeout on attempt {attempt + 1} for {model_name}")
                self._record_failure()
                await self._reset_client()
                await asyncio.sleep((2 ** attempt) + random.uniform(0, 0.25))
                
            except httpx.RequestError as e:
                last_error = OpenRouterError(f"Request failed: {e}")
                logger.warning(f"Request error on attempt {attempt + 1} for {model_name}: {e}")
                self._record_failure()
                await self._reset_client()
                await asyncio.sleep((2 ** attempt) + random.uniform(0, 0.25))

        raise last_error or OpenRouterError(f"Max retries exceeded for {model_name}")

    async def generate_response(self, messages: List[Message], **kwargs) -> str:
        """
        Generate a response from the AI provider.
        
        This is a wrapper around the complete method for compatibility.
        """
        response = await self.complete(messages, **kwargs)
        return response.content
    
    def _parse_response(self, data: Dict[str, Any]) -> CompletionResponse:
        """Parse API response into CompletionResponse."""
        try:
            choice = data["choices"][0]
            return CompletionResponse(
                content=choice["message"]["content"],
                model=data.get("model", self.model),
                usage=data.get("usage", {}),
                finish_reason=choice.get("finish_reason", "unknown"),
                raw_response=data
            )
        except (KeyError, IndexError) as e:
            raise OpenRouterError(f"Failed to parse response: {e}")
    
    async def stream_complete(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        **kwargs
    ):
        """
        Stream completion response.
        
        Yields:
            str: Content chunks as they arrive
        """
        use_model = model or self.model
        
        # Log streaming request
        logger.info(f"AI Stream Request - Model: {use_model}")
        
        if "max_tokens" in kwargs:
            try:
                stream_per_call_tokens = int(kwargs.get("max_tokens"))
            except Exception:
                stream_per_call_tokens = None
            if stream_per_call_tokens is None or stream_per_call_tokens != int(self.max_tokens):
                logger.warning(
                    "Ignoring stream per-call max_tokens=%s for model %s; using configured max_tokens=%s",
                    kwargs.get("max_tokens"),
                    use_model,
                    self.max_tokens,
                )

        # Apply same guards as complete(): sanitize roles and fit within budget.
        messages = self._sanitize_messages(messages)
        if not messages:
            return
        context_limit = self._resolve_model_context_limit(use_model)
        messages = self._fit_messages_within_budget(messages, context_limit)

        payload = {
            "model": use_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "max_tokens": self.max_tokens,
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "top_k": kwargs.get("top_k", self.top_k),
            "presence_penalty": kwargs.get("presence_penalty", self.presence_penalty),
            "frequency_penalty": kwargs.get("frequency_penalty", self.frequency_penalty),
            "stream": True,
        }

        for key, value in kwargs.items():
            if key in payload:
                logger.warning("Ignoring unsafe stream override for '%s'", key)
                continue
            payload[key] = value
        
        client = await self._get_client()
        
        async with client.stream("POST", self.BASE_URL, json=payload) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                raise OpenRouterError(f"Stream error: {error_text.decode()}")
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk["choices"][0].get("delta", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    
    # Convenience methods for common patterns
    
    async def narrate(
        self,
        system_prompt: str,
        user_input: str,
        context: Optional[str] = None
    ) -> str:
        """
        Generate narrative response.
        
        Args:
            system_prompt: DM/narrator instructions
            user_input: Player's action or query
            context: Optional scene context
            
        Returns:
            Narrative text
        """
        messages = [Message(role="system", content=system_prompt)]
        
        if context:
            messages.append(Message(role="user", content=f"[Scene Context]\n{context}"))
            messages.append(Message(role="assistant", content="[Understood. Continuing the narrative.]"))
        
        messages.append(Message(role="user", content=user_input))
        
        response = await self.complete(messages)
        return response.content
    
    async def character_speak(
        self,
        character_prompt: str,
        situation: str,
        player_said: str
    ) -> str:
        """
        Generate character dialogue.
        
        Args:
            character_prompt: Character personality/voice description
            situation: Current scene/situation
            player_said: What the player character said
            
        Returns:
            Character's response in their voice
        """
        system = f"""You are roleplaying as a character in a Norse Viking saga.

CHARACTER:
{character_prompt}

SITUATION:
{situation}

Respond ONLY as this character would. Stay in character. Use appropriate dialect and vocabulary for an 8th century Norse setting. Do not break character or add meta-commentary."""

        messages = [
            Message(role="system", content=system),
            Message(role="user", content=f'The player says: "{player_said}"')
        ]
        
        response = await self.complete(messages, temperature=0.9)
        return response.content


# Synchronous wrapper for convenience
class SyncOpenRouterClient:
    """Synchronous wrapper around OpenRouterClient."""
    
    def __init__(self, *args, **kwargs):
        self._async_client = OpenRouterClient(*args, **kwargs)
        self._loop = None
    
    @property
    def model(self):
        """Expose model from async client."""
        return self._async_client.model
    
    @property
    def provider(self):
        """Expose provider from async client."""
        return self._async_client.provider
    
    def _get_loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop

    def complete(self, *args, **kwargs) -> CompletionResponse:
        try:
            return self._get_loop().run_until_complete(
                self._async_client.complete(*args, **kwargs)
            )
        except Exception as exc:
            logger.warning("Synchronous complete failed: %s", exc)
            raise

    def narrate(self, *args, **kwargs) -> str:
        try:
            return self._get_loop().run_until_complete(
                self._async_client.narrate(*args, **kwargs)
            )
        except Exception as exc:
            logger.warning("Synchronous narrate failed: %s", exc)
            raise

    def character_speak(self, *args, **kwargs) -> str:
        try:
            return self._get_loop().run_until_complete(
                self._async_client.character_speak(*args, **kwargs)
            )
        except Exception as exc:
            logger.warning("Synchronous character_speak failed: %s", exc)
            raise

    def close(self):
        if self._loop and not self._loop.is_closed():
            try:
                self._loop.run_until_complete(self._async_client.close())
            except Exception as exc:
                logger.warning("Failed to close async OpenRouter client cleanly: %s", exc)
            finally:
                self._loop.close()
        self._loop = None  # prevent reuse of closed loop


def list_models():
    """Print available recommended models."""
    print("=" * 60)
    print("RECOMMENDED MODELS FOR NORSE SAGA ENGINE")
    print("=" * 60)
    print()
    
    for model_id, info in RECOMMENDED_MODELS.items():
        rec = " ⭐ RECOMMENDED" if info.get("recommended") else ""
        print(f"{info['name']}{rec}")
        print(f"  ID: {model_id}")
        print(f"  Context: {info['context']:,} tokens")
        print(f"  Notes: {info['notes']}")
        print()


# Test function
async def test_client():
    """Test the OpenRouter client."""
    import os
    
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("Set OPENROUTER_API_KEY environment variable to test")
        return
    
    # Test with DeepSeek
    client = OpenRouterClient(
        api_key=api_key,
        model="deepseek/deepseek-chat-v3-0324",
        provider="DeepInfra"  # Faster provider
    )
    
    try:
        response = await client.narrate(
            system_prompt="You are a Norse saga narrator. Speak in an epic, poetic style.",
            user_input="Describe the great temple at Uppsala as the sun sets."
        )
        print("Response:", response)
    finally:
        await client.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_models()
    else:
        asyncio.run(test_client())
