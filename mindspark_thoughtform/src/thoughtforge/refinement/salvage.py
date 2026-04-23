"""
FragmentSalvage — multi-pass draft scoring and intelligent reassembly.

Implements the BUILD_PLAN_v1 Phase 4 salvage pipeline:
  1. Score each candidate draft: length_score (45%) + citation_score (55%)
  2. Extract best sentence-level fragments from top-scoring drafts
  3. If an inference engine is available: attempt a refine pass (max 2 passes)
  4. Return the best result as a SalvageResult

Design: works with or without an inference engine. Without one, returns the
best-scoring draft directly. With one, tries to synthesize fragments into a
stronger response.

Fragment keep threshold follows the Retrieval_and_Scoring_Spec: 0.54 default.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from thoughtforge.cognition.prompt_builder import PromptBuilder
    from thoughtforge.knowledge.models import (
        CandidateRecord,
        CognitionScaffold,
        InputSketch,
        MemoryActivationBundle,
    )

logger = logging.getLogger(__name__)

# ── Scoring constants (BUILD_PLAN_v1 Phase 4) ─────────────────────────────────

_LENGTH_WEIGHT = 0.45
_CITATION_WEIGHT = 0.55
_IDEAL_LENGTH_CHARS = 550          # chars at which length_score reaches 1.0
_MAX_REFINE_PASSES = 2
_MIN_FRAGMENT_SCORE = 0.54         # from Retrieval_and_Scoring_Spec §30
_MIN_FRAGMENT_WORDS = 4
_MAX_FRAGMENTS_IN_REFINE = 5

_QID_RE = re.compile(r'\bQ\d{3,}\b')


# ── Result types ───────────────────────────────────────────────────────────────

@dataclass
class ScoredDraft:
    """A candidate draft with its salvage score."""
    candidate_id: str
    text: str
    length_score: float
    citation_score: float
    composite: float
    citations_found: list[str] = field(default_factory=list)


@dataclass
class SalvageResult:
    """Output of FragmentSalvage.forge()."""
    text: str
    citations: list[str]
    confidence: float
    passes_used: int
    best_draft_score: float
    fragments_kept: int
    salvage_path: str        # "direct" | "refine_pass_1" | "refine_pass_2" | "best_draft"


# ── FragmentSalvage ────────────────────────────────────────────────────────────

class FragmentSalvage:
    """
    Multi-pass draft scoring and fragment reassembly engine.

    Can operate with or without an inference engine:
      - With engine: attempts up to MAX_REFINE_PASSES refinement passes
      - Without engine: returns best-scoring draft directly
    """

    def forge(
        self,
        candidates: list["CandidateRecord"],
        bundle: "MemoryActivationBundle",
        engine: Any | None = None,
        prompt_builder: "PromptBuilder | None" = None,
        sketch: "InputSketch | None" = None,
        scaffold: "CognitionScaffold | None" = None,
        max_passes: int = _MAX_REFINE_PASSES,
    ) -> SalvageResult:
        """
        Score candidates and attempt fragment-based refinement.

        Args:
            candidates:     List of CandidateRecord from generation.
            bundle:         MemoryActivationBundle for citation validation.
            engine:         Optional TurboQuantEngine for refine passes.
            prompt_builder: Optional PromptBuilder for refine prompts.
            sketch:         Optional InputSketch for prompt context.
            scaffold:       Optional CognitionScaffold for prompt context.
            max_passes:     Max refinement passes (default 2).

        Returns:
            SalvageResult with best text, citations, confidence.
        """
        if not candidates:
            logger.debug("FragmentSalvage: no candidates — returning empty result")
            return SalvageResult(
                text="The forge finds no candidates to salvage.",
                citations=[],
                confidence=0.0,
                passes_used=0,
                best_draft_score=0.0,
                fragments_kept=0,
                salvage_path="empty",
            )

        retrieved_qids = self._extract_qids(bundle)

        # Step 1: Score all drafts
        scored = [self._score_draft(c, retrieved_qids) for c in candidates]
        scored.sort(key=lambda s: s.composite, reverse=True)
        best = scored[0]

        logger.debug(
            "FragmentSalvage: %d candidates scored. Best: id=%s composite=%.3f",
            len(scored), best.candidate_id, best.composite,
        )

        # Step 2: Extract best fragments
        fragments = self._extract_fragments(scored, retrieved_qids)
        logger.debug("FragmentSalvage: %d fragments kept (threshold=%.2f)", len(fragments), _MIN_FRAGMENT_SCORE)

        # Step 3: Attempt refine passes if engine available
        if engine is not None and prompt_builder is not None and sketch is not None and scaffold is not None:
            result = self._refine_with_engine(
                best_draft=best,
                fragments=fragments,
                bundle=bundle,
                retrieved_qids=retrieved_qids,
                engine=engine,
                prompt_builder=prompt_builder,
                sketch=sketch,
                scaffold=scaffold,
                max_passes=max_passes,
            )
            if result is not None:
                return result

        # Step 4: Fall back to best-scoring draft directly
        return SalvageResult(
            text=best.text,
            citations=best.citations_found,
            confidence=best.composite,
            passes_used=0,
            best_draft_score=best.composite,
            fragments_kept=len(fragments),
            salvage_path="best_draft",
        )

    # ── Draft scoring ──────────────────────────────────────────────────────────

    def _score_draft(self, candidate: "CandidateRecord", retrieved_qids: set[str]) -> ScoredDraft:
        """
        Score a candidate draft using the BUILD_PLAN_v1 formula:
          composite = length_score * 0.45 + citation_score * 0.55
        """
        text = candidate.text or ""

        # Length score: 0.0 → 1.0 as char count approaches ideal
        length_score = min(1.0, len(text) / _IDEAL_LENGTH_CHARS)

        # Citation score: fraction of retrieved QIDs that appear in the text
        cited = set(_QID_RE.findall(text))
        if retrieved_qids:
            citation_score = len(cited & retrieved_qids) / len(retrieved_qids)
        else:
            # No QIDs in knowledge base — treat as neutral
            citation_score = 0.5

        composite = length_score * _LENGTH_WEIGHT + citation_score * _CITATION_WEIGHT

        return ScoredDraft(
            candidate_id=candidate.candidate_id,
            text=text,
            length_score=length_score,
            citation_score=citation_score,
            composite=composite,
            citations_found=list(cited & retrieved_qids),
        )

    # ── Fragment extraction ────────────────────────────────────────────────────

    def _extract_fragments(
        self,
        scored_drafts: list[ScoredDraft],
        retrieved_qids: set[str],
    ) -> list[str]:
        """
        Extract and score sentence-level fragments from top-scoring drafts.
        Returns kept fragment texts sorted by their individual scores.
        """
        fragment_scores: list[tuple[str, float]] = []
        seen: set[str] = set()

        for draft in scored_drafts[:2]:     # only top 2 drafts contribute fragments
            sentences = _split_sentences(draft.text)
            for sentence in sentences:
                s = sentence.strip()
                if not s or len(s.split()) < _MIN_FRAGMENT_WORDS:
                    continue
                if s in seen:
                    continue
                seen.add(s)

                score = self._score_fragment(s, retrieved_qids)
                if score >= _MIN_FRAGMENT_SCORE:
                    fragment_scores.append((s, score))

        fragment_scores.sort(key=lambda x: x[1], reverse=True)
        return [text for text, _ in fragment_scores[:_MAX_FRAGMENTS_IN_REFINE]]

    def _score_fragment(self, sentence: str, retrieved_qids: set[str]) -> float:
        """
        Score a single fragment sentence:
          composite = length_score * 0.45 + citation_score * 0.55
        (same formula as draft scoring, applied at sentence level)
        """
        length_score = min(1.0, len(sentence) / 200.0)
        if retrieved_qids:
            cited = set(_QID_RE.findall(sentence))
            citation_score = 0.8 if (cited & retrieved_qids) else 0.4
        else:
            citation_score = 0.5
        return length_score * _LENGTH_WEIGHT + citation_score * _CITATION_WEIGHT

    # ── Refine passes ──────────────────────────────────────────────────────────

    def _refine_with_engine(
        self,
        best_draft: ScoredDraft,
        fragments: list[str],
        bundle: "MemoryActivationBundle",
        retrieved_qids: set[str],
        engine: Any,
        prompt_builder: "PromptBuilder",
        sketch: "InputSketch",
        scaffold: "CognitionScaffold",
        max_passes: int,
    ) -> SalvageResult | None:
        """
        Attempt up to max_passes refine generations using salvaged fragments.
        Returns the best result, or None if all passes fail.
        """
        from thoughtforge.knowledge.models import FragmentRecord, FragmentScores

        current_best_text = best_draft.text
        current_best_score = best_draft.composite
        passes_used = 0

        # Build FragmentRecord stubs for PromptBuilder
        frag_records = [
            FragmentRecord(
                fragment_id=f"frag_{uuid.uuid4().hex[:6]}",
                source_candidate_id=best_draft.candidate_id,
                text=frag_text,
                keep=True,
                scores=FragmentScores(),
            )
            for frag_text in fragments
        ]

        for pass_num in range(1, max_passes + 1):
            if not frag_records:
                break

            try:
                from thoughtforge.inference.turboquant import GenerationParams
                refine_prompt = prompt_builder.build_refine_prompt(
                    fragments=frag_records,
                    sketch=sketch,
                    scaffold=scaffold,
                )
                result = engine.generate(
                    refine_prompt,
                    params=GenerationParams(temperature=0.50 - (pass_num - 1) * 0.05),
                )
                passes_used = pass_num

                # Score the refine output
                refined_text = result.text
                scored_refined = self._score_raw_text(refined_text, retrieved_qids)

                logger.debug(
                    "FragmentSalvage refine pass %d: score=%.3f (prev=%.3f)",
                    pass_num, scored_refined, current_best_score,
                )

                if scored_refined > current_best_score:
                    current_best_text = refined_text
                    current_best_score = scored_refined
                    # Update fragments for next pass from the refined text
                    next_fragments = self._extract_fragments(
                        [ScoredDraft(
                            candidate_id=f"refine_{pass_num}",
                            text=refined_text,
                            length_score=min(1.0, len(refined_text) / _IDEAL_LENGTH_CHARS),
                            citation_score=0.5,
                            composite=scored_refined,
                        )],
                        retrieved_qids,
                    )
                    if next_fragments:
                        frag_records = [
                            FragmentRecord(
                                fragment_id=f"frag_{uuid.uuid4().hex[:6]}",
                                source_candidate_id=f"refine_{pass_num}",
                                text=t,
                                keep=True,
                                scores=FragmentScores(),
                            )
                            for t in next_fragments
                        ]

            except Exception as e:
                logger.warning("FragmentSalvage refine pass %d failed: %s", pass_num, e)
                break

        if passes_used == 0:
            return None

        cited = set(_QID_RE.findall(current_best_text))
        return SalvageResult(
            text=current_best_text,
            citations=list(cited & retrieved_qids),
            confidence=current_best_score,
            passes_used=passes_used,
            best_draft_score=best_draft.composite,
            fragments_kept=len(fragments),
            salvage_path=f"refine_pass_{passes_used}",
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _score_raw_text(self, text: str, retrieved_qids: set[str]) -> float:
        """Score raw text string using the build-plan formula."""
        length_score = min(1.0, len(text) / _IDEAL_LENGTH_CHARS)
        if retrieved_qids:
            cited = set(_QID_RE.findall(text))
            citation_score = len(cited & retrieved_qids) / len(retrieved_qids)
        else:
            citation_score = 0.5
        return length_score * _LENGTH_WEIGHT + citation_score * _CITATION_WEIGHT

    @staticmethod
    def _extract_qids(bundle: "MemoryActivationBundle") -> set[str]:
        qids: set[str] = set()
        for rec in bundle.activated_records:
            raw = getattr(rec, "raw", {}) or {}
            qid = raw.get("qid", "")
            if qid:
                qids.add(qid)
        return qids


# ── Text helpers ───────────────────────────────────────────────────────────────

def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]
