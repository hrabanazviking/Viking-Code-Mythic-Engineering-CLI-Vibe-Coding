"""
Phase 3 test suite — Cognition Scaffolds + Orchestration.

Tests:
  - InputRouter: intent, tone, mode, memory_triggers, urgency, retrieval_path
  - ScaffoldBuilder: goal, tone, focus, avoid, depth, candidate_modes, fact_block
  - PromptBuilder: candidate, refine, repair prompt structure + content
  - ThoughtForgeCore: knowledge-only think(), no-model graceful degradation,
    final response fields, quality scoring
"""

import pytest

from thoughtforge.cognition.router import InputRouter
from thoughtforge.cognition.scaffold import ScaffoldBuilder
from thoughtforge.cognition.prompt_builder import PromptBuilder
from thoughtforge.cognition.core import (
    ThoughtForgeCore,
    _genericness_penalty,
    _specificity_score,
    _keyword_overlap,
    _length_score,
    _split_sentences,
    _score_candidate,
    _score_fragment,
    _score_final,
    _extract_citations,
    _check_citation_gate,
)
from thoughtforge.knowledge.models import (
    ActivatedRecord,
    CognitionScaffold,
    FinalResponseRecord,
    FragmentRecord,
    FragmentScores,
    InputSketch,
    MemoryActivationBundle,
    PersonalityCoreRecord,
)


# ── InputRouter ────────────────────────────────────────────────────────────────

class TestInputRouter:
    def setup_method(self):
        self.router = InputRouter()

    def test_returns_input_sketch(self):
        sketch = self.router.route("Hello, how are you?")
        assert isinstance(sketch, InputSketch)
        assert sketch.raw_text == "Hello, how are you?"

    def test_intent_technical_debugging(self):
        sketch = self.router.route("My function throws an error: AttributeError on line 12")
        assert sketch.intent == "technical_debugging"

    def test_intent_technical_spec(self):
        sketch = self.router.route("write a module that implements the KnowledgeForge class")
        assert sketch.intent == "technical_spec_request"

    def test_intent_emotional_support(self):
        sketch = self.router.route("I'm exhausted and overwhelmed by this project")
        assert sketch.intent == "emotional_support"

    def test_intent_brainstorming(self):
        sketch = self.router.route("I need some ideas and alternatives for the project name")
        assert sketch.intent == "brainstorming"

    def test_intent_planning(self):
        sketch = self.router.route("How should I plan out the development phases?")
        assert sketch.intent == "planning_request"

    def test_intent_editing(self):
        sketch = self.router.route("Rewrite this paragraph to be more concise")
        assert sketch.intent == "editing_refinement"

    def test_intent_factual(self):
        sketch = self.router.route("What is the Yggdrasil in Norse mythology?")
        assert sketch.intent == "factual_query"

    def test_intent_light_conversation_fallback(self):
        sketch = self.router.route("hey there")
        assert sketch.intent == "light_conversation"

    def test_tone_frustrated(self):
        sketch = self.router.route("ugh why doesn't this work, it's been broken for hours")
        assert sketch.tone_in == "frustrated"

    def test_tone_neutral_default(self):
        sketch = self.router.route("What time is it?")
        assert sketch.tone_in == "neutral"

    def test_tone_urgent(self):
        sketch = self.router.route("I need this fixed ASAP, deadline today")
        assert sketch.tone_in == "urgent"

    def test_response_mode_technical(self):
        sketch = self.router.route("write a class that does X")
        assert sketch.response_mode == "structured_technical"

    def test_response_mode_supportive(self):
        sketch = self.router.route("I'm so tired and stressed about this")
        assert sketch.response_mode == "calm_supportive"

    def test_memory_triggers_extracted(self):
        sketch = self.router.route("Tell me about the ThoughtForge knowledge module")
        assert "thoughtforge" in sketch.memory_triggers or "knowledge" in sketch.memory_triggers

    def test_memory_triggers_max_10(self):
        sketch = self.router.route("a " * 50)
        assert len(sketch.memory_triggers) <= 10

    def test_urgency_baseline(self):
        sketch = self.router.route("What is Python?")
        assert 0.0 <= sketch.urgency <= 1.0

    def test_urgency_elevated_for_debugging(self):
        sketch_debug = self.router.route("Exception: TypeError on line 5")
        sketch_chat = self.router.route("Tell me something interesting")
        assert sketch_debug.urgency >= sketch_chat.urgency

    def test_retrieval_path_sql_for_factual(self):
        sketch = self.router.route("What is the capital of Norway?")
        assert sketch.retrieval_path == "sql"

    def test_retrieval_path_vector_for_emotional(self):
        sketch = self.router.route("I feel lost and exhausted")
        assert sketch.retrieval_path == "vector"

    def test_topic_extracted(self):
        sketch = self.router.route("Explain the Sovereign RAG architecture")
        assert sketch.topic != ""
        assert len(sketch.topic) > 0

    def test_thread_state_tags_added_to_triggers(self):
        from thoughtforge.knowledge.models import ActiveThreadStateRecord
        thread = ActiveThreadStateRecord(
            record_id="thr_test",
            tags=["sovereign_rag", "wikidata"],
        )
        sketch = self.router.route("How does it work?", thread_state=thread)
        assert "sovereign_rag" in sketch.memory_triggers or "wikidata" in sketch.memory_triggers


