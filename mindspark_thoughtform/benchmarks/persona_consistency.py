"""
persona_consistency.py — Viking/Skald persona consistency scoring for ThoughtForge.

Validates that the Skald persona (calm, direct, Norse-flavored, no generic AI phrases)
is maintained across many turns of conversation. Designed to run against a list of
response texts from ThoughtForgeCore.think() calls.

Scoring formula:
  consistency_score = (
      (1.0 - generic_penalty)     # penalise AI-sounding phrases
    + norse_bonus                  # reward Norse/Skald tone markers
    + citation_bonus               # reward citations present
  ) / 3.0  — clamped to [0.0, 1.0]

A score ≥ 0.75 indicates consistent persona across the batch.

Usage:
    scorer = PersonaConsistencyScorer()
    result = scorer.score(responses)
    print(result.summary())
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Phrase lists ──────────────────────────────────────────────────────────────

GENERIC_PHRASES: list[str] = [
    "as an ai",
    "i'm an ai",
    "i am an ai",
    "i cannot provide",
    "i'm unable to",
    "i am unable to",
    "i don't have feelings",
    "i don't have opinions",
    "i cannot feel",
    "as a language model",
    "as an assistant",
    "i apologize, but i",
    "i'm just an ai",
    "i am just an ai",
    "i don't have personal",
    "please note that i",
    "it's important to note that i",
    "i must remind you",
    "i should mention that i",
    "my training data",
    "my knowledge cutoff",
]

NORSE_TONE_MARKERS: list[str] = [
    "wyrd",
    "frith",
    "völva",
    "skald",
    "yggdrasil",
    "asgard",
    "midgard",
    "valhalla",
    "odin",
    "thor",
    "freya",
    "freyja",
    "loki",
    "rune",
    "runic",
    "norse",
    "viking",
    "saga",
    "edda",
    "mead",
    "heathen",
    "pagan",
    "vanir",
    "aesir",
    "ragnarök",
    "ragnarok",
    "futhark",
    "seiðr",
    "seidr",
    "nine worlds",
    "nine realms",
    "world tree",
    "shield-maiden",
    "shieldmaiden",
    "norn",
    "norns",
    "urd",
    "verdandi",
    "skuld",
    "bifrost",
    "mjolnir",
    "mjölnir",
]

# Skald persona positive markers (direct, grounded, specific)
SKALD_QUALITY_MARKERS: list[str] = [
    "specifically",
    "directly",
    "in short",
    "to be clear",
    "the answer is",
    "the key",
    "in practice",
    "concretely",
    "in essence",
]

_QID_RE = re.compile(r'\bQ\d{3,}\b')


# ── Result type ───────────────────────────────────────────────────────────────

@dataclass
class TurnConsistency:
    """Per-turn consistency assessment."""
    turn_index: int
    text: str
    generic_hits: list[str]         # generic phrases found
    norse_hits: list[str]           # Norse tone markers found
    has_citation: bool
    skald_quality_hits: list[str]   # Skald quality markers found
    turn_score: float               # 0.0–1.0 for this turn


@dataclass
class ConsistencyResult:
    """Aggregate persona consistency result across all turns."""
    consistency_score: float        # 0.0–1.0 overall score
    total_turns: int
    flagged_turns: int              # turns with any generic phrase
    generic_phrase_hits: int        # total generic phrase occurrences across all turns
    norse_tone_hits: int            # total Norse marker occurrences
    citation_turns: int             # turns with ≥1 QID citation
    skald_quality_hits: int         # total Skald quality marker occurrences
    per_turn: list[TurnConsistency] = field(default_factory=list)

    PASS_THRESHOLD: float = 0.75

    @property
    def passes(self) -> bool:
        return self.consistency_score >= self.PASS_THRESHOLD

    def summary(self) -> str:
        lines = [
            "═══ Persona Consistency Report ═══",
            f"  Score          : {self.consistency_score:.3f}"
            + (" ✓ PASS" if self.passes else " ✗ REVIEW"),
            f"  Total turns    : {self.total_turns}",
            f"  Flagged turns  : {self.flagged_turns}  ({self.flagged_turns/max(1,self.total_turns):.0%})",
            f"  Generic hits   : {self.generic_phrase_hits}",
            f"  Norse tone hits: {self.norse_tone_hits}",
            f"  Citation turns : {self.citation_turns}",
            f"  Skald markers  : {self.skald_quality_hits}",
        ]
        if self.flagged_turns > 0:
            flagged = [t for t in self.per_turn if t.generic_hits]
            for t in flagged[:3]:
                lines.append(f"    Turn {t.turn_index}: {t.generic_hits}")
        return "\n".join(lines)


# ── PersonaConsistencyScorer ──────────────────────────────────────────────────

class PersonaConsistencyScorer:
    """
    Scores the consistency of the Viking/Skald persona across response batches.

    Operates purely on text — no model inference required. Uses phrase-level
    pattern matching against known generic AI phrases and Norse tone markers.
    """

    def score(
        self,
        responses: list[str],
        weights: dict[str, float] | None = None,
    ) -> ConsistencyResult:
        """
        Score persona consistency across a list of response texts.

        Args:
            responses: List of response strings from think() calls.
            weights:   Optional weight override: {"generic": 1.0, "norse": 1.0, "citation": 1.0}
                       Controls relative importance of each scoring component.

        Returns:
            ConsistencyResult with per-turn breakdown and aggregate score.
        """
        if not responses:
            return ConsistencyResult(
                consistency_score=1.0,   # vacuously consistent
                total_turns=0,
                flagged_turns=0,
                generic_phrase_hits=0,
                norse_tone_hits=0,
                citation_turns=0,
                skald_quality_hits=0,
                per_turn=[],
            )

        w = {"generic": 1.0, "norse": 1.0, "citation": 0.5, "skald": 0.5}
        if weights:
            w.update(weights)

        per_turn: list[TurnConsistency] = []
        total_generic = 0
        total_norse = 0
        total_citations = 0
        total_skald = 0
        flagged = 0

        for idx, text in enumerate(responses):
            tc = self._score_turn(idx, text)
            per_turn.append(tc)
            total_generic += len(tc.generic_hits)
            total_norse += len(tc.norse_hits)
            total_citations += int(tc.has_citation)
            total_skald += len(tc.skald_quality_hits)
            if tc.generic_hits:
                flagged += 1

        # Aggregate turn scores with weighting
        turn_scores = [t.turn_score for t in per_turn]
        consistency_score = sum(turn_scores) / len(turn_scores)
        consistency_score = max(0.0, min(1.0, consistency_score))

        return ConsistencyResult(
            consistency_score=consistency_score,
            total_turns=len(responses),
            flagged_turns=flagged,
            generic_phrase_hits=total_generic,
            norse_tone_hits=total_norse,
            citation_turns=total_citations,
            skald_quality_hits=total_skald,
            per_turn=per_turn,
        )

    def _score_turn(self, idx: int, text: str) -> TurnConsistency:
        """Score a single response turn."""
        lower = text.lower()

        # Generic phrase detection (hard penalty)
        generic_hits = [p for p in GENERIC_PHRASES if p in lower]

        # Norse tone marker detection (bonus)
        norse_hits = [m for m in NORSE_TONE_MARKERS if m in lower]

        # Skald quality markers (bonus)
        skald_hits = [m for m in SKALD_QUALITY_MARKERS if m in lower]

        # Citation detection
        has_citation = bool(_QID_RE.search(text))

        # Turn score formula:
        #   generic_penalty = min(1.0, len(generic_hits) * 0.25)  → 1 hit = 25% penalty
        #   norse_bonus     = min(0.3, len(norse_hits) * 0.05)    → each marker = +5%, cap 30%
        #   citation_bonus  = 0.1 if has_citation else 0.0
        #   skald_bonus     = min(0.1, len(skald_hits) * 0.03)
        #   turn_score = clamp(1.0 - generic_penalty + norse_bonus + citation_bonus + skald_bonus)

        generic_penalty = min(1.0, len(generic_hits) * 0.25)
        norse_bonus = min(0.3, len(norse_hits) * 0.05)
        citation_bonus = 0.1 if has_citation else 0.0
        skald_bonus = min(0.1, len(skald_hits) * 0.03)

        turn_score = 1.0 - generic_penalty + norse_bonus + citation_bonus + skald_bonus
        turn_score = max(0.0, min(1.0, turn_score))

        return TurnConsistency(
            turn_index=idx,
            text=text[:200],        # truncate for storage
            generic_hits=generic_hits,
            norse_hits=norse_hits[:5],      # top 5 for readability
            has_citation=has_citation,
            skald_quality_hits=skald_hits,
            turn_score=turn_score,
        )

    @staticmethod
    def generate_report(result: ConsistencyResult, output_path: str | None = None) -> str:
        """
        Generate a full markdown report from a ConsistencyResult.

        Args:
            result:      ConsistencyResult from score().
            output_path: If provided, write report to this file path.

        Returns:
            Markdown report string.
        """
        lines = [
            "# ThoughtForge Persona Consistency Report",
            "",
            f"**Score:** {result.consistency_score:.3f} / 1.000  "
            + ("**PASS** ✓" if result.passes else "**REVIEW** ✗"),
            f"**Threshold:** {result.PASS_THRESHOLD}",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|---|---|",
            f"| Total turns | {result.total_turns} |",
            f"| Flagged turns | {result.flagged_turns} ({result.flagged_turns/max(1,result.total_turns):.0%}) |",
            f"| Generic phrase hits | {result.generic_phrase_hits} |",
            f"| Norse tone hits | {result.norse_tone_hits} |",
            f"| Citation turns | {result.citation_turns} |",
            f"| Skald quality markers | {result.skald_quality_hits} |",
            "",
        ]

        if result.flagged_turns > 0:
            lines += [
                "## Flagged Turns",
                "",
            ]
            for tc in result.per_turn:
                if tc.generic_hits:
                    lines.append(f"**Turn {tc.turn_index}** (score: {tc.turn_score:.3f})")
                    lines.append(f"  - Generic phrases: {tc.generic_hits}")
                    lines.append(f"  - Text: _{tc.text[:120]}..._")
                    lines.append("")

        report = "\n".join(lines)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)

        return report


# ── CLI entry point ────────────────────────────────────────────────────────────

def main() -> None:
    """Run persona consistency scoring from stdin (one response per line)."""
    import sys
    responses = [line.strip() for line in sys.stdin if line.strip()]
    if not responses:
        print("No responses provided. Pipe responses via stdin.")
        sys.exit(1)

    scorer = PersonaConsistencyScorer()
    result = scorer.score(responses)
    print(result.summary())


if __name__ == "__main__":
    main()
