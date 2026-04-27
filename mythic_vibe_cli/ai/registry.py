from __future__ import annotations

from dataclasses import dataclass

from .providers import (
    AIProvider,
    AnthropicProvider,
    CopyPasteProvider,
    GeminiProvider,
    LocalProvider,
    OpenAIProvider,
    OpenRouterProvider,
)


@dataclass
class ProviderRegistry:
    def providers(self) -> dict[str, AIProvider]:
        return {
            "copy-paste": CopyPasteProvider(),
            "local": LocalProvider(),
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "gemini": GeminiProvider(),
            "openrouter": OpenRouterProvider(),
        }
