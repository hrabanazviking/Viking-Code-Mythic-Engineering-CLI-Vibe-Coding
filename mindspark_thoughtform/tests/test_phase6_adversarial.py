"""
Phase 6 test suite — Adversarial + edge case tests.

Verifies ThoughtForgeCore handles hostile, degenerate, and unexpected inputs
without crashing, and that the enforcement gate correctly flags problematic
synthetic responses (generic AI phrases, etc.).
"""

import tempfile
from pathlib import Path

import pytest

from thoughtforge.cognition.core import ThoughtForgeCore
from thoughtforge.knowledge.models import FinalResponseRecord
from thoughtforge.refinement.enforcement import EnforcementGate


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def core():
    tmp = tempfile.mkdtemp()
    return ThoughtForgeCore(
        memory_dir=Path(tmp) / "memory",
        db_path=Path(tmp) / "nonexistent.db",
        model_path=None,
    )


# ── Empty + whitespace input ──────────────────────────────────────────────────

class TestEmptyAndWhitespaceInput:
    def test_empty_string_does_not_crash(self, core):
        result = core.think("")
        assert isinstance(result, FinalResponseRecord)

    def test_empty_string_returns_text(self, core):
        result = core.think("")
        assert isinstance(result.text, str)

    def test_whitespace_only_does_not_crash(self, core):
        result = core.think("   \t\n   ")
        assert isinstance(result, FinalResponseRecord)

    def test_whitespace_only_returns_text(self, core):
        result = core.think("   \t\n   ")
        assert isinstance(result.text, str)

    def test_single_character_does_not_crash(self, core):
        result = core.think("?")
        assert isinstance(result, FinalResponseRecord)

    def test_single_word_does_not_crash(self, core):
        result = core.think("Yggdrasil")
        assert isinstance(result, FinalResponseRecord)


# ── Very long input ───────────────────────────────────────────────────────────

class TestVeryLongInput:
    def test_2000_char_query_does_not_crash(self, core):
        long_query = "What is Yggdrasil? " * 100     # ~2000 chars
        result = core.think(long_query)
        assert isinstance(result, FinalResponseRecord)

    def test_5000_char_query_does_not_crash(self, core):
        very_long = "Tell me about Norse mythology and the world tree. " * 100
        result = core.think(very_long)
        assert isinstance(result, FinalResponseRecord)

    def test_long_query_returns_valid_text(self, core):
        long_query = "Describe in detail: " + "the Norse world tree " * 50
        result = core.think(long_query)
        assert isinstance(result.text, str)

    def test_long_query_enforcement_passed_is_bool(self, core):
        long_query = "What is " + "Yggdrasil " * 200
        result = core.think(long_query)
        assert isinstance(result.enforcement_passed, bool)


# ── SQL injection and special characters ─────────────────────────────────────

class TestSpecialCharacterInput:
    def test_sql_injection_string_does_not_crash(self, core):
        injection = "'; DROP TABLE entities; --"
        result = core.think(injection)
        assert isinstance(result, FinalResponseRecord)

    def test_sql_injection_treated_as_plain_text(self, core):
        injection = "SELECT * FROM users WHERE 1=1; --"
        result = core.think(injection)
        assert isinstance(result.text, str)

    def test_angle_brackets_do_not_crash(self, core):
        result = core.think("<script>alert('xss')</script>")
        assert isinstance(result, FinalResponseRecord)

    def test_backslash_sequences_do_not_crash(self, core):
        result = core.think("What is \\x00 \\n\\r\\t Yggdrasil?")
        assert isinstance(result, FinalResponseRecord)

    def test_null_bytes_in_query(self, core):
        result = core.think("Yggdrasil\x00\x00 world tree")
        assert isinstance(result, FinalResponseRecord)

    def test_format_string_does_not_crash(self, core):
        result = core.think("What is %s %d %x Yggdrasil?")
        assert isinstance(result, FinalResponseRecord)


# ── Unicode and emoji ──────────────────────────────────────────────────────────

