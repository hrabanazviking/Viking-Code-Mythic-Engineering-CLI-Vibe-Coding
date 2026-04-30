"""Routing runtime — fallback orchestration (PH-08 slice 8.3).

Given a slice-8.1 :class:`RouteDecision`, walk the primary
provider plus the ordered fallback chain until one succeeds.

A "failure" is one of:

- the provider isn't configured (``ProviderStatus.configured ==
  False``);
- the provider's ``run`` raises any ``Exception`` (Ollama's
  ``ConnectionError``, OpenAI's ``URLError``, etc.).

Every attempt — successful or not — is recorded in
``mythic/ai/provider_calls.jsonl`` under a ``routing_attempt``
top-level key so operators can audit which fallbacks fired and
why. The final fallback is **always** ``copy-paste``: it requires
no keys / no daemon / no network and can't fail.

The runtime is provider-agnostic — it consumes a callable that
maps a provider name to an ``AIProvider`` instance (typically the
slice 6-era ``ProviderRegistry.providers().get``). That keeps it
easy to mock in tests without standing up a registry.

Cross-platform: stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .providers.base import AIProvider, ProviderResponse, write_provider_log
from .router import RouteDecision


@dataclass(frozen=True)
class FallbackAttempt:
    """One step of the fallback walk. Records what was tried, what
    happened, and why we moved on (or stopped)."""

    provider: str
    succeeded: bool
    error: str = ""
    skipped_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "succeeded": self.succeeded,
            "error": self.error,
            "skipped_reason": self.skipped_reason,
        }


@dataclass(frozen=True)
class FallbackResult:
    """Wrapper returned by :func:`run_with_fallback`. ``response``
    is the chosen provider's :class:`ProviderResponse` (always
    populated — copy-paste guarantees a final success). ``attempts``
    captures every step for audit / TUI surfacing."""

    response: ProviderResponse
    used_provider: str
    primary_provider: str
    attempts: tuple[FallbackAttempt, ...] = field(default_factory=tuple)

    @property
    def fell_back(self) -> bool:
        return self.used_provider != self.primary_provider

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_provider": self.primary_provider,
            "used_provider": self.used_provider,
            "fell_back": self.fell_back,
            "attempts": [a.to_dict() for a in self.attempts],
            "response": {
                "provider": self.response.provider,
                "model": self.response.model,
                "content": self.response.content,
                "packet_id": self.response.packet_id,
                "dry_run": self.response.dry_run,
                "usage": dict(self.response.usage),
                "metadata": dict(self.response.metadata),
            },
        }


ProviderResolver = Callable[[str], AIProvider | None]
"""Callable that maps a provider name to a registry entry, or
``None`` if the name isn't recognised."""


def _coerce_chain(decision: RouteDecision) -> tuple[str, ...]:
    """Build the ordered "try-this" list: primary → fallbacks.
    Always appends ``copy-paste`` at the very end if it isn't
    already present so a complete failure is impossible (the
    copy-paste provider needs no keys / no daemon)."""
    chain: list[str] = [decision.provider]
    for name in decision.fallbacks:
        if name and name not in chain:
            chain.append(name)
    if "copy-paste" not in chain:
        chain.append("copy-paste")
    return tuple(chain)


def _record_attempt(
    root: Any,
    decision: RouteDecision,
    attempt: FallbackAttempt,
    *,
    packet_id: str = "",
) -> None:
    """Write a ``routing_attempt`` entry into provider_calls.jsonl
    so the slice 6.5 telemetry reader and PH-08 audits can see each
    fallback step."""
    write_provider_log(
        root,
        {
            "routing_attempt": True,
            "from_provider": decision.provider,
            "to_provider": attempt.provider,
            "role": decision.role,
            "task_type": decision.task_type,
            "packet_id": packet_id,
            "succeeded": attempt.succeeded,
            "error": attempt.error,
            "skipped_reason": attempt.skipped_reason,
        },
    )


def run_with_fallback(
    decision: RouteDecision,
    packet: object,
    *,
    resolver: ProviderResolver,
    root: Any = None,
    dry_run: bool = False,
) -> FallbackResult:
    """Try the decision's primary provider, then each fallback in
    order, until one succeeds. Always returns a
    :class:`FallbackResult` — copy-paste guarantees a final-success
    leg.

    Args:
        decision: The slice 8.1 :class:`RouteDecision`.
        packet: The packet payload — same shape providers already
            accept via ``provider.run``.
        resolver: Callable that maps a provider name to a registry
            entry. Typically ``lambda n: registry.providers().get(n)``.
        root: Project root passed through to ``write_provider_log``
            so the routing-attempt entries land in the right ledger.
        dry_run: Forwarded to each provider's ``run`` call.
    """
    chain = _coerce_chain(decision)
    attempts: list[FallbackAttempt] = []

    last_response: ProviderResponse | None = None
    used_provider = ""

    for name in chain:
        provider = resolver(name)
        if provider is None:
            attempt = FallbackAttempt(
                provider=name,
                succeeded=False,
                skipped_reason="unknown provider name",
            )
            attempts.append(attempt)
            _record_attempt(root, decision, attempt)
            continue

        # Skip clearly-misconfigured providers without invoking
        # them (saves a urllib timeout per skipped fallback).
        # copy-paste is always considered configured by design.
        try:
            status = provider.validate_config()
        except Exception as exc:  # noqa: BLE001 — provider misbehaving shouldn't crash routing
            attempt = FallbackAttempt(
                provider=name,
                succeeded=False,
                error=f"validate_config raised: {exc}",
            )
            attempts.append(attempt)
            _record_attempt(root, decision, attempt)
            continue
        if not status.configured and name != "copy-paste":
            attempt = FallbackAttempt(
                provider=name,
                succeeded=False,
                skipped_reason="provider not configured",
            )
            attempts.append(attempt)
            _record_attempt(root, decision, attempt)
            continue

        try:
            response = provider.run(packet, dry_run=dry_run)
        except Exception as exc:  # noqa: BLE001 — by design: any failure falls forward
            attempt = FallbackAttempt(
                provider=name,
                succeeded=False,
                error=str(exc) or type(exc).__name__,
            )
            attempts.append(attempt)
            _record_attempt(root, decision, attempt)
            continue

        # Success.
        attempt = FallbackAttempt(provider=name, succeeded=True)
        attempts.append(attempt)
        _record_attempt(root, decision, attempt, packet_id=response.packet_id)
        last_response = response
        used_provider = name
        break

    if last_response is None:
        # This should be unreachable (copy-paste is always in the
        # chain and always succeeds), but keep a defensive
        # construction so the function's return type stays honest.
        # Build a minimal copy-paste-shaped placeholder.
        last_response = ProviderResponse(
            provider="copy-paste",
            model="manual",
            content=str(packet),
            packet_id="manual",
            dry_run=dry_run,
            usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            metadata={
                "source": "fallback-runtime-defensive",
                "reason": "no provider in chain succeeded",
            },
        )
        used_provider = "copy-paste"

    return FallbackResult(
        response=last_response,
        used_provider=used_provider,
        primary_provider=decision.provider,
        attempts=tuple(attempts),
    )


__all__ = [
    "FallbackAttempt",
    "FallbackResult",
    "ProviderResolver",
    "run_with_fallback",
]


# Internal helper used elsewhere in the codebase.
def _route_chain(decision: RouteDecision) -> Iterable[str]:
    """Public-ish helper for tests / introspection — returns the
    ordered chain :func:`run_with_fallback` would walk."""
    return _coerce_chain(decision)
