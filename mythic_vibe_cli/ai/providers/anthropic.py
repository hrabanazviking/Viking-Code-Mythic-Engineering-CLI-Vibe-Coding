from __future__ import annotations

from dataclasses import dataclass
import os

from .base import Estimate, ProviderResponse, ProviderStatus, estimate_packet, normalize_packet, post_json, utc_now, write_provider_log


@dataclass
class AnthropicProvider:
    name: str = "anthropic"
    model: str = "claude-sonnet-4"
    root: object | None = None

    def validate_config(self) -> ProviderStatus:
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        return ProviderStatus(configured=bool(key), details=["ANTHROPIC_API_KEY is required"] if not key else ["ANTHROPIC_API_KEY detected"])

    def estimate(self, packet: object) -> Estimate:
        return estimate_packet(packet)

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:
        view = normalize_packet(packet)
        estimate = self.estimate(view)
        log_payload = {
            "timestamp": utc_now(),
            "provider": self.name,
            "model": self.model,
            "packet_id": view.packet_id,
            "dry_run": dry_run,
            "estimate": estimate.__dict__,
            "request": {"input": view.text},
        }
        if dry_run:
            response = ProviderResponse(provider=self.name, model=self.model, content=view.text, packet_id=view.packet_id, dry_run=True)
            log_payload["response"] = {"content": view.text, "dry_run": True}
            write_provider_log(self.root, log_payload)
            return response

        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": view.text}],
        }
        response_payload = post_json(
            "https://api.anthropic.com/v1/messages",
            payload,
            {
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
                "User-Agent": "mythic-vibe-cli",
            },
        )
        content_parts = response_payload.get("content", [])
        content = "".join(part.get("text", "") for part in content_parts if isinstance(part, dict))
        response = ProviderResponse(provider=self.name, model=self.model, content=content, packet_id=view.packet_id, dry_run=False)
        log_payload["response"] = response_payload
        write_provider_log(self.root, log_payload)
        return response
