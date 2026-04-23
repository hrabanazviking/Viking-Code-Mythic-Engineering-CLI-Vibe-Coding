"""Phase 8 — PerfTracker tests: recording, statistics, ring buffer, bottleneck report."""

from __future__ import annotations

import threading
import time

import pytest

from thoughtforge.utils.perf import EventStats, PerfSummary, PerfTracker, _percentile


# ── _percentile helper ────────────────────────────────────────────────────────

class TestPercentile:
    def test_single_element(self):
        assert _percentile([5.0], 50) == pytest.approx(5.0)
        assert _percentile([5.0], 99) == pytest.approx(5.0)

    def test_two_elements_p50(self):
        assert _percentile([1.0, 3.0], 50) == pytest.approx(2.0)

    def test_known_values(self):
        data = sorted(float(i) for i in range(1, 101))   # 1..100
        assert _percentile(data, 50) == pytest.approx(50.5, abs=1.0)
        assert _percentile(data, 95) == pytest.approx(95.05, abs=1.0)

    def test_empty(self):
        assert _percentile([], 50) == pytest.approx(0.0)


# ── PerfTracker ────────────────────────────────────────────────────────────────

class TestPerfTracker:
    def test_record_and_summary(self):
        t = PerfTracker()
        t.record("retrieval", 42.0)
        t.record("retrieval", 58.0)
        t.record("generation", 1200.0)

        s = t.summary()
        assert "retrieval" in s.events
        assert "generation" in s.events
        assert s.events["retrieval"].count == 2
        assert s.events["retrieval"].mean == pytest.approx(50.0)
        assert s.events["generation"].count == 1
        assert s.total_tracked == 3

    def test_summary_empty(self):
        t = PerfTracker()
        s = t.summary()
        assert s.events == {}
        assert s.total_tracked == 0

    def test_summary_last_n(self):
        t = PerfTracker()
        for i in range(20):
            t.record("step", float(i))

        s = t.summary(last_n=5)
        # Should only see the last 5 events (15..19)
        assert s.events["step"].count == 5
        assert s.events["step"].min == pytest.approx(15.0)
        assert s.events["step"].max == pytest.approx(19.0)

    def test_event_stats_fields(self):
        t = PerfTracker()
        for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
            t.record("x", v)
        s = t.summary()
        ev = s.events["x"]
        assert ev.min == pytest.approx(10.0)
        assert ev.max == pytest.approx(50.0)
        assert ev.mean == pytest.approx(30.0)
        assert ev.p50 >= ev.min
        assert ev.p95 <= ev.max
        assert ev.p99 <= ev.max

    def test_slowest_events_sorted_descending(self):
        t = PerfTracker()
        t.record("fast", 10.0)
        t.record("slow", 1000.0)
        t.record("medium", 100.0)

        s = t.summary()
        names = [name for name, _ in s.slowest_events]
        assert names[0] == "slow"
        assert names[-1] == "fast"

    def test_ring_buffer_evicts_oldest(self):
        t = PerfTracker(ring_buffer_size=5)
        for i in range(10):
            t.record("ev", float(i))

        s = t.summary(last_n=100)
        # Ring buffer only holds 5
        assert s.total_tracked == 5
        # Most recent values (5..9) should be present
        assert s.events["ev"].min == pytest.approx(5.0)
        assert s.events["ev"].max == pytest.approx(9.0)

    def test_metadata_stored(self):
        t = PerfTracker()
        t.record("gen", 500.0, metadata={"backend": "ollama", "model": "llama3"})
        # Metadata is stored but not returned in summary (internal)
        # Just check it doesn't crash
        s = t.summary()
        assert s.events["gen"].count == 1

    def test_reset_clears_buffer(self):
        t = PerfTracker()
        t.record("x", 1.0)
        t.record("x", 2.0)
        t.reset()
        s = t.summary()
        assert s.total_tracked == 0
        assert s.events == {}

    def test_bottleneck_report_empty(self):
        t = PerfTracker()
        report = t.bottleneck_report()
        assert "No performance data" in report

    def test_bottleneck_report_format(self):
        t = PerfTracker()
        t.record("retrieval", 42.5)
        t.record("generation", 1800.0)
        report = t.bottleneck_report()
        assert "retrieval" in report
        assert "generation" in report
        assert "Bottleneck" in report
        assert "generation" in report.split("Bottleneck")[-1]

    def test_thread_safety(self):
        t = PerfTracker(ring_buffer_size=1000)
        errors = []

        def worker(name: str, count: int) -> None:
            try:
                for i in range(count):
                    t.record(name, float(i))
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=worker, args=(f"ev{i}", 50))
            for i in range(5)
        ]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        assert not errors
        s = t.summary(last_n=1000)
        assert s.total_tracked <= 1000   # ring buffer cap


# ── get_perf_tracker singleton ────────────────────────────────────────────────

class TestGlobalTracker:
    def test_singleton(self):
        from thoughtforge.utils.perf import get_perf_tracker
        t1 = get_perf_tracker()
        t2 = get_perf_tracker()
        assert t1 is t2

    def test_singleton_is_perf_tracker(self):
        from thoughtforge.utils.perf import get_perf_tracker
        assert isinstance(get_perf_tracker(), PerfTracker)
