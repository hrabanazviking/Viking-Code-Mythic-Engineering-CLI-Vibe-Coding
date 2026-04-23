"""
ScaffoldBuilder — assembles a CognitionScaffold from an InputSketch + memory bundle.

The scaffold is the deterministic steering object passed to the prompt builder.
It encodes goal, tone, focus, avoid, depth, candidate_modes, and the fact block
assembled from retrieved knowledge records.

Design: small, fast, no model calls. All logic is table-driven + heuristic.
"""

from __future__ import annotations

import logging
from typing import Any

from thoughtforge.knowledge.models import (
    ActivatedRecord,
    CognitionScaffold,
    InputSketch,
    MemoryActivationBundle,
    PersonalityCoreRecord,
)

logger = logging.getLogger(__name__)


# ── Goal derivation ────────────────────────────────────────────────────────────

_INTENT_TO_GOAL: dict[str, str] = {
    "technical_spec_request": "produce a clear, structured, implementation-ready response",
    "technical_debugging":    "identify the likely cause and provide a concrete fix",
    "editing_refinement":     "preserve meaning while improving clarity and force",
    "brainstorming":          "generate strong, distinct options with low repetition",
    "naming_or_branding":     "produce memorable, distinctive name candidates",
    "planning_request":       "produce a clear, ordered, actionable plan",
    "emotional_support":      "validate the emotion and offer one useful stabilizing thought",
    "factual_query":          "give an accurate, direct answer with cited sources",
    "light_conversation":     "keep the exchange natural, warm, and engaging",
}

# ── Tone derivation ────────────────────────────────────────────────────────────

_MODE_TO_TONE: dict[str, list[str]] = {
    "structured_technical": ["direct", "structured", "precise"],
    "concise_editorial":    ["sharp", "natural", "economical"],
    "creative_brainstorm":  ["energetic", "open", "inventive"],
    "calm_supportive":      ["calm", "warm", "grounded"],
    "factual_direct":       ["direct", "factual", "clear"],
    "light_natural_chat":   ["warm", "natural", "easy"],
}

_USER_TONE_OVERLAY: dict[str, list[str]] = {
    "frustrated": ["patient", "steady"],
    "tired":      ["gentle", "clear"],
    "urgent":     ["focused", "fast"],
    "curious":    ["curious", "engaged"],
    "playful":    ["light", "playful"],
}

# ── Focus derivation ───────────────────────────────────────────────────────────

_INTENT_TO_FOCUS: dict[str, list[str]] = {
    "technical_spec_request": ["clarity", "specificity", "completeness"],
    "technical_debugging":    ["root cause", "concrete fix", "minimal change"],
    "editing_refinement":     ["precision", "rhythm", "no redundancy"],
    "brainstorming":          ["originality", "relevance", "distinctiveness"],
    "naming_or_branding":     ["memorability", "fit", "brevity"],
    "planning_request":       ["order", "clarity", "feasibility"],
    "emotional_support":      ["recognition", "one useful thought"],
    "factual_query":          ["accuracy", "brevity", "citation"],
    "light_conversation":     ["naturalness", "engagement"],
}

# ── Avoid derivation ───────────────────────────────────────────────────────────

_ALWAYS_AVOID = ["filler", "padding", "repetition of the user's question"]

_INTENT_AVOID_EXTRAS: dict[str, list[str]] = {
    "technical_spec_request": ["vagueness", "handwaving", "pseudo-code"],
    "technical_debugging":    ["speculation without evidence", "multiple unrelated fixes"],
    "editing_refinement":     ["meaning distortion", "over-editing"],
    "brainstorming":          ["generic ideas", "overexplaining"],
    "naming_or_branding":     ["generic options", "overly long names"],
    "planning_request":       ["vague milestones", "over-engineering"],
    "emotional_support":      ["platitudes", "preachiness", "robotic tone"],
    "factual_query":          ["guessing", "unverified claims"],
    "light_conversation":     ["lecture mode", "unsolicited advice"],
}

# ── Depth derivation ───────────────────────────────────────────────────────────

_EXPERT_INTENTS = {"technical_spec_request", "technical_debugging", "planning_request"}
_LIGHT_INTENTS = {"light_conversation", "naming_or_branding", "emotional_support"}


def _derive_depth(sketch: InputSketch) -> str:
    if sketch.intent in _EXPERT_INTENTS:
        return "expert" if sketch.urgency < 0.8 else "medium"
    if sketch.intent in _LIGHT_INTENTS:
        return "light"
    return "medium"


