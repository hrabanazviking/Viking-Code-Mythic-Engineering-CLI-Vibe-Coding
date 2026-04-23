"""
Memory Hardening (T3-B)
=======================

Two subsystems that harden the NorseSagaEngine memory layer:

T6 — Identity Drift Detection
  Periodically compares a character's accumulated event history against their
  base YAML personality traits and produces a DriftVector when meaningful
  divergence is detected. Significant drift is injected into the AI prompt as
  a [CHARACTER EVOLUTION NOTE] so the LLM reflects lived experience.

T2 — Elastic Memory Windows
  Computes a dynamic retrieval window size for memory queries based on:
    • chaos_factor     (1–10)
    • emotional intensity (0–3)
    • inferred scene type (idle → combat → death)
  This expands context during pivotal scenes and compresses it during idle
  travel, balancing narrative richness against token budget.

Based on:
  arXiv:2603.09043 — Identity & Consciousness in LLM agents
  arXiv:2603.09716 — AutoAgent Elastic Memory
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── T6: Identity Drift ────────────────────────────────────────────────────────

# Maps lowercase narrative keywords to OCEAN-style personality dimension deltas.
DRIFT_SIGNALS: Dict[str, Dict[str, float]] = {
    # Bravery / Fear axis
    "charged":      {"courage": +0.08, "openness": +0.05},
    "fled":         {"courage": -0.10},
    "stood firm":   {"courage": +0.10},
    "cowered":      {"courage": -0.12},
    "attacked":     {"courage": +0.06},
    "retreated":    {"courage": -0.07},
    # Loyalty axis
    "betrayed":     {"loyalty": -0.15},
    "defended":     {"loyalty": +0.10},
    "abandoned":    {"loyalty": -0.12},
    "oath":         {"loyalty": +0.08},
    "swore":        {"loyalty": +0.07},
    # Kindness / cruelty axis
    "helped":       {"agreeableness": +0.06},
    "killed":       {"agreeableness": -0.08},
    "healed":       {"agreeableness": +0.10},
    "tortured":     {"agreeableness": -0.15},
    "spared":       {"agreeableness": +0.09},
    "slaughtered":  {"agreeableness": -0.10},
    # Discipline / impulsiveness
    "refused":      {"conscientiousness": +0.05},
    "impulsive":    {"conscientiousness": -0.08},
    "planned":      {"conscientiousness": +0.07},
    "reckless":     {"conscientiousness": -0.09},
    # Openness / curiosity
    "explored":     {"openness": +0.06},
    "curious":      {"openness": +0.05},
    "investigated": {"openness": +0.04},
}


@dataclass
class DriftVector:
    """Quantified identity drift for one character over a window of turns."""

    character_id: str
    turn_evaluated: int
    dimension_deltas: Dict[str, float]   # e.g. {"courage": -0.3, "loyalty": +0.2}
    dominant_drift: Optional[str]        # highest-magnitude dimension
    magnitude: float                      # sum of abs(deltas)
    narrative_summary: str               # human-readable prose

    def is_significant(self, threshold: float = 0.25) -> bool:
        return self.magnitude >= threshold


class IdentityDriftChecker:
    """
    Periodically evaluates a character's recent memory events and computes a
    drift vector against their base personality.

    Attach to ``EnhancedMemoryManager``.
    Call ``evaluate_character()`` from the engine turn loop.

    Never raises — all exceptions are caught and logged.
    """

    CHECK_INTERVAL: int = 20   # turns between evaluations
    LOOKBACK_TURNS: int = 30   # recent events to scan

    def __init__(self, memory_manager: Any, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = (config or {}).get("memory_hardening", {}).get("identity_drift", {})
        self.CHECK_INTERVAL = int(cfg.get("check_interval_turns", self.CHECK_INTERVAL))
        self.LOOKBACK_TURNS = int(cfg.get("lookback_turns", self.LOOKBACK_TURNS))
        self._significance_threshold = float(cfg.get("significance_threshold", 0.25))
        self._memory = memory_manager
        self._drift_log: Dict[str, List[DriftVector]] = {}

    def evaluate_character(
        self,
        character_id: str,
        current_turn: int,
        base_traits: Optional[Dict[str, Any]] = None,
    ) -> Optional[DriftVector]:
        """
        Evaluate identity drift for *character_id* at *current_turn*.

        Returns a ``DriftVector`` if drift is significant, otherwise None.
        Only runs on turns that are multiples of ``CHECK_INTERVAL``.
        """
        try:
            if current_turn % self.CHECK_INTERVAL != 0:
                return None

            recent_events: List[Dict] = []
            if hasattr(self._memory, "get_recent_events_for_character"):
                recent_events = self._memory.get_recent_events_for_character(
                    character_id=character_id,
                    count=self.LOOKBACK_TURNS,
                )
            if not recent_events:
                return None

            # Accumulate drift signals from event descriptions
            accumulated: Dict[str, float] = {}
            for event in recent_events:
                desc = str(event.get("description", "")).lower()
                for keyword, deltas in DRIFT_SIGNALS.items():
                    if keyword in desc:
                        for dim, delta in deltas.items():
                            accumulated[dim] = accumulated.get(dim, 0.0) + delta

            if not accumulated:
                return None

            magnitude = sum(abs(v) for v in accumulated.values())
            dominant_entry = max(accumulated.items(), key=lambda kv: abs(kv[1]), default=(None, 0))
            dominant = dominant_entry[0]

            # Build narrative summary
            positive = [d for d, v in accumulated.items() if v > 0.1]
            negative = [d for d, v in accumulated.items() if v < -0.1]
            parts: List[str] = []
            if positive:
                parts.append(f"growing more {', '.join(positive)}")
            if negative:
                parts.append(f"growing less {', '.join(negative)}")
            if parts:
                summary = f"{character_id} has been " + "; ".join(parts)
            else:
                summary = f"{character_id} appears stable"

            drift = DriftVector(
                character_id=character_id,
                turn_evaluated=current_turn,
                dimension_deltas=accumulated,
                dominant_drift=dominant,
                magnitude=magnitude,
                narrative_summary=summary,
            )

            if drift.is_significant(self._significance_threshold):
                self._drift_log.setdefault(character_id, []).append(drift)
                logger.info("Identity drift detected: %s (magnitude=%.2f)", summary, magnitude)
                return drift

            return None

        except Exception as exc:
            logger.warning("IdentityDriftChecker.evaluate_character failed for %s: %s", character_id, exc)
            return None

    def get_drift_history(self, character_id: str) -> List[DriftVector]:
        return list(self._drift_log.get(character_id, []))


# ── T2: Elastic Memory Windows ───────────────────────────────────────────────

# Per-scene-type base multipliers applied to BASE_WINDOW.
SCENE_MULTIPLIERS: Dict[str, float] = {
    "idle":        0.5,
    "travel":      0.6,
    "commerce":    0.7,
    "dialogue":    1.0,
    "ritual":      1.5,
    "oath":        1.8,
    "combat":      1.8,
    "revelation":  2.0,
    "betrayal":    2.2,
    "death":       2.5,
}

BASE_WINDOW: int = 15

# Keyword sets used to infer scene type from free text.
SCENE_KEYWORDS: Dict[str, List[str]] = {
    "combat":     ["attack", "battle", "fight", "strike", "wound", "kill", "blood", "sword", "axe", "shield",
                   # SRD condition terms that signal active combat
                   "paralyzed", "stunned", "grappled", "restrained", "prone", "unconscious",
                   "death saving", "concentration", "spell slot", "action economy"],
    "death":      ["die", "dies", "dead", "slain", "killed", "final breath", "falls", "corpse", "burial",
                   "unconscious", "dying", "death save"],
    "betrayal":   ["betray", "deceive", "lied", "backstab", "treachery", "treason"],
    "oath":       ["oath", "swear", "vow", "promise", "pledge", "bind"],
    "ritual":     ["ritual", "rune", "seidr", "sacrifice", "invocation", "offering", "blót"],
    "revelation": ["revealed", "truth", "secret", "discovered", "realised", "knew all along", "confessed"],
    "commerce":   ["trade", "barter", "coin", "silver", "buy", "sell", "merchant"],
    "travel":     ["travel", "journey", "road", "sail", "voyage", "passage"],
    "idle":       ["wait", "rest", "sit", "idle", "pause", "linger", "watch", "stand"],
    # SRD-specific condition events — mapped to "combat" scene type by infer_scene_type
    "condition_event": ["condition_event", "near_death", "exhaustion_critical"],
}


def infer_scene_type(text: str, event_tags: Optional[List[str]] = None) -> str:
    """
    Classify *text* into a scene type string.

    Priority order: combat → death → betrayal → oath → ritual → revelation →
    commerce → travel → dialogue → idle.
    Falls back to ``"dialogue"`` for long text and ``"idle"`` for short.

    Args:
        text: Free-form turn text to classify.
        event_tags: Optional pre-computed tags from enhanced_memory
            (e.g. "condition_event", "near_death") — condition_event and
            near_death both map to "combat" / "death" respectively.
    """
    if not text and not event_tags:
        return "idle"
    # Fast path: pre-tagged condition events
    if event_tags:
        tags_lower = {str(t).lower() for t in event_tags}
        if "near_death" in tags_lower or "death" in tags_lower:
            return "death"
        if "condition_event" in tags_lower or "combat" in tags_lower:
            return "combat"
    if not text:
        return "idle"
    low = text.lower()
    for scene_type in ("combat", "death", "betrayal", "oath", "ritual",
                        "revelation", "commerce", "travel"):
        if any(kw in low for kw in SCENE_KEYWORDS[scene_type]):
            return scene_type
    return "dialogue" if len(text.split()) > 20 else "idle"


class ElasticWindowCalculator:
    """
    Computes a dynamic memory retrieval window size for a given game snapshot.

    Formula:
      window = BASE_WINDOW × scene_mult × chaos_mult × emotion_mult × change_mult
      clamped to [MIN_WINDOW, MAX_WINDOW]
    """

    MIN_WINDOW: int = 5
    MAX_WINDOW: int = 40

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        cfg = (config or {}).get("memory_hardening", {}).get("elastic_memory", {})
        self._base    = int(cfg.get("base_window",  BASE_WINDOW))
        self._min     = int(cfg.get("min_window",   self.MIN_WINDOW))
        self._max     = int(cfg.get("max_window",   self.MAX_WINDOW))
        self._enabled = cfg.get("enabled", True)

    def compute(
        self,
        chaos_factor: int,
        dominant_emotion_intensity: float,
        scene_type: str,
        turn_rate_of_change: float = 0.0,
    ) -> int:
        """
        Return the recommended window size (number of memory items to retrieve).
        Always returns a valid integer even if disabled (returns BASE_WINDOW).
        """
        if not self._enabled:
            return self._base

        # Scene multiplier
        scene_mult = SCENE_MULTIPLIERS.get(scene_type, 1.0)

        # Chaos: 1–10 → 0.80–1.40 multiplier
        chaos_clamped = max(1, min(10, int(chaos_factor)))
        chaos_mult = 0.80 + (chaos_clamped - 1) * 0.0667

        # Emotion: 0–3 → 0.90–1.30 multiplier
        emo_clamped = max(0.0, min(3.0, float(dominant_emotion_intensity)))
        emotion_mult = 0.90 + emo_clamped * 0.1333

        # Rate of change: 0–1 → 0.95–1.20 multiplier
        roc_clamped = max(0.0, min(1.0, float(turn_rate_of_change)))
        change_mult = 0.95 + roc_clamped * 0.25

        raw = self._base * scene_mult * chaos_mult * emotion_mult * change_mult
        return int(max(self._min, min(self._max, round(raw))))
