"""
locustfile.py — Locust load test for MindSpark: ThoughtForge.

Simulates concurrent users calling ThoughtForgeCore.think() in knowledge-only
mode (no GGUF model), measuring throughput and latency under load.

Usage:
    pip install locust
    locust -f locustfile.py --headless -u 10 -r 2 --run-time 60s

Note: ThoughtForge is an offline local system — Locust is used here in
"no-HTTP" mode (TaskSet without HttpUser) to measure Python-level throughput.
For a real HTTP deployment, wrap ThoughtForgeCore in a FastAPI/Flask app
and point Locust at the HTTP endpoints instead.
"""

from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path

try:
    from locust import User, between, events, task
    from locust.exception import StopUser
    _LOCUST_AVAILABLE = True
except ImportError:
    _LOCUST_AVAILABLE = False

logger = logging.getLogger(__name__)

# ── Shared core (created once per worker process) ──────────────────────────────

_shared_core = None


def _get_core():
    global _shared_core
    if _shared_core is None:
        from thoughtforge.cognition.core import ThoughtForgeCore
        tmp = tempfile.mkdtemp()
        _shared_core = ThoughtForgeCore(
            memory_dir=Path(tmp) / "memory",
            db_path=Path(tmp) / "bench.db",
            model_path=None,
        )
    return _shared_core


# ── Query bank ─────────────────────────────────────────────────────────────────

_QUERIES = [
    "What is Yggdrasil?",
    "Explain the concept of frith.",
    "Who are the Vanir gods?",
    "What is Valhalla?",
    "Describe the role of ravens in Norse mythology.",
    "What does wyrd mean?",
    "Who is Loki?",
    "What are the nine worlds?",
    "Explain seiðr in Norse culture.",
    "Who was a völva in Norse society?",
    "What is the significance of Mjolnir?",
    "Describe Bifrost.",
    "What are the Norns?",
    "Who is Freya and what is her domain?",
    "Explain the concept of orlog.",
]


# ── Locust User class ──────────────────────────────────────────────────────────

if _LOCUST_AVAILABLE:

    class ThoughtForgeUser(User):
        """
        Simulates a single user of ThoughtForge in local (non-HTTP) mode.

        Each task calls core.think() and reports the result to Locust's
        event system for throughput and latency tracking.
        """
        wait_time = between(0.1, 0.5)
        _query_idx: int = 0

        def on_start(self) -> None:
            self._core = _get_core()
            self._query_idx = 0

        @task(3)
        def single_factual_query(self) -> None:
            """Standard factual query — most common user action."""
            query = _QUERIES[self._query_idx % len(_QUERIES)]
            self._query_idx += 1
            self._run_think(query, name="factual_query")

        @task(1)
        def short_query(self) -> None:
            """Brief query — tests low-latency path."""
            self._run_think("What is Yggdrasil?", name="short_query")

        @task(1)
        def multi_word_query(self) -> None:
            """Longer query with more context."""
            self._run_think(
                "Explain in detail the cosmological significance of Yggdrasil "
                "and how it connects the nine worlds in Norse mythology.",
                name="multi_word_query",
            )

        def _run_think(self, query: str, name: str) -> None:
            """Execute think() and report to Locust events."""
            start = time.perf_counter()
            try:
                result = self._core.think(query)
                elapsed_ms = (time.perf_counter() - start) * 1000.0

                response_length = len(getattr(result, "text", "") or "")
                events.request.fire(
                    request_type="think",
                    name=name,
                    response_time=elapsed_ms,
                    response_length=response_length,
                    exception=None,
                    context={},
                )

            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                events.request.fire(
                    request_type="think",
                    name=name,
                    response_time=elapsed_ms,
                    response_length=0,
                    exception=e,
                    context={},
                )


else:
    # Stub class when locust is not installed
    class ThoughtForgeUser:  # type: ignore[no-redef]
        """Stub — install locust to use: pip install locust"""
        pass
