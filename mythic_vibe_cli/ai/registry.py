from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .providers import (
    AIProvider,
    AnthropicProvider,
    CopyPasteProvider,
    GeminiProvider,
    LocalProvider,
    OllamaProvider,
    OpenAIProvider,
    OpenRouterProvider,
)


@dataclass
class ProviderRegistry:
    root: Path | None = None

    def providers(self) -> dict[str, AIProvider]:
        return {
            "copy-paste": CopyPasteProvider(root=self.root),
            "local": LocalProvider(root=self.root),
            "openai": OpenAIProvider(root=self.root),
            "anthropic": AnthropicProvider(root=self.root),
            "gemini": GeminiProvider(root=self.root),
            "openrouter": OpenRouterProvider(root=self.root),
            "ollama": OllamaProvider(root=self.root),
        }
