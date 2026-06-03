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

import importlib
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
    object, or ``None`` if the package isn't on ``sys.path``.

    Phase F.2 2026-05-02 (audit remediation, finding #8): the canonical
    WYRD package is actually published under the name ``wyrdforge``
    (per ``pyproject.toml`` of WYRD-Protocol HEAD on 2026-05-02 — the
    legacy ``yggdrasil`` name was an aspirational alias that was never
    published). The provider continues to try-import ``yggdrasil``
    first to honour the legacy path; ``wyrdforge`` is tried as a
    fallback in :func:`_try_import_wyrdforge`. Both modules are kept
    available so the operator can install whichever one their
    deployment ships."""
    try:
        return importlib.import_module("yggdrasil")
    except ImportError:
        return None


def _try_import_wyrdforge() -> Any | None:
    """Best-effort try-import for the canonical published WYRD
    package. Returns the ``wyrdforge`` module object, or ``None``
    when the package isn't on ``sys.path``. Phase F.2 (additive)."""
    try:
        return importlib.import_module("wyrdforge")
    except ImportError:
        return None


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
        # Phase F.2 2026-05-02 (audit remediation, finding #8):
        # try the canonical ``wyrdforge`` first, then fall back to
        # the legacy ``yggdrasil`` import. Either resolves to a
        # usable router for the dispatch path; whichever is on
        # sys.path wins. ``self._module`` carries the resolved one;
        # the dispatch helper records which entry point fired in
        # the response metadata.
        self._module = _try_import_wyrdforge() or _try_import_yggdrasil()

    def validate_config(self) -> ProviderStatus:
        details: list[str] = []
        flag_on = is_island_enabled()
        details.append(
            f"feature flag {ISLAND_ENABLED_ENV}={'on' if flag_on else 'off'}"
        )
        if self._module is None:
            details.append(
                "yggdrasil / wyrdforge package not installed "
                "(try-import failed for both)"
            )
            details.append(
                "Install hint: pip install wyrdforge "
                "(canonical WYRD-Protocol package) — or pip install "
                "yggdrasil if using Volmarr's legacy alias"
            )
            return ProviderStatus(configured=False, details=details)
        # Identify which package resolved so operators can see it.
        module_name = getattr(self._module, "__name__", "<unknown>")
        details.append(f"{module_name} package import OK")
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

        # Real path: dispatch into the resolved router. The adapter
        # is intentionally narrow — we only call a
        # `route(prompt: str) -> str` shape (or one of its
        # documented siblings) and accept whatever the upstream
        # package returns. Future slices can widen the contract
        # once the upstream API stabilises.
        try:
            content, entry_point_label = _invoke_yggdrasil(self._module, view.text)
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
                # Phase F.2 2026-05-02 (audit remediation, #8): record
                # which package + entry point fired so operators can
                # tell at a glance whether wyrdforge / yggdrasil /
                # legacy probe path was used.
                "entry_point": entry_point_label,
            },
        )


def _invoke_yggdrasil(module: Any, prompt: str) -> tuple[str, str]:
    """Dispatch into the resolved router and return
    ``(response_text, entry_point_label)``.

    Phase F.2 2026-05-02 (audit remediation, finding #8): the entry-
    point list was reorganised into a documented tuple of
    ``(attribute_path, label)`` candidates so operators can see at
    a glance which shapes the adapter expects. Both ``wyrdforge``
    (the canonical WYRD-Protocol package, verified against HEAD on
    2026-05-02) and ``yggdrasil`` (legacy alias) are accepted —
    the candidate list applies to whichever module
    ``__post_init__`` resolved.

    The legacy speculative shapes (``route``, ``router.route``,
    ``ask``) are **preserved as fallbacks** per the additive-only
    rule. Operators wrapping wyrdforge's class-based Oracle /
    TurnLoop machinery in a top-level ``route(prompt)`` callable
    get caught by the first candidate; older callers / forks that
    expose ``ask`` continue to work.

    Raises :class:`AttributeError` only when none of the documented
    candidates resolve. The caller surfaces the gap via
    ``metadata["error"]``.
    """
    module_name = getattr(module, "__name__", "<unknown>")
    candidates = (
        # Documented top-level entry point operators wrap their
        # router behind. wyrdforge users typically write a
        # ``def route(prompt: str) -> str`` shim that wraps
        # ``Oracle.query`` or ``TurnLoop.advance``; yggdrasil's
        # original spec also used this name.
        ("route", "route"),
        # Documented sub-module router shape.
        ("router.route", "router.route"),
        # Legacy aliases preserved per additive rule.
        ("ask", "ask"),
    )
    for attr_path, label in candidates:
        target: Any = module
        for piece in attr_path.split("."):
            target = getattr(target, piece, None)
            if target is None:
                break
        if callable(target):
            return str(target(prompt)), f"{module_name}.{label}"
    raise AttributeError(
        f"{module_name} package does not expose a known entry point "
        f"(tried: {', '.join(label for _, label in candidates)}). "
        "Install wyrdforge (canonical WYRD-Protocol package) and "
        "expose a top-level `route(prompt)->str` callable, or use "
        "the legacy yggdrasil alias with the same shape."
    )


__all__ = [
    "ISLAND_ENABLED_ENV",
    "YggdrasilProvider",
    "is_island_enabled",
    # Phase F.2 2026-05-02: exported for direct testing / re-use.
    "_try_import_wyrdforge",
    "_try_import_yggdrasil",
]
