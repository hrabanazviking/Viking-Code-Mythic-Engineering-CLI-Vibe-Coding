"""
Stress System
=============

Registry of StressAccumulator objects — one per active character.

Stress accumulates from internalized (suppressed) emotions that never
reach the expression threshold. When it breaches defined thresholds it
fires STRESS_SPIKE and STRESS_BREAKDOWN events through the EventDispatcher.

This system sits alongside soul_mechanics.py's CognitiveFriction — they
are complementary:
  CognitiveFriction — dissonance between values and actions
  StressSystem      — residual pressure from unexpressed emotions
"""

import logging
from typing import Dict, Any, Optional, List

from systems.emotional_engine import StressAccumulator

logger = logging.getLogger(__name__)


class StressSystem:
    """
    Central registry for per-character stress accumulators.

    Attached to YggdrasilEngine and ticked each turn via tick_all().
    """

    STRESS_STAGES = [
        (90.0, "crisis"),
        (75.0, "panic_risk"),
        (55.0, "impaired_focus"),
        (30.0, "unease"),
        (0.0, "composed"),
    ]

    RITUAL_EFFECTS = {
        "fire_vigil": {
            "stress_delta": -16.0,
            "note": "fear rumination softened by fire vigil",
        },
        "oath_speaking": {
            "stress_delta": -10.0,
            "note": "heart steadied through oath-speaking",
        },
        "night_watch": {
            "stress_delta": -8.0,
            "note": "anger tempered into watchful resolve",
        },
        "communal_feast": {
            "stress_delta": -12.0,
            "note": "burden eased by feast-bond fellowship",
        },
    }

    def __init__(self, dispatcher=None):
        self._accumulators: Dict[str, StressAccumulator] = {}
        self.dispatcher = dispatcher
        self._last_stage: Dict[str, str] = {}
        self._recovery_imprints: Dict[str, List[Dict[str, Any]]] = {}

        if self.dispatcher:
            try:
                from systems.event_dispatcher import EventType

                # Subscribe to EMOTION_SPIKED so we can check suppression
                self.dispatcher.subscribe(
                    EventType.EMOTION_SPIKED.value,
                    self._on_emotion_spiked,
                )
            except Exception as exc:
                logger.warning(
                    "StressSystem could not subscribe to EMOTION_SPIKED: %s", exc
                )

        logger.info("StressSystem initialized")

    # -- Accumulator access -------------------------------------------------

    def get_or_create(self, character_id: str) -> StressAccumulator:
        if character_id not in self._accumulators:
            self._accumulators[character_id] = StressAccumulator(
                character_id=character_id
            )
        return self._accumulators[character_id]

    def accumulate(
        self,
        character_id: str,
        suppressed: Dict[str, float],
        resistance: float = 0.5,
    ):
        """Feed suppressed emotion amounts into the character's stress pool."""
        acc = self.get_or_create(character_id)
        acc.accumulate(suppressed, resistance)

    @classmethod
    def stage_for_stress(cls, stress_level: float) -> str:
        """Return stage label for a stress value."""
        for threshold, label in cls.STRESS_STAGES:
            if stress_level >= threshold:
                return label
        return "composed"

    def apply_ritual_recovery(
        self,
        character_id: str,
        ritual_type: str,
        turn: int,
    ) -> Dict[str, Any]:
        """Apply ritual stress relief and store a recovery imprint."""
        effect = self.RITUAL_EFFECTS.get(ritual_type, self.RITUAL_EFFECTS["fire_vigil"])
        acc = self.get_or_create(character_id)
        before = acc.stress_level
        acc.stress_level = max(0.0, min(100.0, acc.stress_level + float(effect["stress_delta"])))
        after = acc.stress_level
        imprint = {
            "turn": int(turn),
            "ritual": ritual_type,
            "from": round(before, 1),
            "to": round(after, 1),
            "note": str(effect.get("note", "ritual recovery")),
        }
        self._recovery_imprints.setdefault(character_id, []).append(imprint)
        self._recovery_imprints[character_id] = self._recovery_imprints[character_id][-20:]
        return imprint

    # -- Turn tick ----------------------------------------------------------

    def tick_all(self, turn: int):
        """
        Decay stress for all characters and dispatch any threshold events.
        Call once per turn, after emotional state updates.
        """
        for char_id, acc in list(self._accumulators.items()):
            acc.decay_turn()
            stage = self.stage_for_stress(acc.stress_level)
            prior = self._last_stage.get(char_id, "composed")
            self._last_stage[char_id] = stage
            if stage != prior and stage != "composed":
                logger.info(
                    "Stress stage shift for %s: %s -> %s (%.1f)",
                    char_id,
                    prior,
                    stage,
                    acc.stress_level,
                )
            events = acc.check_events()
            for ev_str in events:
                self._dispatch_stress_event(ev_str, acc, turn)

    def _dispatch_stress_event(self, event_str: str, acc: StressAccumulator, turn: int):
        if not self.dispatcher:
            return
        try:
            from systems.event_dispatcher import EventType

            kind, char_id = event_str.split(":", 1)
            if kind == "STRESS_BREAKDOWN":
                self.dispatcher.dispatch(
                    EventType.COGNITIVE_BREAKDOWN.value,
                    {
                        "character_id": char_id,
                        "stress_level": acc.stress_level,
                        "trigger": "stress_accumulation",
                        "turn": turn,
                    },
                )
                logger.warning(
                    "Stress breakdown dispatched for %s (stress=%.1f)",
                    char_id,
                    acc.stress_level,
                )
            elif kind == "STRESS_SPIKE":
                # No dedicated event type — dispatch as EMOTION_SPIKED
                self.dispatcher.dispatch(
                    EventType.EMOTION_SPIKED.value,
                    {
                        "character_id": char_id,
                        "emotion": "stress",
                        "impact": acc.stress_level / 100.0,
                        "new_state": acc.stress_level,
                        "turn": turn,
                    },
                )
                logger.info(
                    "Stress spike for %s (stress=%.1f)", char_id, acc.stress_level
                )
        except Exception as exc:
            logger.warning("StressSystem dispatch failed: %s", exc)

    # -- Event subscription -------------------------------------------------

    def _on_emotion_spiked(self, event_type: str, context: Dict[str, Any]):
        """
        Convert suppressed emotion spikes into stress burden.

        Called when EMOTION_SPIKED fires.  If the emotion's impact is
        meaningful (>= 0.4) we feed ~30 % of that intensity directly into
        the character's stress accumulator.  This models the mechanic that
        bottled-up fear, grief, or rage accumulates as psychological stress.
        """
        try:
            character_id = context.get("character_id")
            emotion = context.get("emotion", "unknown")
            impact = float(context.get("impact", 0.0))

            if not character_id or impact < 0.4:
                return

            # 30 % of the spike becomes suppression stress
            stress_delta = round(impact * 0.30, 3)
            acc = self.get_or_create(character_id)
            acc.stress_level = min(100.0, acc.stress_level + stress_delta)
            logger.debug(
                "Suppressed %s (impact=%.2f) → +%.3f stress for %s (now %.1f)",
                emotion, impact, stress_delta, character_id, acc.stress_level,
            )
        except Exception as exc:
            logger.warning("_on_emotion_spiked failed: %s", exc)

    # -- Context ------------------------------------------------------------

    def get_ai_context(self, character_ids: Optional[list] = None) -> str:
        """Return stress context string for AI narrator."""
        entries = []
        for char_id, acc in self._accumulators.items():
            if character_ids and char_id not in character_ids:
                continue
            if acc.stress_level >= 20.0:
                stage = self.stage_for_stress(acc.stress_level)
                entries.append(
                    f"{char_id}: stress {acc.stress_level:.0f}/100 ({acc.label}; stage={stage})"
                )
                imprints = self._recovery_imprints.get(char_id, [])
                if imprints:
                    last = imprints[-1]
                    entries.append(
                        f"  recovery memory: {last.get('ritual', 'ritual')} turn {last.get('turn', 0)}"
                    )
        if not entries:
            return ""
        return "EMOTIONAL STRESS:\n" + "\n".join(entries)

    # -- Persistence --------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accumulators": {cid: acc.to_dict() for cid, acc in self._accumulators.items()},
            "recovery_imprints": self._recovery_imprints,
        }

    def load_from_dict(self, data: Dict[str, Any]):
        payload = data or {}
        _META_KEYS = {"accumulators", "recovery_imprints"}
        accum = payload.get("accumulators") if isinstance(payload, dict) else None
        if accum is None and isinstance(payload, dict):
            # Backward compatibility with earlier flat structure — exclude known
            # meta-keys so they are not mistakenly treated as accumulator entries.
            accum = {k: v for k, v in payload.items() if k not in _META_KEYS}
        for char_id, acc_data in (accum or {}).items():
            self._accumulators[char_id] = StressAccumulator.from_dict(acc_data)
        self._recovery_imprints = dict(payload.get("recovery_imprints", {})) if isinstance(payload, dict) else {}
        logger.info("StressSystem loaded %d accumulators", len(self._accumulators))
