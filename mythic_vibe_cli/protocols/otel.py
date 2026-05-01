"""OpenTelemetry exporter (PH-16 Slice 16.4).

Opt-in OTLP tracing for every CLI command. The integration is
deliberately tiny: we expose a context manager
:func:`command_span` that wraps a CLI invocation and emits a
span when the OpenTelemetry SDK is installed AND the env flag
is on.

Default behaviour: when the dep isn't installed OR
``MYTHIC_OTEL_ENABLED`` is unset, :func:`command_span` is a
zero-cost no-op (no tracer construction, no span emission).
The hot path stays clean for operators who never enable
tracing.

Cross-platform: pure stdlib on the must-work path; OTLP
exporter is the only optional dep.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator


OTEL_ENABLED_ENV = "MYTHIC_OTEL_ENABLED"
INSTALL_HINT = (
    "Install with `pip install mythic-vibe[otel]` (or "
    "`pip install opentelemetry-api opentelemetry-sdk "
    "opentelemetry-exporter-otlp-proto-http`)."
)
_TRUTHY = {"1", "true", "yes", "on"}


def is_otel_enabled() -> bool:
    """Read :data:`OTEL_ENABLED_ENV`. Empty / unset / falsy →
    ``False``. Operators must explicitly opt in."""
    raw = os.environ.get(OTEL_ENABLED_ENV, "").strip().lower()
    return raw in _TRUTHY


@dataclass
class OtelStatus:
    """Diagnostic snapshot. Returned by :func:`status` for the
    ``mythic-vibe protocols otel-status`` introspection command.
    """

    enabled_env: bool
    sdk_available: bool
    notes: list[str] = field(default_factory=list)

    @property
    def active(self) -> bool:
        return self.enabled_env and self.sdk_available

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled_env": self.enabled_env,
            "sdk_available": self.sdk_available,
            "active": self.active,
            "notes": list(self.notes),
        }


def _try_import_otel() -> Any | None:
    """Best-effort try-import. Returns the
    :mod:`opentelemetry.trace` module when the SDK is
    installed, else ``None``."""
    try:
        from opentelemetry import trace  # type: ignore[import-not-found]
    except ImportError:
        return None
    return trace


def status() -> OtelStatus:
    """One-shot diagnostic — used by the ``mythic-vibe protocols``
    introspection command + tests."""
    enabled = is_otel_enabled()
    sdk = _try_import_otel()
    notes: list[str] = []
    if not enabled:
        notes.append(
            f"set {OTEL_ENABLED_ENV}=1 to enable OpenTelemetry export"
        )
    if sdk is None:
        notes.append(f"OpenTelemetry SDK not installed. {INSTALL_HINT}")
    if enabled and sdk is not None:
        notes.append("OTLP tracing active for every CLI command")
    return OtelStatus(
        enabled_env=enabled,
        sdk_available=sdk is not None,
        notes=notes,
    )


@contextmanager
def command_span(
    command: str,
    *,
    attributes: dict[str, Any] | None = None,
) -> Iterator[None]:
    """Wrap a CLI command in an OpenTelemetry span. When the SDK
    isn't installed OR ``MYTHIC_OTEL_ENABLED`` is unset, this is
    a zero-cost no-op (no tracer construction, no span emission).

    Usage::

        with command_span("status", attributes={"path": str(root)}):
            return cmd_status(args)

    Errors raised inside the block are re-raised — the span
    captures them via OpenTelemetry's standard
    ``record_exception`` API when the SDK is active.
    """
    if not is_otel_enabled():
        yield
        return

    trace_module = _try_import_otel()
    if trace_module is None:
        yield
        return

    tracer = trace_module.get_tracer("mythic_vibe_cli", "0.1.0")
    span_attributes = dict(attributes or {})
    span_attributes.setdefault("mythic.command", command)
    with tracer.start_as_current_span(
        f"mythic_vibe.{command}",
        attributes=span_attributes,
    ) as span:
        try:
            yield
        except Exception as exc:
            try:
                span.record_exception(exc)
                # Map to ERROR status if the SDK exposes it.
                status_module = getattr(trace_module, "Status", None)
                status_code = getattr(trace_module, "StatusCode", None)
                if status_module is not None and status_code is not None:
                    span.set_status(status_module(status_code.ERROR))
            except Exception:  # noqa: BLE001 — never let span recording crash callers
                pass
            raise


__all__ = [
    "INSTALL_HINT",
    "OTEL_ENABLED_ENV",
    "OtelStatus",
    "command_span",
    "is_otel_enabled",
    "status",
]
