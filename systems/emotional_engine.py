"""
Emotional Engine
================

Profile-weighted emotional computation layer for the Norse Saga Engine.

Bridges the low-level SoulLayer.Hugr (Phase 2 soul mechanics) with
character-specific psychological profiles (MBTI T/F axis, chronotype,
gender tendency, individual variance) to produce deterministic,
tunable emotional responses.

Architecture:
  EmotionalProfile  — static character config (loaded from YAML emotion_profile)
  EmotionalEngine   — per-character runtime. Wraps a SoulLayer and applies
                      profile modifiers to every stimulus.
  EmotionalBehavior — behavior probability tables: emotion → action suggestion
  StressAccumulator — tracks suppressed emotion → stress_level (0–100)
  EMOTION_KEYWORDS  — keyword→channel lookup for narrative extraction

All emotional writes flow through EmotionalEngine.apply_narrative_stimuli()
which calls SoulLayer.hugr.apply() so the Phase 2 system remains the
authoritative store.
"""

import logging
import random
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyword extraction table
# ---------------------------------------------------------------------------

EMOTION_KEYWORDS: Dict[str, List[Tuple[str, float]]] = {
    "fear": [
        ("fear", 0.12),
        ("afraid", 0.12),
        ("terrified", 0.20),
        ("dread", 0.16),
        ("horror", 0.20),
        ("panic", 0.18),
        ("tremble", 0.14),
        ("cower", 0.14),
        ("flee", 0.12),
        ("nightmare", 0.14),
        ("ominous", 0.10),
    ],
    "anger": [
        ("anger", 0.12),
        ("angry", 0.12),
        ("rage", 0.20),
        ("fury", 0.20),
        ("wrath", 0.18),
        ("irritated", 0.10),
        ("snarl", 0.14),
        ("growl", 0.12),
        ("scowl", 0.10),
        ("strike", 0.10),
        ("shout", 0.12),
        ("curse", 0.14),
    ],
    "sadness": [
        ("sad", 0.12),
        ("grief", 0.18),
        ("sorrow", 0.16),
        ("despair", 0.20),
        ("mourn", 0.16),
        ("weep", 0.14),
        ("lament", 0.16),
        ("anguish", 0.18),
        ("desolate", 0.18),
        ("loss", 0.10),
        ("hollow", 0.12),
    ],
    "joy": [
        ("joy", 0.12),
        ("happy", 0.12),
        ("delight", 0.14),
        ("pleasure", 0.12),
        ("content", 0.10),
        ("laugh", 0.14),
        ("celebrate", 0.14),
        ("triumph", 0.16),
        ("gleam", 0.10),
        ("cheer", 0.12),
        ("smile", 0.10),
        ("merry", 0.12),
    ],
    "shame": [
        ("shame", 0.14),
        ("guilt", 0.14),
        ("embarrass", 0.12),
        ("humiliate", 0.18),
        ("disgrace", 0.18),
        ("dishonor", 0.18),
        ("coward", 0.16),
        ("unworthy", 0.16),
        ("failure", 0.10),
    ],
    "attachment": [
        ("love", 0.14),
        ("loyal", 0.12),
        ("trust", 0.12),
        ("bond", 0.12),
        ("friend", 0.10),
        ("ally", 0.10),
        ("devotion", 0.16),
        ("cherish", 0.14),
        ("protect", 0.12),
        ("kinship", 0.14),
        ("oath", 0.14),
    ],
}


