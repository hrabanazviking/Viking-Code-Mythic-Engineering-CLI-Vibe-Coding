"""Phase 20.3 — plugin circuit breaker.

Tracks consecutive failures (timeout or exception) per plugin
``plugin_id``. When a plugin trips the threshold, the breaker
flips to ``tripped`` state — the next ``safe_call`` for that
plugin can be short-circuited by the caller (saving the cost of
running the timing-out / crashing plugin yet again).

The breaker is **soft**: it does not modify the registry
(disabling is the operator's call via ``mythic-vibe plugin
disable``). It surfaces state so:

- ``mythic-vibe plugin doctor`` reports tripped plugins clearly.
- The plugin-hook dispatcher can skip tripped plugins on the
  next event so a hung plugin doesn't slow every event by
  ``MYTHIC_PLUGIN_TIMEOUT_SEC``.

**Threshold resolution order** (configurable per the PH-20 plan):

1. Constructor argument (programmatic — for tests / explicit
   wiring).
2. ``MYTHIC_PLUGIN_BREAKER_THRESHOLD`` env var (operator
   override).
3. Built-in default (3 consecutive failures — short enough to
   catch a runaway, long enough to absorb transient blips).

Cross-platform: pure stdlib. Thread-safe via ``threading.Lock``.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Literal


THRESHOLD_ENV = "MYTHIC_PLUGIN_BREAKER_THRESHOLD"
DEFAULT_THRESHOLD = 3

BreakerState = Literal["closed", "tripped"]


@dataclass(frozen=True)
class BreakerStatus:
    """Snapshot of one plugin's breaker state. Returned from
    :meth:`CircuitBreaker.snapshot` for ``plugin doctor`` and
    similar surfaces."""

    plugin_id: str
    state: BreakerState
    consecutive_failures: int
    threshold: int

    def to_dict(self) -> dict[str, object]:
        return {
            "plugin_id": self.plugin_id,
            "state": self.state,
            "consecutive_failures": self.consecutive_failures,
            "threshold": self.threshold,
        }


def _resolve_threshold(
    explicit: int | None,
    *,
    env: dict[str, str] | None = None,
) -> int:
    """Resolve threshold from constructor → env var → default.
    Always returns a positive int. Invalid env values fall back
    silently to the default rather than raising — operators
    shouldn't get a startup crash from a typo'd env var."""
    if explicit is not None and explicit > 0:
        return int(explicit)
    source = env if env is not None else os.environ
    raw = (source.get(THRESHOLD_ENV, "") or "").strip()
    if raw:
        try:
            value = int(raw)
            if value > 0:
                return value
        except ValueError:
            pass
    return DEFAULT_THRESHOLD


@dataclass
class _PluginRecord:
    """Internal mutable per-plugin state. Not exported."""
    consecutive_failures: int = 0
    state: BreakerState = "closed"


class CircuitBreaker:
    """Per-plugin failure tracker. Construct once per process /
    test; share across ``safe_call`` invocations via the new
    ``breaker=`` kwarg. Thread-safe."""

    def __init__(
        self,
        *,
        threshold: int | None = None,
        env: dict[str, str] | None = None,
    ):
        self.threshold = _resolve_threshold(threshold, env=env)
        self._records: dict[str, _PluginRecord] = {}
        self._lock = threading.Lock()

    def record_success(self, plugin_id: str) -> BreakerState:
        """Reset the consecutive-failure count for ``plugin_id``
        and (if currently tripped) re-close the breaker.
        Returns the post-call state."""
        with self._lock:
            record = self._records.setdefault(plugin_id, _PluginRecord())
            record.consecutive_failures = 0
            record.state = "closed"
            return record.state

    def record_failure(self, plugin_id: str) -> BreakerState:
        """Increment the consecutive-failure count and trip the
        breaker if the threshold is met. Returns the post-call
        state."""
        with self._lock:
            record = self._records.setdefault(plugin_id, _PluginRecord())
            record.consecutive_failures += 1
            if record.consecutive_failures >= self.threshold:
                record.state = "tripped"
            return record.state

    def is_tripped(self, plugin_id: str) -> bool:
        """Read-only check — does NOT mutate state."""
        with self._lock:
            record = self._records.get(plugin_id)
            return record is not None and record.state == "tripped"

    def reset(self, plugin_id: str) -> None:
        """Manual reset — operator-driven re-enable after the
        underlying plugin issue is fixed. Equivalent to a
        successful invocation in terms of state machine."""
        with self._lock:
            self._records.pop(plugin_id, None)

    def reset_all(self) -> None:
        """Wipe all per-plugin state. Useful for tests; rarely
        appropriate at runtime."""
        with self._lock:
            self._records.clear()

    def snapshot(self) -> list[BreakerStatus]:
        """Return per-plugin status snapshots. Stable
        (alphabetical by plugin_id) so output is deterministic
        for snapshot tests / operator diffs."""
        with self._lock:
            items = sorted(self._records.items(), key=lambda kv: kv[0])
            return [
                BreakerStatus(
                    plugin_id=plugin_id,
                    state=record.state,
                    consecutive_failures=record.consecutive_failures,
                    threshold=self.threshold,
                )
                for plugin_id, record in items
            ]


__all__ = [
    "DEFAULT_THRESHOLD",
    "THRESHOLD_ENV",
    "BreakerState",
    "BreakerStatus",
    "CircuitBreaker",
]
