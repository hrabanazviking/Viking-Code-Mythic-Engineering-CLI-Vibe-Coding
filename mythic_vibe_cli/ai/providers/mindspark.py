"""MindSpark island adapter (PH-09 Slice 9.2).

Optional Planner-agent backend that try-imports the
``thoughtforge`` package — Volmarr's MindSpark ThoughtForge
project, a universal cognitive enhancement layer (sovereign
offline RAG + TurboQuant inference + deterministic cognition
scaffolds + fragment salvage).

Per ADR-0002 (no-direct-vendor-imports) and ADR-0006 (this
adapter's boundary), this module **never** imports from any
in-tree vendored MindSpark snapshot. It only resolves whatever
``thoughtforge`` package the operator's ``sys.path`` / pip env
makes available.

Default-disabled. Even when the dep resolves, the adapter is a
stub-only no-op until the operator sets
``MYTHIC_ISLAND_MINDSPARK_ENABLED=1``.

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


ISLAND_ENABLED_ENV = "MYTHIC_ISLAND_MINDSPARK_ENABLED"
INSTALL_HINT = (
    "Install with `pip install thoughtforge` "
    "(or `pip install mythic-vibe[mindspark]` once the extra is published)."
)
_TRUTHY = {"1", "true", "yes", "on"}


def is_island_enabled() -> bool:
    raw = os.environ.get(ISLAND_ENABLED_ENV, "").strip().lower()
    return raw in _TRUTHY


def _try_import_thoughtforge() -> Any | None:
    try:
        import thoughtforge  # type: ignore[import-not-found]
    except ImportError:
        return None
    return thoughtforge


@dataclass
class MindSparkProvider:
    """Planner-agent biased adapter that delegates planning /
    cognition-scaffolding tasks to MindSpark when both the dep is
    installed AND the feature flag is on."""

    name: str = "mindspark"
    model: str = "thoughtforge-planner"
    root: Any = None
    _module: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._module = _try_import_thoughtforge()

    def validate_config(self) -> ProviderStatus:
        details: list[str] = []
        flag_on = is_island_enabled()
        details.append(
            f"feature flag {ISLAND_ENABLED_ENV}={'on' if flag_on else 'off'}"
        )
        if self._module is None:
            details.append("thoughtforge package not installed (try-import failed)")
            details.append(f"Install hint: {INSTALL_HINT}")
            return ProviderStatus(configured=False, details=details)
        details.append("thoughtforge package import OK")
        if not flag_on:
            details.append(
                f"Set {ISLAND_ENABLED_ENV}=1 to enable Planner-agent routing"
            )
            return ProviderStatus(configured=False, details=details)
        return ProviderStatus(configured=True, details=details)

    def estimate(self, packet: object) -> Estimate:
        # MindSpark's inference happens locally; no per-call cost.
        return estimate_packet(packet, provider_name=self.name)

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:
        view = normalize_packet(packet)
        estimate = self.estimate(view)
        status = self.validate_config()
        if not status.configured:
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
                    "source": "mindspark-stub",
                    "configured": False,
                    "reason": "; ".join(status.details),
                },
            )

        try:
            content = _invoke_thoughtforge(self._module, view.text)
        except Exception as exc:  # noqa: BLE001 — never crash the CLI on island misbehaviour
            return ProviderResponse(
                provider=self.name,
                model=self.model,
                content="",
                packet_id=view.packet_id,
                dry_run=dry_run,
                usage={
                    "input_tokens": estimate.input_tokens,
                    "output_tokens": 0,
                    "total_tokens": estimate.input_tokens,
                },
                metadata={
                    "source": "mindspark",
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
                "source": "mindspark",
                "agent_bias": "planner",
            },
        )


def _invoke_thoughtforge(module: Any, prompt: str) -> str:
    """Best-effort dispatch into the thoughtforge package. Tries a
    couple of common shapes — ``plan(prompt)``, ``cognition.plan(prompt)``,
    ``cognition.scaffold.plan(prompt)``, ``ask(prompt)`` — and
    returns the string result. Anything else raises
    :class:`AttributeError` so the adapter's caller logs the
    contract gap into ``metadata["error"]``."""
    candidates = (
        "plan",
        "cognition.plan",
        "cognition.scaffold.plan",
        "cognition.router.route",
        "ask",
    )
    for attr_path in candidates:
        target: Any = module
        for piece in attr_path.split("."):
            target = getattr(target, piece, None)
            if target is None:
                break
        if callable(target):
            return str(target(prompt))
    raise AttributeError(
        "thoughtforge package does not expose a known entry point "
        f"(tried: {', '.join(candidates)})"
    )


__all__ = [
    "INSTALL_HINT",
    "ISLAND_ENABLED_ENV",
    "MindSparkProvider",
    "is_island_enabled",
]