def extract_stimuli(text: str) -> Dict[str, float]:
    """
    Scan ``text`` for EMOTION_KEYWORDS and return per-channel strength floats.

    Phase 2 extraction upgrades:
    - tokenized matching (punctuation-safe)
    - simple negation handling ("not afraid", "never angry")
    - simple intensity modifiers ("very", "slightly", "utterly")

    Strength is summed per channel and capped at 1.0.
    """
    stimuli: Dict[str, float] = {}
    lowered = (text or "").lower()
    tokens = re.findall(r"[a-z']+", lowered)
    if not tokens:
        return stimuli

    negators = {"not", "never", "no", "hardly"}
    intensifiers = {
        "very": 1.30,
        "extremely": 1.55,
        "utterly": 1.55,
        "deeply": 1.35,
        "slightly": 0.70,
        "barely": 0.60,
    }

    for channel, pairs in EMOTION_KEYWORDS.items():
        total = 0.0
        for idx, token in enumerate(tokens):
            for keyword, base_weight in pairs:
                # Prefix/stem style match allows "embarrassed" to match "embarrass".
                if token == keyword or token.startswith(keyword):
                    factor = 1.0
                    if idx > 0:
                        prev = tokens[idx - 1]
                        if prev in negators:
                            factor *= 0.25
                        factor *= intensifiers.get(prev, 1.0)
                    total += base_weight * factor
        if total > 0.0:
            stimuli[channel] = min(1.0, total)

    return stimuli


# ---------------------------------------------------------------------------
# Intensity labels for prompt builder
# ---------------------------------------------------------------------------

_INTENSITY_LABELS = [
    (0.75, "overwhelming"),
    (0.55, "strong"),
    (0.35, "simmering"),
    (0.15, "faint"),
    (0.0, "absent"),
]


def intensity_label(value: float) -> str:
    """Convert a 0–1 float into a human-readable intensity label."""
    for threshold, label in _INTENSITY_LABELS:
        if value >= threshold:
            return label
    return "absent"


# ---------------------------------------------------------------------------
# EmotionalProfile — static per-character config
# ---------------------------------------------------------------------------


