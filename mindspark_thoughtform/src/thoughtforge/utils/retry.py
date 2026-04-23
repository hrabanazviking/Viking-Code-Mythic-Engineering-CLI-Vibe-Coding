"""Retry decorator with exponential backoff and circuit breaker.

Usage:
    from thoughtforge.utils.retry import retry, exponential, CircuitBreaker
    from thoughtforge.utils.errors import BackendTimeoutError, BackendUnavailableError

    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

    @retry(attempts=3, backoff=exponential(base=0.5, max_wait=10.0),
           on=(BackendTimeoutError, BackendUnavailableError), circuit_breaker=cb)
    def call_backend(request):
        ...
"""

from __future__ import annotations

import functools
import logging
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Sequence, Type

logger = logging.getLogger(__name__)


# ── Backoff strategies ─────────────────────────────────────────────────────────

def exponential(base: float = 0.5, max_wait: float = 10.0, jitter: bool = True) -> Callable[[int], float]:
    """Exponential backoff: base * 2^attempt, capped at max_wait, with optional jitter."""
    def _backoff(attempt: int) -> float:
        wait = min(base * (2 ** attempt), max_wait)
        if jitter:
            wait *= (0.5 + random.random() * 0.5)   # ±50% jitter
        return wait
    return _backoff


def linear(step: float = 1.0, max_wait: float = 30.0) -> Callable[[int], float]:
    """Linear backoff: step * attempt, capped at max_wait."""
    def _backoff(attempt: int) -> float:
        return min(step * (attempt + 1), max_wait)
    return _backoff


def fixed(seconds: float = 1.0) -> Callable[[int], float]:
    """Fixed backoff: same wait every attempt."""
    def _backoff(attempt: int) -> float:
        return seconds
    return _backoff


# ── Circuit Breaker ────────────────────────────────────────────────────────────

class CircuitState(str, Enum):
    CLOSED     = "closed"      # normal operation
    OPEN       = "open"        # failing, reject all calls
    HALF_OPEN  = "half_open"   # probing: allow one call through


@dataclass
class CircuitBreaker:
    """
    Simple thread-safe circuit breaker.

    States:
        CLOSED    → normal; count failures; open when threshold reached
        OPEN      → reject immediately; wait recovery_timeout; then HALF_OPEN
        HALF_OPEN → let one probe through; success → CLOSED, failure → OPEN
    """
    failure_threshold: int = 5
    recovery_timeout: float = 60.0   # seconds before attempting half-open

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False, repr=False)
    _failures: int = field(default=0, init=False, repr=False)
    _opened_at: float = field(default=0.0, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._opened_at >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    logger.info("CircuitBreaker: OPEN → HALF_OPEN (probe allowed)")
            return self._state

    def allow_request(self) -> bool:
        """Returns True if the request should be allowed through."""
        return self.state != CircuitState.OPEN

    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info("CircuitBreaker: HALF_OPEN → CLOSED (probe succeeded)")
            self._state = CircuitState.CLOSED
            self._failures = 0

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._state == CircuitState.HALF_OPEN:
                logger.warning("CircuitBreaker: HALF_OPEN → OPEN (probe failed)")
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
            elif self._failures >= self.failure_threshold:
                logger.warning(
                    "CircuitBreaker: CLOSED → OPEN after %d failures", self._failures
                )
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()

    def reset(self) -> None:
        """Manually reset the breaker (useful in tests)."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failures = 0
            self._opened_at = 0.0


class CircuitOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""


# ── Sentinel for "no fallback provided" ───────────────────────────────────────
_SENTINEL = object()


# ── @retry decorator ──────────────────────────────────────────────────────────

def retry(
    attempts: int = 3,
    backoff: Callable[[int], float] = exponential(),
    on: Sequence[Type[Exception]] = (Exception,),
    fallback: Any = _SENTINEL,
    circuit_breaker: CircuitBreaker | None = None,
) -> Callable:
    """
    Decorator that retries a function on specified exceptions.

    Args:
        attempts:        Maximum number of total attempts (including the first call).
        backoff:         Callable(attempt_index) → seconds to sleep before retry.
        on:              Tuple of exception types to catch and retry.
        fallback:        Value to return after all attempts are exhausted.
                         If not provided, the last exception is re-raised.
        circuit_breaker: Optional CircuitBreaker; if open, raises CircuitOpenError
                         without attempting the call.

    Returns:
        The wrapped function's return value, or `fallback` on exhaustion.
    """
    on_types = tuple(on)

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if circuit_breaker is not None and not circuit_breaker.allow_request():
                raise CircuitOpenError(
                    f"Circuit breaker is OPEN for {fn.__qualname__} — "
                    f"call rejected until recovery timeout elapses"
                )

            last_exc: Exception | None = None
            for attempt in range(attempts):
                try:
                    result = fn(*args, **kwargs)
                    if circuit_breaker is not None:
                        circuit_breaker.record_success()
                    return result
                except on_types as exc:
                    last_exc = exc
                    if circuit_breaker is not None:
                        circuit_breaker.record_failure()
                    if attempt < attempts - 1:
                        wait = backoff(attempt)
                        logger.warning(
                            "%s failed (attempt %d/%d): %s — retrying in %.2fs",
                            fn.__qualname__,
                            attempt + 1,
                            attempts,
                            exc,
                            wait,
                        )
                        time.sleep(wait)
                    else:
                        logger.warning(
                            "%s failed (attempt %d/%d): %s — giving up",
                            fn.__qualname__,
                            attempt + 1,
                            attempts,
                            exc,
                        )

            if fallback is not _SENTINEL:
                return fallback
            if last_exc is not None:
                raise last_exc
            return None   # unreachable, but satisfies type checkers

        return wrapper
    return decorator
