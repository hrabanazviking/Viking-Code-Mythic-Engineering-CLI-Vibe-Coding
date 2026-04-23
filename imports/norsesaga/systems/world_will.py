"""
World Will — World Consciousness (slow evolution, 8-12 turns)

The world itself develops desires and atmospheric direction.
Not player-driven, not random — the world has a will of its own
that slowly shifts based on chaos, gravity anchors, and time.

Part of the Norse Saga Engine Myth Engine (v4.2.0)
"""
import random
import logging

logger = logging.getLogger(__name__)

WORLD_DESIRES = [
    "seek transformation",
    "restore balance",
    "test the worthy",
    "reveal hidden truths",
    "forge new bonds",
    "break old chains",
    "remember what was forgotten",
    "punish betrayal",
    "reward courage",
    "stir dormant powers",
    "call wanderers home",
    "birth something new",
]

WORLD_TONES = [
    "quiet mythic unease",
    "rising tension",
    "brooding stillness",
    "fierce urgency",
    "melancholy beauty",
    "wild anticipation",
    "solemn grandeur",
    "warm golden calm",
    "cold iron resolve",
    "dreaming awareness",
]

WORLD_FOCUSES = [
    "relationships shifting",
    "power changing hands",
    "ancestral debts surfacing",
    "the land itself stirring",
    "old alliances tested",
    "new paths opening",
    "fate tightening its weave",
    "the boundary between worlds thinning",
]


class WorldWill:
    """World consciousness layer — the world develops desires and atmosphere."""

    def __init__(self):
        self.desire = "seek transformation"
        self.tone = "quiet mythic unease"
        self.focus = "relationships shifting"
        self.age = 0
        self.shift_interval = 8

    def update(self, chaos_factor=30, strongest_anchor_theme=None):
        """Evolve the world's will based on chaos and narrative gravity."""
        # ── Input coercion — callers may pass wrong types ──────────────────
        try:
            chaos_factor = int(chaos_factor)
            # Huginn scouts the temperature of wyrd: chaos flows on a 1-100 scale.
            chaos_factor = max(1, min(100, chaos_factor))
        except (TypeError, ValueError):
            logger.warning(
                "WorldWill.update() received non-numeric chaos_factor %r; using default 30.",
                chaos_factor,
            )
            chaos_factor = 30

        if strongest_anchor_theme is not None and not isinstance(strongest_anchor_theme, str):
            logger.warning(
                "WorldWill.update() received non-string strongest_anchor_theme %r; ignoring.",
                strongest_anchor_theme,
            )
            strongest_anchor_theme = None

        # ── Main update logic ───────────────────────────────────────────────
        try:
            self.age += 1

            if strongest_anchor_theme:
                # The world's gaze tracks the loudest saga thread in real time.
                self.focus = strongest_anchor_theme

            # High chaos drives the world toward unpredictability
            if chaos_factor >= 75:
                self.desire = random.choice([
                    "unpredictable change", "test the worthy",
                    "break old chains", "stir dormant powers"
                ])
                self.tone = random.choice([
                    "rising tension", "fierce urgency", "wild anticipation"
                ])
            elif chaos_factor <= 25:
                self.desire = random.choice([
                    "restore balance", "forge new bonds",
                    "reward courage", "warm golden calm"
                ])
                self.tone = random.choice([
                    "warm golden calm", "solemn grandeur", "dreaming awareness"
                ])

            # Periodic full shift
            if self.age % self.shift_interval == 0:
                self.desire = random.choice(WORLD_DESIRES)
                self.tone = random.choice(WORLD_TONES)
                self.focus = random.choice(WORLD_FOCUSES)

                # Let the strongest saga anchor pull the world's focus
                if strongest_anchor_theme:
                    self.focus = strongest_anchor_theme

                logger.info(
                    "World Will shifted: desire=%s, tone=%s, focus=%s",
                    self.desire, self.tone, self.focus,
                )
        except Exception:
            logger.error(
                "WorldWill.update() failed; world will state unchanged.",
                exc_info=True,
            )

    def build_context(self):
        """Build the world will context block for prompt injection."""
        try:
            return (
                "=== WORLD WILL ===\n"
                f"The world desires: {self.desire}\n"
                f"Atmospheric tone: {self.tone}\n"
                f"Narrative focus: {self.focus}\n"
                "Events may subtly move in this direction even without player intent."
            )
        except Exception:
            logger.error(
                "WorldWill.build_context() failed; returning empty string.",
                exc_info=True,
            )
            return ""

    def to_dict(self):
        """Serialize for save."""
        try:
            return {
                "desire": self.desire,
                "tone": self.tone,
                "focus": self.focus,
                "age": self.age,
            }
        except Exception:
            logger.error(
                "WorldWill.to_dict() failed; returning defaults.",
                exc_info=True,
            )
            return {
                "desire": "seek transformation",
                "tone": "quiet mythic unease",
                "focus": "relationships shifting",
                "age": 0,
            }

    def from_dict(self, data):
        """Restore from save."""
        try:
            if data:
                self.desire = data.get("desire", "seek transformation")
                self.tone = data.get("tone", "quiet mythic unease")
                self.focus = data.get("focus", "relationships shifting")
                self.age = data.get("age", 0)
        except Exception:
            logger.error(
                "WorldWill.from_dict() failed; leaving current state unchanged.",
                exc_info=True,
            )