# ── ScaffoldBuilder ────────────────────────────────────────────────────────────

class TestScaffoldBuilder:
    def setup_method(self):
        self.builder = ScaffoldBuilder()
        self.bundle = MemoryActivationBundle()

    def _sketch(self, intent: str, mode: str = "structured_technical", tone: str = "neutral") -> InputSketch:
        return InputSketch(
            raw_text="test query",
            intent=intent,
            topic="test topic",
            tone_in=tone,
            response_mode=mode,
            urgency=0.4,
        )

    def test_returns_cognition_scaffold(self):
        sketch = self._sketch("factual_query", "factual_direct")
        result = self.builder.build(sketch, self.bundle)
        assert isinstance(result, CognitionScaffold)

    def test_goal_is_set(self):
        sketch = self._sketch("technical_spec_request")
        result = self.builder.build(sketch, self.bundle)
        assert result.goal != ""
        assert "implementation" in result.goal or "structured" in result.goal

    def test_tone_list_not_empty(self):
        sketch = self._sketch("technical_spec_request")
        result = self.builder.build(sketch, self.bundle)
        assert len(result.tone) >= 1

    def test_tone_overlay_for_frustrated(self):
        sketch = self._sketch("technical_debugging", tone="frustrated")
        result = self.builder.build(sketch, self.bundle)
        assert "patient" in result.tone or "steady" in result.tone

    def test_focus_list_not_empty(self):
        sketch = self._sketch("technical_spec_request")
        result = self.builder.build(sketch, self.bundle)
        assert len(result.focus) >= 1

    def test_avoid_list_contains_filler(self):
        sketch = self._sketch("factual_query")
        result = self.builder.build(sketch, self.bundle)
        assert "filler" in result.avoid or "padding" in result.avoid

    def test_depth_expert_for_technical(self):
        sketch = self._sketch("technical_spec_request")
        sketch.urgency = 0.3
        result = self.builder.build(sketch, self.bundle)
        assert result.depth == "expert"

    def test_depth_light_for_conversation(self):
        sketch = self._sketch("light_conversation", "light_natural_chat")
        result = self.builder.build(sketch, self.bundle)
        assert result.depth == "light"

    def test_candidate_modes_populated(self):
        sketch = self._sketch("brainstorming", "creative_brainstorm")
        result = self.builder.build(sketch, self.bundle)
        assert len(result.candidate_modes) >= 1

    def test_fact_block_empty_when_no_records(self):
        sketch = self._sketch("factual_query")
        result = self.builder.build(sketch, MemoryActivationBundle())
        assert result.fact_block == ""

    def test_fact_block_populated_from_bundle(self):
        sketch = self._sketch("factual_query")
        bundle = MemoryActivationBundle(
            activated_records=[
                ActivatedRecord(
                    record_id="Q123",
                    record_type="entity",
                    score=0.8,
                    cue="Odin: chief god of Norse mythology",
                    raw={"qid": "Q123", "label_en": "Odin", "description_en": "chief god"},
                )
            ],
            total_retrieved=1,
            retrieval_confidence=0.8,
        )
        result = self.builder.build(sketch, bundle)
        assert "Odin" in result.fact_block or "Q123" in result.fact_block

    def test_personality_avoid_added(self):
        sketch = self._sketch("light_conversation")
        personality = PersonalityCoreRecord(
            record_id="pers_001",
            avoid=["hollow affirmations", "robotic tone"],
        )
        result = self.builder.build(sketch, self.bundle, personality=personality)
        combined_avoid = " ".join(result.avoid)
        assert "hollow" in combined_avoid or "robotic" in combined_avoid

    def test_tone_max_4_items(self):
        sketch = self._sketch("emotional_support", "calm_supportive", tone="tired")
        result = self.builder.build(sketch, self.bundle)
        assert len(result.tone) <= 4


