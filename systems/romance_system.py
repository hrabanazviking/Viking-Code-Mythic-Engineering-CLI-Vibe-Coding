"""Advanced romance progression engine rooted in Norse social custom."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

logger = logging.getLogger(__name__)


RELAXATION_KEYWORDS = {
    "rest",
    "sleep",
    "breathe",
    "calm",
    "meditate",
    "sauna",
    "bathe",
    "relax",
    "gentle",
    "soft",
    "quiet",
}


@dataclass
class RomanceBond:
    """Tracks romantic progression between an NPC and the player."""

    npc_id: str
    attraction: float = 0.0
    trust: float = 0.0
    devotion: float = 0.0
    desire: float = 0.0
    jealousy: float = 0.0
    relaxation_level: float = 0.0
    intimacy: int = 0
    shared_rituals: int = 0
    stage: str = "strangers"
    events: List[Dict[str, Any]] = field(default_factory=list)
    last_turn_updated: int = 0

    def to_snapshot(self) -> Dict[str, Any]:
        return {
            "npc_id": self.npc_id,
            "attraction": round(self.attraction, 3),
            "trust": round(self.trust, 3),
            "devotion": round(self.devotion, 3),
            "desire": round(self.desire, 3),
            "jealousy": round(self.jealousy, 3),
            "relaxation_level": round(self.relaxation_level, 3),
            "intimacy": self.intimacy,
            "shared_rituals": self.shared_rituals,
            "stage": self.stage,
            "last_turn_updated": self.last_turn_updated,
            "event_count": len(self.events),
        }


class RomanceSystemEngine:
    """Interprets turn text into persistent romance-bond updates."""

    def __init__(self, data_path: str = "data") -> None:
        self.data_path = Path(data_path)
        loaded = self._load_yaml("charts/romance_events.yaml", {})
        menstrual_chart = self._load_yaml("charts/menstrual_cycle.yaml", {})
        emotional_chart = self._load_yaml("charts/emotional_expressions.yaml", {})
        fate_chart = self._load_yaml("charts/fate_twists.yaml", {})
        self.metric_weights = loaded.get("metric_weights", {}) if isinstance(loaded, dict) else {}
        self.stage_thresholds = loaded.get("stage_thresholds", {}) if isinstance(loaded, dict) else {}
        self.event_keywords = loaded.get("event_keywords", {}) if isinstance(loaded, dict) else {}
        self.emotional_channels = self._load_emotional_channels(emotional_chart)
        self.fate_twist_modifiers = self._load_fate_twist_modifiers(fate_chart)
        self.phase_romance_modifiers = self._load_phase_modifiers(menstrual_chart)
        self.bonds: Dict[str, RomanceBond] = {}

    def process_turn(
        self,
        action: str,
        response: str,
        npcs_present: List[Dict[str, Any]],
        turn_count: int = 0,
        romance_context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Freyja's threads: convert scene events into bond deltas for present NPCs."""
        lowered = f"{action} {response}".lower()
        inferred_events = self._infer_events(lowered)
        romance_context = romance_context if isinstance(romance_context, dict) else {}
        updated: List[str] = []

        for npc in npcs_present:
            try:
                if not isinstance(npc, dict):
                    continue
                npc_id = str(npc.get("id") or npc.get("identity", {}).get("name", "")).strip()
                if not npc_id:
                    continue

                if not inferred_events:
                    continue

                bond = self.bonds.setdefault(npc_id, RomanceBond(npc_id=npc_id))
                updated.append(npc_id)

                for event_name in inferred_events:
                    impact = self._resolve_metric_delta(event_name)
                    # Huginn scouts whether this NPC profile welcomes closeness.
                    compatibility = self._compatibility_multiplier(npc)
                    contextual = self._contextual_multiplier(
                        lowered_text=lowered,
                        npc=npc,
                        bond=bond,
                        romance_context=romance_context,
                    )
                    self._apply_delta(bond, impact, compatibility * contextual)
                    bond.events.append(
                        {
                            "timestamp": datetime.now().isoformat(),
                            "event": event_name,
                            "compatibility": compatibility,
                            "contextual": round(contextual, 3),
                            "delta": impact,
                        }
                    )

                bond.last_turn_updated = max(0, int(turn_count or 0))
                bond.stage = self._resolve_stage(bond)
            except Exception as exc:
                logger.warning("Romance update skipped for NPC due to malformed data: %s", exc)

        return {
            "updated_npcs": updated,
            "event_types": inferred_events,
            "bond_count": len(self.bonds),
            "bond_snapshots": {npc_id: self.bonds[npc_id].to_snapshot() for npc_id in updated},
        }

    def _infer_events(self, lowered_text: str) -> List[str]:
        inferred: List[str] = []
        for event_name, keywords in self.event_keywords.items():
            if not isinstance(keywords, list):
                continue
            if any(str(token).lower() in lowered_text for token in keywords):
                inferred.append(event_name)
        return inferred

    def _resolve_metric_delta(self, event_name: str) -> Dict[str, float]:
        values = self.metric_weights.get(event_name, {})
        if not isinstance(values, dict):
            return {}
        return {str(metric): float(amount) for metric, amount in values.items()}

    def _contextual_multiplier(
        self,
        lowered_text: str,
        npc: Dict[str, Any],
        bond: RomanceBond,
        romance_context: Dict[str, Any],
    ) -> float:
        # Skuld braids fate, mood, moonlight, and mortal calm into one thread.
        multiplier = 1.0
        multiplier *= self._emotion_multiplier(lowered_text, npc, romance_context)
        multiplier *= self._fate_multiplier(romance_context)
        multiplier *= self._rune_multiplier(romance_context)
        multiplier *= self._chaos_multiplier(romance_context)
        multiplier *= self._time_and_moon_multiplier(romance_context)
        multiplier *= self._menstrual_multiplier(npc, romance_context)

        bond.relaxation_level = self._resolve_relaxation_level(
            lowered_text=lowered_text,
            npc=npc,
            bond=bond,
            romance_context=romance_context,
        )
        multiplier *= 1.0 + (bond.relaxation_level * 0.35)
        return max(0.2, min(2.4, multiplier))

    def _emotion_multiplier(
        self,
        lowered_text: str,
        npc: Dict[str, Any],
        romance_context: Dict[str, Any],
    ) -> float:
        emotional_states = romance_context.get("npc_emotional_states", {})
        npc_id = str(npc.get("id") or npc.get("identity", {}).get("name", "")).strip()
        state = emotional_states.get(npc_id, {}) if isinstance(emotional_states, dict) else {}
        attachment = float(state.get("attachment", 0.0) or 0.0)
        joy = float(state.get("joy", 0.0) or 0.0)
        anger = float(state.get("anger", 0.0) or 0.0)
        sadness = float(state.get("sadness", 0.0) or 0.0)

        phrase_bonus = 0.0
        for channel, tokens in self.emotional_channels.items():
            if any(token in lowered_text for token in tokens):
                if channel in {"joy", "attachment"}:
                    phrase_bonus += 0.06
                if channel in {"anger", "shame", "fear"}:
                    phrase_bonus -= 0.05

        val = 1.0 + (attachment * 0.2) + (joy * 0.15) - (anger * 0.2) - (sadness * 0.1) + phrase_bonus
        return max(0.65, min(1.55, val))

    def _fate_multiplier(self, romance_context: Dict[str, Any]) -> float:
        fate_count = len(romance_context.get("fate_threads", []))
        chart_bias = float(self.fate_twist_modifiers.get("twist_bias", 0.03) or 0.03)
        twist_bias = float(romance_context.get("fate_twist_bias", chart_bias) or chart_bias)
        # The Norns reward entwined destinies with stronger romantic resonance.
        return max(0.8, min(1.4, 1.0 + (fate_count * 0.03) + (twist_bias * 0.08)))

    def _rune_multiplier(self, romance_context: Dict[str, Any]) -> float:
        rune = romance_context.get("active_scene_rune", {})
        if not isinstance(rune, dict):
            return 1.0
        rune_name = str(rune.get("name") or rune.get("rune") or "").lower()
        positive = {"gebo", "wunjo", "berkana", "ingwaz", "ehwaz"}
        volatile = {"hagalaz", "thurisaz", "perthro", "laguz"}
        if rune_name in positive:
            return 1.16
        if rune_name in volatile:
            return 1.08
        return 1.0

    def _chaos_multiplier(self, romance_context: Dict[str, Any]) -> float:
        chaos = float(romance_context.get("chaos_factor", 30) or 30)
        # Chaos becomes a creative current for romance, not merely disorder.
        return max(0.85, min(1.45, 0.95 + (chaos / 100.0) * 0.5))

    def _time_and_moon_multiplier(self, romance_context: Dict[str, Any]) -> float:
        moon_phase = str(romance_context.get("moon_phase", "")).lower()
        time_of_day = str(romance_context.get("time_of_day", "")).lower()
        moon_map = {
            "full_moon": 1.12,
            "waxing_gibbous": 1.08,
            "waxing_crescent": 1.04,
            "new_moon": 0.96,
            "waning_crescent": 0.96,
        }
        time_map = {
            "evening": 1.06,
            "night": 1.1,
            "midnight": 1.12,
            "dawn": 1.02,
            "midday": 0.98,
        }
        return moon_map.get(moon_phase, 1.0) * time_map.get(time_of_day, 1.0)

    def _menstrual_multiplier(self, npc: Dict[str, Any], romance_context: Dict[str, Any]) -> float:
        menstrual_states = romance_context.get("menstrual_states", {})
        npc_id = str(npc.get("id") or npc.get("identity", {}).get("name", "")).strip()
        state = menstrual_states.get(npc_id, {}) if isinstance(menstrual_states, dict) else {}
        phase_name = str(state.get("current_phase", "")).lower()
        return self.phase_romance_modifiers.get(phase_name, 1.0)

    def _resolve_relaxation_level(
        self,
        lowered_text: str,
        npc: Dict[str, Any],
        bond: RomanceBond,
        romance_context: Dict[str, Any],
    ) -> float:
        emotional_states = romance_context.get("npc_emotional_states", {})
        npc_id = str(npc.get("id") or npc.get("identity", {}).get("name", "")).strip()
        state = emotional_states.get(npc_id, {}) if isinstance(emotional_states, dict) else {}
        joy = float(state.get("joy", 0.0) or 0.0)
        fear = float(state.get("fear", 0.0) or 0.0)
        anger = float(state.get("anger", 0.0) or 0.0)
        calmness = max(0.0, min(1.0, 0.5 + (joy * 0.25) - (fear * 0.2) - (anger * 0.2)))

        if any(token in lowered_text for token in RELAXATION_KEYWORDS):
            calmness += 0.15

        rest_bias = float(romance_context.get("relaxation_bias", 0.0) or 0.0)
        adjusted = calmness + rest_bias
        # Muninn remembers a rolling calm baseline so stress spikes self-correct.
        smoothed = (bond.relaxation_level * 0.65) + (adjusted * 0.35)
        return max(0.0, min(1.0, smoothed))

    def _compatibility_multiplier(self, npc: Dict[str, Any]) -> float:
        identity = npc.get("identity", {}) if isinstance(npc.get("identity"), dict) else {}
        preferences = npc.get("romantic_preferences", {}) if isinstance(npc.get("romantic_preferences"), dict) else {}
        temperament = str(identity.get("temperament", "")).lower()
        orientation = str(preferences.get("orientation", "unknown")).lower()

        multiplier = 1.0
        if temperament in {"warm", "charismatic", "curious"}:
            multiplier += 0.15
        if temperament in {"cold", "vengeful", "guarded"}:
            multiplier -= 0.2
        if orientation in {"aromantic", "unknown"}:
            multiplier -= 0.25

        return max(0.4, min(multiplier, 1.35))

    def _apply_delta(
        self,
        bond: RomanceBond,
        delta: Dict[str, float],
        compatibility: float,
    ) -> None:
        for metric, amount in delta.items():
            scaled = float(amount) * compatibility
            if metric == "attraction":
                bond.attraction += scaled
            elif metric == "trust":
                bond.trust += scaled
            elif metric == "devotion":
                bond.devotion += scaled
            elif metric == "desire":
                bond.desire += scaled
            elif metric == "jealousy":
                bond.jealousy += scaled
            elif metric == "intimacy":
                bond.intimacy = max(0, bond.intimacy + int(round(scaled)))
            elif metric == "shared_rituals":
                bond.shared_rituals = max(0, bond.shared_rituals + int(round(scaled)))

        bond.attraction = max(-1.0, min(3.0, bond.attraction))
        bond.trust = max(-1.0, min(3.0, bond.trust))
        bond.devotion = max(-1.0, min(3.0, bond.devotion))
        bond.desire = max(-1.0, min(3.0, bond.desire))
        bond.jealousy = max(0.0, min(3.0, bond.jealousy))
        bond.relaxation_level = max(0.0, min(1.0, bond.relaxation_level))

    def _resolve_stage(self, bond: RomanceBond) -> str:
        # Muninn weighs affection, trust, and ritual depth as braided strands.
        score = (
            (bond.attraction * 0.3)
            + (bond.trust * 0.3)
            + (bond.devotion * 0.2)
            + (bond.desire * 0.1)
            + (bond.shared_rituals * 0.05)
            + (bond.intimacy * 0.05)
            - (bond.jealousy * 0.25)
        )

        ordered = sorted(
            (
                (str(stage), float(threshold))
                for stage, threshold in self.stage_thresholds.items()
            ),
            key=lambda item: item[1],
        )
        chosen = "strangers"
        for stage, threshold in ordered:
            if score >= threshold:
                chosen = stage
        return chosen

    def _load_yaml(self, relative_path: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        path = self.data_path / relative_path
        if not path.exists():
            return fallback
        try:
            with path.open("r", encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or fallback
        except Exception as exc:
            logger.warning("Failed to load chart %s: %s", path, exc)
            return fallback
        return loaded if isinstance(loaded, dict) else fallback

    def _load_emotional_channels(self, emotional_chart: Dict[str, Any]) -> Dict[str, List[str]]:
        entries = emotional_chart.get("entries", []) if isinstance(emotional_chart, dict) else []
        channels: Dict[str, List[str]] = {}
        for row in entries:
            if not isinstance(row, dict):
                continue
            channel = str(row.get("channel", "")).strip().lower()
            expressions = row.get("expressions", [])
            if channel and isinstance(expressions, list):
                channels[channel] = [str(exp).lower() for exp in expressions if isinstance(exp, str)]
        return channels

    def _load_fate_twist_modifiers(self, fate_chart: Dict[str, Any]) -> Dict[str, float]:
        entries = fate_chart.get("entries", []) if isinstance(fate_chart, dict) else []
        severity_weights = {"minor": 0.02, "moderate": 0.04, "major": 0.06}
        weighted = [
            severity_weights.get(str(item.get("severity", "minor")).lower(), 0.02)
            for item in entries
            if isinstance(item, dict)
        ]
        average = sum(weighted) / len(weighted) if weighted else 0.03
        return {"twist_bias": round(average, 3)}

    def _load_phase_modifiers(self, menstrual_chart: Dict[str, Any]) -> Dict[str, float]:
        phases = menstrual_chart.get("phases", []) if isinstance(menstrual_chart, dict) else []
        modifiers: Dict[str, float] = {}
        for phase in phases:
            if not isinstance(phase, dict):
                continue
            name = str(phase.get("name", "")).strip().lower()
            emotion_multiplier = phase.get("emotion_multiplier", {})
            if not name or not isinstance(emotion_multiplier, dict):
                continue
            joy = float(emotion_multiplier.get("joy", 1.0) or 1.0)
            attachment = float(emotion_multiplier.get("attachment", 1.0) or 1.0)
            anger = float(emotion_multiplier.get("anger", 1.0) or 1.0)
            composite = 1.0 + ((joy - 1.0) * 0.25) + ((attachment - 1.0) * 0.2) - ((anger - 1.0) * 0.1)
            modifiers[name] = max(0.82, min(1.25, composite))
        return modifiers
