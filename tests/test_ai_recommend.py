"""Phase 20.4 (audit remediation 2026-05-03) — ai recommend tests.

Two layers:

- **Pure scoring** — fabricate ``ModelInfo`` instances and feed
  them to ``score_model`` / ``recommend_models``. Avoids
  coupling to the catalog (which churns).
- **CLI integration** — invoke ``cmd_ai_recommend`` with a
  faked argparse Namespace; assert text and JSON outputs.

Pure stdlib; no provider calls.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest

from mythic_vibe_cli.ai.providers.model_catalog import ModelInfo
from mythic_vibe_cli.ai.recommend import (
    COST_CLASSES,
    SUPPORTED_FAMILIES,
    ModelRecommendation,
    RecommendationCriteria,
    recommend_models,
    score_model,
)
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR


def _model(
    *,
    id: str,
    family: str = "anthropic",
    context_window: int = 100_000,
    capabilities: tuple[str, ...] = (),
) -> ModelInfo:
    return ModelInfo(
        id=id,
        family=family,
        display_name=id,
        context_window=context_window,
        max_output_tokens=4096,
        capabilities=capabilities,
        source="static",
        last_updated="2026-05-03",
    )


# ---------------------------------------------------------------------------
# Pure scoring
# ---------------------------------------------------------------------------


class ScoreModelTests(unittest.TestCase):
    def test_empty_criteria_yields_capability_richness_only(self) -> None:
        """With no constraints, score = capability count."""
        m = _model(id="claude-opus-4-7", capabilities=("vision", "tools"))
        score, _ = score_model(m, RecommendationCriteria())
        self.assertEqual(score, 2)

    def test_context_satisfied_adds_30(self) -> None:
        m = _model(id="x", context_window=200_000, capabilities=())
        score, reasons = score_model(
            m, RecommendationCriteria(max_context=100_000)
        )
        self.assertEqual(score, 30)
        self.assertTrue(any("context window" in r for r in reasons))

    def test_context_under_required_hits_hard_penalty(self) -> None:
        m = _model(id="x", context_window=4_000, capabilities=())
        score, _ = score_model(
            m, RecommendationCriteria(max_context=100_000)
        )
        self.assertLess(score, 0)

    def test_explicit_vision_required_with_capability(self) -> None:
        m = _model(id="x", capabilities=("vision",))
        score, reasons = score_model(
            m, RecommendationCriteria(vision_required=True)
        )
        # Base: 1 (capabilities) + 25 (vision present, required).
        self.assertEqual(score, 26)
        self.assertTrue(any("vision capability present" in r for r in reasons))

    def test_explicit_vision_required_without_capability(self) -> None:
        m = _model(id="x", capabilities=())
        score, _ = score_model(
            m, RecommendationCriteria(vision_required=True)
        )
        self.assertEqual(score, -50)

    def test_inferred_vision_from_task_keyword(self) -> None:
        """Task containing 'image' implies vision_required."""
        m = _model(id="x", capabilities=("vision",))
        score, reasons = score_model(
            m, RecommendationCriteria(task="analyse an image of a chart")
        )
        self.assertGreater(score, 1)
        self.assertTrue(
            any("inferred from task" in r for r in reasons)
        )

    def test_cost_class_match_adds_20(self) -> None:
        m = _model(id="claude-haiku-4-5", capabilities=())
        score, reasons = score_model(
            m, RecommendationCriteria(cost_class="cheap")
        )
        self.assertEqual(score, 20)
        self.assertTrue(any("cost class matches" in r for r in reasons))

    def test_cost_class_mismatch_mild_penalty(self) -> None:
        m = _model(id="claude-opus-4-7", capabilities=())
        score, _ = score_model(
            m, RecommendationCriteria(cost_class="cheap")
        )
        # opus → premium; -5 penalty.
        self.assertEqual(score, -5)

    def test_family_match_adds_10(self) -> None:
        m = _model(id="x", family="openai", capabilities=())
        score, _ = score_model(
            m, RecommendationCriteria(family="openai")
        )
        self.assertEqual(score, 10)

    def test_family_all_does_not_bonus(self) -> None:
        m = _model(id="x", family="openai", capabilities=())
        score, _ = score_model(
            m, RecommendationCriteria(family="all")
        )
        self.assertEqual(score, 0)


class RecommendModelsTests(unittest.TestCase):
    def test_top_n_limits_returned(self) -> None:
        candidates = [
            _model(id=f"m{i}", capabilities=())
            for i in range(10)
        ]
        recs = recommend_models(
            RecommendationCriteria(),
            top_n=3,
            candidates=candidates,
        )
        self.assertEqual(len(recs), 3)

    def test_top_n_zero_returns_all(self) -> None:
        candidates = [
            _model(id=f"m{i}", capabilities=())
            for i in range(5)
        ]
        recs = recommend_models(
            RecommendationCriteria(),
            top_n=0,
            candidates=candidates,
        )
        self.assertEqual(len(recs), 5)

    def test_sort_descending_by_score_then_id(self) -> None:
        # All same score (no criteria) → sort by id ascending.
        candidates = [
            _model(id="z"), _model(id="a"), _model(id="m"),
        ]
        recs = recommend_models(
            RecommendationCriteria(),
            top_n=0,
            candidates=candidates,
        )
        self.assertEqual([r.model.id for r in recs], ["a", "m", "z"])

    def test_real_catalog_returns_results(self) -> None:
        """Smoke test against the real static catalog — ensures
        the integration with model_catalog hasn't drifted."""
        recs = recommend_models(
            RecommendationCriteria(),
            top_n=3,
        )
        self.assertGreater(len(recs), 0)
        # Every recommendation should have a non-empty model id.
        for rec in recs:
            self.assertTrue(rec.model.id)

    def test_family_filter_restricts_pool(self) -> None:
        recs_all = recommend_models(
            RecommendationCriteria(),
            top_n=0,
        )
        recs_anthropic = recommend_models(
            RecommendationCriteria(family="anthropic"),
            top_n=0,
        )
        self.assertGreater(len(recs_all), len(recs_anthropic))
        self.assertTrue(
            all(r.model.family == "anthropic" for r in recs_anthropic)
        )