# ── PromptBuilder ──────────────────────────────────────────────────────────────

class TestPromptBuilder:
    def setup_method(self):
        self.pb = PromptBuilder()
        self.sketch = InputSketch(
            raw_text="What is the Yggdrasil?",
            intent="factual_query",
            topic="yggdrasil norse mythology",
            tone_in="curious",
            response_mode="factual_direct",
            urgency=0.3,
        )
        self.scaffold = CognitionScaffold(
            goal="give an accurate, direct answer with cited sources",
            tone=["direct", "factual", "clear"],
            focus=["accuracy", "brevity", "citation"],
            avoid=["filler", "guessing", "unverified claims"],
            depth="medium",
            candidate_modes=["implementation_friendly", "strict_spec"],
        )

    def test_candidate_prompt_is_string(self):
        result = self.pb.build_candidate_prompt(
            self.sketch, self.scaffold, "implementation_friendly", []
        )
        assert isinstance(result, str)
        assert len(result) > 20

    def test_candidate_prompt_contains_user_request(self):
        result = self.pb.build_candidate_prompt(
            self.sketch, self.scaffold, "implementation_friendly", []
        )
        assert "Yggdrasil" in result

    def test_candidate_prompt_contains_goal(self):
        result = self.pb.build_candidate_prompt(
            self.sketch, self.scaffold, "strict_spec", []
        )
        assert "accurate" in result or "cited" in result

    def test_candidate_prompt_contains_avoid(self):
        result = self.pb.build_candidate_prompt(
            self.sketch, self.scaffold, "practical", []
        )
        assert "filler" in result

    def test_candidate_prompt_injects_memory_cues(self):
        cues = ["prefers direct answers", "Norse mythology context active"]
        result = self.pb.build_candidate_prompt(
            self.sketch, self.scaffold, "practical", cues
        )
        assert "prefers direct answers" in result

    def test_candidate_prompt_max_3_cues(self):
        cues = ["cue1", "cue2", "cue3", "cue4", "cue5"]
        result = self.pb.build_candidate_prompt(
            self.sketch, self.scaffold, "practical", cues
        )
        assert "cue4" not in result
        assert "cue5" not in result

    def test_candidate_prompt_includes_fact_block(self):
        scaffold_with_facts = CognitionScaffold(
            goal="answer accurately",
            fact_block="[Q123] Odin — chief god of Norse mythology",
        )
        result = self.pb.build_candidate_prompt(
            self.sketch, scaffold_with_facts, "practical", []
        )
        assert "Q123" in result or "Odin" in result

    def test_refine_prompt_is_string(self):
        frags = [
            FragmentRecord("f1", "c1", text="Yggdrasil is the world tree in Norse mythology", scores=FragmentScores(), keep=True),
            FragmentRecord("f2", "c1", text="It connects the nine worlds", scores=FragmentScores(), keep=True),
        ]
        result = self.pb.build_refine_prompt(frags, self.sketch, self.scaffold)
        assert isinstance(result, str)
        assert "Yggdrasil" in result or "world tree" in result

    def test_refine_prompt_max_5_fragments(self):
        frags = [
            FragmentRecord(f"f{i}", "c1", text=f"fragment text {i}", scores=FragmentScores(), keep=True)
            for i in range(8)
        ]
        result = self.pb.build_refine_prompt(frags, self.sketch, self.scaffold)
        assert "fragment text 5" not in result
        assert "fragment text 6" not in result

    def test_repair_prompt_is_string(self):
        result = self.pb.build_repair_prompt(self.sketch, self.scaffold, [])
        assert isinstance(result, str)
        assert "Yggdrasil" in result

    def test_repair_prompt_contains_direct_opener(self):
        result = self.pb.build_repair_prompt(self.sketch, self.scaffold, [])
        assert "direct" in result.lower()

    def test_repair_prompt_max_2_cues(self):
        cues = ["cue1", "cue2", "cue3"]
        result = self.pb.build_repair_prompt(self.sketch, self.scaffold, cues)
        assert "cue3" not in result

    def test_extract_memory_cues_prefers_preference_records(self):
        bundle = MemoryActivationBundle(
            activated_records=[
                ActivatedRecord("entity_1", "entity", score=0.9, cue="entity cue"),
                ActivatedRecord("usr_1", "user_preference", score=0.5, cue="prefers concise answers"),
                ActivatedRecord("fct_1", "user_fact", score=0.6, cue="user is a developer"),
            ]
        )
        cues = self.pb.extract_memory_cues(bundle, max_cues=2)
        assert "prefers concise answers" in cues or "user is a developer" in cues

    def test_extract_memory_cues_respects_max(self):
        bundle = MemoryActivationBundle(
            activated_records=[
                ActivatedRecord(f"r{i}", "entity", score=0.5, cue=f"cue {i}")
                for i in range(10)
            ]
        )
        cues = self.pb.extract_memory_cues(bundle, max_cues=3)
        assert len(cues) <= 3


