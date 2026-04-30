from __future__ import annotations

from dataclasses import dataclass
import os

from .base import (
    Estimate,
    ProviderResponse,
    ProviderStatus,
    estimate_packet,
    estimate_cost,
    extract_request_id,
    extract_usage,
    normalize_packet,
    timed_post_json,
    utc_now,
    write_provider_log,
)


@dataclass
class GeminiProvider:
    name: str = "gemini"
    model: str = "gemini-2.5-pro"
    root: object | None = None

    def validate_config(self) -> ProviderStatus:
        key = os.getenv("GEMINI_API_KEY", "").strip()
        return ProviderStatus(configured=bool(key), details=["GEMINI_API_KEY is required"] if not key else ["GEMINI_API_KEY detected"])

    def estimate(self, packet: object) -> Estimate:
        return estimate_packet(packet, provider_name=self.name)

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
            response = ProviderResponse(
                provider=self.name,
                model=self.model,
                content=view.text,
                packet_id=view.packet_id,
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
            log_payload["response"] = {"content": view.text, "dry_run": True}
            write_provider_log(self.root, log_payload)
            return response

        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            raise ValueError("GEMINI_API_KEY is required")

        payload = {
            "contents": [{"role": "user", "parts": [{"text": view.text}]}],
        }
        response_payload, latency_ms = timed_post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={key}",
            payload,
            {
                "Content-Type": "application/json",
                "User-Agent": "mythic-vibe-cli",
            },
        )
        candidates = response_payload.get("candidates", [])
        text = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        usage = extract_usage(self.name, response_payload)
        if not usage:
            usage = {
                "input_tokens": estimate.input_tokens,
                "output_tokens": estimate.output_tokens,
                "total_tokens": estimate.input_tokens + estimate.output_tokens,
            }
        request_id = extract_request_id(response_payload)
        response = ProviderResponse(
            provider=self.name,
            model=self.model,
            content=text,
            packet_id=view.packet_id,
            dry_run=False,
            usage=usage,
            metadata={
                "request_id": request_id,
                "source": view.source,
                "estimated_cost_usd": estimate.cost_usd,
                "observed_cost_usd": estimate_cost(
                    self.name,
                    usage.get("input_tokens", estimate.input_tokens),
                    usage.get("output_tokens", estimate.output_tokens),
                ),
            },
        )
        log_payload["response"] = response_payload
        log_payload["latency_ms"] = latency_ms
        write_provider_log(self.root, log_payload)
        return response
