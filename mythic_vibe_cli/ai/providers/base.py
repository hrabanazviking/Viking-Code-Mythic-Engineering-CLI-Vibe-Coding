from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ProviderStatus:
    configured: bool
    details: list[str] = field(default_factory=list)


@dataclass
class Estimate:
    input_tokens: int
    output_tokens: int
    cost_usd: float = 0.0


@dataclass
class ProviderResponse:
    provider: str
    model: str
    content: str
    packet_id: str
    dry_run: bool = True


class AIProvider(Protocol):
    name: str

    def validate_config(self) -> ProviderStatus:
        ...

    def estimate(self, packet: object) -> Estimate:
        ...

    def run(self, packet: object) -> ProviderResponse:
        ...
