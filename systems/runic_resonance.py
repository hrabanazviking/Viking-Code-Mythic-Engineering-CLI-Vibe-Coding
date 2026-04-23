"""
Runic Resonance
===============

The world holds a metaphysical frequency. Actions alter it. Places
remember it. People feel it.

Each location possesses a ``ResonanceField`` — a float spanning from
-1.0 (pure chaos) to +1.0 (pure order). Actions tagged with a
``spiritual_weight`` shift the local field. A place where a massive
betrayal occurred permanently holds a "stagnant" or "chaotic"
resonance, subtly altering the psychology of anyone present.

The Runic Resonance system:
  - Modifies characters' Hugr (conscious) emotional baseline when
    they enter a location with extreme resonance.
  - Emits RESONANCE_SPIKE events when a location crosses thresholds.
  - Persists field state in WorldState per-location.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Spiritual weight categories for events
SPIRITUAL_EVENT_WEIGHTS: Dict[str, float] = {
    "player_action": 0.02,
    "murder": 0.30,
    "betrayal": 0.25,
    "oath_broken": 0.35,
    "sacred_rite": -0.20,  # Negative = toward order
    "heroic_deed": -0.10,
    "desecration": 0.40,
    "healing": -0.12,
    "sacrifice": 0.15,  # Even holy sacrifice adds some chaos
    "combat": 0.08,
}


@dataclass
class ResonanceField:
    """
    Per-location metaphysical frequency record.
    resonance: float in [-1.0 (pure order), +1.0 (pure chaos)]
    (Note: positive = chaos, negative = order, 0 = balance)
    """

    location_id: str
    resonance: float = 0.0
    event_history: List[Dict[str, Any]] = field(default_factory=list)
    decay_rate: float = 0.005  # Slow drift back toward balance per turn

    def shift(self, delta: float, cause: str, turn: int) -> float:
        """Shift the resonance field and record the cause."""
        old = self.resonance
        self.resonance = max(-1.0, min(1.0, self.resonance + delta))
        self.event_history.append(
            {
                "turn": turn,
                "delta": round(delta, 4),
                "cause": cause,
                "result": round(self.resonance, 4),
            }
        )
        if len(self.event_history) > 50:
            self.event_history = self.event_history[-50:]
        logger.debug(
            "Resonance[%s]: %.3f → %.3f (%s)",
            self.location_id,
            old,
            self.resonance,
            cause,
        )
        return self.resonance

    def decay(self):
        """Gently pull resonance back toward 0 each turn."""
        if abs(self.resonance) < self.decay_rate:
            self.resonance = 0.0
        elif self.resonance > 0:
            self.resonance -= self.decay_rate
        else:
            self.resonance += self.decay_rate

    @property
    def label(self) -> str:
        r = self.resonance
        if r >= 0.7:
            return "violently chaotic"
        if r >= 0.4:
            return "chaotic"
        if r >= 0.15:
            return "unsettled"
        if r <= -0.7:
            return "deeply sacred"
        if r <= -0.4:
            return "ordered"
        if r <= -0.15:
            return "calm"
        return "balanced"

    def get_psychological_modifier(self) -> Dict[str, float]:
        """
        Return emotion modifiers applied to characters present here.
        Negative resonance (order) → calm. Positive (chaos) → anxiety.
        """
        r = self.resonance
        mods: Dict[str, float] = {}
        if r > 0.3:
            mods["anxiety"] = r * 0.4
            mods["aggression"] = r * 0.3
        if r > 0.6:
            mods["dread"] = (r - 0.6) * 0.8
        if r < -0.3:
            mods["calm"] = abs(r) * 0.3
            mods["awe"] = abs(r) * 0.2
        return mods

    def get_ai_summary(self) -> str:
        mods = self.get_psychological_modifier()
        mod_str = (
            (", ".join(f"{k} +{v:.2f}" for k, v in mods.items())) if mods else "none"
        )
        return (
            f"Resonance[{self.location_id}]: {self.label} "
            f"({self.resonance:+.3f}) — psychological modifiers: {mod_str}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "location_id": self.location_id,
            "resonance": self.resonance,
            "event_history": self.event_history,
            "decay_rate": self.decay_rate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResonanceField":
        obj = cls(
            location_id=data["location_id"],
            resonance=data.get("resonance", 0.0),
            decay_rate=data.get("decay_rate", 0.005),
        )
        obj.event_history = data.get("event_history", [])
        return obj


class RunicResonance:
    """
    World-wide runic resonance manager.
    Maintains a ``ResonanceField`` per known location.
    """

    SPIKE_THRESHOLD = 0.55  # Resonance magnitude triggers event

    def __init__(self, dispatcher=None):
        self._fields: Dict[str, ResonanceField] = {}
        self.dispatcher = dispatcher

    def get_field(self, location_id: str) -> ResonanceField:
        if location_id not in self._fields:
            self._fields[location_id] = ResonanceField(location_id=location_id)
        return self._fields[location_id]

    def apply_event(
        self,
        location_id: str,
        event_type: str,
        turn: int,
        custom_weight: Optional[float] = None,
    ):
        """
        Apply a spiritually-weighted event to the location's field.
        """
        weight = (
            custom_weight
            if custom_weight is not None
            else (SPIRITUAL_EVENT_WEIGHTS.get(event_type, 0.02))
        )
        field = self.get_field(location_id)
        prev_magnitude = abs(field.resonance)
        field.shift(weight, event_type, turn)
        new_magnitude = abs(field.resonance)

        # Emit resonance spike event if threshold crossed
        if (
            new_magnitude >= self.SPIKE_THRESHOLD
            and prev_magnitude < self.SPIKE_THRESHOLD
            and self.dispatcher
        ):
            try:
                from systems.event_dispatcher import EventType

                self.dispatcher.dispatch(
                    EventType.RESONANCE_SPIKE.value,
                    {
                        "location_id": location_id,
                        "resonance": field.resonance,
                        "label": field.label,
                        "turn": turn,
                    },
                )
            except Exception as exc:
                logger.warning("Failed to dispatch RESONANCE_SPIKE: %s", exc)

    def tick_all(self):
        """Apply decay to all fields each turn."""
        for f in self._fields.values():
            f.decay()

    def apply_to_characters(self, location_id: str, soul_registry, turn: int):
        """
        Pull psychological modifiers from the location resonance field
        and apply them to every soul in the registry currently there.
        Only call this for characters confirmed at this location.
        """
        field = self.get_field(location_id)
        mods = field.get_psychological_modifier()
        if not mods or not soul_registry:
            return
        for soul in soul_registry._souls.values():
            for emotion, delta in mods.items():
                soul.hugr.apply(emotion, delta * 0.5, turn)

    def get_ai_context(self, location_id: Optional[str] = None) -> str:
        """Return resonance context for AI narrator."""
        if location_id:
            if location_id in self._fields:
                return self._fields[location_id].get_ai_summary()
            return ""
        lines = [f.get_ai_summary() for f in self._fields.values()]
        return "RUNIC RESONANCE:\n" + "\n".join(lines) if lines else ""

    def to_dict(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self._fields.items()}

    def load_from_dict(self, data: Dict[str, Any]):
        for loc_id, field_data in data.items():
            self._fields[loc_id] = ResonanceField.from_dict(field_data)
        logger.info("RunicResonance loaded %d fields", len(self._fields))
