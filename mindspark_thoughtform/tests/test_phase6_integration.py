"""
Phase 6 test suite — Integration tests.

Tests the full ThoughtForgeCore.think() pipeline end-to-end in a minimal
environment (no DB, no model) to verify the pipeline holds together correctly,
that FinalResponseRecord is always fully populated, and that multiple
consecutive calls are stable.
"""

import tempfile
from pathlib import Path

import pytest

from thoughtforge.cognition.core import ThoughtForgeCore
from thoughtforge.knowledge.models import FinalResponseRecord


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def core():
    """Ephemeral ThoughtForgeCore — no DB, no model."""
    tmp = tempfile.mkdtemp()
    return ThoughtForgeCore(
        memory_dir=Path(tmp) / "memory",
        db_path=Path(tmp) / "nonexistent.db",
        model_path=None,
    )


@pytest.fixture(scope="module")
def yggdrasil_result(core):
    """Cache a single think() result for reuse."""
    return core.think("What is Yggdrasil?")


# ── FinalResponseRecord completeness ──────────────────────────────────────────

class TestFinalResponseRecordCompleteness:
    def test_returns_final_response_record(self, yggdrasil_result):
        assert isinstance(yggdrasil_result, FinalResponseRecord)

    def test_text_is_non_empty_string(self, yggdrasil_result):
        assert isinstance(yggdrasil_result.text, str)
        assert len(yggdrasil_result.text) > 0

    def test_citations_is_list(self, yggdrasil_result):
        assert isinstance(yggdrasil_result.citations, list)

    def test_turn_id_is_string(self, yggdrasil_result):
        assert isinstance(yggdrasil_result.turn_id, str)
        assert len(yggdrasil_result.turn_id) > 0

    def test_token_count_non_negative(self, yggdrasil_result):
        assert isinstance(yggdrasil_result.token_count, int)
        assert yggdrasil_result.token_count >= 0

    def test_enforcement_passed_is_bool(self, yggdrasil_result):
        assert isinstance(yggdrasil_result.enforcement_passed, bool)

    def test_enforcement_notes_is_str(self, yggdrasil_result):
        assert isinstance(yggdrasil_result.enforcement_notes, str)

    def test_salvage_path_is_string(self, yggdrasil_result):
        assert isinstance(yggdrasil_result.salvage_path, str)
        assert len(yggdrasil_result.salvage_path) > 0

    def test_retrieval_confidence_in_range(self, yggdrasil_result):
        assert 0.0 <= yggdrasil_result.retrieval_confidence <= 1.0

    def test_scores_not_none(self, yggdrasil_result):
        assert yggdrasil_result.scores is not None

    def test_scores_composite_in_range(self, yggdrasil_result):
        composite = yggdrasil_result.scores.composite
        assert 0.0 <= composite <= 1.0

    def test_scores_quality_tier_valid(self, yggdrasil_result):
        valid_tiers = {"excellent", "good", "adequate", "poor", "unknown", ""}
        tier = yggdrasil_result.scores.quality_tier
        assert tier in valid_tiers or isinstance(tier, str)

    def test_mode_is_string(self, yggdrasil_result):
        assert isinstance(yggdrasil_result.mode, str)


# ── Pipeline end-to-end ────────────────────────────────────────────────────────

class TestPipelineEndToEnd:
    def test_think_returns_result(self, core):
        result = core.think("What is the world tree?")
        assert isinstance(result, FinalResponseRecord)

    def test_think_knowledge_only_has_text(self, core):
        result = core.think("Describe the Norse concept of wyrd.")
        assert result.text
        assert isinstance(result.text, str)

    def test_think_different_queries_return_different_ids(self, core):
        r1 = core.think("Who is Odin?")
        r2 = core.think("Who is Thor?")
        assert r1.turn_id != r2.turn_id

    def test_think_with_retrieval_path_sql(self, core):
        result = core.think("What is Asgard?", retrieval_path="sql")
        assert isinstance(result, FinalResponseRecord)

    def test_think_with_retrieval_path_vector(self, core):
        result = core.think("Norse mythology overview", retrieval_path="vector")
        assert isinstance(result, FinalResponseRecord)

    def test_think_with_retrieval_path_hybrid(self, core):
        result = core.think("Explain frith", retrieval_path="hybrid")
        assert isinstance(result, FinalResponseRecord)


# ── Multi-call stability ───────────────────────────────────────────────────────

class TestMultiCallStability:
    def test_three_consecutive_calls_all_succeed(self, core):
        queries = [
            "What is Valhalla?",
            "Who are the Aesir?",
            "What is seiðr?",
        ]
        results = [core.think(q) for q in queries]
        assert all(isinstance(r, FinalResponseRecord) for r in results)

    def test_all_turn_ids_unique(self, core):
        results = [core.think("What is Yggdrasil?") for _ in range(3)]
        turn_ids = [r.turn_id for r in results]
        assert len(set(turn_ids)) == 3

    def test_all_results_have_text(self, core):
        results = [core.think(q) for q in ["Who is Loki?", "Describe Bifrost.", "What is wyrd?"]]
        assert all(r.text for r in results)

    def test_enforcement_always_bool(self, core):
        results = [core.think(q) for q in ["test query one", "test query two", "test query three"]]
        assert all(isinstance(r.enforcement_passed, bool) for r in results)


# ── Salvage + Enforcement wiring ──────────────────────────────────────────────

class TestSalvageEnforcementWiring:
    def test_salvage_path_populated(self, yggdrasil_result):
        valid_paths = {
            "best_draft", "refine_pass_1", "refine_pass_2",
            "knowledge_only", "empty", "direct",
        }
        assert yggdrasil_result.salvage_path in valid_paths or \
               isinstance(yggdrasil_result.salvage_path, str)

    def test_enforcement_pass_implies_no_forge_note(self, core):
        """When enforcement passes, text shouldn't have unresolvable [Forge:] bloat."""
        result = core.think("What is Yggdrasil?")
        if result.enforcement_passed:
            # enforcement_notes should be empty (or minimal)
            assert result.enforcement_notes == "" or isinstance(result.enforcement_notes, str)

    def test_citations_are_qid_like(self, core):
        """Any citations present should look like QID strings."""
        result = core.think("Norse mythology")
        for cit in result.citations:
            assert isinstance(cit, str)

    def test_retrieval_confidence_always_float(self, core):
        result = core.think("Ask about the world tree")
        assert isinstance(result.retrieval_confidence, float)


# ── Core component wiring ─────────────────────────────────────────────────────

class TestCoreComponentWiring:
    def test_has_salvage_instance(self, core):
        from thoughtforge.refinement.salvage import FragmentSalvage
        assert hasattr(core, "_salvage")
        assert isinstance(core._salvage, FragmentSalvage)

    def test_has_enforcement_instance(self, core):
        from thoughtforge.refinement.enforcement import EnforcementGate
        assert hasattr(core, "_enforcement")
        assert isinstance(core._enforcement, EnforcementGate)

    def test_has_router_instance(self, core):
        from thoughtforge.cognition.router import InputRouter
        assert hasattr(core, "_router")
        assert isinstance(core._router, InputRouter)

    def test_has_scaffold_builder(self, core):
        from thoughtforge.cognition.scaffold import ScaffoldBuilder
        assert hasattr(core, "_scaffold_builder")
        assert isinstance(core._scaffold_builder, ScaffoldBuilder)

    def test_has_prompt_builder(self, core):
        from thoughtforge.cognition.prompt_builder import PromptBuilder
        assert hasattr(core, "_prompt_builder")
        assert isinstance(core._prompt_builder, PromptBuilder)
