from __future__ import annotations

from dataclasses import dataclass

from .base import Estimate, ProviderResponse, ProviderStatus, estimate_packet, normalize_packet


@dataclass
class LocalProvider:
    name: str = "local"
    model: str = "local-reflection"
    root: object | None = None

    def validate_config(self) -> ProviderStatus:
        return ProviderStatus(configured=True, details=["local provider is always available"])

    def estimate(self, packet: object) -> Estimate:
        return estimate_packet(packet, provider_name=self.name)

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:
        view = normalize_packet(packet)
        packet_id = view.packet_id if view.packet_id != "inline" else "local"
        estimate = self.estimate(view)
        return ProviderResponse(
            provider=self.name,
            model=self.model,
            content=view.text,
            packet_id=packet_id,
            dry_run=True,
            usage={
                "input_tokens": estimate.input_tokens,
                "output_tokens": estimate.output_tokens,
                "total_tokens": estimate.input_tokens + estimate.output_tokens,
            },
            metadata={
                "source": view.source,
                "estimated_cost_usd": estimate.cost_usd,
                "dry_run": True,
            },
        )