@dataclass
class EmotionalProfile:
    """
    All tunable emotional parameters for one character.

    Loaded from the ``emotion_profile`` block in character YAML.
    Falls back to sensible defaults if the block is absent.
    Missing ``tf_axis`` is auto-derived from the ``myers_briggs`` string
    if available (T → 0.35, F → 0.65, missing → 0.50).
    """

    tf_axis: float = 0.50
    """0.0 = pure Thinking (suppresses emotion), 1.0 = pure Feeling (amplifies)."""

    gender_axis: float = 0.0
    """
    Statistical tendency only. -1.0 = male-leaning, +1.0 = female-leaning.
    ``individual_offset`` is always applied on top, so a single character
    can completely invert this tendency.
    """

    individual_offset: float = 0.0
    """Random variance seeded at creation. Range ±0.2."""

    baseline_intensity: float = 1.0
    """Overall emotional reactivity multiplier (0.5 = very stoic, 1.5 = very reactive)."""

    expression_threshold: float = 0.55
    """Minimum hugr intensity for an emotion to manifest externally in narration."""

    rumination_bias: float = 0.30
    """0 = moves on quickly, 1 = ruminates and dwells on events."""

    decay_rate: float = 0.10
    """Base hugr decay fraction per turn (overrides SoulLayer default when present)."""

    channel_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "fear": 1.0,
            "anger": 1.0,
            "sadness": 1.0,
            "joy": 1.0,
            "shame": 0.9,
            "attachment": 1.0,
        }
    )

    chronotype: str = "diurnal"
    """diurnal | nocturnal | crepuscular"""

    stress_resistance: float = 0.5
    """
    How well this character absorbs suppressed emotional pressure.
    High resistance → less stress accumulates from internalized emotions.
    """

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmotionalProfile":
        """Build from a character YAML ``emotion_profile`` block."""
        if not data:
            return cls()
        return cls(
            tf_axis=float(data.get("tf_axis", 0.50)),
            gender_axis=float(data.get("gender_axis", 0.0)),
            individual_offset=float(data.get("individual_offset", 0.0)),
            baseline_intensity=float(data.get("baseline_intensity", 1.0)),
            expression_threshold=float(data.get("expression_threshold", 0.55)),
            rumination_bias=float(data.get("rumination_bias", 0.30)),
            decay_rate=float(data.get("decay_rate", 0.10)),
            channel_weights=dict(data.get("channel_weights", {}))
            or {
                "fear": 1.0,
                "anger": 1.0,
                "sadness": 1.0,
                "joy": 1.0,
                "shame": 0.9,
                "attachment": 1.0,
            },
            chronotype=str(data.get("chronotype", "diurnal")),
            stress_resistance=float(data.get("stress_resistance", 0.5)),
        )

    @classmethod
    def from_character(cls, char_data: Dict[str, Any]) -> "EmotionalProfile":
        """
        Derive an EmotionalProfile from any character dict.
        Uses ``emotion_profile`` if present; otherwise auto-derives
        tf_axis from MBTI ``myers_briggs`` field.
        """
        profile_raw = char_data.get("emotion_profile")
        if profile_raw:
            return cls.from_dict(profile_raw)

        # Auto-derive from MBTI
        mbti = (
            char_data.get("psychology", {}).get("myers_briggs", "")
            or char_data.get("myers_briggs", "")
        ).upper()
        if "F" in mbti:
            tf_axis = 0.65
        elif "T" in mbti:
            tf_axis = 0.35
        else:
            tf_axis = 0.50

        gender = (
            char_data.get("identity", {}).get("gender", "")
            or char_data.get("gender", "")
        ).lower()
        gender_axis = (
            0.25 if gender == "female" else (-0.15 if gender == "male" else 0.0)
        )

        chronotype = char_data.get("chronotype", None) or char_data.get(
            "psychology", {}
        ).get("chronotype", "diurnal")

        return cls(
            tf_axis=tf_axis,
            gender_axis=gender_axis,
            individual_offset=round(random.uniform(-0.15, 0.15), 3),
            chronotype=chronotype,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tf_axis": self.tf_axis,
            "gender_axis": self.gender_axis,
            "individual_offset": self.individual_offset,
            "baseline_intensity": self.baseline_intensity,
            "expression_threshold": self.expression_threshold,
            "rumination_bias": self.rumination_bias,
            "decay_rate": self.decay_rate,
            "channel_weights": self.channel_weights,
            "chronotype": self.chronotype,
            "stress_resistance": self.stress_resistance,
        }

    @property
    def effective_tf(self) -> float:
        """tf_axis adjusted for individual variance and gender tendency."""
        raw = self.tf_axis + (self.gender_axis * 0.1) + self.individual_offset
        return max(0.0, min(1.0, raw))

    def nature_summary(self) -> str:
        """Return a human-readable emotional nature string for prompt building."""
        tf = self.effective_tf
        if tf >= 0.70:
            tf_label = "strongly Feeling-leaning"
        elif tf >= 0.55:
            tf_label = "Feeling-leaning"
        elif tf <= 0.30:
            tf_label = "strongly Thinking-leaning"
        elif tf <= 0.45:
            tf_label = "Thinking-leaning"
        else:
            tf_label = "balanced Thinking-Feeling"

        rumination = (
            "ruminates deeply"
            if self.rumination_bias >= 0.6
            else (
                "moves on quickly"
                if self.rumination_bias <= 0.25
                else "processes and moves on"
            )
        )
        expression = (
            "expressive"
            if self.expression_threshold <= 0.35
            else (
                "reserved"
                if self.expression_threshold >= 0.65
                else "selectively expressive"
            )
        )
        return f"{tf_label}, {expression}, {rumination}"


# ---------------------------------------------------------------------------
# EmotionalEngine — per-character runtime
# ---------------------------------------------------------------------------


