"""
All retrieval, pruning, and writeback scoring formulas for ThoughtForge.

Every formula is sourced directly from the spec documents.
No magic numbers — all weights are named constants.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Retrieval scoring weights (base) ──────────────────────────────────────────

RETRIEVAL_WEIGHTS_BASE = {
    "semantic_similarity": 0.35,
    "tone_similarity": 0.20,
    "preference_relevance": 0.20,
    "recency": 0.10,
    "importance": 0.15,
}

RETRIEVAL_WEIGHTS_BY_TYPE: dict[str, dict[str, float]] = {
    "user_preference": {
        "semantic_similarity": 0.25,
        "tone_similarity": 0.20,
        "preference_relevance": 0.30,
        "recency": 0.05,
        "importance": 0.20,
        "thread_boost": 0.00,
        "pattern_quality": 0.00,
        "priority": 0.00,
    },
    "user_fact": {
        "semantic_similarity": 0.40,
        "tone_similarity": 0.05,
        "preference_relevance": 0.15,
        "recency": 0.10,
        "importance": 0.20,
        "thread_boost": 0.10,
        "pattern_quality": 0.00,
        "priority": 0.00,
    },
    "episode": {
        "semantic_similarity": 0.30,
        "tone_similarity": 0.25,
        "preference_relevance": 0.10,
        "recency": 0.20,
        "importance": 0.15,
        "thread_boost": 0.00,
        "pattern_quality": 0.00,
        "priority": 0.00,
    },
    "response_pattern": {
        "semantic_similarity": 0.25,
        "tone_similarity": 0.15,
        "preference_relevance": 0.30,
        "recency": 0.05,
        "importance": 0.10,
        "thread_boost": 0.00,
        "pattern_quality": 0.15,
        "priority": 0.00,
    },
    "active_thread_state": {
        "semantic_similarity": 0.30,
        "tone_similarity": 0.10,
        "preference_relevance": 0.15,
        "recency": 0.10,
        "importance": 0.05,
        "thread_boost": 0.15,
        "pattern_quality": 0.00,
        "priority": 0.15,
    },
}

# ── Thresholds ─────────────────────────────────────────────────────────────────

MIN_MEMORY_SCORE: float = 0.45
MIN_FRAGMENT_SCORE: float = 0.54
MIN_FINAL_RESPONSE_SCORE: float = 0.68
MIN_PREFERENCE_WRITEBACK_SCORE: float = 0.72
MIN_EPISODE_WRITEBACK_SCORE: float = 0.58
MIN_PATTERN_LEARNING_SCORE: float = 0.78

# ── Pruning score weights ──────────────────────────────────────────────────────

PRUNE_SCORE_WEIGHTS = {
    "staleness": 0.25,
    "redundancy": 0.20,
    "low_confidence": 0.15,
    "low_importance": 0.15,
    "low_quality": 0.10,
    "low_future_relevance": 0.10,
    "low_reinforcement": 0.05,
}

SURVIVAL_SCORE_WEIGHTS = {
    "importance": 0.25,
    "confidence": 0.20,
    "quality": 0.15,
    "future_relevance": 0.20,
    "recency": 0.10,
    "reinforcement_strength": 0.10,
}

# ── Recency decay half-lives (in days) ────────────────────────────────────────

HALF_LIFE_DAYS: dict[str, float] = {
    "active_thread_state": 0.07,   # ~2 turns at 10 min/turn
    "episode": 7.0,
    "response_pattern": 30.0,
    "user_preference": 90.0,
    "user_fact": 180.0,
    "personality_core": 9999.0,
}

# ── Reinforcement increments ───────────────────────────────────────────────────

REINFORCE_CONFIDENCE_DELTA: float = 0.05
REINFORCE_IMPORTANCE_DELTA: float = 0.03
REINFORCE_QUALITY_DELTA: float = 0.02


# ── Scoring functions ──────────────────────────────────────────────────────────

@dataclass
class RetrievalDimensions:
    semantic_similarity: float = 0.0
    tone_similarity: float = 0.0
    preference_relevance: float = 0.0
    recency: float = 0.0
    importance: float = 0.0
    thread_boost: float = 0.0
    pattern_quality: float = 0.0
    priority: float = 0.0


def score_retrieval(dims: RetrievalDimensions, record_type: str) -> float:
    """Compute retrieval score for a memory record using type-specific weights."""
    weights = RETRIEVAL_WEIGHTS_BY_TYPE.get(record_type, RETRIEVAL_WEIGHTS_BASE)
    d = {
        "semantic_similarity": dims.semantic_similarity,
        "tone_similarity": dims.tone_similarity,
        "preference_relevance": dims.preference_relevance,
        "recency": dims.recency,
        "importance": dims.importance,
        "thread_boost": dims.thread_boost,
        "pattern_quality": dims.pattern_quality,
        "priority": dims.priority,
    }
    return sum(d.get(k, 0.0) * w for k, w in weights.items())


def compute_recency_score(age_days: float, record_type: str) -> float:
    """Half-life recency decay: score = 0.5 ^ (age / half_life)."""
    half_life = HALF_LIFE_DAYS.get(record_type, 30.0)
    if half_life <= 0:
        return 1.0
    return math.pow(0.5, age_days / half_life)


@dataclass
class PruneComponents:
    staleness: float = 0.0
    redundancy: float = 0.0
    low_confidence: float = 0.0
    low_importance: float = 0.0
    low_quality: float = 0.0
    low_future_relevance: float = 0.0
    low_reinforcement: float = 0.0


def compute_prune_score(c: PruneComponents) -> float:
    """Higher score = more likely to be pruned."""
    return (
        c.staleness * PRUNE_SCORE_WEIGHTS["staleness"]
        + c.redundancy * PRUNE_SCORE_WEIGHTS["redundancy"]
        + c.low_confidence * PRUNE_SCORE_WEIGHTS["low_confidence"]
        + c.low_importance * PRUNE_SCORE_WEIGHTS["low_importance"]
        + c.low_quality * PRUNE_SCORE_WEIGHTS["low_quality"]
        + c.low_future_relevance * PRUNE_SCORE_WEIGHTS["low_future_relevance"]
        + c.low_reinforcement * PRUNE_SCORE_WEIGHTS["low_reinforcement"]
    )


@dataclass
class SurvivalComponents:
    importance: float = 0.0
    confidence: float = 0.0
    quality: float = 0.0
    future_relevance: float = 0.0
    recency: float = 0.0
    reinforcement_strength: float = 0.0


def compute_survival_score(c: SurvivalComponents) -> float:
    """Higher score = more likely to survive pruning."""
    return (
        c.importance * SURVIVAL_SCORE_WEIGHTS["importance"]
        + c.confidence * SURVIVAL_SCORE_WEIGHTS["confidence"]
        + c.quality * SURVIVAL_SCORE_WEIGHTS["quality"]
        + c.future_relevance * SURVIVAL_SCORE_WEIGHTS["future_relevance"]
        + c.recency * SURVIVAL_SCORE_WEIGHTS["recency"]
        + c.reinforcement_strength * SURVIVAL_SCORE_WEIGHTS["reinforcement_strength"]
    )


@dataclass
class WritebackComponents:
    durability: float = 0.0
    novelty: float = 0.0
    confidence: float = 0.0
    importance: float = 0.0
    future_relevance: float = 0.0
    thread_relevance: float = 0.0
    final_response_quality: float = 0.0
    pattern_reusability: float = 0.0


def compute_preference_writeback_score(c: WritebackComponents) -> float:
    return (
        c.durability * 0.30
        + c.novelty * 0.20
        + c.confidence * 0.25
        + c.importance * 0.10
        + c.future_relevance * 0.15
    )


def compute_episode_writeback_score(c: WritebackComponents) -> float:
    return (
        c.novelty * 0.20
        + c.confidence * 0.15
        + c.importance * 0.25
        + c.future_relevance * 0.20
        + c.thread_relevance * 0.20
    )


def compute_pattern_learning_score(c: WritebackComponents) -> float:
    return (
        c.final_response_quality * 0.45
        + c.pattern_reusability * 0.30
        + c.future_relevance * 0.25
    )


GENERICNESS_PHRASES: frozenset[str] = frozenset({
    "a lot of people", "it's normal", "as an ai", "everything will be okay",
    "in today's world", "many people feel", "you're not alone", "it is what it is",
    "at the end of the day", "there are many ways", "it depends on the situation",
})


def compute_genericness_penalty(text: str) -> float:
    """Heuristic genericness penalty (0.0–1.0). Higher = more generic."""
    text_lower = text.lower()
    hits = sum(1 for phrase in GENERICNESS_PHRASES if phrase in text_lower)
    words = text.split()
    if not words:
        return 0.0
    word_count = len(words)
    unique_words = len(set(w.lower() for w in words))
    repetition_ratio = 1.0 - (unique_words / word_count) if word_count > 0 else 0.0
    phrase_penalty = min(hits * 0.15, 0.6)
    return min(phrase_penalty + repetition_ratio * 0.4, 1.0)
