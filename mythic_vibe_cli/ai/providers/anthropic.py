from __future__ import annotations

from dataclasses import dataclass
import os

from .base import Estimate, ProviderResponse, ProviderStatus


@dataclass
class AnthropicProvider:
    name: str = "anthropic"
    model: str = "claude-sonnet-4"

    def validate_config(self) -> ProviderStatus:
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        return ProviderStatus(configured=bool(key), details=["ANTHROPIC_API_KEY is required"] if not key else ["ANTHROPIC_API_KEY detected"])

    def estimate(self, packet: object) -> Estimate:
        text = str(packet)
        return Estimate(input_tokens=max(1, len(text) // 4), output_tokens=max(1, len(text) // 8), cost_usd=0.0)

    def run(self, packet: object) -> ProviderResponse:
        return ProviderResponse(provider=self.name, model=self.model, content=str(packet), packet_id="dry-run", dry_run=True)
