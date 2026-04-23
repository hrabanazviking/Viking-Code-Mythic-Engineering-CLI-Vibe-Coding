"""
Mythic Mirror — Player Identity Reflection (continuous)

The world perceives and reflects the player's emerging legend.
Tracks behavioral signals across turns to detect the player's
archetype, which shapes how NPCs and the world respond.

Part of the Norse Saga Engine Myth Engine (v4.2.0)
"""
import logging

logger = logging.getLogger(__name__)

ARCHETYPE_MAP = {
    "exploration": ("wanderer", "One who seeks what lies beyond the horizon"),
    "loyalty": ("oathkeeper", "One whose word is iron and whose bonds are unbreakable"),
    "conflict": ("stormbringer", "One who draws battle like thunder draws lightning"),
    "mystery": ("seer", "One who walks between worlds and reads the threads of fate"),
    "mercy": ("peaceweaver", "One who mends what is broken and soothes what burns"),
    "change": ("shapeshifter", "One who adapts, transforms, and defies expectation"),
}

# Keywords that signal each behavioral tendency
SIGNAL_KEYWORDS = {
    "mercy": ["spare", "forgive", "mercy", "heal", "help", "comfort", "save", "tend", "gentle", "peace"],
    "conflict": ["fight", "attack", "strike", "kill", "battle", "slay", "challenge", "duel", "charge", "rage"],
    "exploration": ["explore", "search", "investigate", "discover", "wander", "travel", "look", "examine", "venture", "seek"],
    "loyalty": ["protect", "defend", "oath", "honor", "loyal", "vow", "pledge", "shield", "guard", "serve"],
    "mystery": ["rune", "vision", "prophecy", "dream", "mystery", "seidr", "magic", "ritual", "omen", "spirit"],
    "change": ["change", "transform", "become", "reshape", "evolve", "adapt", "shift", "new", "different", "reborn"],
}


class MythicMirror:
    """Player identity layer — tracks behavior and reflects emerging archetype."""

    def __init__(self):
        self.archetype = "wanderer"
        self.archetype_description = "One who seeks what lies beyond the horizon"
        self.titles = []
        self.signals = {
            "mercy": 0, "conflict": 0, "exploration": 0,
            "loyalty": 0, "mystery": 0, "change": 0,
        }
        self._previous_archetype = "wanderer"

    def update_from_turn(self, player_input, narrative):
        """Analyze player input and narrative for behavioral signals."""
        text = (player_input + " " + narrative).lower()

        for signal_type, keywords in SIGNAL_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    self.signals[signal_type] += 1

        # Determine strongest signal
        strongest = max(self.signals, key=self.signals.get)

        # Only shift archetype if the signal is meaningfully dominant
        total = sum(self.signals.values())
        if total > 0:
            dominance = self.signals[strongest] / total
            if dominance > 0.25:  # At least 25% of all signals
                archetype_data = ARCHETYPE_MAP.get(strongest, ("wanderer", "One who wanders"))
                self._previous_archetype = self.archetype
                self.archetype = archetype_data[0]
                self.archetype_description = archetype_data[1]

                if self.archetype != self._previous_archetype:
                    logger.info(f"Mythic Mirror shifted: {self._previous_archetype} → {self.archetype}")

    def add_title(self, title):
        """Award a player title based on actions."""
        if title not in self.titles:
            self.titles.append(title)
            self.titles = self.titles[-5:]  # Keep last 5 titles
            logger.info(f"Player title awarded: {title}")

    def build_context(self):
        """Build the mythic mirror context block for prompt injection."""
        parts = [
            "=== MYTHIC MIRROR (PLAYER LEGEND) ===",
            f"The world sees this player as: THE {self.archetype.upper()}",
            f"  \"{self.archetype_description}\"",
        ]
        if self.titles:
            parts.append("Known as: " + ", ".join(self.titles[-3:]))

        # Show signal balance for nuanced portrayal
        total = sum(self.signals.values())
        if total > 5:
            top_signals = sorted(self.signals.items(), key=lambda x: x[1], reverse=True)[:3]
            signal_str = ", ".join([f"{k}: {v}" for k, v in top_signals if v > 0])
            parts.append(f"Behavioral tendencies: {signal_str}")

        parts.append("NPCs may react to the player's reputation and emerging legend.")
        return "\n".join(parts)

    def to_dict(self):
        """Serialize for save."""
        return {
            "archetype": self.archetype,
            "archetype_description": self.archetype_description,
            "titles": self.titles,
            "signals": self.signals,
        }

    def from_dict(self, data):
        """Restore from save."""
        if data:
            self.archetype = data.get("archetype", "wanderer")
            self.archetype_description = data.get("archetype_description", "One who seeks what lies beyond the horizon")
            self.titles = data.get("titles", [])
            self.signals = data.get("signals", {
                "mercy": 0, "conflict": 0, "exploration": 0,
                "loyalty": 0, "mystery": 0, "change": 0,
            })