class EmotionalEngine:
    """
    Per-character emotional computation engine.

    Wraps an existing ``SoulLayer`` (from soul_mechanics.py) and applies
    profile-weighted impact calculations before writing to ``hugr``.

    If no soul layer is provided, operates in standalone mode with an
    internal emotion dict for simpler cases.
    """

    def __init__(
        self,
        character_id: str,
        profile: Optional[EmotionalProfile] = None,
        soul_layer=None,
    ):
        self.character_id = character_id
        self.profile = profile or EmotionalProfile()
        self.soul_layer = soul_layer

        # Standalone fallback dict when no SoulLayer is available
        self._standalone_emotions: Dict[str, float] = {}

        # Internalized (suppressed) emotion accumulation this turn
        self._suppressed_this_turn: Dict[str, float] = {}

        # Optional menstrual cycle state (set by engine._get_emotional_engine)
        # Type: Optional[MenstrualCycleState] — imported lazily to avoid
        # circular import. None for male / post-menopausal characters.
        self.cycle_state = None

        logger.debug(
            "EmotionalEngine created for '%s' (tf=%.2f, decay=%.2f)",
            character_id,
            self.profile.effective_tf,
            self.profile.decay_rate,
        )

    # -- Impact computation -------------------------------------------------

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        """Linear interpolation between a and b by fraction t."""
        return a + (b - a) * max(0.0, min(1.0, t))

    def _chronotype_mod(self, time_of_day: str) -> float:
        """
        Emotional clarity modifier based on chronotype alignment.
        In-phase → +0.12 amplification (clearer processing).
        Out-of-phase → -0.12 (emotional fog).
        """
        tod = (time_of_day or "").lower()
        ct = (self.profile.chronotype or "diurnal").lower()
        night_times = {"night", "midnight", "dusk"}
        day_times = {"dawn", "morning", "midday", "afternoon"}
        crep_times = {"dusk", "dawn", "twilight"}

        if ct == "nocturnal" and tod in night_times:
            return 1.12
        if ct == "diurnal" and tod in day_times:
            return 1.12
        if ct == "crepuscular" and tod in crep_times:
            return 1.12
        # Misaligned
        if ct == "nocturnal" and tod in day_times:
            return 0.88
        if ct == "diurnal" and tod in night_times:
            return 0.88
        return 1.0

    def compute_impact(
        self,
        channel: str,
        raw_strength: float,
        time_of_day: str = "",
    ) -> float:
        """
        Convert raw stimulus strength into a profile-adjusted emotional impact.

        Modifiers applied (multiplicative):
          - channel_weight (per-emotion sensitivity)
          - tf_modifier (Thinking suppresses, Feeling amplifies)
          - chronotype_modifier (in-phase amplifies, misaligned dampens)
          - baseline_intensity (overall reactivity)
          - cycle_multiplier (menstrual phase, if applicable)
        """
        channel_w = self.profile.channel_weights.get(channel, 1.0)
        tf_mod = self._lerp(0.80, 1.20, self.profile.effective_tf)
        chron_mod = self._chronotype_mod(time_of_day)

        # Menstrual cycle modifier (female pre-menopausal characters only)
        cycle_mod = 1.0
        if self.cycle_state is not None and getattr(
            self.cycle_state, "is_premenopausal", False
        ):
            cycle_mod = self.cycle_state.emotion_multiplier(channel)

        # Energy delta from cycle shifts baseline_intensity temporarily
        cycle_energy = 1.0
        if self.cycle_state is not None:
            delta = getattr(self.cycle_state, "energy_delta", lambda: 0.0)()
            cycle_energy = max(0.5, 1.0 + delta)

        impact = (
            raw_strength
            * channel_w
            * tf_mod
            * chron_mod
            * self.profile.baseline_intensity
            * cycle_energy
            * cycle_mod
        )
        return round(max(0.0, min(1.0, impact)), 4)

    # -- State access -------------------------------------------------------

    def _get_emotion(self, channel: str) -> float:
        """Return current intensity for a channel from soul layer or standalone."""
        if self.soul_layer:
            return self.soul_layer.hugr.emotions.get(channel, 0.0)
        return self._standalone_emotions.get(channel, 0.0)

    def _set_emotion(self, channel: str, value: float, turn: int):
        """Write emotion to soul layer (or standalone dict)."""
        if self.soul_layer:
            self.soul_layer.hugr.apply(
                channel, value - self._get_emotion(channel), turn
            )
        else:
            self._standalone_emotions[channel] = max(-1.0, min(1.0, value))

    # -- Core update --------------------------------------------------------

    def apply_stimulus(
        self,
        channel: str,
        raw_strength: float,
        turn: int,
        time_of_day: str = "",
    ) -> Tuple[float, bool]:
        """
        Apply a single-channel stimulus.

        Returns:
            (impact_applied, expressed) where ``expressed`` is True if the
            resulting intensity crossed the expression_threshold.
        """
        impact = self.compute_impact(channel, raw_strength, time_of_day)
        current = self._get_emotion(channel)
        new_val = max(-1.0, min(1.0, current + impact))
        self._set_emotion(channel, new_val, turn)

        expressed = abs(new_val) >= self.profile.expression_threshold
        if not expressed:
            # Internalize — accumulate stress contribution
            suppressed = impact * (1.0 - self.profile.stress_resistance)
            self._suppressed_this_turn[channel] = (
                self._suppressed_this_turn.get(channel, 0.0) + suppressed
            )

        return impact, expressed

    def apply_narrative_stimuli(
        self,
        stimuli: Dict[str, float],
        turn: int,
        time_of_day: str = "",
    ) -> Dict[str, bool]:
        """
        Apply all extracted stimuli from a narrative chunk.

        Returns dict of {channel: expressed} for logging / prompt building.
        """
        self._suppressed_this_turn.clear()
        results: Dict[str, bool] = {}
        for channel, strength in stimuli.items():
            _, expressed = self.apply_stimulus(channel, strength, turn, time_of_day)
            results[channel] = expressed
            logger.debug(
                "[Emotion] %s/%s: +%.3f → %.3f (expressed=%s)",
                self.character_id,
                channel,
                strength,
                self._get_emotion(channel),
                expressed,
            )
        return results

    def flush_suppressed(self) -> Dict[str, float]:
        """Return and clear the suppressed accumulation dict."""
        out = dict(self._suppressed_this_turn)
        self._suppressed_this_turn.clear()
        return out

    def apply_ritual_calm(self, channels: Optional[List[str]] = None, turn: int = 0):
        """
        Apply a calming effect from a ritual action (fire, prayer, etc.).
        Reduces negative channels toward neutral by a fixed amount.
        """
        targets = channels or ["fear", "anger", "shame", "sadness"]
        for ch in targets:
            val = self._get_emotion(ch)
            if val > 0.1:
                self._set_emotion(ch, max(0.0, val - 0.18), turn)
                logger.info(
                    "[Ritual] %s/%s calmed: %.2f → %.2f",
                    self.character_id,
                    ch,
                    val,
                    self._get_emotion(ch),
                )

    # -- Introspection ------------------------------------------------------

    def should_express(self, channel: str) -> bool:
        return abs(self._get_emotion(channel)) >= self.profile.expression_threshold

    def dominant_emotion(self) -> Optional[Tuple[str, float]]:
        if self.soul_layer:
            return self.soul_layer.hugr.dominant_emotion()
        if not self._standalone_emotions:
            return None
        return max(self._standalone_emotions.items(), key=lambda kv: abs(kv[1]))

    def get_all_emotions(self) -> Dict[str, float]:
        if self.soul_layer:
            return dict(self.soul_layer.hugr.emotions)
        return dict(self._standalone_emotions)

    def get_ai_summary(self) -> str:
        """Compact string for AI context injection."""
        emotions = self.get_all_emotions()
        expressed = {ch: v for ch, v in emotions.items() if abs(v) >= 0.10}
        if not expressed:
            dom = "emotionally neutral"
        else:
            parts = sorted(expressed.items(), key=lambda kv: abs(kv[1]), reverse=True)
            dom = ", ".join(f"{ch} ({intensity_label(abs(v))})" for ch, v in parts[:3])
        return f"[{self.character_id}] {dom} | Nature: {self.profile.nature_summary()}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "profile": self.profile.to_dict(),
            "standalone_emotions": self._standalone_emotions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], soul_layer=None) -> "EmotionalEngine":
        profile = EmotionalProfile.from_dict(data.get("profile", {}))
        obj = cls(
            character_id=data.get("character_id", "unknown"),
            profile=profile,
            soul_layer=soul_layer,
        )
        if not soul_layer:
            obj._standalone_emotions = data.get("standalone_emotions", {})
        return obj


