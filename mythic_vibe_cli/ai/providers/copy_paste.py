from __future__ import annotations

from dataclasses import dataclass

from .base import Estimate, ProviderResponse, ProviderStatus


@dataclass
class CopyPasteProvider:
    name: str = "copy-paste"
    model: str = "manual"

    def validate_config(self) -> ProviderStatus:
        return ProviderStatus(configured=True, details=["copy-paste bridge does not require keys"])

    def estimate(self, packet: object) -> Estimate:
        text = str(packet)
        return Estimate(input_tokens=max(1, len(text) // 4), output_tokens=max(1, len(text) // 8), cost_usd=0.0)

    def run(self, packet: object) -> ProviderResponse:
        return ProviderResponse(provider=self.name, model=self.model, content=str(packet), packet_id="manual", dry_run=True)