# ── Candidate modes derivation ─────────────────────────────────────────────────

_INTENT_TO_CANDIDATE_MODES: dict[str, list[str]] = {
    "technical_spec_request": ["strict_spec", "implementation_friendly"],
    "technical_debugging":    ["implementation_friendly", "strict_spec"],
    "editing_refinement":     ["editorial_sharp", "implementation_friendly"],
    "brainstorming":          ["brainstorm_distinct", "brainstorm_distinct"],
    "naming_or_branding":     ["brainstorm_distinct", "practical"],
    "planning_request":       ["strict_spec", "practical"],
    "emotional_support":      ["empathic", "reflective"],
    "factual_query":          ["implementation_friendly", "strict_spec"],
    "light_conversation":     ["practical", "playful"],
}


# ── Fact block assembly ────────────────────────────────────────────────────────

def _build_fact_block(records: list[ActivatedRecord], max_records: int = 8) -> str:
    """Assemble a compact fact block from top-scored knowledge records."""
    if not records:
        return ""

    top = sorted(records, key=lambda r: r.score, reverse=True)[:max_records]
    lines: list[str] = []
    for r in top:
        raw: dict[str, Any] = r.raw or {}
        qid = raw.get("qid", "")
        label = raw.get("label_en") or raw.get("title") or r.record_id
        desc = raw.get("description_en") or raw.get("content", "")
        source = raw.get("source", r.record_type)

        if qid:
            line = f"[{qid}] {label}"
            if desc:
                short = desc[:120].rsplit(" ", 1)[0]
                line += f" — {short}"
        elif label:
            line = f"[{source}] {label}"
            if desc:
                short = desc[:120].rsplit(" ", 1)[0]
                line += f" — {short}"
        else:
            line = r.cue

        lines.append(line)

    return "\n".join(lines)


# ── ScaffoldBuilder ────────────────────────────────────────────────────────────

class ScaffoldBuilder:
    """
    Assembles a CognitionScaffold from InputSketch + MemoryActivationBundle.
    Table-driven + heuristic. No model calls.
    """

    def build(
        self,
        sketch: InputSketch,
        bundle: MemoryActivationBundle,
        personality: PersonalityCoreRecord | None = None,
    ) -> CognitionScaffold:
        """
        Build a CognitionScaffold for the current turn.

        Args:
            sketch:      The classified InputSketch for this turn.
            bundle:      Retrieved memory/knowledge records.
            personality: Loaded PersonalityCoreRecord (optional — uses defaults if None).

        Returns:
            A fully populated CognitionScaffold ready for PromptBuilder.
        """
        goal = _INTENT_TO_GOAL.get(sketch.intent, "produce a useful, direct response")

        # Tone: start from mode default, overlay user tone signals
        base_tone = list(_MODE_TO_TONE.get(sketch.response_mode, ["direct", "natural"]))
        overlay = _USER_TONE_OVERLAY.get(sketch.tone_in, [])
        tone = _merge_unique(base_tone, overlay, max_items=4)

        focus = list(_INTENT_TO_FOCUS.get(sketch.intent, ["clarity", "usefulness"]))

        # Avoid: universal defaults + intent-specific + personality avoids
        avoid = list(_ALWAYS_AVOID)
        avoid.extend(_INTENT_AVOID_EXTRAS.get(sketch.intent, []))
        if personality and personality.avoid:
            for a in personality.avoid[:3]:
                if a not in avoid:
                    avoid.append(a)

        depth = _derive_depth(sketch)
        candidate_modes = list(_INTENT_TO_CANDIDATE_MODES.get(sketch.intent, ["practical", "practical"]))
        fact_block = _build_fact_block(bundle.activated_records)

        scaffold = CognitionScaffold(
            goal=goal,
            tone=tone,
            focus=focus,
            avoid=avoid,
            depth=depth,
            candidate_modes=candidate_modes,
            fact_block=fact_block,
            prompt_text="",      # filled in by PromptBuilder
        )

        logger.debug(
            "ScaffoldBuilder: goal=%r depth=%s modes=%s records_in_block=%d",
            goal, depth, candidate_modes,
            len(bundle.activated_records),
        )
        return scaffold


def _merge_unique(base: list[str], extras: list[str], max_items: int = 4) -> list[str]:
    seen: set[str] = set(base)
    result = list(base)
    for item in extras:
        if item not in seen and len(result) < max_items:
            result.append(item)
            seen.add(item)
    return result