# ---------------------------------------------------------------------------
# EmotionalBehavior — behavior probability tables
# ---------------------------------------------------------------------------


class EmotionalBehavior:
    """
    Maps (emotion channel, intensity) to a weighted-random behavior suggestion.

    Behavior suggestions are advisory — the AI Narrator may override them,
    but they bias NPC decision-making toward psychologically coherent choices.
    """

    BEHAVIOR_TABLE: Dict[str, List[Tuple[str, float]]] = {
        "fear": [
            ("flee", 0.35),
            ("hide", 0.28),
            ("defensive_posture", 0.25),
            ("ritual_ward", 0.12),
        ],
        "anger": [
            ("confront_directly", 0.38),
            ("passive_aggression", 0.28),
            ("ritual_release", 0.20),
            ("cold_withdrawal", 0.14),
        ],
        "sadness": [
            ("withdrawal", 0.38),
            ("seek_comfort", 0.28),
            ("ritual_mourning", 0.22),
            ("stoic_endurance", 0.12),
        ],
        "joy": [
            ("celebrate_openly", 0.38),
            ("share_with_others", 0.28),
            ("boasting", 0.20),
            ("quiet_contentment", 0.14),
        ],
        "shame": [
            ("withdrawal", 0.42),
            ("atonement_act", 0.28),
            ("denial", 0.18),
            ("confession", 0.12),
        ],
        "attachment": [
            ("protectiveness", 0.38),
            ("confide_secrets", 0.28),
            ("gift_giving", 0.22),
            ("possessiveness", 0.12),
        ],
    }

    # Personality modifiers: (personality_key, personality_value, behavior_key, weight_delta)
    PERSONALITY_MODS = [
        # High extraversion amplifies outward behaviors
        ("extraversion", 70, "confront_directly", +0.10),
        ("extraversion", 70, "cold_withdrawal", -0.08),
        ("extraversion", 70, "celebrate_openly", +0.08),
        # High agreeableness shifts away from aggression
        ("agreeableness", 70, "confront_directly", -0.10),
        ("agreeableness", 70, "seek_comfort", +0.10),
        # High neuroticism amplifies fear/shame responses
        ("neuroticism", 65, "flee", +0.10),
        ("neuroticism", 65, "denial", +0.08),
        # Low neuroticism → stoicism
        ("neuroticism", 30, "stoic_endurance", +0.12),
    ]

    @classmethod
    def choose_behavior(
        cls,
        channel: str,
        intensity: float,
        personality: Optional[Dict[str, int]] = None,
        cycle_bias: Optional[Dict[str, float]] = None,
    ) -> Optional[str]:
        """
        Return a weighted-randomly selected behavior suggestion.

        Args:
            channel: Emotion channel name
            intensity: Current intensity (0–1)
            personality: Optional dict of Big Five scores (0–100) for modifiers

        Returns:
            Behavior label string, or None if channel unknown or intensity < 0.15
        """
        if intensity < 0.15 or channel not in cls.BEHAVIOR_TABLE:
            return None

        weights = {beh: w for beh, w in cls.BEHAVIOR_TABLE[channel]}

        # Apply menstrual cycle behavior biases
        if cycle_bias:
            for beh_key, delta in cycle_bias.items():
                if beh_key in weights:
                    weights[beh_key] = max(0.01, weights[beh_key] + delta)
                else:
                    # Phase introduces a new behavior bias
                    if delta > 0.05:
                        weights[beh_key] = delta

        # Apply personality modifiers
        if personality:
            for p_key, p_threshold, beh_key, delta in cls.PERSONALITY_MODS:
                if beh_key not in weights:
                    continue
                p_val = personality.get(p_key, 50)
                if (delta > 0 and p_val >= p_threshold) or (
                    delta < 0 and p_val < p_threshold
                ):
                    weights[beh_key] = max(0.01, weights.get(beh_key, 0.0) + delta)

        # Scale by intensity (higher intensity → less nuanced, more extreme behaviors)
        if intensity >= 0.75:
            # Very high intensity: first option weight doubled
            first_key = list(weights.keys())[0]
            weights[first_key] = weights[first_key] * 1.5

        total = sum(weights.values())
        if total <= 0:
            return None

        roll = random.random() * total
        cumulative = 0.0
        for behavior, weight in weights.items():
            cumulative += weight
            if roll <= cumulative:
                return behavior

        return list(weights.keys())[-1]


