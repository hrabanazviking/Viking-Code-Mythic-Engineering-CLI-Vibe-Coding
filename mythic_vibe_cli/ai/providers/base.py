from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, Any

from urllib import request as urllib_request


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
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PacketView:
    text: str
    packet_id: str
    source: str = "inline"


class AIProvider(Protocol):
    name: str

    def validate_config(self) -> ProviderStatus:
        ...

    def estimate(self, packet: object) -> Estimate:
        ...

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:
        ...


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{10,}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{10,}"),
    re.compile(r"(?i)\b(bearer\s+[A-Za-z0-9\-\._~\+/=]+)"),
    re.compile(r"(?i)\b(api[_-]?key\s*[:=]\s*)([^\s,;]+)"),
    re.compile(r"(?i)\b(secret|token|password)\s*[:=]\s*([^\s,;]+)"),
]

PROVIDER_PRICING_PER_1K = {
    "copy-paste": (0.0, 0.0),
    "local": (0.0, 0.0),
    "openai": (0.005, 0.015),
    "anthropic": (0.008, 0.024),
    "gemini": (0.003, 0.009),
    "openrouter": (0.005, 0.015),
}


def normalize_packet(packet: object) -> PacketView:
    if isinstance(packet, PacketView):
        return packet
    if isinstance(packet, dict):
        return PacketView(
            text=str(packet.get("text", "")),
            packet_id=str(packet.get("packet_id", "inline")),
            source=str(packet.get("source", "inline")),
        )
    return PacketView(text=str(packet), packet_id="inline", source="inline")


def redact_text(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {key: redact_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


def estimate_cost(provider_name: str | None, input_tokens: int, output_tokens: int) -> float:
    input_rate, output_rate = PROVIDER_PRICING_PER_1K.get(provider_name or "", (0.0, 0.0))
    if input_rate == 0.0 and output_rate == 0.0:
        return 0.0
    return round(((input_tokens * input_rate) + (output_tokens * output_rate)) / 1000.0, 6)


def estimate_packet(packet: object, *, provider_name: str | None = None) -> Estimate:
    view = normalize_packet(packet)
    text = view.text
    input_tokens = max(1, len(text) // 4)
    output_tokens = max(1, len(text) // 8)
    return Estimate(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=estimate_cost(provider_name, input_tokens, output_tokens),
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(url, data=body, headers=headers, method="POST")
    with urllib_request.urlopen(req, timeout=60) as resp:
        data = resp.read().decode("utf-8", errors="replace")
    parsed = json.loads(data)
    if not isinstance(parsed, dict):
        raise ValueError("Provider response was not a JSON object")
    return parsed


def extract_usage(provider_name: str, payload: dict[str, Any]) -> dict[str, int]:
    usage = payload.get("usage")
    if isinstance(usage, dict):
        input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", usage.get("inputTokens", 0)))
        output_tokens = usage.get("completion_tokens", usage.get("output_tokens", usage.get("outputTokens", 0)))
        total_tokens = usage.get("total_tokens", usage.get("totalTokens", 0))
        return {
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "total_tokens": int(total_tokens or 0),
        }

    if provider_name == "anthropic":
        usage = payload.get("usage", {})
        if isinstance(usage, dict):
            input_tokens = int(usage.get("input_tokens", 0) or 0)
            output_tokens = int(usage.get("output_tokens", 0) or 0)
            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            }

    if provider_name == "gemini":
        usage = payload.get("usageMetadata", {})
        if isinstance(usage, dict):
            input_tokens = int(usage.get("promptTokenCount", 0) or 0)
            output_tokens = int(usage.get("candidatesTokenCount", 0) or 0)
            return {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": int(usage.get("totalTokenCount", input_tokens + output_tokens) or (input_tokens + output_tokens)),
            }

    return {}


def extract_request_id(payload: dict[str, Any]) -> str | None:
    for key in ("id", "request_id", "requestId", "response_id", "responseId"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def provider_log_path(root: Path | None) -> Path | None:
    if root is None:
        return None
    return root / "mythic" / "ai" / "provider_calls.jsonl"


def write_provider_log(root: Path | None, payload: dict[str, Any]) -> None:
    path = provider_log_path(root)
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(redact_value(payload), ensure_ascii=False) + "\n")
