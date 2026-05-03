"""Plugin sandbox layer (PH-10 Slice 10.2).

Best-effort isolation around plugin hook calls:

- **Exception isolation** — every call is wrapped in try/except,
  exceptions are captured into a typed :class:`SandboxResult`
  rather than propagated. Pre-existing behaviour in the event
  bus already does this for the main hook channel; the sandbox
  formalises the contract for direct callers (e.g. the
  slice-10.6 reference plugin's tests).

- **Timing budgets (opt-in)** — when
  :envvar:`MYTHIC_PLUGIN_TIMEOUT_SEC` is set to a positive number,
  the sandbox runs the call on a worker thread and reports a
  ``timed_out=True`` result if the wall-clock deadline expires.
  The worker thread is daemon-flagged but cannot be forcibly
  killed (Python has no safe thread kill primitive); operators
  see the timeout in plugin health and can disable misbehaving
  plugins via ``mythic-vibe plugin disable``.

- **Resource-cap reporting** — on POSIX hosts, a one-shot
  :func:`probe_resource_caps` samples ``resource.getrusage`` and
  ``resource.getrlimit`` so operators can see the host's process
  limits in plugin health output. On Windows / non-POSIX hosts,
  the same call returns ``advisory_only=True`` with empty
  payload — there is no portable RLIMIT API.

Cross-platform: pure stdlib. POSIX-only paths gate behind
``hasattr(resource, ...)`` so the import never fails.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, TypeVar

if TYPE_CHECKING:
    # Phase 20.3 — circuit breaker is opt-in via the new
    # ``breaker=`` kwarg on safe_call. Imported under
    # TYPE_CHECKING so the runtime dependency is none-by-default.
    from .circuit_breaker import CircuitBreaker  # noqa: F401


T = TypeVar("T")

TIMEOUT_ENV = "MYTHIC_PLUGIN_TIMEOUT_SEC"


@dataclass(frozen=True)
class SandboxResult:
    """Typed wrapper around a plugin-hook invocation. ``value`` is
    the call's return when it succeeded; ``error`` is non-empty
    when an exception was raised; ``timed_out`` flags an enforced
    deadline expiry."""

    value: Any = None
    elapsed_ms: float = 0.0
    error: str = ""
    timed_out: bool = False
    plugin_id: str = ""

    @property
    def ok(self) -> bool:
        return not self.error and not self.timed_out

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": _safe_repr(self.value),
            "elapsed_ms": self.elapsed_ms,
            "error": self.error,
            "timed_out": self.timed_out,
            "plugin_id": self.plugin_id,
            "ok": self.ok,
        }


def _safe_repr(value: Any, *, limit: int = 200) -> str:
    """Compact repr for serialisation. Exceptions during repr()
    are contained — we never want sandbox reporting to crash on
    an exotic plugin return value."""
    try:
        text = repr(value)
    except Exception as exc:  # noqa: BLE001 — repr can crash on weird objects
        text = f"<unrepr-able: {type(value).__name__}: {exc}>"
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def resolve_timeout_sec(*, env: dict[str, str] | None = None) -> float | None:
    """Read :data:`TIMEOUT_ENV`. Returns ``None`` when unset / blank
    / non-numeric / non-positive — the sandbox treats any of those
    as "no timeout". Tests inject a fake env via the kwarg."""
    source = env if env is not None else os.environ
    raw = (source.get(TIMEOUT_ENV, "") or "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


def safe_call(
    func: Callable[..., T],
    *args: Any,
    timeout_sec: float | None = None,
    plugin_id: str = "",
    breaker: "CircuitBreaker | None" = None,
    **kwargs: Any,
) -> SandboxResult:
    """Invoke ``func`` inside the sandbox. Always returns a
    :class:`SandboxResult`; never raises into the caller.

    When ``timeout_sec`` is None and :envvar:`MYTHIC_PLUGIN_TIMEOUT_SEC`
    is unset, the call runs synchronously without thread overhead.
    Otherwise the call runs on a worker thread with a soft
    deadline.

    Phase 20.3 (additive 2026-05-02): when a ``breaker`` is
    supplied, every result is reported into the breaker so it
    can track consecutive failures per ``plugin_id``. The
    breaker is **soft** — this function never short-circuits a
    call. Callers (e.g. the plugin-hook dispatcher) can
    pre-check ``breaker.is_tripped(plugin_id)`` to skip the
    invocation entirely. Default ``breaker=None`` preserves
    pre-20.3 behaviour byte-identically.
    """
    effective_timeout = (
        timeout_sec if timeout_sec is not None else resolve_timeout_sec()
    )
    start = time.monotonic()

    if effective_timeout is None:
        # Fast path: synchronous call, exception isolation only.
        try:
            value = func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — sandbox swallows by design
            result = SandboxResult(
                elapsed_ms=(time.monotonic() - start) * 1000.0,
                error=f"{type(exc).__name__}: {exc}",
                plugin_id=plugin_id,
            )
            return _report_to_breaker(result, breaker, plugin_id)
        result = SandboxResult(
            value=value,
            elapsed_ms=(time.monotonic() - start) * 1000.0,
            plugin_id=plugin_id,
        )
        return _report_to_breaker(result, breaker, plugin_id)

    # Slow path: timeout enforcement on a daemon thread. We don't
    # use ThreadPoolExecutor here because its __exit__ blocks on
    # the worker, which defeats the timeout. Daemon threads orphan
    # cleanly on timeout — the worker keeps running but doesn't
    # block process shutdown.
    holder: dict[str, Any] = {}

    def _runner() -> None:
        try:
            holder["value"] = func(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 — capture for the caller
            holder["error"] = exc

    worker = threading.Thread(target=_runner, daemon=True)
    worker.start()
    worker.join(timeout=effective_timeout)
    elapsed_ms = (time.monotonic() - start) * 1000.0

    if worker.is_alive():
        result = SandboxResult(
            elapsed_ms=elapsed_ms,
            error=(
                f"plugin exceeded {effective_timeout:.3f}s timeout "
                f"(MYTHIC_PLUGIN_TIMEOUT_SEC); worker thread is "
                "daemon-flagged but cannot be force-killed"
            ),
            timed_out=True,
            plugin_id=plugin_id,
        )
        return _report_to_breaker(result, breaker, plugin_id)

    captured_exc = holder.get("error")
    if isinstance(captured_exc, BaseException):
        result = SandboxResult(
            elapsed_ms=elapsed_ms,
            error=f"{type(captured_exc).__name__}: {captured_exc}",
            plugin_id=plugin_id,
        )
        return _report_to_breaker(result, breaker, plugin_id)

    result = SandboxResult(
        value=holder.get("value"),
        elapsed_ms=elapsed_ms,
        plugin_id=plugin_id,
    )
    return _report_to_breaker(result, breaker, plugin_id)


def _report_to_breaker(
    result: SandboxResult,
    breaker: "CircuitBreaker | None",
    plugin_id: str,
) -> SandboxResult:
    """Phase 20.3 (additive): notify the circuit breaker of a
    success / failure if one is wired in. Returns the result
    unchanged so callers can still use it normally. No-op when
    ``breaker`` is None (default)."""
    if breaker is None or not plugin_id:
        return result
    if result.ok:
        breaker.record_success(plugin_id)
    else:
        breaker.record_failure(plugin_id)
    return result


@dataclass(frozen=True)
class ResourceProbe:
    """Snapshot of host resource limits + current usage. Empty
    fields on Windows / non-POSIX hosts where ``resource`` isn't
    available."""

    advisory_only: bool
    platform: str
    rlimit: dict[str, list[Any]] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "advisory_only": self.advisory_only,
            "platform": self.platform,
            "rlimit": dict(self.rlimit),
            "usage": dict(self.usage),
            "notes": list(self.notes),
        }


def probe_resource_caps() -> ResourceProbe:
    """One-shot snapshot of ``resource.getrusage`` and the
    interesting RLIMIT_* values. POSIX-only by stdlib design;
    Windows hosts get an empty advisory-only payload."""
    import platform as _platform
    plat = _platform.system().lower()

    try:
        import resource  # type: ignore[import-not-found]
    except ImportError:
        return ResourceProbe(
            advisory_only=True,
            platform=plat,
            notes=[
                "Resource caps unavailable on this platform — Python's "
                "stdlib `resource` module is POSIX-only. Plugin "
                "performance budgets are reported via timing only."
            ],
        )

    rlimit_payload: dict[str, list[Any]] = {}
    interesting = (
        "RLIMIT_CPU",
        "RLIMIT_FSIZE",
        "RLIMIT_DATA",
        "RLIMIT_STACK",
        "RLIMIT_AS",
        "RLIMIT_NPROC",
        "RLIMIT_NOFILE",
    )
    for name in interesting:
        const = getattr(resource, name, None)
        if const is None:
            continue
        try:
            soft, hard = resource.getrlimit(const)
        except (OSError, ValueError):
            continue
        rlimit_payload[name] = [soft, hard]

    usage_payload: dict[str, Any] = {}
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        for attr in (
            "ru_utime",
            "ru_stime",
            "ru_maxrss",
            "ru_minflt",
            "ru_majflt",
            "ru_inblock",
            "ru_oublock",
        ):
            usage_payload[attr] = getattr(usage, attr, None)
    except OSError:
        pass

    return ResourceProbe(
        advisory_only=False,
        platform=plat,
        rlimit=rlimit_payload,
        usage=usage_payload,
        notes=[
            "POSIX resource caps reported as informational only — "
            "the sandbox does not enforce limits, it reports them."
        ],
    )


__all__ = [
    "ResourceProbe",
    "SandboxResult",
    "TIMEOUT_ENV",
    "probe_resource_caps",
    "resolve_timeout_sec",
    "safe_call",
]