# ---------------------------------------------------------------------------
# StressAccumulator — suppressed emotion → stress
# ---------------------------------------------------------------------------


@dataclass
class StressAccumulator:
    """
    Tracks suppressed emotional pressure for one character and converts
    it to a 0–100 stress score.

    High stress feeds into CognitiveFriction and STRESS_BREAKDOWN events.
    """

    character_id: str
    stress_level: float = 0.0  # 0–100
    _history: List[Dict[str, Any]] = field(default_factory=list)

    DECAY_PER_TURN: float = 1.5  # natural stress relief each turn
    SPIKE_THRESHOLD: float = 40.0
    BREAKDOWN_THRESHOLD: float = 80.0

    def accumulate(self, suppressed: Dict[str, float], resistance: float = 0.5):
        """
        Add suppressed emotion totals to stress.

        Args:
            suppressed: {channel: amount} from EmotionalEngine.flush_suppressed()
            resistance: Character's stress_resistance (0–1), reduces accumulation
        """
        total_incoming = sum(suppressed.values()) * (1.0 - resistance) * 100
        old = self.stress_level
        self.stress_level = min(100.0, self.stress_level + total_incoming)
        if total_incoming > 0.1:
            self._history.append(
                {
                    "from": round(old, 1),
                    "to": round(self.stress_level, 1),
                    "suppressed": suppressed,
                }
            )
            self._history = self._history[-30:]
        logger.debug(
            "[Stress] %s: %.1f → %.1f (incoming %.1f)",
            self.character_id,
            old,
            self.stress_level,
            total_incoming,
        )

    def decay_turn(self):
        """Natural stress relief — call once per turn."""
        self.stress_level = max(0.0, self.stress_level - self.DECAY_PER_TURN)

    def check_events(self) -> List[str]:
        """
        Return list of event strings that should be dispatched.
        Caller is responsible for dispatching via EventDispatcher.
        """
        events = []
        if self.stress_level >= self.BREAKDOWN_THRESHOLD:
            events.append(f"STRESS_BREAKDOWN:{self.character_id}")
        elif self.stress_level >= self.SPIKE_THRESHOLD:
            events.append(f"STRESS_SPIKE:{self.character_id}")
        return events

    @property
    def label(self) -> str:
        if self.stress_level >= 80:
            return "breaking point"
        if self.stress_level >= 60:
            return "severely stressed"
        if self.stress_level >= 40:
            return "under strain"
        if self.stress_level >= 20:
            return "mildly stressed"
        return "composed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "character_id": self.character_id,
            "stress_level": self.stress_level,
            "history": self._history[-10:],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StressAccumulator":
        obj = cls(character_id=data["character_id"])
        obj.stress_level = data.get("stress_level", 0.0)
        obj._history = data.get("history", [])
        return obj
