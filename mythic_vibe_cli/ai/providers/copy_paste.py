from __future__ import annotations

from dataclasses import dataclass

from .base import Estimate, ProviderResponse, ProviderStatus, estimate_packet, normalize_packet


@dataclass
class CopyPasteProvider:
    name: str = "copy-paste"
    model: str = "manual"
    root: object | None = None

    def validate_config(self) -> ProviderStatus:
        return ProviderStatus(configured=True, details=["copy-paste bridge does not require keys"])

    def estimate(self, packet: object) -> Estimate:
        return estimate_packet(packet)

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:
        view = normalize_packet(packet)
        packet_id = view.packet_id if view.packet_id != "inline" else "manual"
        return ProviderResponse(provider=self.name, model=self.model, content=view.text, packet_id=packet_id, dry_run=True)
