# Spec for the Pi-derived event bus. Pi has no direct unit tests for
# event-bus.ts (only integration via agent-session); these cases are
# Mythic-flavored unit tests written against the Python port.
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# The Python implementation under test (mythic_vibe_cli.runtime.event_bus)
# is licensed under the Apache License, Version 2.0.
"""Tests for the Pi-derived synchronous event bus."""

from __future__ import annotations

import io
import sys
import threading
import unittest

from mythic_vibe_cli.runtime.event_bus import (
    EventBus,
    EventBusController,
    create_event_bus,
)


class EventBusTests(unittest.TestCase):
    def test_create_returns_controller_implementing_event_bus_protocol(self) -> None:
        bus = create_event_bus()
        self.assertIsInstance(bus, EventBusController)
        self.assertIsInstance(bus, EventBus)

    def test_subscribed_handler_receives_emitted_data(self) -> None:
        bus = create_event_bus()
        received: list[object] = []
        bus.on("ping", lambda data: received.append(data))

        bus.emit("ping", {"value": 42})

        self.assertEqual(received, [{"value": 42}])

    def test_multiple_handlers_on_same_channel_all_fire_in_order(self) -> None:
        bus = create_event_bus()
        order: list[str] = []
        bus.on("step", lambda _data: order.append("first"))
        bus.on("step", lambda _data: order.append("second"))
        bus.on("step", lambda _data: order.append("third"))

        bus.emit("step", None)

        self.assertEqual(order, ["first", "second", "third"])

    def test_channels_are_isolated(self) -> None:
        bus = create_event_bus()
        a_received: list[object] = []
        b_received: list[object] = []
        bus.on("a", lambda data: a_received.append(data))
        bus.on("b", lambda data: b_received.append(data))

        bus.emit("a", "for-a")
        bus.emit("b", "for-b")

        self.assertEqual(a_received, ["for-a"])
        self.assertEqual(b_received, ["for-b"])

    def test_unsubscribe_removes_only_that_handler(self) -> None:
        bus = create_event_bus()
        received: list[str] = []

        def keep(_data: object) -> None:
            received.append("keep")

        def drop(_data: object) -> None:
            received.append("drop")

        bus.on("ch", keep)
        unsubscribe_drop = bus.on("ch", drop)

        bus.emit("ch", None)
        unsubscribe_drop()
        bus.emit("ch", None)

        self.assertEqual(received, ["keep", "drop", "keep"])

    def test_unsubscribe_called_twice_is_a_noop(self) -> None:
        bus = create_event_bus()
        received: list[object] = []
        unsubscribe = bus.on("ch", lambda data: received.append(data))

        unsubscribe()
        unsubscribe()
        bus.emit("ch", "after")

        self.assertEqual(received, [])

    def test_emit_to_channel_with_no_handlers_is_safe(self) -> None:
        bus = create_event_bus()
        bus.emit("nobody-listens", None)  # must not raise

    def test_handler_exception_is_logged_and_other_handlers_still_fire(self) -> None:
        bus = create_event_bus()
        captured: list[str] = []

        def boom(_data: object) -> None:
            raise RuntimeError("handler-explodes")

        def survivor(data: object) -> None:
            captured.append(f"survived:{data}")

        bus.on("ch", boom)
        bus.on("ch", survivor)

        original_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            bus.emit("ch", "payload")
            stderr_text = sys.stderr.getvalue()
        finally:
            sys.stderr = original_stderr

        self.assertEqual(captured, ["survived:payload"])
        self.assertIn("Event handler error (ch)", stderr_text)
        self.assertIn("handler-explodes", stderr_text)

    def test_handler_unsubscribing_during_emit_does_not_break_iteration(self) -> None:
        bus = create_event_bus()
        received: list[str] = []
        unsubscribe_holder: list[object] = []

        def first(_data: object) -> None:
            received.append("first")
            unsubscribe = unsubscribe_holder[0]
            assert callable(unsubscribe)
            unsubscribe()

        def second(_data: object) -> None:
            received.append("second")

        unsubscribe_holder.append(bus.on("ch", first))
        bus.on("ch", second)

        bus.emit("ch", None)

        self.assertEqual(received, ["first", "second"])

    def test_clear_removes_all_handlers(self) -> None:
        bus = create_event_bus()
        received: list[str] = []
        bus.on("a", lambda _data: received.append("a"))
        bus.on("b", lambda _data: received.append("b"))

        bus.clear()
        bus.emit("a", None)
        bus.emit("b", None)

        self.assertEqual(received, [])

    def test_concurrent_emit_and_subscribe_are_thread_safe(self) -> None:
        bus = create_event_bus()
        received: list[int] = []
        receive_lock = threading.Lock()

        def append_value(value: int) -> None:
            def handler(_data: object) -> None:
                with receive_lock:
                    received.append(value)
            return handler  # type: ignore[return-value]

        # Pre-register many handlers so emits have meaningful work
        unsubs = [bus.on("ch", append_value(index)) for index in range(20)]

        emit_threads = [
            threading.Thread(target=lambda: bus.emit("ch", None)) for _ in range(8)
        ]
        # Threads that subscribe and immediately unsubscribe to stress the lock
        churn_threads = []
        for _ in range(8):
            def churn() -> None:
                u = bus.on("ch", lambda _d: None)
                u()
            churn_threads.append(threading.Thread(target=churn))

        for thread in emit_threads + churn_threads:
            thread.start()
        for thread in emit_threads + churn_threads:
            thread.join(timeout=5.0)

        # Every emit invoked the 20 pre-registered handlers (8 emits * 20 handlers = 160).
        # Churn handlers may or may not have been included on each emit depending on
        # interleaving; the key safety property is that no emit raised and the count
        # is at least the lower bound.
        self.assertGreaterEqual(len(received), 8 * 20)

        for unsubscribe in unsubs:
            unsubscribe()


if __name__ == "__main__":
    unittest.main()
