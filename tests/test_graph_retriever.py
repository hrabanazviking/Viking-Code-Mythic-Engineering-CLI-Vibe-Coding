"""Tests for the relevance-ranked retriever (PH-05 slice 5.3)."""

from __future__ import annotations

import unittest

from mythic_vibe_cli.context.graph import GraphStore
from mythic_vibe_cli.context.retriever import (
    DEFAULT_TOP_K,
    NEIGHBOUR_DECAY,
    RetrievalResult,
    rank_entities,
    top_k,
)


class _SeededStore:
    """Helper that builds a small graph fixture for retriever tests.

    Layout:

        modules: app, drift, picker
        documents: README, ARCHITECTURE
        tags: app=[cli, core] drift=[cli, drift]  picker=[cli, tui]
              README=[docs] ARCHITECTURE=[docs, core]
        edges: app -references-> drift, app -mentions-> README,
               drift -mentions-> ARCHITECTURE
    """

    def __init__(self) -> None:
        self.store = GraphStore.open_in_memory()
        s = self.store
        self.app = s.upsert_entity("module", "app")
        self.drift = s.upsert_entity("module", "drift")
        self.picker = s.upsert_entity("module", "picker")
        self.readme = s.upsert_entity("document", "README")
        self.arch = s.upsert_entity("document", "ARCHITECTURE")

        s.add_tag(self.app.id, "cli", weight=2.0)
        s.add_tag(self.app.id, "core", weight=1.0)
        s.add_tag(self.drift.id, "cli", weight=1.0)
        s.add_tag(self.drift.id, "drift", weight=2.0)
        s.add_tag(self.picker.id, "cli", weight=1.0)
        s.add_tag(self.picker.id, "tui", weight=1.5)
        s.add_tag(self.readme.id, "docs", weight=1.0)
        s.add_tag(self.arch.id, "docs", weight=1.0)
        s.add_tag(self.arch.id, "core", weight=2.0)

        s.upsert_edge(self.app.id, self.drift.id, "references")
        s.upsert_edge(self.app.id, self.readme.id, "mentions")
        s.upsert_edge(self.drift.id, self.arch.id, "mentions")

    def close(self) -> None:
        self.store.close()


class RankEntitiesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _SeededStore()
        self.addCleanup(self.fixture.close)

    def test_empty_query_returns_empty(self) -> None:
        self.assertEqual(rank_entities(self.fixture.store, []), [])
        self.assertEqual(rank_entities(self.fixture.store, ["", "  "]), [])

    def test_no_matches_returns_empty(self) -> None:
        self.assertEqual(rank_entities(self.fixture.store, ["nonexistent"]), [])

    def test_tag_overlap_scores_in_descending_order(self) -> None:
        # "cli" matches all three modules with weights 2.0, 1.0, 1.0.
        results = rank_entities(
            self.fixture.store, ["cli"], expand_neighbours=False
        )
        scores = [(r.entity.name, r.score) for r in results]
        self.assertEqual(scores[0], ("app", 2.0))
        self.assertIn(("drift", 1.0), scores)
        self.assertIn(("picker", 1.0), scores)

    def test_multi_tag_summed_weights(self) -> None:
        # "cli" + "core" hits app with 2.0 + 1.0 = 3.0 and drift with 1.0,
        # picker with 1.0, ARCHITECTURE with 2.0.
        results = rank_entities(
            self.fixture.store, ["cli", "core"], expand_neighbours=False
        )
        scores = {r.entity.name: r.score for r in results}
        self.assertEqual(scores["app"], 3.0)
        self.assertEqual(scores["ARCHITECTURE"], 2.0)
        self.assertEqual(scores["drift"], 1.0)

    def test_neighbour_expansion_adds_decayed_scores(self) -> None:
        # Querying "drift" matches drift module (score 2.0). With
        # expansion, app (references drift) and ARCHITECTURE
        # (drift mentions ARCHITECTURE) appear with score 2.0 * 0.5 = 1.0.
        results = rank_entities(self.fixture.store, ["drift"])
        scored = {r.entity.name: r.score for r in results}
        self.assertEqual(scored["drift"], 2.0)
        self.assertAlmostEqual(scored["app"], 1.0)
        self.assertAlmostEqual(scored["ARCHITECTURE"], 1.0)

    def test_neighbour_expansion_can_be_disabled(self) -> None:
        results = rank_entities(
            self.fixture.store, ["drift"], expand_neighbours=False
        )
        names = [r.entity.name for r in results]
        self.assertEqual(names, ["drift"])

    def test_reasons_list_explains_match(self) -> None:
        results = rank_entities(self.fixture.store, ["cli"])
        app = next(r for r in results if r.entity.name == "app")
        self.assertIn("tag:cli", app.reasons)
        # Neighbours of app (drift, README) inherited score → reasons
        # include "neighbour-of:<id>".
        readme_results = [r for r in results if r.entity.name == "README"]
        self.assertEqual(len(readme_results), 1)
        self.assertTrue(
            any(reason.startswith("neighbour-of") for reason in readme_results[0].reasons)
        )

    def test_seed_neighbours_are_not_double_counted(self) -> None:
        """If a query hits both ``app`` and ``drift`` (which are
        connected), the neighbour-expansion pass must not boost the
        already-seeded entities again."""
        results = rank_entities(
            self.fixture.store, ["cli", "drift"], expand_neighbours=True
        )
        scored = {r.entity.name: r.score for r in results}
        # app: cli (2.0) directly; drift: cli (1.0) + drift (2.0) = 3.0
        # Seed scores stay seeded — neighbours of seeds don't add to
        # other seeds.
        self.assertEqual(scored["app"], 2.0)
        self.assertEqual(scored["drift"], 3.0)

    def test_results_are_deterministic_on_tie(self) -> None:
        results = rank_entities(
            self.fixture.store, ["cli"], expand_neighbours=False
        )
        # drift and picker both score 1.0; tie-break by kind then name —
        # both modules → name lexicographic.
        tied = [r.entity.name for r in results if r.score == 1.0]
        self.assertEqual(tied, ["drift", "picker"])


class TopKTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _SeededStore()
        self.addCleanup(self.fixture.close)

    def test_default_k_is_documented(self) -> None:
        self.assertEqual(DEFAULT_TOP_K, 10)

    def test_top_k_limits_results(self) -> None:
        results = top_k(self.fixture.store, ["cli"], k=2)
        self.assertEqual(len(results), 2)

    def test_top_k_zero_or_negative_returns_empty(self) -> None:
        self.assertEqual(top_k(self.fixture.store, ["cli"], k=0), [])
        self.assertEqual(top_k(self.fixture.store, ["cli"], k=-1), [])

    def test_top_k_passes_through_when_k_exceeds_results(self) -> None:
        results = top_k(self.fixture.store, ["nonexistent"], k=50)
        self.assertEqual(results, [])


class RetrievalResultTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        with GraphStore.open_in_memory() as store:
            ent = store.upsert_entity("module", "x", path="x.py")
            result = RetrievalResult(entity=ent, score=1.5, reasons=("tag:foo",))
        payload = result.to_dict()
        self.assertEqual(payload["score"], 1.5)
        self.assertEqual(payload["reasons"], ["tag:foo"])
        self.assertEqual(payload["entity"]["name"], "x")

    def test_neighbour_decay_constant(self) -> None:
        # Locked at 0.5 — slice 5.7 packet builder calibrates against
        # this constant, so a future change should be deliberate.
        self.assertEqual(NEIGHBOUR_DECAY, 0.5)


if __name__ == "__main__":
    unittest.main()
