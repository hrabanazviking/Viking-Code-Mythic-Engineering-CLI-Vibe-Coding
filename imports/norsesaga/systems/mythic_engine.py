import logging
from typing import Dict, Any

from systems.mythic_age import MythicAge
from systems.mythic_mirror import MythicMirror
from systems.world_dreams import WorldDreams
from systems.world_will import WorldWill
from systems.event_dispatcher import get_global_dispatcher, EventType

logger = logging.getLogger(__name__)


class MythicEngine:
    """
    Central manager for all mythic subsystems (Age, Mirror, Will, Dreams).
    Connects to the EventDispatcher to track the pulse of the world.
    """

    def __init__(self, engine=None, dispatcher=None):
        self.engine = engine
        self.dispatcher = dispatcher or get_global_dispatcher()

        # Initialize subsystems
        self.age = MythicAge()
        self.mirror = MythicMirror()
        self.will = WorldWill()
        self.dreams = WorldDreams()

        # Listen to relevant events
        self.dispatcher.subscribe(EventType.TURN_START.value, self._on_turn_start)
        self.dispatcher.subscribe(EventType.PLAYER_ACTION.value, self._on_player_action)
        self.dispatcher.subscribe(EventType.CHAOS_SHIFTED.value, self._on_chaos_shifted)

        logger.info("Mythic Engine initialized - The world awakens")

    def _on_turn_start(self, event_type: str, context: Dict[str, Any]):
        """Progress the ages and dreams when a new turn begins."""
        turn_number = context.get("turn_number", 1)
        chaos_factor = 30
        strongest_fate_theme = None
        wyrd_karma = 0

        # Try to pull chaos factor from GameState if engine exists
        if hasattr(self.engine, "state"):
            chaos_factor = getattr(self.engine.state, "chaos_factor", 30)
            fate_threads = list(getattr(self.engine.state, "fate_threads", []) or [])
            if fate_threads:
                strongest_fate_theme = str(fate_threads[-1])
            if getattr(self.engine, "wyrd_system", None):
                try:
                    wyrd_karma = int(self.engine.wyrd_system.mimir.state.total_karma)
                except Exception:
                    wyrd_karma = 0

        self.age.update(turn_count=turn_number)
        self.dreams.update(turn_count=turn_number, mythic_age_name=self.age.age_name)

        # World Will breathes every turn; full shifts still occur internally on interval.
        self.will.update(
            chaos_factor=chaos_factor,
            strongest_anchor_theme=strongest_fate_theme,
        )

        # Update specific pressure metrics on WorldState
        if hasattr(self.engine, "state"):
            # Mythic pressure rises with chaos, dreams, and accumulated wyrd karma magnitude.
            pressure = (
                (chaos_factor * 0.08)
                + (len(self.dreams.dreams) * 0.08)
                + (min(40, abs(wyrd_karma)) * 0.01)
            )
            self.engine.state.mythic_pressure = min(1.0, pressure)

    def _on_player_action(self, event_type: str, context: Dict[str, Any]):
        """Reflect player actions in the Mythic Mirror."""
        action = context.get("action", "")
        # Usually available from AI response, but we might just have action
        narrative = context.get("narrative", "")
        if action:
            self.mirror.update_from_turn(player_input=action, narrative=narrative)

    def _on_chaos_shifted(self, event_type: str, context: Dict[str, Any]):
        """If chaos spikes suddenly, the world will might violently shift."""
        new_chaos = context.get("new_chaos", 30)
        old_chaos = context.get("old_chaos", 30)
        diff = abs(new_chaos - old_chaos)

        if diff >= 20:
            logger.info("Violent chaos shift detected. Forcing WorldWill update.")
            self.will.update(chaos_factor=new_chaos)

    def get_mythic_summary_for_ai(self) -> str:
        """
        Produce a unified mythic context block for the AI director.
        """
        parts = [
            self.age.build_context(),
            self.will.build_context(),
            self.dreams.build_context(),
            self.mirror.build_context(),
        ]
        # Filter out empty blocks
        return "\n\n".join([p for p in parts if p.strip()])

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for GameState saving."""
        return {
            "age": self.age.to_dict(),
            "mirror": self.mirror.to_dict(),
            "will": self.will.to_dict(),
            "dreams": self.dreams.to_dict(),
        }

    def from_dict(self, data: Dict[str, Any]):
        """Restore from GameState."""
        if not data:
            return

        self.age.from_dict(data.get("age", {}))
        self.mirror.from_dict(data.get("mirror", {}))
        self.will.from_dict(data.get("will", {}))
        self.dreams.from_dict(data.get("dreams", {}))
