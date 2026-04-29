# Portions adapted from badlogic/pi-mono (packages/coding-agent/src/core/event-bus.ts).
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# Adapted by Volmarr / RuneForgeAI, 2026.
# This file is licensed under the Apache License, Version 2.0; the upstream
# MIT permission notice is preserved in THIRD_PARTY_NOTICES.md at the repo root.
"""Synchronous publish/subscribe event bus.

Pi uses Node's async ``EventEmitter`` so handlers can be ``async``; the
Mythic codebase is sync throughout, so we use a per-channel handler list with
a ``threading.Lock`` for thread safety. Otherwise the contract matches pi:

- ``emit(channel, data)`` invokes every handler subscribed to ``channel`` in
  registration order, snapshotting the handler list so handlers that
  unsubscribe themselves during dispatch do not break iteration.
- ``on(channel, handler)`` returns an ``unsubscribe()`` callable that removes
  exactly the registered handler.
- A handler raising an exception is logged to stderr (channel name + full
  traceback) and never crashes the bus or interrupts the dispatch of later
  handlers — the same "log + continue" contract pi enforces with its
  ``console.error`` wrapper.
- ``clear()`` removes every subscription on every channel.
"""

from __future__ import annotations

from collections import defaultdict
import sys
import threading
import traceback
from typing import Callable, Protocol, runtime_checkable


EventHandler = Callable[[object], None]
Unsubscribe = Callable[[], None]


@runtime_checkable
class EventBus(Protocol):
    """Public read/write surface of the event bus."""

    def emit(self, channel: str, data: object) -> None: ...
    def on(self, channel: str, handler: EventHandler) -> Unsubscribe: ...


class EventBusController:
    """Concrete event bus with the additional ``clear()`` admin operation."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._lock = threading.Lock()

    def emit(self, channel: str, data: object) -> None:
        with self._lock:
            handlers = list(self._handlers.get(channel, ()))
        for handler in handlers:
            try:
                handler(data)
            except Exception:  # noqa: BLE001 - match pi's log-and-continue contract
                print(f"Event handler error ({channel}):", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

    def on(self, channel: str, handler: EventHandler) -> Unsubscribe:
        with self._lock:
            self._handlers[channel].append(handler)

        def unsubscribe() -> None:
            with self._lock:
                handlers = self._handlers.get(channel)
                if handlers is None:
                    return
                try:
                    handlers.remove(handler)
                except ValueError:
                    return
                if not handlers:
                    self._handlers.pop(channel, None)

        return unsubscribe

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()


def create_event_bus() -> EventBusController:
    """Factory mirroring pi's ``createEventBus()`` — returns a fresh controller."""
    return EventBusController()
