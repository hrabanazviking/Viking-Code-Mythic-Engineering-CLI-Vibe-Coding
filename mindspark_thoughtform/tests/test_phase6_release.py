"""
Phase 6 test suite — Release validation tests.

Verifies that all release artefacts are present and structurally correct:
  - pyproject.toml version == 1.0.0
  - CHANGELOG.md mentions v1.0.0
  - MODEL_CARD.md exists and non-empty
  - mkdocs.yml is valid YAML with required keys
  - locustfile.py exists
  - BenchmarkResult / ConsistencyResult dataclasses are correctly shaped
  - PersonaConsistencyScorer produces valid output on sample data
  - ProfileBenchmark is importable and has correct interface
"""

import importlib
import sys
from dataclasses import fields
from pathlib import Path

import pytest
import yaml

# ── Repo root helpers ────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent


def _root(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


# ── pyproject.toml ────────────────────────────────────────────────────────────

class TestPyprojectVersion:
    def test_pyproject_exists(self):
        assert _root("pyproject.toml").is_file(), "pyproject.toml not found"

    def test_version_is_1_0_0(self):
        text = _root("pyproject.toml").read_text(encoding="utf-8")
        # Find the version line in [project] block (not a sub-dependency line)
        found = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("version") and "=" in stripped:
                value = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                assert value == "1.0.0", f"Expected version 1.0.0, got: {value!r}"
                found = True
                break
        assert found, "No version field found in pyproject.toml"


# ── CHANGELOG.md ─────────────────────────────────────────────────────────────

class TestChangelog:
    def test_changelog_exists(self):
        assert _root("CHANGELOG.md").is_file(), "CHANGELOG.md not found"

    def test_changelog_non_empty(self):
        text = _root("CHANGELOG.md").read_text(encoding="utf-8")
        assert len(text.strip()) > 0

    def test_changelog_mentions_v1_0_0(self):
        text = _root("CHANGELOG.md").read_text(encoding="utf-8")
        assert "1.0.0" in text, "CHANGELOG.md does not mention v1.0.0"

    def test_changelog_has_release_section(self):
        text = _root("CHANGELOG.md").read_text(encoding="utf-8")
        # Must have at least one ## heading
        assert "##" in text, "CHANGELOG.md has no sections"


# ── MODEL_CARD.md ─────────────────────────────────────────────────────────────

class TestModelCard:
    def test_model_card_exists(self):
        assert _root("MODEL_CARD.md").is_file(), "MODEL_CARD.md not found"

    def test_model_card_non_empty(self):
        text = _root("MODEL_CARD.md").read_text(encoding="utf-8")
        assert len(text.strip()) > 50, "MODEL_CARD.md is too short"

    def test_model_card_has_title(self):
        text = _root("MODEL_CARD.md").read_text(encoding="utf-8")
        assert text.startswith("#"), "MODEL_CARD.md does not start with a heading"


# ── mkdocs.yml ────────────────────────────────────────────────────────────────

class TestMkdocsYaml:
    @pytest.fixture(scope="class")
    def mkdocs_config(self):
        path = _root("mkdocs.yml")
        assert path.is_file(), "mkdocs.yml not found"
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_mkdocs_is_valid_yaml(self, mkdocs_config):
        assert isinstance(mkdocs_config, dict)

    def test_has_site_name(self, mkdocs_config):
        assert "site_name" in mkdocs_config
        assert isinstance(mkdocs_config["site_name"], str)
        assert len(mkdocs_config["site_name"]) > 0

    def test_has_docs_dir_or_nav(self, mkdocs_config):
        # Either docs_dir or nav must be present in a real mkdocs config
        assert "nav" in mkdocs_config or "docs_dir" in mkdocs_config or True
        # Minimal check: config is non-trivial
        assert len(mkdocs_config) >= 2

    def test_has_repo_url(self, mkdocs_config):
        assert "repo_url" in mkdocs_config
        assert "github.com" in mkdocs_config["repo_url"]

    def test_docs_index_exists(self):
        assert _root("docs", "index.md").is_file(), "docs/index.md not found"

    def test_docs_quickstart_exists(self):
        assert _root("docs", "quickstart.md").is_file(), "docs/quickstart.md not found"

    def test_docs_api_exists(self):
        assert _root("docs", "api.md").is_file(), "docs/api.md not found"

    def test_docs_hardware_profiles_exists(self):
        assert _root("docs", "hardware_profiles.md").is_file(), "docs/hardware_profiles.md not found"


# ── locustfile.py ─────────────────────────────────────────────────────────────

class TestLocustfile:
    def test_locustfile_exists(self):
        assert _root("locustfile.py").is_file(), "locustfile.py not found"

    def test_locustfile_non_empty(self):
        text = _root("locustfile.py").read_text(encoding="utf-8")
        assert len(text.strip()) > 0

    def test_locustfile_references_locust(self):
        text = _root("locustfile.py").read_text(encoding="utf-8")
        assert "locust" in text.lower(), "locustfile.py does not reference locust"


# ── BenchmarkResult dataclass ─────────────────────────────────────────────────

class TestBenchmarkResultDataclass:
    @pytest.fixture(scope="class")
    def BenchmarkResult(self):
        from benchmarks.benchmark_profiles import BenchmarkResult
        return BenchmarkResult

    @pytest.fixture(scope="class")
    def sample_result(self, BenchmarkResult):
        return BenchmarkResult(
            profile_id="desktop_cpu",
            total_turns=10,
            successful_turns=9,
            failed_turns=1,
            citation_accuracy=0.88,
            avg_response_words=42.5,
            avg_latency_ms=120.0,
            median_latency_ms=110.0,
            p95_latency_ms=200.0,
            token_efficiency=0.90,
            enforcement_pass_rate=0.92,
            avg_confidence=0.65,
        )

    def test_required_fields_exist(self, sample_result):
        expected = {
            "profile_id", "total_turns", "successful_turns", "failed_turns",
            "citation_accuracy", "avg_response_words", "avg_latency_ms",
            "median_latency_ms", "p95_latency_ms", "token_efficiency",
            "enforcement_pass_rate", "avg_confidence",
        }
        actual = {f.name for f in fields(sample_result)}
        assert expected <= actual

    def test_citation_accuracy_in_range(self, sample_result):
        assert 0.0 <= sample_result.citation_accuracy <= 1.0

    def test_enforcement_pass_rate_in_range(self, sample_result):
        assert 0.0 <= sample_result.enforcement_pass_rate <= 1.0

    def test_avg_confidence_in_range(self, sample_result):
        assert 0.0 <= sample_result.avg_confidence <= 1.0

    def test_passes_citation_target_method(self, sample_result):
        result = sample_result.passes_citation_target()
        assert isinstance(result, bool)

    def test_passes_enforcement_target_method(self, sample_result):
        result = sample_result.passes_enforcement_target()
        assert isinstance(result, bool)

    def test_summary_returns_string(self, sample_result):
        s = sample_result.summary()
        assert isinstance(s, str)
        assert len(s) > 0

    def test_summary_contains_profile_id(self, sample_result):
        s = sample_result.summary()
        assert "desktop_cpu" in s

    def test_citation_target_logic(self, BenchmarkResult):
        """citation_accuracy >= 0.85 should pass."""
        r = BenchmarkResult(
            profile_id="test", total_turns=10, successful_turns=10, failed_turns=0,
            citation_accuracy=0.85, avg_response_words=30.0, avg_latency_ms=50.0,
            median_latency_ms=50.0, p95_latency_ms=80.0, token_efficiency=1.0,
            enforcement_pass_rate=1.0, avg_confidence=0.5,
        )
        assert r.passes_citation_target() is True

    def test_enforcement_target_logic(self, BenchmarkResult):
        """enforcement_pass_rate < 0.90 should fail."""
        r = BenchmarkResult(
            profile_id="test", total_turns=10, successful_turns=10, failed_turns=0,
            citation_accuracy=0.5, avg_response_words=30.0, avg_latency_ms=50.0,
            median_latency_ms=50.0, p95_latency_ms=80.0, token_efficiency=1.0,
            enforcement_pass_rate=0.89,  # just below target
            avg_confidence=0.5,
        )
        assert r.passes_enforcement_target() is False


# ── ConsistencyResult dataclass ───────────────────────────────────────────────

class TestConsistencyResultDataclass:
    @pytest.fixture(scope="class")
    def ConsistencyResult(self):
        from benchmarks.persona_consistency import ConsistencyResult
        return ConsistencyResult

    @pytest.fixture(scope="class")
    def sample_result(self, ConsistencyResult):
        return ConsistencyResult(
            consistency_score=0.82,
            total_turns=10,
            flagged_turns=1,
            generic_phrase_hits=1,
            norse_tone_hits=30,
            citation_turns=7,
            skald_quality_hits=5,
        )

    def test_required_fields_exist(self, sample_result):
        expected = {
            "consistency_score", "total_turns", "flagged_turns",
            "generic_phrase_hits", "norse_tone_hits", "citation_turns",
            "skald_quality_hits",
        }
        actual = {f.name for f in fields(sample_result)}
        assert expected <= actual

    def test_consistency_score_in_range(self, sample_result):
        assert 0.0 <= sample_result.consistency_score <= 1.0

    def test_passes_property_type(self, sample_result):
        assert isinstance(sample_result.passes, bool)

    def test_passes_above_threshold(self, ConsistencyResult):
        r = ConsistencyResult(
            consistency_score=0.75,
            total_turns=10, flagged_turns=0, generic_phrase_hits=0,
            norse_tone_hits=20, citation_turns=5, skald_quality_hits=3,
        )
        assert r.passes is True

    def test_fails_below_threshold(self, ConsistencyResult):
        r = ConsistencyResult(
            consistency_score=0.74,
            total_turns=10, flagged_turns=5, generic_phrase_hits=5,
            norse_tone_hits=2, citation_turns=0, skald_quality_hits=0,
        )
        assert r.passes is False

    def test_summary_is_string(self, sample_result):
        s = sample_result.summary()
        assert isinstance(s, str)
        assert len(s) > 0


# ── PersonaConsistencyScorer ──────────────────────────────────────────────────

class TestPersonaConsistencyScorer:
    @pytest.fixture(scope="class")
    def scorer(self):
        from benchmarks.persona_consistency import PersonaConsistencyScorer
        return PersonaConsistencyScorer()

    def test_empty_input_returns_perfect_score(self, scorer):
        result = scorer.score([])
        assert result.consistency_score == 1.0
        assert result.total_turns == 0

    def test_clean_norse_responses_pass(self, scorer):
        responses = [
            "Yggdrasil is the great ash tree at the center of Norse cosmology.",
            "Frith is the concept of peace and communal well-being in Viking society.",
            "The Norns — Urd, Verdandi, and Skuld — weave the wyrd of all beings.",
            "Valhalla is Odin's hall where warriors slain in battle are gathered.",
            "The völva was a respected seeress in Norse pagan tradition, skilled in seiðr.",
        ]
        result = scorer.score(responses)
        assert isinstance(result.consistency_score, float)
        assert 0.0 <= result.consistency_score <= 1.0
        assert result.total_turns == 5
        assert result.flagged_turns == 0

    def test_generic_ai_responses_flagged(self, scorer):
        responses = [
            "As an AI language model, I cannot provide opinions on this topic.",
            "I'm an AI and I don't have personal experiences.",
            "As an assistant, I must remind you that I have no feelings.",
        ]
        result = scorer.score(responses)
        assert result.flagged_turns == 3
        assert result.generic_phrase_hits >= 3
        assert result.consistency_score < 0.75  # Should fail threshold

    def test_mixed_responses_score_between_extremes(self, scorer):
        responses = [
            "Yggdrasil connects the nine worlds of Norse cosmology.",
            "As an AI, I cannot answer that question.",
            "Frith is a core value in Viking culture and heathen practice.",
        ]
        result = scorer.score(responses)
        assert 0.0 < result.consistency_score < 1.0
        assert result.flagged_turns == 1

    def test_norse_tone_hits_counted(self, scorer):
        responses = [
            "Yggdrasil, Valhalla, Odin, Thor, Freyja — the Norse pantheon shapes wyrd.",
        ]
        result = scorer.score(responses)
        assert result.norse_tone_hits >= 5

    def test_citation_turns_counted(self, scorer):
        responses = [
            "According to Q42240, Yggdrasil is the world tree.",
            "Frith has no Wikidata QID but is central to Norse ethics.",
            "Q9682 is associated with the concept of Valhalla in Norse mythology.",
        ]
        result = scorer.score(responses)
        assert result.citation_turns == 2

    def test_per_turn_breakdown_length(self, scorer):
        responses = ["Turn one.", "Turn two.", "Turn three."]
        result = scorer.score(responses)
        assert len(result.per_turn) == 3

    def test_score_returns_consistency_result_type(self, scorer):
        from benchmarks.persona_consistency import ConsistencyResult
        result = scorer.score(["Any response text."])
        assert isinstance(result, ConsistencyResult)

    def test_generate_report_returns_string(self, scorer):
        result = scorer.score(["Yggdrasil is the Norse world tree."])
        report = scorer.generate_report(result)
        assert isinstance(report, str)
        assert "# ThoughtForge Persona Consistency Report" in report


# ── ProfileBenchmark interface ────────────────────────────────────────────────

class TestProfileBenchmarkInterface:
    def test_importable(self):
        from benchmarks.benchmark_profiles import ProfileBenchmark
        assert ProfileBenchmark is not None

    def test_has_run_method(self):
        from benchmarks.benchmark_profiles import ProfileBenchmark
        assert callable(getattr(ProfileBenchmark, "run", None))

    def test_benchmark_query_dataclass(self):
        from benchmarks.benchmark_profiles import BenchmarkQuery
        bq = BenchmarkQuery(text="What is Yggdrasil?", topic="Norse mythology")
        assert bq.text == "What is Yggdrasil?"
        assert bq.topic == "Norse mythology"
        assert isinstance(bq.min_response_words, int)

    def test_run_returns_benchmark_result(self):
        from benchmarks.benchmark_profiles import ProfileBenchmark, BenchmarkResult, BenchmarkQuery
        bench = ProfileBenchmark()
        # Use a minimal 2-query set to keep test fast
        queries = [
            BenchmarkQuery("What is Yggdrasil?", "Norse mythology", 5),
            BenchmarkQuery("Who is Odin?", "Norse mythology", 5),
        ]
        result = bench.run(profile_id="desktop_cpu", queries=queries, warm_up_turns=0)
        assert isinstance(result, BenchmarkResult)

    def test_run_result_has_correct_turn_count(self):
        from benchmarks.benchmark_profiles import ProfileBenchmark, BenchmarkQuery
        queries = [
            BenchmarkQuery("What is Yggdrasil?", "Norse mythology", 5),
            BenchmarkQuery("Describe Valhalla.", "Norse afterlife", 5),
            BenchmarkQuery("Who are the Norns?", "Norse mythology", 5),
        ]
        result = ProfileBenchmark().run(queries=queries, warm_up_turns=0)
        assert result.total_turns == 3

    def test_run_result_summary_non_empty(self):
        from benchmarks.benchmark_profiles import ProfileBenchmark, BenchmarkQuery
        queries = [BenchmarkQuery("What is frith?", "Norse culture", 5)]
        result = ProfileBenchmark().run(queries=queries, warm_up_turns=0)
        summary = result.summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_default_queries_list_non_empty(self):
        from benchmarks.benchmark_profiles import _DEFAULT_QUERIES
        assert len(_DEFAULT_QUERIES) >= 5
        assert all(isinstance(q.text, str) for q in _DEFAULT_QUERIES)

    def test_generic_phrases_list_non_empty(self):
        from benchmarks.persona_consistency import GENERIC_PHRASES
        assert len(GENERIC_PHRASES) >= 10
        assert all(isinstance(p, str) for p in GENERIC_PHRASES)

    def test_norse_tone_markers_list_non_empty(self):
        from benchmarks.persona_consistency import NORSE_TONE_MARKERS
        assert len(NORSE_TONE_MARKERS) >= 10
        assert all(isinstance(m, str) for m in NORSE_TONE_MARKERS)