class ModelRecommendationSerializationTests(unittest.TestCase):
    def test_to_dict_contains_expected_keys(self) -> None:
        m = _model(id="x", capabilities=("vision",))
        rec = ModelRecommendation(model=m, score=42, reasons=("a",))
        payload = rec.to_dict()
        self.assertEqual(payload["score"], 42)
        self.assertEqual(payload["reasons"], ["a"])
        self.assertEqual(payload["model"]["id"], "x")
        json.dumps(payload)  # JSON-serialisable.


class ConstantsTests(unittest.TestCase):
    def test_supported_families_match_catalog(self) -> None:
        self.assertEqual(
            SUPPORTED_FAMILIES,
            ("anthropic", "openai", "gemini", "openrouter"),
        )

    def test_cost_classes_locked(self) -> None:
        self.assertEqual(
            COST_CLASSES, ("cheap", "standard", "premium")
        )


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


class CmdAiRecommendIntegrationTests(unittest.TestCase):
    def _run(self, ns: argparse.Namespace) -> tuple[int, str]:
        from mythic_vibe_cli.commands import cmd_ai_recommend

        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = cmd_ai_recommend(ns)
        finally:
            sys.stdout = original
        return code, captured.getvalue()

    def _ns(self, **overrides) -> argparse.Namespace:
        kwargs = {
            "task": "",
            "max_context": 0,
            "vision": False,
            "cost_class": None,
            "family": None,
            "top": 3,
            "json": False,
            "path": tempfile.gettempdir(),
        }
        kwargs.update(overrides)
        return argparse.Namespace(**kwargs)

    def test_default_invocation_renders_text(self) -> None:
        code, output = self._run(self._ns())
        self.assertEqual(code, SUCCESS)
        self.assertIn("Model recommendations", output)
        self.assertIn("Top picks", output)

    def test_json_payload_shape(self) -> None:
        code, output = self._run(self._ns(json=True))
        payload = json.loads(output)
        self.assertEqual(code, SUCCESS)
        self.assertIn("recommendations", payload)
        self.assertIn("criteria", payload)
        self.assertEqual(payload["top_n"], 3)
        for rec in payload["recommendations"]:
            self.assertIn("model", rec)
            self.assertIn("score", rec)
            self.assertIn("reasons", rec)

    def test_invalid_cost_class_rejected(self) -> None:
        code, _ = self._run(self._ns(cost_class="luxury"))
        self.assertEqual(code, USER_INPUT_ERROR)

    def test_negative_top_rejected(self) -> None:
        code, _ = self._run(self._ns(top=-1))
        self.assertEqual(code, USER_INPUT_ERROR)


if __name__ == "__main__":
    unittest.main()
