"""
Wyrd Tethers
============

Spiritual and ancestral bonds that transcend ordinary relationship logic.

Two types of metaphysical tethers exist in the Norse worldview:

  BloodOath — A sworn spiritual contract between two characters.
              Breaking it permanently damages the offender's Hamingja
              (spiritual momentum) and dispatches an OATH_BROKEN event.

  AncestralDebt — An inherited alliance or grudge from a character's
                  lineage. Auto-loaded from character YAML seeds.
                  Characters may be forced into historical conflicts
                  they personally never started.

Both types are stored in WorldState and hydrate the AI Narrator's
relationship context to ensure the prose reflects spiritual weight.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Blood Oath
# ---------------------------------------------------------------------------


@dataclass
class BloodOath:
    """
    A sworn spiritual contract between two characters.
    Breaking it fires OATH_BROKEN and damages the offender's Hamingja.
    """

    oath_id: str
    swearer_id: str  # The character who swore
    witness_id: str  # The character it was sworn to
    terms: str  # Description of what was promised
    sworn_at_turn: int
    fulfilled: bool = False
    broken: bool = False
    broken_at_turn: Optional[int] = None
    hamingja_penalty: float = 0.25  # Applied to swearer's spiritual soul

    def break_oath(self, current_turn: int, soul_registry=None, dispatcher=None):
        """
        Mark the oath broken, penalize Hamingja, dispatch OATH_BROKEN.
        """
        if self.broken or self.fulfilled:
            return

        self.broken = True
        self.broken_at_turn = current_turn

        # Damage swearer's spiritual momentum
        if soul_registry:
            soul = soul_registry.get_or_create(self.swearer_id)
            soul.hamingja.shift(
                -self.hamingja_penalty, f"Blood oath broken: {self.oath_id}"
            )
            # The subconscious also remembers
            soul.fylgja.add_trauma(f"oath_broken:{self.oath_id}")
            logger.info(
                "BloodOath '%s' broken by %s — hamingja penalized %.2f",
                self.oath_id,
                self.swearer_id,
                self.hamingja_penalty,
            )

        # Dispatch event
        if dispatcher:
            try:
                from systems.event_dispatcher import EventType

                dispatcher.dispatch(
                    EventType.OATH_BROKEN.value,
                    {
                        "oath_id": self.oath_id,
                        "swearer_id": self.swearer_id,
                        "witness_id": self.witness_id,
                        "terms": self.terms,
                        "hamingja_penalty": self.hamingja_penalty,
                        "turn": current_turn,
                    },
                )
            except Exception as exc:
                logger.warning("Failed to dispatch OATH_BROKEN: %s", exc)

    def fulfill_oath(self, current_turn: int, soul_registry=None):
        """Mark the oath fulfilled — grants a small Hamingja bonus."""
        if self.broken or self.fulfilled:
            return
        self.fulfilled = True
        if soul_registry:
            soul = soul_registry.get_or_create(self.swearer_id)
            soul.hamingja.shift(0.1, f"Blood oath honored: {self.oath_id}")
        logger.info("BloodOath '%s' fulfilled by %s", self.oath_id, self.swearer_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "oath_id": self.oath_id,
            "swearer_id": self.swearer_id,
            "witness_id": self.witness_id,
            "terms": self.terms,
            "sworn_at_turn": self.sworn_at_turn,
            "fulfilled": self.fulfilled,
            "broken": self.broken,
            "broken_at_turn": self.broken_at_turn,
            "hamingja_penalty": self.hamingja_penalty,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BloodOath":
        return cls(
            oath_id=data["oath_id"],
            swearer_id=data["swearer_id"],
            witness_id=data["witness_id"],
            terms=data.get("terms", ""),
            sworn_at_turn=data.get("sworn_at_turn", 0),
            fulfilled=data.get("fulfilled", False),
            broken=data.get("broken", False),
            broken_at_turn=data.get("broken_at_turn"),
            hamingja_penalty=data.get("hamingja_penalty", 0.25),
        )


# ---------------------------------------------------------------------------
# Ancestral Debt
# ---------------------------------------------------------------------------


@dataclass
class AncestralDebt:
    """
    An inherited alliance or grudge from a character's lineage.
    These cannot be dismissed — they impose obligations or enmity that
    bypass normal emotional relationship logic.
    """

    debt_id: str
    holder_id: str  # The character who inherits this debt
    counterpart_id: str  # Bloodline/faction owed to or feuding with
    debt_type: str  # 'alliance', 'blood_feud', 'debt_of_honor'
    description: str
    generation: int = 1  # How many generations back (affects weight)
    active: bool = True

    @property
    def weight(self) -> float:
        """
        Older debts carry more mythic weight but less urgent obligation.
        Returns 0.0–1.0.
        """
        return max(0.1, 1.0 - (self.generation - 1) * 0.15)

    def get_ai_context(self) -> str:
        """Return brief AI-readable summary."""
        gen_label = (
            "their own"
            if self.generation == 1
            else f"their {self.generation}-generation ancestor's"
        )
        return (
            f"{self.holder_id} carries {gen_label} "
            f"{self.debt_type.replace('_', ' ')} with "
            f"{self.counterpart_id}: {self.description}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "debt_id": self.debt_id,
            "holder_id": self.holder_id,
            "counterpart_id": self.counterpart_id,
            "debt_type": self.debt_type,
            "description": self.description,
            "generation": self.generation,
            "active": self.active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AncestralDebt":
        return cls(
            debt_id=data["debt_id"],
            holder_id=data["holder_id"],
            counterpart_id=data["counterpart_id"],
            debt_type=data.get("debt_type", "debt_of_honor"),
            description=data.get("description", ""),
            generation=data.get("generation", 1),
            active=data.get("active", True),
        )


# ---------------------------------------------------------------------------
# Tether Registry
# ---------------------------------------------------------------------------


class WyrdTethers:
    """
    Central registry for all spiritual tethers (oaths and debts).
    Attached to WorldState and consulted each turn.
    """

    def __init__(self, soul_registry=None, dispatcher=None):
        self._oaths: Dict[str, BloodOath] = {}
        self._debts: Dict[str, AncestralDebt] = {}
        self.soul_registry = soul_registry
        self.dispatcher = dispatcher

    # --- Blood Oaths -------------------------------------------------------

    def register_oath(
        self,
        swearer_id: str,
        witness_id: str,
        terms: str,
        turn: int,
        hamingja_penalty: float = 0.25,
    ) -> BloodOath:
        oath_id = f"oath_{swearer_id}_{turn}"
        oath = BloodOath(
            oath_id=oath_id,
            swearer_id=swearer_id,
            witness_id=witness_id,
            terms=terms,
            sworn_at_turn=turn,
            hamingja_penalty=hamingja_penalty,
        )
        self._oaths[oath_id] = oath
        logger.info("BloodOath registered: %s swears to %s", swearer_id, witness_id)
        return oath

    def break_oath(self, oath_id: str, turn: int) -> Optional[BloodOath]:
        oath = self._oaths.get(oath_id)
        if oath:
            oath.break_oath(
                turn,
                soul_registry=self.soul_registry,
                dispatcher=self.dispatcher,
            )
        return oath

    def fulfill_oath(self, oath_id: str, turn: int) -> Optional[BloodOath]:
        oath = self._oaths.get(oath_id)
        if oath:
            oath.fulfill_oath(turn, soul_registry=self.soul_registry)
        return oath

    # --- Ancestral Debts ---------------------------------------------------

    def register_debt(
        self,
        holder_id: str,
        counterpart_id: str,
        debt_type: str,
        description: str,
        generation: int = 1,
    ) -> AncestralDebt:
        debt_id = f"debt_{holder_id}_{counterpart_id}"
        debt = AncestralDebt(
            debt_id=debt_id,
            holder_id=holder_id,
            counterpart_id=counterpart_id,
            debt_type=debt_type,
            description=description,
            generation=generation,
        )
        self._debts[debt_id] = debt
        return debt

    def load_from_character(self, character_id: str, char_data: Dict[str, Any]):
        """
        Auto-seed ancestral debts from character YAML
        ``ancestral_debts`` field.
        """
        debts = char_data.get("ancestral_debts", [])
        if not isinstance(debts, list):
            return
        for raw in debts:
            if not isinstance(raw, dict):
                continue
            self.register_debt(
                holder_id=character_id,
                counterpart_id=raw.get("with", "unknown"),
                debt_type=raw.get("type", "debt_of_honor"),
                description=raw.get("description", ""),
                generation=raw.get("generation", 1),
            )

    # --- Context -----------------------------------------------------------

    def get_ai_context(self, character_id: Optional[str] = None) -> str:
        """Return tether context for the AI narrator."""
        lines = []

        # Active oaths
        for oath in self._oaths.values():
            if not oath.broken and not oath.fulfilled:
                if character_id is None or character_id in (
                    oath.swearer_id,
                    oath.witness_id,
                ):
                    lines.append(
                        f"OATH [{oath.oath_id}]: "
                        f"{oath.swearer_id} is bound to "
                        f"{oath.witness_id}: {oath.terms}"
                    )

        # Ancestral debts
        for debt in self._debts.values():
            if debt.active and (character_id is None or debt.holder_id == character_id):
                lines.append(debt.get_ai_context())

        if not lines:
            return ""
        return "WYRD TETHERS:\n" + "\n".join(lines)

    # --- Persistence -------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "oaths": {k: v.to_dict() for k, v in self._oaths.items()},
            "debts": {k: v.to_dict() for k, v in self._debts.items()},
        }

    def load_from_dict(self, data: Dict[str, Any]):
        for k, v in data.get("oaths", {}).items():
            self._oaths[k] = BloodOath.from_dict(v)
        for k, v in data.get("debts", {}).items():
            self._debts[k] = AncestralDebt.from_dict(v)
        logger.info(
            "WyrdTethers loaded: %d oaths, %d debts", len(self._oaths), len(self._debts)
        )
