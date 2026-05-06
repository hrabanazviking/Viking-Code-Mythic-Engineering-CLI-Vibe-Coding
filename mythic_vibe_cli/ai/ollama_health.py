"""Ollama daemon discovery (PH-06 slice 6.2).

Stdlib-only health probes for a local Ollama daemon. Used by the
slice 6.1 :class:`OllamaProvider` to short-circuit network calls
when the daemon isn't reachable, and by the slice 6.3
``mythic-vibe ai models`` subcommand to surface a clean error
instead of an opaque connection failure.

Cross-platform: pure stdlib (`socket`, `urllib.request`, `time`).
No external deps; no per-OS branches. Honours the
``OLLAMA_HOST`` environment variable so operators with a daemon
on a non-default host / port don't have to thread it through every
caller.
"""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any


DEFAULT_OLLAMA_HOST = "127.0.0.1"
DEFAULT_OLLAMA_PORT = 11434
DEFAULT_PROBE_TIMEOUT_S = 0.5
OLLAMA_HOST_ENV = "OLLAMA_HOST"


def _resolve_endpoint(
    host: str | None = None, port: int | None = None
) -> tuple[str, int]:
    """Return ``(host, port)`` honouring ``OLLAMA_HOST`` when both
    args are absent. ``OLLAMA_HOST`` may be ``host``, ``host:port``,
    or ``http(s)://host:port`` — the parser handles all three.

    Explicit args always win; the env var only fills in unset
    fields. Empty / unparseable env values fall back to defaults.
    """
    env_host: str | None = None
    env_port: int | None = None
    raw = os.environ.get(OLLAMA_HOST_ENV, "").strip()
    if raw:
        # Tolerate scheme-prefixed values (`http://localhost:11434`).
        if "://" in raw:
            try:
                parsed = urllib.parse.urlparse(raw)
                env_host = parsed.hostname or DEFAULT_OLLAMA_HOST
                env_port = parsed.port or DEFAULT_OLLAMA_PORT
            except ValueError:
                env_host = DEFAULT_OLLAMA_HOST
                env_port = DEFAULT_OLLAMA_PORT
        elif ":" in raw:
            host_part, _, port_part = raw.partition(":")
            env_host = host_part or DEFAULT_OLLAMA_HOST
            try:
                env_port = int(port_part) if port_part else DEFAULT_OLLAMA_PORT
            except ValueError:
                env_port = DEFAULT_OLLAMA_PORT
        else:
            env_host = raw
            env_port = DEFAULT_OLLAMA_PORT

    resolved_host = host if host is not None else (env_host or DEFAULT_OLLAMA_HOST)
    resolved_port = port if port is not None else (env_port or DEFAULT_OLLAMA_PORT)
    return resolved_host, int(resolved_port)


def is_ollama_daemon_up(
    host: str | None = None,
    port: int | None = None,
    *,
    timeout: float = DEFAULT_PROBE_TIMEOUT_S,
) -> bool:
    """Cheap liveness probe — opens a TCP connection and closes it.
    Returns ``True`` only on a clean connect; any error (refused,
    timeout, DNS failure) returns ``False`` without raising.
    """
    resolved_host, resolved_port = _resolve_endpoint(host, port)
    try:
        with socket.create_connection(
            (resolved_host, resolved_port), timeout=timeout
        ):
            return True
    except (OSError, socket.timeout):
        return False


@dataclass(frozen=True)
class OllamaHealth:
    """Richer probe result. ``reachable`` mirrors
    :func:`is_ollama_daemon_up` for callers that want the boolean;
    ``endpoint``, ``latency_ms``, and ``error`` add the metadata
    a UI needs to render a useful message."""

    reachable: bool
    endpoint: str
    latency_ms: float
    error: str = ""
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reachable": self.reachable,
            "endpoint": self.endpoint,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "details": list(self.details),
        }


def check_ollama_health(
    host: str | None = None,
    port: int | None = None,
    *,
    timeout: float = DEFAULT_PROBE_TIMEOUT_S,
) -> OllamaHealth:
    """Probe the daemon and time the round-trip. ``latency_ms``
    is the connect time on success, or 0 on failure."""
    resolved_host, resolved_port = _resolve_endpoint(host, port)
    endpoint = f"http://{resolved_host}:{resolved_port}"
    start = time.perf_counter()
    try:
        with socket.create_connection(
            (resolved_host, resolved_port), timeout=timeout
        ):
            latency = (time.perf_counter() - start) * 1000.0
            return OllamaHealth(
                reachable=True,
                endpoint=endpoint,
                latency_ms=round(latency, 2),
                details=[f"connected in {round(latency, 2)} ms"],
            )
    except (OSError, socket.timeout) as exc:
        return OllamaHealth(
            reachable=False,
            endpoint=endpoint,
            latency_ms=0.0,
            error=str(exc) or type(exc).__name__,
            details=[
                f"could not reach {endpoint}",
                "start the daemon with `ollama serve` (or your platform's equivalent)",
            ],
        )


def list_models(
    host: str | None = None,
    port: int | None = None,
    *,
    timeout: float = 2.0,
) -> tuple[list[dict[str, Any]], OllamaHealth]:
    """Return the daemon's installed models via ``/api/tags`` plus
    the health snapshot used to make the call.

    Returns ``([], <unreachable health>)`` when the daemon isn't up
    or the request fails — the caller can render a clean error
    using the health metadata."""
    health = check_ollama_health(host, port, timeout=timeout)
    if not health.reachable:
        return [], health
    from ..runtime.url_guard import assert_safe_url
    url = f"{health.endpoint}/api/tags"
    assert_safe_url(url)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 — scheme validated
            data = resp.read().decode("utf-8", errors="replace")
        payload = json.loads(data)
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return [], OllamaHealth(
            reachable=False,
            endpoint=health.endpoint,
            latency_ms=health.latency_ms,
            error=str(exc) or type(exc).__name__,
            details=health.details + ["/api/tags request failed"],
        )
    if not isinstance(payload, dict):
        return [], OllamaHealth(
            reachable=False,
            endpoint=health.endpoint,
            latency_ms=health.latency_ms,
            error="malformed /api/tags response",
            details=health.details,
        )
    models_raw = payload.get("models", [])
    models: list[dict[str, Any]] = []
    if isinstance(models_raw, list):
        for entry in models_raw:
            if isinstance(entry, dict):
                models.append(entry)
    return models, health


__all__ = [
    "DEFAULT_OLLAMA_HOST",
    "DEFAULT_OLLAMA_PORT",
    "DEFAULT_PROBE_TIMEOUT_S",
    "OLLAMA_HOST_ENV",
    "OllamaHealth",
    "check_ollama_health",
    "is_ollama_daemon_up",
    "list_models",
]
