from __future__ import annotations

from dataclasses import dataclass

from .base import Estimate, ProviderResponse, ProviderStatus


@dataclass
class LocalProvider:
    name: str = "local"
    model: str = "local-reflection"

    def validate_config(self) -> ProviderStatus:
        return ProviderStatus(configured=True, details=["local provider is always available"])

    def estimate(self, packet: object) -> Estimate:
        text = str(packet)
        return Estimate(input_tokens=max(1, len(text) // 5), output_tokens=max(1, len(text) // 10), cost_usd=0.0)

    def run(self, packet: object) -> ProviderResponse:
        return ProviderResponse(provider=self.name, model=self.model, content=str(packet), packet_id="local", dry_run=True)