# ── Scoring helpers ────────────────────────────────────────────────────────────

class TestScoringHelpers:
    def test_genericness_penalty_zero_for_clean_text(self):
        text = "Yggdrasil connects the nine worlds in Norse cosmology."
        assert _genericness_penalty(text) == 0.0

    def test_genericness_penalty_nonzero_for_ai_phrases(self):
        text = "Of course! As an AI, I'd be happy to help you with that."
        assert _genericness_penalty(text) > 0.0

    def test_specificity_score_high_for_qids(self):
        text = "According to Q123 and Q456, Odin is the AllFather."
        assert _specificity_score(text) > 0.0

    def test_keyword_overlap_perfect(self):
        text = "Yggdrasil is the world tree"
        query = "what is Yggdrasil world tree"
        assert _keyword_overlap(text, query) > 0.7

    def test_keyword_overlap_zero_for_unrelated(self):
        assert _keyword_overlap("apples and oranges", "quantum physics neutron") < 0.3

    def test_length_score_short_text_is_low(self):
        assert _length_score("ok") < 0.5

    def test_length_score_ideal_text_is_high(self):
        text = " ".join(["word"] * 50)
        assert _length_score(text) > 0.7

    def test_split_sentences_basic(self):
        text = "First sentence. Second sentence. Third one."
        parts = _split_sentences(text)
        assert len(parts) == 3

    def test_split_sentences_single(self):
        parts = _split_sentences("Just one sentence")
        assert len(parts) == 1


# ── ThoughtForgeCore (no-model / no-DB mode) ───────────────────────────────────

