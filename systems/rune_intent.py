"""
Rune Intent — Short-term Fate (1-3 turns)

A 3-rune spread (Past/Present/Future) drawn every 3 turns,
injected into the prompt as symbolic direction for the narrative.
The runes shape probability and meaning, not scripted events.

Part of the Norse Saga Engine Myth Engine (v4.2.0)
"""
import random
import logging

logger = logging.getLogger(__name__)

RUNES = {
    "Fehu": "wealth, abundance, fulfillment",
    "Uruz": "strength, primal force, endurance",
    "Thurisaz": "conflict, defense, reactive force",
    "Ansuz": "wisdom, messages, revelation",
    "Raidho": "journey, movement, alignment",
    "Kenaz": "illumination, change, creative fire",
    "Gebo": "exchange, bonds, sacred gift",
    "Wunjo": "joy, harmony, fellowship",
    "Hagalaz": "disruption, sudden change, hailstorm",
    "Nauthiz": "necessity, constraint, endurance through hardship",
    "Isa": "stillness, patience, frozen potential",
    "Jera": "harvest, cycles, earned reward",
    "Eihwaz": "transformation, death/rebirth, the yew tree",
    "Perthro": "fate, mystery, the unknown",
    "Algiz": "protection, divine connection, sanctuary",
    "Sowilo": "victory, vitality, the sun's power",
    "Tiwaz": "honor, justice, decisive action",
    "Berkano": "growth, nurturing, new beginnings",
    "Ehwaz": "partnership, trust, movement together",
    "Mannaz": "humanity, community, self-awareness",
    "Laguz": "emotion, intuition, the deep waters",
    "Ingwaz": "potential, gestation, inner fire",
    "Dagaz": "breakthrough, dawn, radical clarity",
    "Othala": "heritage, ancestral wisdom, homeland",
}


class RuneIntent:
    """Short-term fate layer — 3-rune spread every 3 turns."""

    def __init__(self):
        self.current_spread = None
        self.last_draw_turn = 0
        self.draw_interval = 3
        self.history = []  # Past spreads for continuity

    def update(self, turn_count, chaos_factor=30):
        """Draw a new 3-rune spread if the interval has passed."""
        if turn_count - self.last_draw_turn >= self.draw_interval or self.current_spread is None:
            try:
                chaos_factor = max(1, min(100, int(chaos_factor)))
            except (TypeError, ValueError):
                logger.warning(
                    "RuneIntent.update() received non-numeric chaos_factor %r; using default 30.",
                    chaos_factor,
                )
                chaos_factor = 30
            pool = list(RUNES.keys())
            # Higher chaos weights disruptive runes
            if chaos_factor >= 75:
                pool += ["Hagalaz", "Thurisaz", "Nauthiz"] * 2
            elif chaos_factor >= 55:
                pool += ["Hagalaz", "Perthro"] * 1
            # Low chaos favors stable runes
            elif chaos_factor <= 25:
                pool += ["Wunjo", "Jera", "Gebo", "Sowilo"] * 1

            self.current_spread = random.sample(pool, 3)
            self.last_draw_turn = turn_count

            # Keep history of last 5 spreads
            self.history.append(self.current_spread[:])
            self.history = self.history[-5:]

            logger.info(f"Rune Intent drawn: {self.current_spread}")

    def build_context(self):
        """Build the rune intent context block for prompt injection."""
        if not self.current_spread:
            return ""
        past, present, future = self.current_spread
        return (
            "=== ᚱ RUNE INTENT (FATE READING) ᚱ ===\n"
            f"Past Influence: {past} — {RUNES[past]}\n"
            f"Present Force: {present} — {RUNES[present]}\n"
            f"Future Pull: {future} — {RUNES[future]}\n"
            "Let this evolving fate subtly color the tone, encounters, and events of the narration."
        )

    def to_dict(self):
        """Serialize for save."""
        return {
            "current_spread": self.current_spread,
            "last_draw_turn": self.last_draw_turn,
            "history": self.history,
        }

    def from_dict(self, data):
        """Restore from save."""
        if data:
            self.current_spread = data.get("current_spread")
            self.last_draw_turn = data.get("last_draw_turn", 0)
            self.history = data.get("history", [])

    # ── SRD condition probability modifiers ────────────────────────────────

    # Rune → {condition_name: probability_weight_modifier}
    # Positive values increase the chance that condition applies in encounters;
    # negative values reduce the chance. These are additive bonuses to any
    # base chance the system already calculates.
    _RUNE_CONDITION_WEIGHTS: dict = {
        "Thurisaz":  {"grappled": +0.15, "prone": +0.10, "stunned": +0.08},
        "Hagalaz":   {"prone": +0.20, "frightened": +0.15, "exhaustion": +0.10},
        "Nauthiz":   {"exhaustion": +0.15, "restrained": +0.10},
        "Isa":       {"paralyzed": +0.10, "restrained": +0.10, "exhaustion": +0.08},
        "Eihwaz":    {"unconscious": +0.12, "poisoned": +0.08},
        "Perthro":   {"charmed": +0.12, "poisoned": +0.08},
        "Laguz":     {"charmed": +0.10, "frightened": +0.05},
        "Algiz":     {"frightened": -0.15, "charmed": -0.10, "prone": -0.10},
        "Sowilo":    {"frightened": -0.20, "exhaustion": -0.15, "paralyzed": -0.10},
        "Wunjo":     {"frightened": -0.15, "charmed": -0.08},
        "Tiwaz":     {"prone": -0.08, "grappled": -0.08, "restrained": -0.08},
        "Uruz":      {"stunned": -0.10, "paralyzed": -0.08, "exhaustion": -0.12},
        "Berkano":   {"poisoned": -0.10, "exhaustion": -0.10},
        "Dagaz":     {"blinded": -0.12, "frightened": -0.12, "unconscious": -0.10},
        "Mannaz":    {"charmed": -0.08, "frightened": -0.08},
    }

    def get_condition_modifiers(self) -> dict:
        """Return a dict of {condition_name: combined_weight_modifier} for the
        current 3-rune spread.

        These modifiers can be used by combat, encounter, and lore systems to
        adjust condition probability or resistance based on the current fate
        reading. Values are floats summed across all three runes in the spread.

        Returns an empty dict if no spread has been drawn yet.
        """
        if not self.current_spread:
            return {}
        combined: dict = {}
        for rune in self.current_spread:
            for cond, weight in self._RUNE_CONDITION_WEIGHTS.get(rune, {}).items():
                combined[cond] = combined.get(cond, 0.0) + weight
        return combined

    def get_narrative_condition_hints(self) -> list:
        """Return a list of human-readable condition hints derived from the rune
        spread — for injection into the AI prompt as subtle probability cues.

        Only includes conditions with a non-trivial combined modifier (>= 0.05
        or <= -0.05).
        """
        mods = self.get_condition_modifiers()
        hints = []
        for cond, mod in sorted(mods.items(), key=lambda x: abs(x[1]), reverse=True):
            if mod >= 0.05:
                hints.append(f"The runes suggest {cond} is more likely this turn (+{mod:.0%})")
            elif mod <= -0.05:
                hints.append(f"The runes suggest {cond} is less likely this turn ({mod:.0%})")
        return hints
