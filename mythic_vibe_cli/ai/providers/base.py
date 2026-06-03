from __future__ import annotations

import threading
from dataclasses import dataclass, field
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Protocol, Any, runtime_checkable

from urllib import request as urllib_request

from ...runtime.paths import paths_for


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
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class PacketView:
    text: str
    packet_id: str
    source: str = "inline"
    system_prompt: str | None = None
    conversation_history: list[dict[str, Any]] | None = None
    tools: list[dict[str, Any]] | None = None


class AIProvider(Protocol):
    name: str

    def validate_config(self) -> ProviderStatus:
        ...

    def estimate(self, packet: object) -> Estimate:
        ...

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:
        ...


# ---- Streaming contract (PH-06 Slice 6.4) ----------------------------


@dataclass(frozen=True)
class StreamChunk:
    """One increment of a streaming provider response.

    ``text`` is the delta — what new text this chunk contributes.
    ``done`` flags the terminal chunk (carries final usage +
    metadata; ``text`` may be empty on the terminal chunk if the
    provider already emitted the full response in earlier
    chunks).

    Streaming consumers concatenate ``text`` across chunks to
    reconstruct the full response, then read ``usage`` /
    ``metadata`` from the ``done=True`` chunk."""

    text: str = ""
    done: bool = False
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "done": self.done,
            "usage": dict(self.usage),
            "metadata": dict(self.metadata),
        }


@runtime_checkable
class StreamingProvider(Protocol):
    """Optional streaming surface. Providers that natively
    support token streaming (Ollama, OpenAI streaming mode, etc.)
    implement :meth:`run_stream` returning an iterator of
    :class:`StreamChunk`. Providers that don't support streaming
    are wrapped via :func:`single_chunk_stream` to satisfy the
    same contract."""

    name: str

    def run_stream(
        self,
        packet: object,
        *,
        dry_run: bool = False,
        cancel_event: threading.Event | None = None,
    ) -> Iterator[StreamChunk]:
        ...


def single_chunk_stream(
    provider: AIProvider,
    packet: object,
    *,
    dry_run: bool = False,
    cancel_event: threading.Event | None = None,
) -> Iterator[StreamChunk]:
    """Adapt a non-streaming provider into the streaming contract.

    Calls ``provider.run(packet, dry_run=dry_run)`` once and
    yields exactly one terminal :class:`StreamChunk` carrying
    the full content + usage + metadata.

    Honours ``cancel_event``: if the event is already set when
    we're about to invoke ``run``, we yield an empty terminal
    chunk with ``metadata["cancelled"]=True`` instead. (We
    can't interrupt a synchronous ``run()`` mid-flight from the
    outside; the event acts as a pre-flight gate.)
    """
    if cancel_event is not None and cancel_event.is_set():
        yield StreamChunk(
            text="",
            done=True,
            metadata={"cancelled": True, "source": "single_chunk_stream"},
        )
        return

    response = provider.run(packet, dry_run=dry_run)
    yield StreamChunk(
        text=response.content,
        done=True,
        usage=dict(response.usage),
        metadata={
            **dict(response.metadata),
            "source": "single_chunk_stream",
            "wraps_provider": getattr(provider, "name", ""),
        },
    )


def stream_provider_response(
    provider: AIProvider,
    packet: object,
    *,
    dry_run: bool = False,
    cancel_event: threading.Event | None = None,
) -> Iterator[StreamChunk]:
    """Top-level streaming entry point. Routes through the
    provider's native ``run_stream`` if available, else falls
    back to :func:`single_chunk_stream`. Callers always get a
    valid :class:`StreamChunk` iterator regardless of provider
    capability."""
    run_stream = getattr(provider, "run_stream", None)
    if callable(run_stream):
        return run_stream(packet, dry_run=dry_run, cancel_event=cancel_event)
    return single_chunk_stream(
        provider, packet, dry_run=dry_run, cancel_event=cancel_event
    )


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
            tools=packet.get("tools"),
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
    # PH-24.5: scheme-validated before urlopen.
    from ...runtime.url_guard import assert_safe_url
    assert_safe_url(url)
    body = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(url, data=body, headers=headers, method="POST")
    with urllib_request.urlopen(req, timeout=60) as resp:  # noqa: S310 — scheme validated above
        data = resp.read().decode("utf-8", errors="replace")
    parsed = json.loads(data)
    if not isinstance(parsed, dict):
        raise ValueError("Provider response was not a JSON object")
    return parsed


def timed_post_json(
    url: str, payload: dict[str, Any], headers: dict[str, str]
) -> tuple[dict[str, Any], float]:
    """Wrap :func:`post_json` with a ``time.perf_counter`` round-trip
    measurement. Returns ``(parsed, latency_ms)`` where ``latency_ms``
    is rounded to two decimal places.

    PH-06 slice 6.5: the telemetry extension. The latency value is
    written into ``provider_calls.jsonl`` so the slice 6.5 reader
    can surface latency / cost trends across providers.
    """
    import time as _time

    start = _time.perf_counter()
    parsed = post_json(url, payload, headers)
    latency_ms = round((_time.perf_counter() - start) * 1000.0, 2)
    return parsed, latency_ms


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
    return paths_for(root).provider_calls_log


def write_provider_log(root: Path | None, payload: dict[str, Any]) -> None:
    path = provider_log_path(root)
    if path is None:
        return
    try:
        line = json.dumps(redact_value(payload), ensure_ascii=False) + "\n"
    except (TypeError, ValueError):
        line = json.dumps(
            {"provider_log_error": "payload was not JSON serializable"},
            ensure_ascii=False,
        ) + "\n"
    try:
        from ...runtime.cross_process_lock import cross_process_lock

        path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = path.with_suffix(path.suffix + ".lock")
        with cross_process_lock(lock_path, deadline=5.0):
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)
    except OSError:
        return
