"""
PromptBuilder — assembles mode-specific prompts from CognitionScaffold.

Follows the Prompt_Templates_Spec exactly:
  - candidate (generic / technical / supportive / brainstorm / editorial)
  - refine   (from fragments)
  - repair   (fallback when refined output is still weak)

Token discipline: prompts are narrow, labeled, and lean.
Each builder method returns a plain string ready for TurboQuantEngine.generate().
"""

from __future__ import annotations

import logging

from thoughtforge.knowledge.models import (
    CognitionScaffold,
    FragmentRecord,
    InputSketch,
    MemoryActivationBundle,
)

logger = logging.getLogger(__name__)

# ── Output shape table ─────────────────────────────────────────────────────────

_MODE_TO_OUTPUT_SHAPE: dict[str, str] = {
    "structured_technical": "markdown-ready section with concise headings",
    "concise_editorial":    "one refined version only",
    "creative_brainstorm":  "3 compact distinct options",
    "calm_supportive":      "3-5 sentences",
    "factual_direct":       "1-3 sentences with source citation",
    "light_natural_chat":   "2-4 sentences",
}

_DEPTH_TO_LENGTH_HINT: dict[str, str] = {
    "light":  "Keep it short.",
    "medium": "Keep it focused.",
    "expert": "Be thorough but not verbose.",
}

# ── Candidate mode → template variant ─────────────────────────────────────────

_CANDIDATE_OPENERS: dict[str, str] = {
    "strict_spec":            "Write one concise, structured technical response.",
    "implementation_friendly":"Write one clear, implementation-ready response.",
    "editorial_sharp":        "Rewrite the text cleanly and precisely.",
    "brainstorm_distinct":    "Write one strong, distinctive option.",
    "empathic":               "Write one short, warm, grounded supportive reply.",
    "reflective":             "Write one thoughtful, perceptive reply.",
    "practical":              "Write one direct, practical response.",
    "playful":                "Write one light, natural reply with some warmth.",
}


