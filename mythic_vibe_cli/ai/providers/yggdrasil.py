"""Yggdrasil island adapter (PH-09 Slice 9.1).

Optional Architect-agent backend that try-imports the
``yggdrasil`` package (a separate Norse cognitive-architecture
project — Volmarr's experimental router on top of Asgard /
Vanaheim / Alfheim / etc. realms).

Per ADR-0002 (no-direct-vendor-imports) and ADR-0005 (this
adapter's boundary), this module **never** imports from the
in-tree quarantined ``yggdrasil/`` directory. It only resolves
whatever Python package name ``yggdrasil`` happens to map to on
the current ``sys.path``. If nothing matches, the adapter
reports as unconfigured and never raises into the CLI.

Default-disabled: even when the dep resolves, the adapter is a
stub-only no-op until the operator sets
``MYTHIC_ISLAND_YGGDRASIL_ENABLED=1``. Same pattern as the PH-07
``MYTHIC_VOICE_TTS_ENABLED`` gate — operators opt in, never
silent activation.

Cross-platform: stdlib only on the must-work path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from .base import (
    Estimate,
    ProviderResponse,
    ProviderStatus,
    estimate_packet,
    normalize_packet,
)


ISLAND_ENABLED_ENV = "MYTHIC_ISLAND_YGGDRASIL_ENABLED"
_TRUTHY = {"1", "true", "yes", "on"}


def is_island_enabled() -> bool:
    """Read :data:`ISLAND_ENABLED_ENV`. Empty / unset / falsy values
    return ``False`` — the island stays default-disabled until the
    operator explicitly opts in."""
    raw = os.environ.get(ISLAND_ENABLED_ENV, "").strip().lower()
    return raw in _TRUTHY


def _try_import_yggdrasil() -> Any | None:
    """Best-effort try-import. Returns the ``yggdrasil`` module
    object, or ``None`` if the package isn't on ``sys.path``."""
    try:
        import yggdrasil  # type: ignore[import-not-found]
    except ImportError:
        return None
    return yggdrasil


@dataclass
class YggdrasilProvider:
    """Architect-agent biased adapter that delegates to the
    Yggdrasil router when both the package is installed AND the
    feature flag is on. Falls back to a clean "unconfigured"
    surface otherwise — never crashes the CLI."""

    name: str = "yggdrasil"
    model: str = "yggdrasil-architect"
    root: Any = None
    _module: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._module = _try_import_yggdrasil()

    def validate_config(self) -> ProviderStatus:
        details: list[str] = []
        flag_on = is_island_enabled()
        details.append(
            f"feature flag {ISLAND_ENABLED_ENV}={'on' if flag_on else 'off'}"
        )
        if self._module is None:
            details.append("yggdrasil package not installed (try-import failed)")
            details.append(
                "Install hint: pip install yggdrasil "
                "(or add to PYTHONPATH if using Volmarr's local copy)"
            )
            return ProviderStatus(configured=False, details=details)
        details.append("yggdrasil package import OK")
        if not flag_on:
            details.append(
                f"Set {ISLAND_ENABLED_ENV}=1 to enable Architect-agent routing"
            )
            return ProviderStatus(configured=False, details=details)
        return ProviderStatus(configured=True, details=details)

    def estimate(self, packet: object) -> Estimate:
        # Yggdrasil routing happens locally; cost is zero. Token
        # counts mirror the packet shape so cost-guard / fallback
        # continue to behave sensibly.
        return estimate_packet(packet, provider_name=self.name)

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:
        view = normalize_packet(packet)
        estimate = self.estimate(view)
        status = self.validate_config()
        if not status.configured:
            # Not configured → return a stub response shape rather
            # than raising. The slice 8.3 fallback runtime treats
            # "not configured" as a skip signal anyway, but keeping
            # this graceful means direct callers get a clean
            # placeholder + an error string instead of an exception.
            return ProviderResponse(
                provider=self.name,
                model=self.model,
                content="",
                packet_id=view.packet_id,
                dry_run=True,
                usage={
                    "input_tokens": estimate.input_tokens,
                    "output_tokens": 0,
                    "total_tokens": estimate.input_tokens,
                },
                metadata={
                    "source": "yggdrasil-stub",
                    "configured": False,
                    "reason": "; ".join(status.details),
                },
            )

        # Real path: dispatch into the yggdrasil router. The
        # adapter is intentionally narrow today — we only call a
        # `route(prompt: str) -> str` shape and accept whatever
        # the upstream package returns. Future slices can widen
        # the contract once the upstream API stabilises.
        try:
            content = _invoke_yggdrasil(self._module, view.text)
        except Exception as exc:  # noqa: BLE001 — never crash the CLI on island misbehaviour
            return ProviderResponse(
                provider=self.name,
                model=self.model,
                content="",
                packet_id=view.packet_id,
                dry_run=dry_run,
                usage={"input_tokens": estimate.input_tokens, "output_tokens": 0, "total_tokens": estimate.input_tokens},
                metadata={
                    "source": "yggdrasil",
                    "error": str(exc) or type(exc).__name__,
                },
            )
        return ProviderResponse(
            provider=self.name,
            model=self.model,
            content=content,
            packet_id=view.packet_id,
            dry_run=dry_run,
            usage={
                "input_tokens": estimate.input_tokens,
                "output_tokens": estimate.output_tokens,
                "total_tokens": estimate.input_tokens + estimate.output_tokens,
            },
            metadata={
                "source": "yggdrasil",
                "agent_bias": "architect",
            },
        )


def _invoke_yggdrasil(module: Any, prompt: str) -> str:
    """Best-effort dispatch into the yggdrasil package. Tries a
    couple of common entry points (``route``, ``router.route``,
    ``ask``) and returns the string result. Anything else falls
    back to ``str(module)`` so the call shape doesn't crash."""
    for attr_path in ("route", "router.route", "ask"):
        target: Any = module
        for piece in attr_path.split("."):
            target = getattr(target, piece, None)
            if target is None:
                break
        if callable(target):
            return str(target(prompt))
    raise AttributeError(
        "yggdrasil package does not expose a known entry point "
        "(tried: route, router.route, ask)"
    )


__all__ = [
    "ISLAND_ENABLED_ENV",
    "YggdrasilProvider",
    "is_island_enabled",
]
