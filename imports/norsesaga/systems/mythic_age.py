"""
Mythic Age — Era-level World Context (20+ turns per age)

The world breathes through mythic eras. Each age colors the entire
atmosphere, the types of events that emerge, and how the world
responds to player actions. Ages cycle like seasons of fate.

Part of the Norse Saga Engine Myth Engine (v4.2.0)
"""
import logging

logger = logging.getLogger(__name__)

MYTHIC_AGES = [
    ("Age of Awakening", "discovery, curiosity, new bonds — the world stirs from sleep"),
    ("Age of Expansion", "growth, exploration, alliances forming — horizons widen"),
    ("Age of Strife", "conflict rises, pressure builds, opposing forces clash"),
    ("Age of Shadows", "uncertainty, hidden truths, difficult choices — darkness gathers"),
    ("Age of Revelation", "truths emerge, fate clarifies, turning points — the veil thins"),
    ("Age of Renewal", "healing, rebuilding, transformation complete — the world reborn"),
]


class MythicAge:
    """Era-level atmosphere layer — the world breathes through mythic eras."""

    def __init__(self):
        self.age_index = 0
        self.age_turn_start = 0
        self.turns_per_age = 20
        self.cycle_count = 0

    @property
    def current_age(self):
        return MYTHIC_AGES[self.age_index]

    @property
    def age_name(self):
        return self.current_age[0]

    @property
    def age_description(self):
        return self.current_age[1]

    def update(self, turn_count, force_advance=False):
        """Advance the mythic age if enough turns have passed."""
        turns_in_age = turn_count - self.age_turn_start
        if turns_in_age > self.turns_per_age or force_advance:
            old_age = self.age_name
            self.age_index = (self.age_index + 1) % len(MYTHIC_AGES)
            self.age_turn_start = turn_count
            if self.age_index == 0:
                self.cycle_count += 1
            logger.info(f"Mythic Age advanced: {old_age} → {self.age_name} (cycle {self.cycle_count})")

    def build_context(self):
        """Build the mythic age context block for prompt injection."""
        name, desc = self.current_age
        return (
            f"=== MYTHIC AGE: {name.upper()} ===\n"
            f"{desc}\n"
            "The entire world is colored by this era. "
            "NPCs, events, and atmosphere should reflect this age."
        )

    def to_dict(self):
        """Serialize for save."""
        return {
            "age_index": self.age_index,
            "age_turn_start": self.age_turn_start,
            "cycle_count": self.cycle_count,
        }

    def from_dict(self, data):
        """Restore from save."""
        if data:
            self.age_index = data.get("age_index", 0)
            self.age_turn_start = data.get("age_turn_start", 0)
            self.cycle_count = data.get("cycle_count", 0)
