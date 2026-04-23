"""
World Dreams — Between-turn Atmospheric Visions (every 7 turns)

The world generates symbolic dreams that foreshadow and create
continuity. Dreams grow more prophetic over time, and their
symbols may manifest in later narration or atmosphere.

Part of the Norse Saga Engine Myth Engine (v4.2.0)
"""
import random
import logging

logger = logging.getLogger(__name__)

DREAM_SYMBOLS = [
    "a lone wolf beneath stars",
    "fire burning without smoke",
    "raven wings over silent water",
    "roots growing through stone",
    "a broken sword glowing faintly",
    "snow falling upward",
    "the sound of distant horns",
    "embers floating from an empty hearth",
    "ice forming in the shape of runes",
    "a door standing in an open field",
    "a ship sailing through fog with no crew",
    "blood on fresh snow spelling a name",
    "a tree struck by lightning still bearing fruit",
    "an eye watching from deep water",
    "a chain of silver dissolving into mist",
    "wolves circling a sleeping warrior",
    "a flame that casts no shadow",
    "runestones arranged in a pattern unseen before",
    "the sound of weeping from beneath the earth",
    "an eagle perched on a sword hilt",
]

DREAM_MEANINGS = [
    "change approaches",
    "truth hidden beneath calm",
    "old promises stirring",
    "fate tightening its weave",
    "transformation nearing",
    "the world remembering",
    "forgotten bonds awakening",
    "power seeking a vessel",
    "a reckoning draws close",
    "the boundary between worlds thins",
    "something lost is calling out",
    "the gods are watching",
]

_STRENGTH_MAX = 99.9


class WorldDreams:
    """Atmospheric vision layer — symbolic dreams that foreshadow and connect."""

    def __init__(self):
        self.dreams = []
        self.symbols = DREAM_SYMBOLS[:]
        self.meanings = DREAM_MEANINGS[:]
        self.dream_interval = 7
        self.max_active = 5
        self.growth_rate = 1.03  # Older dreams grow more prophetic

    def update(self, turn_count, mythic_age_name=""):
        """Generate a new dream every N turns and grow existing dream strength."""
        try:
            if turn_count > 0 and turn_count % self.dream_interval == 0:
                dream = {
                    "symbol": random.choice(self.symbols),
                    "meaning": random.choice(self.meanings),
                    "origin_age": mythic_age_name,
                    "origin_turn": turn_count,
                    "strength": 1.0,
                }
                self.dreams.append(dream)
                self.dreams = self.dreams[-self.max_active:]
                logger.info(
                    "World dream: %s (%s)", dream["symbol"], dream["meaning"]
                )

            # Grow all existing dream strength; clamp to prevent inf/NaN leaking
            for d in self.dreams:
                d["strength"] *= self.growth_rate
                d["strength"] = min(d["strength"], _STRENGTH_MAX)

        except Exception:
            logger.error(
                "WorldDreams.update() failed; dreams state unchanged.",
                exc_info=True,
            )

    def build_context(self):
        """Build the world dreams context block for prompt injection."""
        try:
            if not self.dreams:
                return ""
            strongest = sorted(self.dreams, key=lambda d: d["strength"], reverse=True)[:2]
            lines = "\n".join([
                f"  - {d['symbol']} ({d['meaning']}, "
                f"strength: {'VIVID' if d['strength'] > 1.5 else 'growing' if d['strength'] > 1.1 else 'faint'})"
                for d in strongest
            ])
            return (
                "=== WORLD DREAMS (PROPHETIC VISIONS) ===\n"
                f"The world has been dreaming of:\n{lines}\n"
                "These symbols may appear naturally in narration, atmosphere, or NPC visions."
            )
        except Exception:
            logger.error(
                "WorldDreams.build_context() failed; returning empty string.",
                exc_info=True,
            )
            return ""

    def to_dict(self):
        """Serialize for save."""
        try:
            return {
                "dreams": self.dreams,
            }
        except Exception:
            logger.error(
                "WorldDreams.to_dict() failed; returning empty dreams.",
                exc_info=True,
            )
            return {"dreams": []}

    def from_dict(self, data):
        """Restore from save."""
        try:
            if data:
                self.dreams = data.get("dreams", [])
        except Exception:
            logger.error(
                "WorldDreams.from_dict() failed; leaving current dreams unchanged.",
                exc_info=True,
            )