class TestThoughtForgeCoreNoModel:
    def setup_method(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        from pathlib import Path
        self.core = ThoughtForgeCore(
            memory_dir=Path(self.tmp) / "memory",
            db_path=Path(self.tmp) / "nonexistent.db",  # DB doesn't exist
            model_path=None,
        )

    def test_think_returns_final_response_record(self):
        result = self.core.think("What is Yggdrasil?")
        assert isinstance(result, FinalResponseRecord)

    def test_think_text_not_empty(self):
        result = self.core.think("Hello")
        assert result.text.strip() != ""

    def test_think_response_id_set(self):
        result = self.core.think("test query")
        assert result.response_id.startswith("resp_")

    def test_think_token_count_set(self):
        result = self.core.think("What is Python?")
        assert result.token_count >= 0

    def test_think_knowledge_only_message_when_db_missing(self):
        result = self.core.think("Tell me about ConceptNet")
        assert "forge" in result.text.lower() or "knowledge" in result.text.lower()

    def test_think_does_not_raise_on_empty_input(self):
        result = self.core.think("")
        assert isinstance(result, FinalResponseRecord)

    def test_think_does_not_raise_on_long_input(self):
        long_text = "word " * 500
        result = self.core.think(long_text)
        assert isinstance(result, FinalResponseRecord)

    def test_think_scores_have_valid_range(self):
        result = self.core.think("What is machine learning?")
        scores = result.scores
        assert 0.0 <= scores.relevance <= 1.0
        assert 0.0 <= scores.clarity <= 1.0
        assert 0.0 <= scores.coherence <= 1.0

    def test_think_quality_tier_is_valid_string(self):
        result = self.core.think("Hello")
        assert result.scores.quality_tier in ("excellent", "strong", "usable", "weak", "reject")

    def test_think_technical_query(self):
        result = self.core.think("Write a Python function that reads a YAML file")
        assert isinstance(result, FinalResponseRecord)

    def test_think_emotional_query(self):
        result = self.core.think("I'm exhausted and feel like giving up")
        assert isinstance(result, FinalResponseRecord)


# ── Citation helpers ───────────────────────────────────────────────────────────

class TestCitationHelpers:
    def _bundle_with_qids(self) -> MemoryActivationBundle:
        return MemoryActivationBundle(
            activated_records=[
                ActivatedRecord("Q123", "entity", 0.9, "Odin", raw={"qid": "Q123"}),
                ActivatedRecord("Q456", "entity", 0.8, "Yggdrasil", raw={"qid": "Q456"}),
            ]
        )

    def test_extract_citations_finds_qids(self):
        text = "According to Q123, Odin is the AllFather. Q456 is the world tree."
        bundle = self._bundle_with_qids()
        citations = _extract_citations(text, bundle)
        assert "Q123" in citations
        assert "Q456" in citations

    def test_extract_citations_only_valid_qids(self):
        text = "Q999 is not in our knowledge base."
        bundle = self._bundle_with_qids()
        citations = _extract_citations(text, bundle)
        assert "Q999" not in citations

    def test_citation_gate_passes_empty_bundle(self):
        assert _check_citation_gate("any text", MemoryActivationBundle()) is True

    def test_citation_gate_passes_when_qid_present(self):
        text = "Odin (Q123) is the chief god."
        bundle = self._bundle_with_qids()
        assert _check_citation_gate(text, bundle) is True

    def test_citation_gate_fails_when_no_qids_cited(self):
        text = "Odin is the chief god of Norse mythology."
        bundle = self._bundle_with_qids()
        assert _check_citation_gate(text, bundle) is False

    def test_citation_gate_passes_when_no_wikidata_records(self):
        bundle = MemoryActivationBundle(
            activated_records=[
                ActivatedRecord("ref_1", "reference_chunk", 0.7, "some cue", raw={})
            ]
        )
        assert _check_citation_gate("any text", bundle) is True
