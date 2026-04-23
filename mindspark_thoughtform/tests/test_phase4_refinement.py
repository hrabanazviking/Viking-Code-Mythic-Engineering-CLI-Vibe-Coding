"""
Phase 4 test suite — Fragment Salvage + Refinement.

Tests:
  - FragmentSalvage: draft scoring, fragment extraction, forge() with/without engine
  - EnforcementGate: citation check, length check, genericness check, soft-fail notes
  - ThoughtForgeCore: wired salvage + enforcement in full pipeline
  - run_thoughtforge: CLI argument parsing
"""

import pytest

from thoughtforge.refinement.salvage import FragmentSalvage, SalvageResult, _split_sentences
from thoughtforge.refinement.enforcement import EnforcementGate, EnforcementResult
from thoughtforge.knowledge.models import (
    ActivatedRecord,
    CandidateRecord,
    CandidateScores,
    CognitionScaffold,
    FinalResponseRecord,
    InputSketch,
    MemoryActivationBundle,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_candidate(text: str, cid: str = "cand_001") -> CandidateRecord:
    return CandidateRecord(
        candidate_id=cid,
        mode="practical",
        text=text,
        token_estimate=len(text.split()),
        scores=CandidateScores(),
    )


def _make_bundle_with_qids(*qids: str) -> MemoryActivationBundle:
    return MemoryActivationBundle(
        activated_records=[
            ActivatedRecord(qid, "entity", 0.8, f"cue for {qid}", raw={"qid": qid})
            for qid in qids
        ],
        total_retrieved=len(qids),
        retrieval_confidence=0.8,
    )


def _empty_bundle() -> MemoryActivationBundle:
    return MemoryActivationBundle()


def _sketch(text: str = "test query") -> InputSketch:
    return InputSketch(
        raw_text=text,
        intent="factual_query",
        topic="test topic",
        response_mode="factual_direct",
    )


def _scaffold() -> CognitionScaffold:
    return CognitionScaffold(
        goal="give a clear direct answer",
        tone=["direct", "factual"],
        avoid=["filler"],
    )


# ── FragmentSalvage — draft scoring ───────────────────────────────────────────

class TestFragmentSalvageDraftScoring:
    def setup_method(self):
        self.salvage = FragmentSalvage()

    def test_score_draft_length_only_when_no_qids(self):
        cand = _make_candidate("This is a short response.")
        bundle = _empty_bundle()
        scored = self.salvage._score_draft(cand, set())
        assert 0.0 <= scored.composite <= 1.0
        assert scored.citation_score == 0.5   # neutral when no QIDs

    def test_score_draft_citation_boost(self):
        cand = _make_candidate("According to Q123, the answer is clear.")
        scored_with = self.salvage._score_draft(cand, {"Q123"})
        scored_without = self.salvage._score_draft(cand, {"Q999"})
        assert scored_with.composite > scored_without.composite

    def test_score_draft_longer_text_scores_higher_on_length(self):
        short = _make_candidate("Brief.", "c1")
        long = _make_candidate("This is a much longer response with detailed information about the topic at hand, covering many aspects of the query in depth. " * 5, "c2")
        scored_short = self.salvage._score_draft(short, set())
        scored_long = self.salvage._score_draft(long, set())
        assert scored_long.length_score > scored_short.length_score

    def test_score_draft_returns_scored_draft(self):
        from thoughtforge.refinement.salvage import ScoredDraft
        cand = _make_candidate("Some text here.")
        result = self.salvage._score_draft(cand, set())
        assert isinstance(result, ScoredDraft)
        assert result.candidate_id == cand.candidate_id

    def test_citations_found_populated(self):
        cand = _make_candidate("Q123 and Q456 are both cited here.")
        scored = self.salvage._score_draft(cand, {"Q123", "Q456", "Q789"})
        assert "Q123" in scored.citations_found
        assert "Q456" in scored.citations_found
        assert "Q789" not in scored.citations_found


# ── FragmentSalvage — fragment extraction ─────────────────────────────────────

class TestFragmentSalvageExtraction:
    def setup_method(self):
        self.salvage = FragmentSalvage()

    def test_extract_filters_short_sentences(self):
        from thoughtforge.refinement.salvage import ScoredDraft
        draft = ScoredDraft("c1", "Ok. This is a longer sentence with real content about the topic.", 0.5, 0.5, 0.5)
        frags = self.salvage._extract_fragments([draft], set())
        # "Ok." is too short (1 word), should be excluded
        for f in frags:
            assert len(f.split()) >= 4

    def test_extract_deduplicates(self):
        from thoughtforge.refinement.salvage import ScoredDraft
        text = "The world tree connects nine realms. The world tree connects nine realms."
        draft = ScoredDraft("c1", text, 0.6, 0.5, 0.55)
        frags = self.salvage._extract_fragments([draft], set())
        assert len(frags) == len(set(frags))

    def test_extract_max_5_fragments(self):
        from thoughtforge.refinement.salvage import ScoredDraft
        text = ". ".join([f"Sentence number {i} about the important topic at hand" for i in range(10)])
        draft = ScoredDraft("c1", text, 0.9, 0.5, 0.7)
        frags = self.salvage._extract_fragments([draft], set())
        assert len(frags) <= 5


# ── FragmentSalvage — forge() ─────────────────────────────────────────────────

class TestFragmentSalvageForge:
    def setup_method(self):
        self.salvage = FragmentSalvage()

    def test_forge_returns_salvage_result(self):
        candidates = [_make_candidate("Yggdrasil is the world tree in Norse mythology, connecting the nine worlds.")]
        result = self.salvage.forge(candidates, _empty_bundle())
        assert isinstance(result, SalvageResult)

    def test_forge_empty_candidates(self):
        result = self.salvage.forge([], _empty_bundle())
        assert result.text != ""
        assert result.confidence == 0.0
        assert result.salvage_path == "empty"

    def test_forge_uses_best_draft_without_engine(self):
        short = _make_candidate("Short.", "c1")
        long = _make_candidate(
            "Yggdrasil is the immense sacred tree in Norse mythology, connecting the nine worlds: Asgard, Midgard, and many others in the cosmology.",
            "c2",
        )
        result = self.salvage.forge([short, long], _empty_bundle())
        assert result.salvage_path == "best_draft"
        # Best draft should be the longer one (higher length_score)
        assert len(result.text) > len(short.text)

    def test_forge_populates_citations_from_text(self):
        cand = _make_candidate("According to Q123, Yggdrasil (Q456) connects the worlds.")
        bundle = _make_bundle_with_qids("Q123", "Q456")
        result = self.salvage.forge([cand], bundle)
        assert "Q123" in result.citations or "Q456" in result.citations

    def test_forge_confidence_between_0_and_1(self):
        candidates = [_make_candidate("Some response text here for testing.")]
        result = self.salvage.forge(candidates, _empty_bundle())
        assert 0.0 <= result.confidence <= 1.0

    def test_forge_passes_used_zero_without_engine(self):
        candidates = [_make_candidate("Response text.")]
        result = self.salvage.forge(candidates, _empty_bundle())
        assert result.passes_used == 0

    def test_forge_multiple_candidates_picks_best(self):
        cands = [
            _make_candidate("Q123 mentioned here with lots of detailed content about Norse mythology and the world tree Yggdrasil connecting nine realms.", "c1"),
            _make_candidate("ok", "c2"),
        ]
        bundle = _make_bundle_with_qids("Q123")
        result = self.salvage.forge(cands, bundle)
        assert "Q123" in result.text or len(result.text) > 10


# ── EnforcementGate ────────────────────────────────────────────────────────────

class TestEnforcementGate:
    def setup_method(self):
        self.gate = EnforcementGate()

    def test_passes_when_no_retrieved_qids(self):
        result = self.gate.check("Some normal response text here.", [], set())
        assert result.passed is True
        assert result.citation_check is True

    def test_passes_when_qid_cited(self):
        result = self.gate.check("According to Q123, this is true.", ["Q123"], {"Q123"})
        assert result.passed is True
        assert result.citation_check is True

    def test_fails_citation_when_qid_not_cited(self):
        result = self.gate.check("No citations in this response.", [], {"Q123"})
        assert result.citation_check is False
        assert result.passed is False

    def test_appends_forge_note_on_citation_fail(self):
        result = self.gate.check("No citations here.", [], {"Q123"})
        assert "[Forge:" in result.text

    def test_fails_length_when_too_short(self):
        result = self.gate.check("ok", [], set())
        assert result.length_check is False
        assert result.passed is False

    def test_appends_forge_note_on_length_fail(self):
        result = self.gate.check("ok", [], set())
        assert "[Forge:" in result.text

    def test_passes_length_for_normal_text(self):
        result = self.gate.check("This is a normal length response with enough words.", [], set())
        assert result.length_check is True

    def test_fails_genericness_for_ai_phrase(self):
        result = self.gate.check("As an AI, I am unable to help with that.", [], set())
        assert result.genericness_check is False
        assert result.passed is False

    def test_passes_genericness_for_clean_text(self):
        result = self.gate.check("Yggdrasil is the world tree connecting nine realms.", [], set())
        assert result.genericness_check is True

    def test_enforcement_result_has_status(self):
        result = self.gate.check("Normal response text here.", [], set())
        assert result.status in ("pass", "review")

    def test_pass_status_when_all_checks_pass(self):
        result = self.gate.check("Q123 describes the world tree in Norse mythology.", ["Q123"], {"Q123"})
        assert result.status == "pass"

    def test_review_status_when_any_check_fails(self):
        result = self.gate.check("No citations provided.", [], {"Q123"})
        assert result.status == "review"

    def test_notes_empty_on_full_pass(self):
        result = self.gate.check("Q123 is the world tree in Norse cosmology texts.", ["Q123"], {"Q123"})
        assert result.notes == "" or result.passed is True

    def test_notes_populated_on_fail(self):
        result = self.gate.check("No citations.", [], {"Q123"})
        assert result.notes != ""

    def test_extract_qids_from_bundle(self):
        records = [
            ActivatedRecord("Q123", "entity", 0.9, "cue", raw={"qid": "Q123"}),
            ActivatedRecord("Q456", "entity", 0.8, "cue", raw={"qid": "Q456"}),
            ActivatedRecord("ref_1", "reference_chunk", 0.7, "cue", raw={}),
        ]
        qids = EnforcementGate.extract_qids_from_bundle(records)
        assert "Q123" in qids
        assert "Q456" in qids
        assert len(qids) == 2

    def test_extract_qids_empty_bundle(self):
        assert EnforcementGate.extract_qids_from_bundle([]) == set()


# ── ThoughtForgeCore wiring ────────────────────────────────────────────────────

class TestThoughtForgeCorePhase4Wiring:
    def setup_method(self):
        import tempfile
        from pathlib import Path
        self.tmp = tempfile.mkdtemp()
        from thoughtforge.cognition.core import ThoughtForgeCore
        self.core = ThoughtForgeCore(
            memory_dir=Path(self.tmp) / "memory",
            db_path=Path(self.tmp) / "nonexistent.db",
            model_path=None,
        )

    def test_has_salvage_instance(self):
        assert self.core._salvage is not None
        assert isinstance(self.core._salvage, FragmentSalvage)

    def test_has_enforcement_instance(self):
        assert self.core._enforcement is not None
        assert isinstance(self.core._enforcement, EnforcementGate)

    def test_think_uses_enforcement(self):
        result = self.core.think("What is Yggdrasil?")
        # enforcement_passed is always set (True or False), never None
        assert isinstance(result.enforcement_passed, bool)

    def test_think_enforcement_notes_is_string(self):
        result = self.core.think("Tell me something")
        assert isinstance(result.enforcement_notes, str)

    def test_think_still_returns_final_response(self):
        from thoughtforge.knowledge.models import FinalResponseRecord
        result = self.core.think("What is the world tree?")
        assert isinstance(result, FinalResponseRecord)


# ── _split_sentences helper ────────────────────────────────────────────────────

class TestSplitSentences:
    def test_basic_split(self):
        parts = _split_sentences("First sentence. Second sentence.")
        assert len(parts) == 2

    def test_exclamation(self):
        parts = _split_sentences("Yes! Really? Absolutely.")
        assert len(parts) == 3

    def test_single_no_punct(self):
        parts = _split_sentences("Just one sentence")
        assert len(parts) == 1

    def test_empty_string(self):
        parts = _split_sentences("")
        assert parts == []


# ── CLI argument parsing ───────────────────────────────────────────────────────

class TestCLIArgumentParsing:
    def test_parser_builds(self):
        from run_thoughtforge import _build_parser
        p = _build_parser()
        assert p is not None

    def test_parser_accepts_query_arg(self):
        from run_thoughtforge import _build_parser
        p = _build_parser()
        args = p.parse_args(["What is Yggdrasil?"])
        assert args.query == "What is Yggdrasil?"

    def test_parser_accepts_model_flag(self):
        from run_thoughtforge import _build_parser
        p = _build_parser()
        args = p.parse_args(["--model", "/models/phi.gguf"])
        assert args.model == "/models/phi.gguf"

    def test_parser_accepts_profile_flag(self):
        from run_thoughtforge import _build_parser
        p = _build_parser()
        args = p.parse_args(["--profile", "desktop_cpu"])
        assert args.profile == "desktop_cpu"

    def test_parser_accepts_retrieval_flag(self):
        from run_thoughtforge import _build_parser
        p = _build_parser()
        args = p.parse_args(["--retrieval", "sql"])
        assert args.retrieval == "sql"

    def test_parser_debug_flag(self):
        from run_thoughtforge import _build_parser
        p = _build_parser()
        args = p.parse_args(["--debug"])
        assert args.debug is True

    def test_parser_defaults(self):
        from run_thoughtforge import _build_parser
        p = _build_parser()
        args = p.parse_args([])
        assert args.query is None
        assert args.model is None
        assert args.profile == "auto"
        assert args.debug is False
