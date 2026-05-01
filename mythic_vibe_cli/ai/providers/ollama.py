"""Ollama provider adapter (PH-06 slice 6.1).

Talks to a local Ollama daemon via stdlib HTTP — no third-party
dependency. The official ``ollama`` Python client is intentionally
not required; the adapter mirrors the slice-1.x anthropic / openai
adapters so the surface stays consistent.

Key behaviours:

- Honours ``OLLAMA_HOST`` env var (forms: ``host``, ``host:port``,
  or ``http(s)://host:port``).
- Default model is ``OLLAMA_MODEL`` env var or ``llama3.2``.
- ``validate_config`` runs a daemon-up probe (slice 6.2) and
  reports the endpoint + reachability in ``details``.
- ``run`` measures call latency and writes it into the
  ``provider_calls.jsonl`` ledger (slice 6.5 telemetry hook).
- ``run`` degrades gracefully when the daemon is not reachable —
  raises a clean ``ConnectionError`` instead of a generic urllib
  exception so callers can surface a helpful message.

Cross-platform: stdlib only (``urllib.request``, ``time``, ``os``).
No platform branches.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterator

from ..ollama_health import (
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_PORT,
    OllamaHealth,
    _resolve_endpoint,
    check_ollama_health,
)
from .base import (
    Estimate,
    ProviderResponse,
    ProviderStatus,
    StreamChunk,
    estimate_cost,
    estimate_packet,
    normalize_packet,
    utc_now,
    write_provider_log,
)


OLLAMA_MODEL_ENV = "OLLAMA_MODEL"
DEFAULT_MODEL = "llama3.2"
DEFAULT_REQUEST_TIMEOUT_S = 120.0


@dataclass
class OllamaProvider:
    name: str = "ollama"
    model: str = ""
    root: object | None = None

    def _resolved_model(self) -> str:
        if self.model:
            return self.model
        env_model = os.environ.get(OLLAMA_MODEL_ENV, "").strip()
        return env_model or DEFAULT_MODEL

    def _endpoint(self) -> str:
        host, port = _resolve_endpoint(None, None)
        return f"http://{host}:{port}"

    def validate_config(self) -> ProviderStatus:
        """Daemon-up probe. The Ollama daemon needs no API key — the
        configured/unconfigured signal here is whether it's
        reachable, not whether a credential exists."""
        health: OllamaHealth = check_ollama_health()
        details = list(health.details)
        details.insert(0, f"endpoint: {health.endpoint}")
        if not health.reachable and health.error:
            details.append(f"error: {health.error}")
        details.append(f"model (default): {self._resolved_model()}")
        return ProviderStatus(configured=health.reachable, details=details)

    def estimate(self, packet: object) -> Estimate:
        return estimate_packet(packet, provider_name=self.name)

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:
        view = normalize_packet(packet)
        estimate = self.estimate(view)
        model = self._resolved_model()
        endpoint = self._endpoint()

        log_payload: dict[str, object] = {
            "timestamp": utc_now(),
            "provider": self.name,
            "model": model,
            "packet_id": view.packet_id,
            "dry_run": dry_run,
            "estimate": dict(estimate.__dict__),
            "request": {"input": view.text, "endpoint": endpoint},
        }

        if dry_run:
            response = ProviderResponse(
                provider=self.name,
                model=model,
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
                    "endpoint": endpoint,
                    "dry_run": True,
                },
            )
            log_payload["response"] = {"content": view.text, "dry_run": True}
            log_payload["latency_ms"] = 0.0
            write_provider_log(self.root, log_payload)
            return response

        # Live call: probe first so we fail with a useful message
        # instead of a generic urllib error when the daemon is down.
        health = check_ollama_health()
        if not health.reachable:
            log_payload["latency_ms"] = 0.0
            log_payload["error"] = (
                f"daemon unreachable at {health.endpoint}: {health.error or 'no connection'}"
            )
            write_provider_log(self.root, log_payload)
            raise ConnectionError(
                f"Ollama daemon unreachable at {health.endpoint}. "
                "Start it with `ollama serve` (or your platform's equivalent)."
            )

        request_payload = {
            "model": model,
            "prompt": view.text,
            "stream": False,
        }
        body = json.dumps(request_payload).encode("utf-8")
        request = urllib.request.Request(
            f"{health.endpoint}/api/generate",
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "mythic-vibe-cli",
            },
            method="POST",
        )

        start = time.perf_counter()
        try:
            with urllib.request.urlopen(
                request, timeout=DEFAULT_REQUEST_TIMEOUT_S
            ) as http_resp:
                raw = http_resp.read().decode("utf-8", errors="replace")
            response_payload = json.loads(raw)
            if not isinstance(response_payload, dict):
                raise ValueError("Ollama response was not a JSON object")
        except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
            latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
            log_payload["latency_ms"] = latency_ms
            log_payload["error"] = str(exc) or type(exc).__name__
            write_provider_log(self.root, log_payload)
            raise

        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
        content = str(response_payload.get("response", ""))
        prompt_eval_count = int(response_payload.get("prompt_eval_count", 0) or 0)
        eval_count = int(response_payload.get("eval_count", 0) or 0)
        usage = {
            "input_tokens": prompt_eval_count or estimate.input_tokens,
            "output_tokens": eval_count or estimate.output_tokens,
            "total_tokens": (prompt_eval_count + eval_count)
            or (estimate.input_tokens + estimate.output_tokens),
        }
        response = ProviderResponse(
            provider=self.name,
            model=model,
            content=content,
            packet_id=view.packet_id,
            dry_run=False,
            usage=usage,
            metadata={
                "endpoint": health.endpoint,
                "source": view.source,
                "estimated_cost_usd": estimate.cost_usd,
                "observed_cost_usd": estimate_cost(
                    self.name,
                    usage["input_tokens"],
                    usage["output_tokens"],
                ),
                "total_duration_ns": response_payload.get("total_duration"),
                "load_duration_ns": response_payload.get("load_duration"),
                "eval_duration_ns": response_payload.get("eval_duration"),
                "done_reason": response_payload.get("done_reason"),
            },
        )
        log_payload["latency_ms"] = latency_ms
        log_payload["response"] = {
            "content": content,
            "usage": usage,
            "endpoint": health.endpoint,
        }
        write_provider_log(self.root, log_payload)
        return response


    def run_stream(
        self,
        packet: object,
        *,
        dry_run: bool = False,
        cancel_event: threading.Event | None = None,
    ) -> Iterator[StreamChunk]:
        """PH-06 Slice 6.4 — native streaming via Ollama's NDJSON
        ``/api/generate`` mode.

        Yields one :class:`StreamChunk` per token (``done=False``,
        ``text=delta``) until the daemon returns its terminal
        ``done: true`` packet — that becomes a final
        :class:`StreamChunk` with empty ``text`` plus the full
        ``usage`` + ``metadata`` payload.

        Cancellation: caller passes a ``threading.Event``; the
        method checks it between chunks and on set, closes the
        HTTP response, yields a terminal chunk with
        ``metadata["cancelled"]=True``, and returns.

        Dry-run path mirrors :meth:`run` — yields a single
        terminal chunk carrying the packet text echoed back, no
        daemon call.
        """
        view = normalize_packet(packet)
        estimate = self.estimate(view)
        model = self._resolved_model()
        endpoint = self._endpoint()

        log_payload: dict[str, object] = {
            "timestamp": utc_now(),
            "provider": self.name,
            "model": model,
            "packet_id": view.packet_id,
            "dry_run": dry_run,
            "stream": True,
            "estimate": dict(estimate.__dict__),
            "request": {"input": view.text, "endpoint": endpoint},
        }

        if dry_run:
            log_payload["latency_ms"] = 0.0
            log_payload["response"] = {"content": view.text, "dry_run": True}
            write_provider_log(self.root, log_payload)
            yield StreamChunk(
                text=view.text,
                done=True,
                usage={
                    "input_tokens": estimate.input_tokens,
                    "output_tokens": estimate.output_tokens,
                    "total_tokens": estimate.input_tokens + estimate.output_tokens,
                },
                metadata={
                    "source": view.source,
                    "endpoint": endpoint,
                    "estimated_cost_usd": estimate.cost_usd,
                    "dry_run": True,
                    "stream": True,
                },
            )
            return

        if cancel_event is not None and cancel_event.is_set():
            log_payload["latency_ms"] = 0.0
            log_payload["response"] = {"cancelled": True}
            write_provider_log(self.root, log_payload)
            yield StreamChunk(
                text="",
                done=True,
                metadata={"cancelled": True, "source": "ollama-pre-flight"},
            )
            return

        health = check_ollama_health()
        if not health.reachable:
            log_payload["latency_ms"] = 0.0
            log_payload["error"] = (
                f"daemon unreachable at {health.endpoint}: "
                f"{health.error or 'no connection'}"
            )
            write_provider_log(self.root, log_payload)
            raise ConnectionError(
                f"Ollama daemon unreachable at {health.endpoint}. "
                "Start it with `ollama serve` (or your platform's equivalent)."
            )

        request_payload = {
            "model": model,
            "prompt": view.text,
            "stream": True,
        }
        body = json.dumps(request_payload).encode("utf-8")
        request = urllib.request.Request(
            f"{health.endpoint}/api/generate",
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "mythic-vibe-cli",
            },
            method="POST",
        )

        start = time.perf_counter()
        accumulated_text: list[str] = []
        final_metadata: dict[str, object] = {}
        usage = {
            "input_tokens": estimate.input_tokens,
            "output_tokens": estimate.output_tokens,
            "total_tokens": estimate.input_tokens + estimate.output_tokens,
        }
        cancelled = False

        try:
            http_resp = urllib.request.urlopen(
                request, timeout=DEFAULT_REQUEST_TIMEOUT_S
            )
        except (OSError, urllib.error.URLError) as exc:
            latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
            log_payload["latency_ms"] = latency_ms
            log_payload["error"] = str(exc) or type(exc).__name__
            write_provider_log(self.root, log_payload)
            raise

        try:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    cancelled = True
                    break
                line = http_resp.readline()
                if not line:
                    break
                try:
                    payload = json.loads(line.decode("utf-8", errors="replace"))
                except json.JSONDecodeError:
                    continue
                if not isinstance(payload, dict):
                    continue
                delta = str(payload.get("response", "") or "")
                if delta:
                    accumulated_text.append(delta)
                    yield StreamChunk(text=delta, done=False)
                if payload.get("done"):
                    prompt_eval_count = int(payload.get("prompt_eval_count", 0) or 0)
                    eval_count = int(payload.get("eval_count", 0) or 0)
                    usage = {
                        "input_tokens": prompt_eval_count or estimate.input_tokens,
                        "output_tokens": eval_count or estimate.output_tokens,
                        "total_tokens": (prompt_eval_count + eval_count)
                        or (estimate.input_tokens + estimate.output_tokens),
                    }
                    final_metadata = {
                        "endpoint": health.endpoint,
                        "source": view.source,
                        "estimated_cost_usd": estimate.cost_usd,
                        "observed_cost_usd": estimate_cost(
                            self.name,
                            usage["input_tokens"],
                            usage["output_tokens"],
                        ),
                        "total_duration_ns": payload.get("total_duration"),
                        "load_duration_ns": payload.get("load_duration"),
                        "eval_duration_ns": payload.get("eval_duration"),
                        "done_reason": payload.get("done_reason"),
                    }
                    break
        finally:
            try:
                http_resp.close()
            except Exception:  # noqa: BLE001 — close failure is non-fatal
                pass

        latency_ms = round((time.perf_counter() - start) * 1000.0, 2)
        full_text = "".join(accumulated_text)

        log_payload["latency_ms"] = latency_ms
        log_payload["response"] = {
            "content": full_text,
            "usage": usage,
            "endpoint": health.endpoint,
            "cancelled": cancelled,
        }
        write_provider_log(self.root, log_payload)

        terminal_metadata = dict(final_metadata)
        terminal_metadata["cancelled"] = cancelled
        terminal_metadata.setdefault("source", view.source)
        terminal_metadata.setdefault("endpoint", health.endpoint)
        yield StreamChunk(
            text="",
            done=True,
            usage=usage,
            metadata=terminal_metadata,
        )


__all__ = [
    "DEFAULT_MODEL",
    "DEFAULT_OLLAMA_HOST",
    "DEFAULT_OLLAMA_PORT",
    "DEFAULT_REQUEST_TIMEOUT_S",
    "OLLAMA_MODEL_ENV",
    "OllamaProvider",
]
