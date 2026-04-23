"""
EnforcementGate — final citation integrity and quality gate.

Validates a response before it leaves the pipeline:
  1. Citation check: if Wikidata records were retrieved, at least one QID must appear
  2. Length check: response must be above minimum useful length
  3. Genericness check: response must not be dominated by filler phrases

On hard failure: appends a forge note to the response text (soft degradation —
never silently returns garbage; always annotates what went wrong).

On pass: returns the response unchanged with enforcement_passed=True.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_QID_RE = re.compile(r'\bQ\d{3,}\b')

_FORGE_NOTE_NO_CITATIONS = "\n\n[Forge: limited verified citations available for this response.]"
_FORGE_NOTE_TOO_SHORT = "\n\n[Forge: response is shorter than expected — knowledge may be sparse.]"

_MIN_WORD_COUNT = 5

_HARD_GENERIC_PHRASES = [
    "as an ai", "i'm an ai", "i am an ai",
    "i cannot provide", "i am unable to",
    "i don't have access to",
]


@dataclass
class EnforcementResult:
    """Result of the enforcement gate check."""
    passed: bool
    notes: str = ""
    text: str = ""          # may be modified (forge note appended on soft fail)
    citation_check: bool = True
    length_check: bool = True
    genericness_check: bool = True

    @property
    def status(self) -> str:
        return "pass" if self.passed else "review"


class EnforcementGate:
    """
    Final validation gate for ThoughtForge responses.

    Stateless — all context passed per call.
    Degrades softly: appends notes rather than silently failing.
    """

    def check(
        self,
        text: str,
        citations: list[str],
        retrieved_qids: set[str],
    ) -> EnforcementResult:
        """
        Validate the final response text.

        Args:
            text:           The response text to validate.
            citations:      QIDs already extracted from the text.
            retrieved_qids: Set of QIDs present in the retrieved knowledge bundle.
                            If empty, citation enforcement is skipped.

        Returns:
            EnforcementResult with passed flag, notes, and (possibly annotated) text.
        """
        notes: list[str] = []
        output_text = text
        citation_ok = True
        length_ok = True
        generic_ok = True

        # ── Length check ───────────────────────────────────────────────────────
        word_count = len(text.split())
        if word_count < _MIN_WORD_COUNT:
            length_ok = False
            notes.append(f"response too short ({word_count} words)")
            output_text += _FORGE_NOTE_TOO_SHORT

        # ── Citation check ─────────────────────────────────────────────────────
        # Only enforced when knowledge records with QIDs were actually retrieved
        if retrieved_qids:
            cited_in_text = set(_QID_RE.findall(text))
            if not (cited_in_text & retrieved_qids):
                citation_ok = False
                notes.append("no retrieved QIDs cited in response")
                output_text += _FORGE_NOTE_NO_CITATIONS

        # ── Genericness check ──────────────────────────────────────────────────
        lower = text.lower()
        for phrase in _HARD_GENERIC_PHRASES:
            if phrase in lower:
                generic_ok = False
                notes.append(f"hard generic phrase detected: '{phrase}'")
                break

        passed = citation_ok and length_ok and generic_ok
        return EnforcementResult(
            passed=passed,
            notes="; ".join(notes) if notes else "",
            text=output_text,
            citation_check=citation_ok,
            length_check=length_ok,
            genericness_check=generic_ok,
        )

    @staticmethod
    def extract_qids_from_bundle(bundle_records: list) -> set[str]:
        """
        Extract all valid QIDs from a MemoryActivationBundle's activated_records.
        Accepts list of ActivatedRecord objects.
        """
        qids: set[str] = set()
        for rec in bundle_records:
            raw = getattr(rec, "raw", {}) or {}
            qid = raw.get("qid", "")
            if qid:
                qids.add(qid)
        return qids
