"""Phase 20.4 — ``mythic-vibe ai recommend`` policy DSL.

Pure-policy module that scores models from the Phase-D static
catalog against operator-supplied constraints and returns the
top-N. **Zero provider calls** — runs without any API key set
and produces deterministic output for the same inputs.

Inputs (``RecommendationCriteria``):

- ``task`` — free-form text. Used for keyword heuristics
  (e.g. "image", "vision", "screenshot" → vision_required).
- ``max_context`` — minimum acceptable context window in
  tokens.
- ``vision_required`` — explicit vision capability gate.
- ``cost_class`` — ``"cheap" | "standard" | "premium"`` —
  filters by family-tier heuristic.
- ``family`` — restrict to a specific provider family
  (anthropic / openai / gemini / openrouter / all).

Output: a sorted ``list[ModelRecommendation]`` carrying the
underlying ``ModelInfo``, the integer score, and a list of
human-readable reason strings explaining the score. Top-N is
applied by the caller (``cmd_ai_recommend`` defaults to 3).

Cross-platform: pure stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Literal

from .providers.model_catalog import ModelInfo, list_models_static


SUPPORTED_FAMILIES: tuple[str, ...] = (
    "anthropic", "openai", "gemini", "openrouter",
)

CostClass = Literal["cheap", "standard", "premium"]
COST_CLASSES: tuple[str, ...] = ("cheap", "standard", "premium")


# Heuristic — model id substrings → cost class. Curated against
# the Phase-D catalog at audit-cycle time. Updated when the
# catalog grows (covered by snapshot-style tests against the
# real catalog).
_COST_CLASS_HEURISTICS: dict[CostClass, tuple[str, ...]] = {
    "cheap": (
        "haiku", "flash", "mini", "small", "8b", "phi", "lite",
    ),
    "premium": (
        "opus", "ultra", "pro", "405b", "70b", "o1", "advanced",
    ),
}


_VISION_KEYWORDS = (
    "image", "images", "screenshot", "vision", "photo", "ocr",
    "diagram", "chart", "video frame",
)


@dataclass(frozen=True)
class RecommendationCriteria:
    """Operator-supplied scoring inputs. Every field has a sane
    default so partially-specified criteria still produce
    output."""

    task: str = ""
    max_context: int = 0
    vision_required: bool = False
    cost_class: CostClass | None = None
    family: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "task": self.task,
            "max_context": self.max_context,
            "vision_required": self.vision_required,
            "cost_class": self.cost_class,
            "family": self.family,
        }


@dataclass(frozen=True)
class ModelRecommendation:
    """One scored model. ``reasons`` is a list of short
    operator-readable strings explaining the score breakdown."""

    model: ModelInfo
    score: int
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "model": self.model.to_dict(),
            "score": self.score,
            "reasons": list(self.reasons),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classify_cost(model_id: str) -> CostClass:
    """Bucket a model into cheap / standard / premium using the
    fixed heuristic table. Defaults to ``"standard"`` when no
    substring matches."""
    lower = model_id.lower()
    for token in _COST_CLASS_HEURISTICS["cheap"]:
        if token in lower:
            return "cheap"
    for token in _COST_CLASS_HEURISTICS["premium"]:
        if token in lower:
            return "premium"
    return "standard"


def _detect_vision_intent(task: str) -> bool:
    """Heuristic: does the task text imply vision capability?
    Used to bump scores when the operator didn't explicitly set
    ``vision_required`` but clearly wants it."""
    if not task:
        return False
    lower = task.lower()
    return any(token in lower for token in _VISION_KEYWORDS)


def _all_static_models(family: str | None) -> list[ModelInfo]:
    """Collect static models from the requested family or all
    supported families."""
    if family and family.strip().lower() != "all":
        return list_models_static(family)
    out: list[ModelInfo] = []
    for fam in SUPPORTED_FAMILIES:
        out.extend(list_models_static(fam))
    return out


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_model(
    model: ModelInfo,
    criteria: RecommendationCriteria,
) -> tuple[int, tuple[str, ...]]:
    """Score one model against the criteria. Returns
    ``(score, reasons)``. Higher is better. Zero / negative
    scores are valid — the caller decides whether to filter
    them out."""
    score = 0
    reasons: list[str] = []

    if criteria.max_context:
        if model.context_window >= criteria.max_context:
            score += 30
            reasons.append(
                f"context window {model.context_window:,} ≥ "
                f"{criteria.max_context:,} (required)"
            )
        else:
            # Hard penalty — under-spec context is usually a
            # dealbreaker. Big enough to drop below cost-class
            # bonuses but not so big it causes negative-only
            # output that confuses operators.
            score -= 100
            reasons.append(
                f"context window {model.context_window:,} < "
                f"{criteria.max_context:,} (REQUIRED, hard penalty)"
            )

    explicit_vision = criteria.vision_required
    inferred_vision = _detect_vision_intent(criteria.task)
    needs_vision = explicit_vision or inferred_vision
    has_vision = "vision" in model.capabilities
    if needs_vision:
        if has_vision:
            score += 25
            reasons.append(
                "vision capability present" + (
                    " (required)" if explicit_vision
                    else " (inferred from task keywords)"
                )
            )
        else:
            score -= 50
            reasons.append(
                "vision required but model has no `vision` capability"
            )

    if criteria.cost_class:
        actual = _classify_cost(model.id)
        if actual == criteria.cost_class:
            score += 20
            reasons.append(f"cost class matches: {actual}")
        else:
            # Mild penalty — operators often have flexibility on
            # cost class, so we don't slam the score.
            score -= 5
            reasons.append(
                f"cost class {actual!r} != requested {criteria.cost_class!r}"
            )

    if criteria.family:
        target = criteria.family.strip().lower()
        if target != "all" and model.family.lower() == target:
            score += 10
            reasons.append(f"family matches: {model.family}")

    # Capability-richness tiebreaker — more capabilities = more
    # versatile, useful when scores are otherwise tied.
    score += len(model.capabilities)
    if model.capabilities:
        reasons.append(
            "capabilities: " + ", ".join(sorted(model.capabilities))
        )

    return score, tuple(reasons)


def recommend_models(
    criteria: RecommendationCriteria,
    *,
    top_n: int = 3,
    candidates: Iterable[ModelInfo] | None = None,
) -> list[ModelRecommendation]:
    """Score and sort all candidates, return the top-N. When
    ``candidates`` is None, the static catalog (filtered by
    ``criteria.family``) is used. ``top_n=0`` returns every
    candidate (useful for tests)."""
    pool = (
        list(candidates)
        if candidates is not None
        else _all_static_models(criteria.family)
    )
    scored = [
        ModelRecommendation(
            model=model,
            score=score,
            reasons=reasons,
        )
        for model in pool
        for (score, reasons) in [score_model(model, criteria)]
    ]
    scored.sort(key=lambda r: (-r.score, r.model.id))
    if top_n > 0:
        return scored[:top_n]
    return scored


__all__ = [
    "COST_CLASSES",
    "SUPPORTED_FAMILIES",
    "CostClass",
    "ModelRecommendation",
    "RecommendationCriteria",
    "recommend_models",
    "score_model",
]