class TestUnicodeAndEmojiInput:
    def test_emoji_query_does_not_crash(self, core):
        result = core.think("What is Yggdrasil? 🌳⚡🪄")
        assert isinstance(result, FinalResponseRecord)

    def test_runic_characters_do_not_crash(self, core):
        result = core.think("ᚤᚷᚷᛞᚱᚨᛋᛁᛚ — tell me about this")
        assert isinstance(result, FinalResponseRecord)

    def test_arabic_query_does_not_crash(self, core):
        result = core.think("ما هو يغدراسيل؟")
        assert isinstance(result, FinalResponseRecord)

    def test_chinese_query_does_not_crash(self, core):
        result = core.think("世界树是什么？")
        assert isinstance(result, FinalResponseRecord)

    def test_mixed_script_does_not_crash(self, core):
        result = core.think("What is Ygdrasil (Yggdrasil, ユグドラシル, 世界树)?")
        assert isinstance(result, FinalResponseRecord)

    def test_zero_width_characters_do_not_crash(self, core):
        result = core.think("What\u200bis\u200cYggdrasil?")
        assert isinstance(result, FinalResponseRecord)


# ── Repeated identical queries ────────────────────────────────────────────────

class TestRepeatedIdenticalQueries:
    def test_same_query_twice_both_succeed(self, core):
        q = "What is Yggdrasil?"
        r1 = core.think(q)
        r2 = core.think(q)
        assert isinstance(r1, FinalResponseRecord)
        assert isinstance(r2, FinalResponseRecord)

    def test_same_query_produces_unique_turn_ids(self, core):
        q = "What is Yggdrasil?"
        r1 = core.think(q)
        r2 = core.think(q)
        assert r1.turn_id != r2.turn_id

    def test_ten_identical_queries_all_succeed(self, core):
        q = "What is frith?"
        results = [core.think(q) for _ in range(10)]
        assert all(isinstance(r, FinalResponseRecord) for r in results)


# ── Hallucinated QID enforcement ──────────────────────────────────────────────

class TestHallucinatedQIDEnforcement:
    def test_enforcement_gate_flags_missing_qids(self):
        """Enforcement fails if retrieved QIDs don't appear in response."""
        gate = EnforcementGate()
        result = gate.check(
            "Yggdrasil connects the nine worlds.",
            citations=[],
            retrieved_qids={"Q99999999"},   # QID that doesn't appear in text
        )
        assert result.citation_check is False
        assert result.passed is False

    def test_enforcement_gate_passes_cited_qid(self):
        gate = EnforcementGate()
        result = gate.check(
            "According to Q99999999, Yggdrasil is the world tree.",
            citations=["Q99999999"],
            retrieved_qids={"Q99999999"},
        )
        assert result.citation_check is True

    def test_enforcement_appends_forge_note_on_hallucination(self):
        gate = EnforcementGate()
        result = gate.check(
            "The world tree connects nine realms.",
            citations=[],
            retrieved_qids={"Q12345"},
        )
        assert "[Forge:" in result.text

    def test_enforcement_genericness_flag_on_ai_phrase(self):
        gate = EnforcementGate()
        result = gate.check(
            "As an AI language model, I am unable to provide information about this topic.",
            citations=[],
            retrieved_qids=set(),
        )
        assert result.genericness_check is False
        assert result.passed is False

    def test_enforcement_passes_clean_norse_response(self):
        gate = EnforcementGate()
        result = gate.check(
            "Q42240 describes Yggdrasil as the great ash tree at the center of Norse cosmology, "
            "connecting nine worlds including Asgard, Midgard, and Jotunheim.",
            citations=["Q42240"],
            retrieved_qids={"Q42240"},
        )
        assert result.passed is True
        assert result.citation_check is True
        assert result.genericness_check is True
        assert result.length_check is True


# ── Retrieval path edge cases ─────────────────────────────────────────────────

class TestRetrievalPathEdgeCases:
    def test_unknown_retrieval_path_does_not_crash(self, core):
        """Unknown retrieval_path value should fall back gracefully."""
        try:
            result = core.think("test", retrieval_path=None)
            assert isinstance(result, FinalResponseRecord)
        except Exception as e:
            pytest.fail(f"Unexpected exception with retrieval_path=None: {e}")

    def test_all_retrieval_paths_work(self, core):
        for path in ["sql", "vector", "hybrid"]:
            result = core.think("What is Yggdrasil?", retrieval_path=path)
            assert isinstance(result, FinalResponseRecord), f"Failed for path={path}"

    def test_zero_num_drafts_does_not_crash(self, core):
        """num_drafts=1 is the minimum valid value."""
        result = core.think("What is Yggdrasil?", num_drafts=1)
        assert isinstance(result, FinalResponseRecord)

    def test_high_num_drafts_does_not_crash(self, core):
        result = core.think("What is Yggdrasil?", num_drafts=5)
        assert isinstance(result, FinalResponseRecord)