class PromptBuilder:
    """
    Builds all prompt types for ThoughtForge's generation pipeline.
    Stateless — all context passed per call.
    """

    # ── Candidate prompt ───────────────────────────────────────────────────────

    def build_candidate_prompt(
        self,
        sketch: InputSketch,
        scaffold: CognitionScaffold,
        mode: str,
        memory_cues: list[str],
    ) -> str:
        """
        Build a first-pass candidate generation prompt.

        Args:
            sketch:       InputSketch for this turn.
            scaffold:     CognitionScaffold with goal/tone/focus/avoid.
            mode:         Candidate mode (e.g. "strict_spec", "empathic").
            memory_cues:  Compressed cue strings from MemoryActivationBundle (max 3).

        Returns:
            Prompt string.
        """
        opener = _CANDIDATE_OPENERS.get(mode, "Write one short reply.")
        output_shape = _MODE_TO_OUTPUT_SHAPE.get(sketch.response_mode, "2-4 sentences")
        length_hint = _DEPTH_TO_LENGTH_HINT.get(scaffold.depth, "")

        tone_str = ", ".join(scaffold.tone[:3]) if scaffold.tone else "direct, natural"
        focus_str = ", ".join(scaffold.focus[:3]) if scaffold.focus else "clarity"
        avoid_str = ", ".join(scaffold.avoid[:3]) if scaffold.avoid else "filler"

        cue_lines = "\n".join(f"- {c}" for c in memory_cues[:3]) if memory_cues else "- none"

        fact_section = ""
        if scaffold.fact_block:
            fact_section = f"\nKnowledge context:\n{scaffold.fact_block}\n"

        prompt = (
            f"{opener}\n\n"
            f"User request: {sketch.raw_text}\n"
            f"Intent: {sketch.intent.replace('_', ' ')}\n"
            f"Topic: {sketch.topic}\n"
            f"Tone: {tone_str}\n"
            f"Goal: {scaffold.goal}\n"
            f"Focus: {focus_str}\n"
            f"Avoid: {avoid_str}\n"
            f"Memory cues:\n{cue_lines}\n"
            f"{fact_section}\n"
            f"Output: {output_shape} {length_hint}".rstrip()
        )

        logger.debug("Built candidate prompt (mode=%s, ~%d chars)", mode, len(prompt))
        return prompt

    # ── Refine prompt ──────────────────────────────────────────────────────────

    def build_refine_prompt(
        self,
        fragments: list[FragmentRecord],
        sketch: InputSketch,
        scaffold: CognitionScaffold,
    ) -> str:
        """
        Build a refine prompt from the best salvaged fragments.

        Args:
            fragments: Scored fragments with keep=True (max 5 used).
            sketch:    InputSketch for intent/tone context.
            scaffold:  CognitionScaffold for goal/avoid.

        Returns:
            Prompt string.
        """
        kept = [f for f in fragments if f.keep][:5]
        if not kept:
            # Fall back to all fragments if none flagged
            kept = sorted(fragments, key=lambda f: f.scores.composite, reverse=True)[:3]

        fragment_lines = "\n".join(f"- {f.text.strip()}" for f in kept if f.text.strip())

        output_shape = _MODE_TO_OUTPUT_SHAPE.get(sketch.response_mode, "2-4 sentences")
        tone_str = ", ".join(scaffold.tone[:2]) if scaffold.tone else "direct, natural"
        avoid_str = ", ".join(scaffold.avoid[:3]) if scaffold.avoid else "filler, repetition"

        prompt = (
            f"Using these useful fragments:\n{fragment_lines}\n\n"
            f"Write one clean response.\n\n"
            f"Intent: {sketch.intent.replace('_', ' ')}\n"
            f"Tone: {tone_str}\n"
            f"Goal: {scaffold.goal}\n"
            f"Avoid: {avoid_str}\n\n"
            f"Output: {output_shape}"
        )

        logger.debug("Built refine prompt (~%d chars, %d fragments)", len(prompt), len(kept))
        return prompt

    # ── Repair prompt ──────────────────────────────────────────────────────────

    def build_repair_prompt(
        self,
        sketch: InputSketch,
        scaffold: CognitionScaffold,
        memory_cues: list[str],
    ) -> str:
        """
        Build a repair prompt — used when refined output fails quality threshold.
        More constrained than candidate prompts.

        Args:
            sketch:       InputSketch.
            scaffold:     CognitionScaffold.
            memory_cues:  Top 2 memory cues at most.

        Returns:
            Prompt string.
        """
        output_shape = _MODE_TO_OUTPUT_SHAPE.get(sketch.response_mode, "2-4 sentences")
        tone_str = ", ".join(scaffold.tone[:2]) if scaffold.tone else "direct"
        cue_lines = "\n".join(f"- {c}" for c in memory_cues[:2]) if memory_cues else "- none"

        prompt = (
            f"Write one direct response.\n\n"
            f"User request: {sketch.raw_text}\n"
            f"Intent: {sketch.intent.replace('_', ' ')}\n"
            f"Tone: {tone_str}\n"
            f"Goal: {scaffold.goal}\n"
            f"Memory cues:\n{cue_lines}\n\n"
            f"Avoid generic wording. Keep it specific and useful.\n"
            f"Output: {output_shape}"
        )

        logger.debug("Built repair prompt (~%d chars)", len(prompt))
        return prompt

    # ── Writeback support prompts ──────────────────────────────────────────────

    def build_episode_summary_prompt(self, user_request: str, final_response: str) -> str:
        return (
            f"Summarize the conversation moment in one short memory line.\n\n"
            f"User request: {user_request}\n"
            f"Final response: {final_response[:300]}\n\n"
            f"Output: one compact summary under 20 words"
        )

    def build_preference_inference_prompt(self, user_request: str, context_hint: str) -> str:
        return (
            f"Infer one durable user preference only if strongly supported.\n\n"
            f"User request: {user_request}\n"
            f"Context: {context_hint}\n\n"
            f"Output:\n- preference summary\nor\n- none"
        )

    # ── Memory cue extraction ──────────────────────────────────────────────────

    @staticmethod
    def extract_memory_cues(bundle: MemoryActivationBundle, max_cues: int = 3) -> list[str]:
        """
        Extract the top compressed cue strings from a MemoryActivationBundle.
        Priority: preference/fact/pattern records over raw entity records.
        """
        type_priority = {
            "user_preference": 0,
            "user_fact": 1,
            "response_pattern": 2,
            "active_thread_state": 3,
            "episode": 4,
        }
        records = sorted(
            bundle.activated_records,
            key=lambda r: (type_priority.get(r.record_type, 9), -r.score),
        )
        return [r.cue for r in records[:max_cues] if r.cue]
