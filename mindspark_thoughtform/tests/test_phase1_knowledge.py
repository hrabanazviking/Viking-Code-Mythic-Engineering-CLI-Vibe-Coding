"""
Phase 1 tests — Knowledge Layer + Sovereign RAG.

Tests all data structures, scoring, lifecycle, schema, and retrieval
without requiring the full Wikidata dump. Uses small in-memory or
temp-file SQLite databases.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from thoughtforge.knowledge.models import (
    ActiveThreadStateRecord,
    CandidateRecord,
    CandidateScores,
    CognitionScaffold,
    EpisodicMemoryRecord,
    FinalResponseRecord,
    FinalResponseScores,
    FragmentRecord,
    FragmentScores,
    InputSketch,
    MemoryActivationBundle,
    PersonalityCoreRecord,
    ResponsePatternRecord,
    RuntimeTurnState,
    UserFactRecord,
    UserPreferenceRecord,
    WritebackRecord,
)
from thoughtforge.knowledge.scoring import (
    MIN_MEMORY_SCORE,
    PruneComponents,
    RetrievalDimensions,
    SurvivalComponents,
    WritebackComponents,
    compute_episode_writeback_score,
    compute_genericness_penalty,
    compute_pattern_learning_score,
    compute_preference_writeback_score,
    compute_prune_score,
    compute_recency_score,
    compute_survival_score,
    score_retrieval,
)
from thoughtforge.knowledge.store import MemoryStore
from thoughtforge.knowledge.lifecycle import MemoryLifecycle
from thoughtforge.etl.schema import initialize_schema, get_entity_count


# ── Data Structure Tests ───────────────────────────────────────────────────────

class TestDataStructures:
    def test_personality_core_round_trip(self) -> None:
        r = PersonalityCoreRecord(
            record_id="pers_001",
            traits=["calm", "direct"],
            speech_style=["grounded"],
            behavior_rules=["never lie"],
            avoid=["fluff"],
            weights={"directness": 0.9},
        )
        d = r.to_dict()
        r2 = PersonalityCoreRecord.from_dict(d)
        assert r2.record_id == "pers_001"
        assert r2.traits == ["calm", "direct"]
        assert r2.retention_class == "protected"

    def test_user_preference_round_trip(self) -> None:
        r = UserPreferenceRecord(
            record_id="usr_001",
            category="tone",
            tags=["direct", "brief"],
            summary="prefers direct low-fluff responses",
            value="direct",
            importance=0.8,
        )
        d = r.to_dict()
        r2 = UserPreferenceRecord.from_dict(d)
        assert r2.category == "tone"
        assert r2.importance == 0.8
        assert r2.record_type == "user_preference"

    def test_user_fact_round_trip(self) -> None:
        r = UserFactRecord(
            record_id="fct_001",
            tags=["project", "ai"],
            summary="working on small-model AI system",
            fact_value={"project": "ThoughtForge", "role": "developer"},
        )
        d = r.to_dict()
        r2 = UserFactRecord.from_dict(d)
        assert r2.fact_value["project"] == "ThoughtForge"

    def test_episode_round_trip(self) -> None:
        ep = EpisodicMemoryRecord(
            record_id="ep_001",
            tags=["debugging", "ai"],
            summary="resolved embedding dimension mismatch issue",
            importance=0.7,
            quality=0.8,
        )
        d = ep.to_dict()
        ep2 = EpisodicMemoryRecord.from_dict(d)
        assert ep2.importance == 0.7
        assert ep2.retention_class == "ephemeral"

    def test_response_pattern_round_trip(self) -> None:
        r = ResponsePatternRecord(
            record_id="pat_001",
            tags=["technical", "explanation"],
            pattern_shape=["acknowledge", "explain", "example"],
            quality=0.85,
            times_successful=5,
        )
        d = r.to_dict()
        r2 = ResponsePatternRecord.from_dict(d)
        assert r2.pattern_shape == ["acknowledge", "explain", "example"]

    def test_thread_state_cooldown(self) -> None:
        t = ActiveThreadStateRecord(
            record_id="thr_001",
            topic="AI debugging",
            priority=0.9,
            expires_after_turns=10,
        )
        t.cool_down()
        assert t.priority < 0.9
        assert t.expires_after_turns < 10

    def test_thread_state_expires(self) -> None:
        t = ActiveThreadStateRecord(
            record_id="thr_002",
            priority=0.21,
            expires_after_turns=1,
        )
        # One cooling step should trigger stale
        t.turns_since_touch = 10
        t.cool_down()
        assert t.status == "stale"

    def test_candidate_score_composite(self) -> None:
        s = CandidateScores(relevance=0.8, clarity=0.7, coherence=0.6,
                            personality_fit=0.9, specificity=0.7, goal_fit=0.5,
                            genericness_penalty=0.1)
        assert 0.5 < s.composite < 1.0

    def test_fragment_score_composite(self) -> None:
        s = FragmentScores(relevance=0.7, clarity=0.8, specificity=0.6,
                           usefulness=0.7, personality_fit=0.8, genericness_penalty=0.0)
        assert s.composite > MIN_MEMORY_SCORE

    def test_final_response_quality_tier(self) -> None:
        s = FinalResponseScores(relevance=0.9, clarity=0.9, coherence=0.9,
                                personality_fit=0.9, usefulness=0.9, goal_fit=0.9,
                                genericness_penalty=0.0)
        assert s.quality_tier == "excellent"

        s2 = FinalResponseScores(relevance=0.3, clarity=0.3, coherence=0.3,
                                 personality_fit=0.3, usefulness=0.3, goal_fit=0.3,
                                 genericness_penalty=0.5)
        assert s2.quality_tier == "reject"

    def test_input_sketch_defaults(self) -> None:
        sk = InputSketch(raw_text="Tell me about Odin")
        assert sk.retrieval_path == "hybrid"
        assert sk.urgency == 0.5

    def test_runtime_turn_state_fields(self) -> None:
        state = RuntimeTurnState(turn_id="turn_001")
        assert state.candidates == []
        assert state.final_response is None


# ── Scoring Tests ──────────────────────────────────────────────────────────────

class TestScoring:
    def test_retrieval_score_base(self) -> None:
        dims = RetrievalDimensions(
            semantic_similarity=0.8,
            tone_similarity=0.6,
            preference_relevance=0.7,
            recency=0.9,
            importance=0.8,
        )
        score = score_retrieval(dims, "user_fact")
        assert 0.0 <= score <= 1.0
        assert score > 0.5

    def test_retrieval_score_type_weights(self) -> None:
        dims = RetrievalDimensions(semantic_similarity=1.0)
        score_fact = score_retrieval(dims, "user_fact")
        score_pref = score_retrieval(dims, "user_preference")
        # user_fact has higher semantic weight (0.40) than user_preference (0.25)
        assert score_fact > score_pref

    def test_recency_decay_half_life(self) -> None:
        score_new = compute_recency_score(0, "episode")
        score_halflife = compute_recency_score(7.0, "episode")
        score_old = compute_recency_score(30.0, "episode")
        assert score_new == 1.0
        assert abs(score_halflife - 0.5) < 0.05
        assert score_old < score_halflife

    def test_prune_score_range(self) -> None:
        c = PruneComponents(staleness=0.8, redundancy=0.5, low_confidence=0.7,
                            low_importance=0.6, low_quality=0.5, low_future_relevance=0.4,
                            low_reinforcement=0.3)
        score = compute_prune_score(c)
        assert 0.0 <= score <= 1.0

    def test_survival_score_range(self) -> None:
        c = SurvivalComponents(importance=0.9, confidence=0.8, quality=0.9,
                               future_relevance=0.8, recency=0.9, reinforcement_strength=0.7)
        score = compute_survival_score(c)
        assert 0.5 < score <= 1.0

    def test_genericness_penalty_triggers(self) -> None:
        generic = "A lot of people feel this way in today's world. As an AI, everything will be okay."
        specific = "Odin sacrificed his eye at Mimir's well to gain wisdom."
        assert compute_genericness_penalty(generic) > compute_genericness_penalty(specific)

    def test_writeback_scores(self) -> None:
        c = WritebackComponents(
            durability=0.8, novelty=0.7, confidence=0.9,
            importance=0.8, future_relevance=0.7,
            final_response_quality=0.9, pattern_reusability=0.8,
        )
        pref = compute_preference_writeback_score(c)
        ep = compute_episode_writeback_score(c)
        pat = compute_pattern_learning_score(c)
        assert 0.0 < pref <= 1.0
        assert 0.0 < ep <= 1.0
        assert 0.0 < pat <= 1.0


# ── Memory Store Tests ─────────────────────────────────────────────────────────

class TestMemoryStore:
    @pytest.fixture()
    def store(self, tmp_path: Path) -> MemoryStore:
        return MemoryStore(memory_dir=tmp_path)

    def test_preference_round_trip(self, store: MemoryStore) -> None:
        pref = UserPreferenceRecord(
            record_id=store.new_preference_id(),
            category="tone",
            tags=["direct"],
            summary="direct tone preferred",
        )
        store.append_profile_record(pref)
        records = store.load_profile_records()
        assert len(records) == 1
        assert records[0].summary == "direct tone preferred"

    def test_fact_round_trip(self, store: MemoryStore) -> None:
        fact = UserFactRecord(
            record_id=store.new_fact_id(),
            tags=["project"],
            summary="working on ThoughtForge",
            fact_value={"project": "ThoughtForge"},
        )
        store.append_profile_record(fact)
        records = store.load_profile_records()
        assert any(r.record_type == "user_fact" for r in records)

    def test_episode_round_trip(self, store: MemoryStore) -> None:
        ep = EpisodicMemoryRecord(
            record_id=store.new_episode_id(),
            summary="resolved a tricky bug",
            importance=0.8,
        )
        store.append_episode(ep)
        eps = store.load_episodes()
        assert len(eps) == 1
        assert eps[0].importance == 0.8

    def test_pattern_round_trip(self, store: MemoryStore) -> None:
        pat = ResponsePatternRecord(
            record_id=store.new_pattern_id(),
            pattern_shape=["acknowledge", "explain"],
            quality=0.8,
        )
        store.append_pattern(pat)
        pats = store.load_patterns()
        assert len(pats) == 1

    def test_thread_state_round_trip(self, store: MemoryStore) -> None:
        thread = ActiveThreadStateRecord(
            record_id=store.new_thread_id(),
            topic="Norse mythology",
            priority=0.85,
        )
        store.save_thread_state(thread)
        loaded = store.load_thread_state()
        assert loaded is not None
        assert loaded.topic == "Norse mythology"

    def test_clear_thread_state(self, store: MemoryStore) -> None:
        thread = ActiveThreadStateRecord(record_id="thr_x", topic="test")
        store.save_thread_state(thread)
        store.clear_thread_state()
        assert store.load_thread_state() is None

    def test_tag_index_rebuild(self, store: MemoryStore) -> None:
        pref = UserPreferenceRecord(
            record_id="usr_t1", category="tone", tags=["direct", "brief"], summary="x"
        )
        store.append_profile_record(pref)
        index = store.rebuild_tag_index()
        assert "direct" in index
        assert "usr_t1" in index["direct"]

    def test_recent_queue(self, store: MemoryStore) -> None:
        store.push_to_recent_queue("rec_001")
        store.push_to_recent_queue("rec_002")
        store.push_to_recent_queue("rec_001")  # should move to front
        q = store.load_recent_queue()
        assert q[0] == "rec_001"
        assert len(q) == 2  # no duplicates

    def test_personality_core_round_trip(self, store: MemoryStore) -> None:
        core = PersonalityCoreRecord(
            record_id="pers_001",
            traits=["calm", "wise"],
        )
        store.save_personality_core(core)
        loaded = store.load_personality_core()
        assert loaded is not None
        assert loaded.traits == ["calm", "wise"]


# ── Lifecycle / Pruning Tests ──────────────────────────────────────────────────

class TestLifecycle:
    @pytest.fixture()
    def lifecycle(self, tmp_path: Path) -> MemoryLifecycle:
        store = MemoryStore(memory_dir=tmp_path)
        return MemoryLifecycle(store=store)

    def _seed_preferences(self, lifecycle: MemoryLifecycle, count: int = 5) -> None:
        # Give each record a distinct category to avoid deduplication in tests
        categories = ["tone", "format", "depth", "style", "verbosity"]
        for i in range(count):
            r = UserPreferenceRecord(
                record_id=f"usr_{i:03d}",
                category=categories[i % len(categories)],
                tags=[f"tag_{i}"],
                summary=f"preference {i}",
                importance=0.6 + (i * 0.05),
                confidence=0.6 + (i * 0.05),
            )
            lifecycle.store.append_profile_record(r)

    def test_light_prune_does_not_over_delete(self, lifecycle: MemoryLifecycle) -> None:
        self._seed_preferences(lifecycle, 5)
        counts = lifecycle.prune_light()
        # Light mode has high thresholds; should delete very few records
        assert counts["deleted"] <= 3

    def test_heavy_prune_reduces_stale_store(self, lifecycle: MemoryLifecycle) -> None:
        # Seed many low-quality, year-old preferences — heavy prune should archive/delete them
        # (heavy archive threshold: 0.60; these records score ~0.695)
        from datetime import datetime, timedelta, timezone
        old_ts = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        for i in range(10):
            r = UserPreferenceRecord(
                record_id=f"usr_{i:04d}",
                category=f"cat_{i}",
                tags=[f"old_{i}"],
                summary=f"old stale preference {i}",
                importance=0.1,
                confidence=0.1,
                last_used_at=old_ts,
                updated_at=old_ts,
            )
            lifecycle.store.append_profile_record(r)
        counts = lifecycle.prune_heavy()
        assert counts["archived"] + counts["deleted"] > 0

    def test_reinforce_existing_record(self, lifecycle: MemoryLifecycle) -> None:
        r = UserPreferenceRecord(
            record_id="usr_reinf_01",
            category="tone",
            tags=["direct"],
            summary="test",
            confidence=0.5,
            importance=0.5,
        )
        lifecycle.store.append_profile_record(r)
        result = lifecycle.reinforce("usr_reinf_01", signal_strength=1.0)
        assert result is True
        records = lifecycle.store.load_profile_records()
        updated = next(x for x in records if x.record_id == "usr_reinf_01")
        assert updated.confidence > 0.5

    def test_reinforce_missing_record(self, lifecycle: MemoryLifecycle) -> None:
        result = lifecycle.reinforce("nonexistent_id")
        assert result is False

    def test_cool_thread_reduces_priority(self, lifecycle: MemoryLifecycle) -> None:
        thread = ActiveThreadStateRecord(
            record_id="thr_cool_01",
            topic="test",
            priority=0.9,
            expires_after_turns=5,
        )
        lifecycle.store.save_thread_state(thread)
        lifecycle.cool_thread()
        loaded = lifecycle.store.load_thread_state()
        # Should still be active (not yet expired)
        if loaded is not None:
            assert loaded.priority < 0.9


# ── Schema Tests ───────────────────────────────────────────────────────────────

class TestSchema:
    def test_schema_initialization(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        initialize_schema(db_path)
        assert db_path.exists()

    def test_schema_is_idempotent(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        initialize_schema(db_path)
        initialize_schema(db_path)  # Should not raise

    def test_entity_count_returns_dict(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        initialize_schema(db_path)
        counts = get_entity_count(db_path)
        assert "entities" in counts
        assert counts["entities"] == 0

    def test_can_insert_entity(self, tmp_path: Path) -> None:
        import sqlite3
        db_path = tmp_path / "test.db"
        initialize_schema(db_path)
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO entities (qid, label_en, description_en) VALUES (?, ?, ?)",
            ("Q1", "Universe", "The totality of existence"),
        )
        conn.commit()
        row = conn.execute("SELECT COUNT(*) FROM entities").fetchone()
        assert row[0] == 1
        conn.close()
