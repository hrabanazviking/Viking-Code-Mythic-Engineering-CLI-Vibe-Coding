import logging
import time
import inspect
from typing import Dict, List, Any, Callable, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """
    Core events emitted by the Norse Saga Engine during a turn.

    Phase 1 (Base):
        TURN_START, TURN_END, PLAYER_ACTION, AI_NARRATION,
        COMBAT_RESOLVED, NPC_STATE_CHANGED, MEMORY_STORED,
        CHAOS_SPIKE, RUNE_DRAWN, OATH_SWORN, BETRAYAL_DETECTED,
        RELATIONSHIP_CHANGED, EMOTION_SPIKED,
        MYTHIC_THRESHOLD_CROSSED, CHAOS_SHIFTED

    Phase 2 (Fate-Weaver Protocol):
        FYLGJA_OVERRIDE — Subconscious overrides conscious behavior
        COGNITIVE_BREAKDOWN — High value/action dissonance triggers
        OATH_BROKEN — Blood oath violated (damages Hamingja)
        RESONANCE_SPIKE — Location runic resonance crosses threshold
        OBJECT_REFUSED — Sentient artifact rejects a wielder
        WORLD_MANIFESTATION — Ecosystem imbalance spawns entity/event
        COSMIC_EVENT — Macro astrological cycle fires
    """

    TURN_START = "TURN_START"
    TURN_END = "TURN_END"
    PLAYER_ACTION = "PLAYER_ACTION"
    AI_NARRATION = "AI_NARRATION"
    COMBAT_RESOLVED = "COMBAT_RESOLVED"
    NPC_STATE_CHANGED = "NPC_STATE_CHANGED"
    MEMORY_STORED = "MEMORY_STORED"
    CHAOS_SPIKE = "CHAOS_SPIKE"
    CHAOS_SHIFTED = "CHAOS_SHIFTED"
    RUNE_DRAWN = "RUNE_DRAWN"
    OATH_SWORN = "OATH_SWORN"
    BETRAYAL_DETECTED = "BETRAYAL_DETECTED"
    RELATIONSHIP_CHANGED = "RELATIONSHIP_CHANGED"
    EMOTION_SPIKED = "EMOTION_SPIKED"
    MYTHIC_THRESHOLD_CROSSED = "MYTHIC_THRESHOLD_CROSSED"
    # Phase 2 — Soul Mechanics
    FYLGJA_OVERRIDE = "FYLGJA_OVERRIDE"
    COGNITIVE_BREAKDOWN = "COGNITIVE_BREAKDOWN"
    # Phase 2 — Wyrd Tethers
    OATH_BROKEN = "OATH_BROKEN"
    # Phase 2 — Runic Resonance
    RESONANCE_SPIKE = "RESONANCE_SPIKE"
    # Phase 2 — Object Agency
    OBJECT_REFUSED = "OBJECT_REFUSED"
    # Phase 2 — Cosmic Cycles / Ecosystem
    WORLD_MANIFESTATION = "WORLD_MANIFESTATION"
    COSMIC_EVENT = "COSMIC_EVENT"


class EventDispatcher:
    """
    Central pub/sub message bus for the Engine.
    Subsystems subscribe to specific EventTypes and react asynchronously
    or synchronously without being tightly coupled.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {
            event_type.value: [] for event_type in EventType
        }
        # Allow dynamic string events (like specific encounter triggers)
        self._dynamic_subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        """Register a callback for an event type."""
        if hasattr(EventType, event_type):
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
        else:
            if event_type not in self._dynamic_subscribers:
                self._dynamic_subscribers[event_type] = []
            if callback not in self._dynamic_subscribers[event_type]:
                self._dynamic_subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """Remove a callback from an event type."""
        if hasattr(EventType, event_type):
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
        elif event_type in self._dynamic_subscribers:
            if callback in self._dynamic_subscribers[event_type]:
                self._dynamic_subscribers[event_type].remove(callback)

    def dispatch(self, event_type: str, context: Optional[Dict[str, Any]] = None):
        """
        Broadcast an event to all subscribers.
        Context allows passing the WorldState or specific event data.
        """
        context = context or {}
        context["_timestamp"] = time.time()

        handlers = []
        if hasattr(EventType, event_type):
            handlers = self._subscribers.get(event_type, [])
        else:
            handlers = self._dynamic_subscribers.get(event_type, [])

        if not handlers:
            return

        logger.debug(f"[EVENT] Dispatching {event_type} to {len(handlers)} subscribers")

        for handler in handlers:
            try:
                # Handle both async and sync callbacks just in case, though standard is sync.
                if inspect.iscoroutinefunction(handler):
                    import asyncio

                    try:
                        # get_running_loop() is the correct 3.10+ API; raises
                        # RuntimeError when no loop is running (sync context).
                        loop = asyncio.get_running_loop()
                        loop.create_task(handler(event_type, context))
                    except RuntimeError:
                        # No running loop — fire synchronously via asyncio.run().
                        asyncio.run(handler(event_type, context))
                else:
                    handler(event_type, context)
            except Exception as e:
                logger.error(
                    f"[EVENT] Error in handler {handler.__name__} for {event_type}: {e}",
                    exc_info=True,
                )


# Global singleton so systems can cleanly import it if they don't have engine references,
# though injecting from engine is preferred.
_global_dispatcher_instance = None


def get_global_dispatcher() -> EventDispatcher:
    global _global_dispatcher_instance
    if _global_dispatcher_instance is None:
        _global_dispatcher_instance = EventDispatcher()
    return _global_dispatcher_instance
