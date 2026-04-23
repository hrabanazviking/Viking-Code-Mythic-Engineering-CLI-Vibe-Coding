"""Performance profiler and bottleneck reporter for MindSpark: ThoughtForge.

Lightweight ring-buffer event tracker that records latency at key pipeline
steps and surfaces p50/p95/p99 statistics on demand.

Usage:
    from thoughtforge.utils.perf import get_perf_tracker

    tracker = get_perf_tracker()
    tracker.record("retrieval", duration_ms=42.3)
    tracker.record("generation", duration_ms=1800.0, metadata={"backend": "ollama"})

    print(tracker.bottleneck_report())
"""

from __future__ import annotations

import statistics
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any

# ── Ring-buffer capacity ───────────────────────────────────────────────────────
_RING_BUFFER_SIZE = 1000


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PerfEvent:
    event: str
    duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EventStats:
    event: str
    count: int
    mean: float
    p50: float
    p95: float
    p99: float
    min: float
    max: float


@dataclass
class PerfSummary:
    events: dict[str, EventStats]             # event_name → stats
    slowest_events: list[tuple[str, float]]   # [(event_name, max_ms), ...] sorted desc
    total_tracked: int


# ── PerfTracker ───────────────────────────────────────────────────────────────

class PerfTracker:
    """
    Thread-safe ring-buffer performance tracker.

    Records latency events with a fixed-capacity deque (oldest events
    are automatically dropped when the buffer is full).  Reporting is
    O(n) where n ≤ ring_buffer_size.
    """

    def __init__(self, ring_buffer_size: int = _RING_BUFFER_SIZE) -> None:
        self._buf: deque[PerfEvent] = deque(maxlen=ring_buffer_size)
        self._lock = threading.Lock()

    # ── Recording ──────────────────────────────────────────────────────────────

    def record(
        self,
        event: str,
        duration_ms: float,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a timing event.

        Args:
            event:       Pipeline step name, e.g. "retrieval", "generation"
            duration_ms: Elapsed time in milliseconds
            metadata:    Optional dict of extra context (backend, model, etc.)
        """
        with self._lock:
            self._buf.append(PerfEvent(
                event=event,
                duration_ms=duration_ms,
                metadata=metadata or {},
            ))

    # ── Reporting ──────────────────────────────────────────────────────────────

    def summary(self, last_n: int = 100) -> PerfSummary:
        """Compute per-event statistics over the most recent last_n events.

        Args:
            last_n: How many recent events to include (default 100).

        Returns:
            PerfSummary with per-event stats and a slowest-events ranking.
        """
        with self._lock:
            events = list(self._buf)

        # Take the last_n events
        recent = events[-last_n:] if len(events) > last_n else events

        # Group by event name
        grouped: dict[str, list[float]] = {}
        for ev in recent:
            grouped.setdefault(ev.event, []).append(ev.duration_ms)

        stats: dict[str, EventStats] = {}
        for name, durations in grouped.items():
            sorted_d = sorted(durations)
            n = len(sorted_d)
            stats[name] = EventStats(
                event=name,
                count=n,
                mean=statistics.mean(sorted_d),
                p50=_percentile(sorted_d, 50),
                p95=_percentile(sorted_d, 95),
                p99=_percentile(sorted_d, 99),
                min=sorted_d[0],
                max=sorted_d[-1],
            )

        slowest = sorted(
            ((name, s.max) for name, s in stats.items()),
            key=lambda x: x[1],
            reverse=True,
        )

        return PerfSummary(
            events=stats,
            slowest_events=slowest,
            total_tracked=len(events),
        )

    def bottleneck_report(self, last_n: int = 100) -> str:
        """Return a human-readable bottleneck report string."""
        s = self.summary(last_n=last_n)
        if not s.events:
            return "No performance data recorded yet."

        lines = [
            f"Performance Report (last {min(last_n, s.total_tracked)} of {s.total_tracked} events)",
            "-" * 55,
            f"{'Event':<22} {'Count':>5}  {'Mean':>8}  {'P50':>8}  {'P95':>8}  {'P99':>8}  {'Max':>8}",
            f"{'':22} {'':>5}  {'ms':>8}  {'ms':>8}  {'ms':>8}  {'ms':>8}  {'ms':>8}",
            "-" * 55,
        ]

        # Sort by mean descending (slowest first)
        sorted_events = sorted(
            s.events.values(), key=lambda e: e.mean, reverse=True
        )
        for ev in sorted_events:
            lines.append(
                f"{ev.event:<22} {ev.count:>5}  "
                f"{ev.mean:>8.1f}  {ev.p50:>8.1f}  "
                f"{ev.p95:>8.1f}  {ev.p99:>8.1f}  {ev.max:>8.1f}"
            )

        if s.slowest_events:
            lines.append("")
            lines.append(f"Bottleneck: {s.slowest_events[0][0]} ({s.slowest_events[0][1]:.1f}ms max)")

        return "\n".join(lines)

    def reset(self) -> None:
        """Clear all recorded events (useful in tests)."""
        with self._lock:
            self._buf.clear()


# ── Percentile helper ──────────────────────────────────────────────────────────

def _percentile(sorted_data: list[float], pct: int) -> float:
    """Compute the pct-th percentile of an already-sorted list."""
    if not sorted_data:
        return 0.0
    n = len(sorted_data)
    if n == 1:
        return sorted_data[0]
    idx = (pct / 100) * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_data[lo] + frac * (sorted_data[hi] - sorted_data[lo])


# ── Module-level singleton ────────────────────────────────────────────────────

_global_tracker: PerfTracker | None = None
_tracker_lock = threading.Lock()


def get_perf_tracker() -> PerfTracker:
    """Return the module-level singleton PerfTracker (created on first call)."""
    global _global_tracker
    if _global_tracker is None:
        with _tracker_lock:
            if _global_tracker is None:
                _global_tracker = PerfTracker()
    return _global_tracker
