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
            content, entry_point_label = _invoke_thoughtforge(
                self._module, view.text
            )
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
                # Phase F.2 2026-05-02 (audit remediation, #8): record
                # which entry point was used so operators can see at a
                # glance whether the documented primary path or the
                # legacy fallback fired.
                "entry_point": entry_point_label,
            },
        )


def _invoke_thoughtforge(module: Any, prompt: str) -> tuple[str, str]:
    """Dispatch into the thoughtforge package and return
    ``(response_text, entry_point_label)``.

    Phase F.2 2026-05-02 (audit remediation, finding #8): the
    documented primary entry point is now used first —
    ``thoughtforge.cognition.ThoughtForgeCore`` instantiated with
    default config, then ``.think(prompt)`` returning a
    ``FinalResponseRecord`` whose ``.text`` field carries the
    response (verified against MindSpark_ThoughtForge HEAD on
    2026-05-02; ``ThoughtForgeCore`` is exported from
    ``thoughtforge.cognition.__init__`` as part of the public API).

    The legacy speculative probe loop is **preserved as a fallback**
    per the additive-only rule, so any future / fork variant of the
    package exposing a top-level ``plan(prompt)`` / ``ask(prompt)``
    callable still works without code change.

    Raises :class:`AttributeError` only when neither the documented
    primary path nor any legacy candidate resolves — the adapter's
    caller then reports the contract gap via ``metadata["error"]``.
    """
    # ---- Documented primary path: ThoughtForgeCore.think() -----------
    # Resolved through ``thoughtforge.cognition`` (preferred) with a
    # fallback through ``thoughtforge.cognition.core``. Only the
    # AttributeError / ImportError outcomes fall through to the
    # legacy probes — real runtime errors (config / db missing) are
    # caught by the outer try/except in the provider's ``run()`` and
    # reported faithfully to the operator.
    core_cls = _resolve_thoughtforge_core_class(module)
    if core_cls is not None:
        core = core_cls()
        record = core.think(prompt)
        text = getattr(record, "text", None)
        if isinstance(text, str):
            return text, "thoughtforge.cognition.ThoughtForgeCore.think"
        # If `think()` returned something other than a record-with-text,
        # fall through to legacy probes — the modern API contract was
        # not honoured, possibly an older fork.

    # ---- Legacy speculative probe loop (preserved fallback) ----------
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
            return str(target(prompt)), f"legacy:thoughtforge.{attr_path}"
    raise AttributeError(
        "thoughtforge package does not expose a documented entry "
        "point. Tried documented: thoughtforge.cognition.ThoughtForgeCore.think; "
        f"legacy: {', '.join(candidates)}."
    )


def _resolve_thoughtforge_core_class(module: Any) -> Any | None:
    """Locate ``ThoughtForgeCore`` from the thoughtforge package.

    Tries (in order): ``module.cognition.ThoughtForgeCore`` (the
    public re-export from ``cognition/__init__.py`` if cognition is
    already imported), then a direct
    ``from thoughtforge.cognition import core`` fallback to trigger
    the sub-package import (since ``import thoughtforge`` alone does
    not eagerly import sub-packages).

    Returns the class or ``None`` if neither resolves. The fallback
    direct import is **gated on ``module.__name__ == "thoughtforge"``**
    so test fakes (``_Empty()``, ``MagicMock()``, etc.) don't
    accidentally pull in the real thoughtforge package — only the
    operator's chosen module is honoured for resolution."""
    cognition_pkg = getattr(module, "cognition", None)
    if cognition_pkg is not None:
        cls = getattr(cognition_pkg, "ThoughtForgeCore", None)
        if cls is not None:
            return cls
    # Fallback: only trigger the direct sub-package import when
    # ``module`` is in fact the real ``thoughtforge`` package. For
    # any other module (test fakes, alternative forks), we honour
    # what the caller passed in and don't sneak around behind their
    # back.
    if getattr(module, "__name__", "") != "thoughtforge":
        return None
    try:
        from thoughtforge.cognition import core as _tf_core  # type: ignore[import-not-found]
    except ImportError:
        return None
    return getattr(_tf_core, "ThoughtForgeCore", None)


__all__ = [
    "INSTALL_HINT",
    "ISLAND_ENABLED_ENV",
    "MindSparkProvider",
    "is_island_enabled",
]
