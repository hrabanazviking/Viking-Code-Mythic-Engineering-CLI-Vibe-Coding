"""Tests for the session-brief rehydrator (PH-05 slice 5.4)."""

from __future__ import annotations

import unittest

from mythic_vibe_cli.context.graph import GraphStore
from mythic_vibe_cli.context.rehydrator import (
    DEFAULT_RECENT_DECISIONS,
    SessionBrief,
    build_session_brief,
    render_brief_text,
)


class _FixtureStore:
    """Build a richer fixture covering every section the brief surfaces."""

    def __init__(self) -> None:
        self.store = GraphStore.open_in_memory()
        s = self.store
        # Decisions, artefacts, verification, handoff entities.
        self.d_old = s.upsert_entity(
            "decision", "0001-old", metadata={"status": "accepted"}
        )
        self.d_new = s.upsert_entity(
            "decision", "0002-new", metadata={"status": "accepted"}
        )
        self.module = s.upsert_entity("module", "core")
        self.task = s.upsert_entity("task", "T-100")
        self.verify = s.upsert_entity(
            "verification", "VER-ABC", metadata={"result": "pass"}
        )
        self.handoff = s.upsert_entity(
            "handoff", "HO-9XYZ", metadata={"objective": "ship"}
        )
        # Tag the current phase ("build") onto two artefacts.
        s.add_tag(self.module.id, "build", weight=2.0)
        s.add_tag(self.task.id, "build", weight=1.5)
        s.add_tag(self.d_new.id, "build", weight=1.0)
        # Manually massage updated_at so "newest" is deterministic.
        s._conn.execute(
            "UPDATE entities SET updated_at='2026-04-01T00:00:00Z' WHERE id=?",
            (self.d_old.id,),
        )
        s._conn.execute(
            "UPDATE entities SET updated_at='2026-04-29T00:00:00Z' WHERE id=?",
            (self.d_new.id,),
        )
        s._conn.execute(
            "UPDATE entities SET updated_at='2026-04-29T01:00:00Z' WHERE id=?",
            (self.verify.id,),
        )
        s._conn.execute(
            "UPDATE entities SET updated_at='2026-04-29T02:00:00Z' WHERE id=?",
            (self.handoff.id,),
        )
        s._conn.commit()

    def close(self) -> None:
        self.store.close()


class BuildSessionBriefTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _FixtureStore()
        self.addCleanup(self.fixture.close)

    def test_empty_graph_returns_empty_brief(self) -> None:
        with GraphStore.open_in_memory() as store:
            brief = build_session_brief(store, "build")
        self.assertTrue(brief.is_empty)
        self.assertEqual(brief.current_phase, "build")
        self.assertEqual(brief.recent_decisions, ())
        self.assertEqual(brief.phase_artefacts, ())
        self.assertIsNone(brief.latest_verification)
        self.assertIsNone(brief.latest_handoff)

    def test_brief_surfaces_every_section(self) -> None:
        brief = build_session_brief(self.fixture.store, "build")
        # Decisions sorted newest-first.
        self.assertEqual(
            [e.name for e in brief.recent_decisions],
            ["0002-new", "0001-old"],
        )
        # Phase artefacts include every entity tagged with "build".
        names = {e.name for e in brief.phase_artefacts}
        self.assertIn("core", names)
        self.assertIn("T-100", names)
        self.assertIn("0002-new", names)
        # Latest verification / handoff resolved.
        assert brief.latest_verification is not None
        self.assertEqual(brief.latest_verification.name, "VER-ABC")
        assert brief.latest_handoff is not None
        self.assertEqual(brief.latest_handoff.name, "HO-9XYZ")

    def test_recent_decisions_limit_caps_list(self) -> None:
        s = self.fixture.store
        # Add 8 more decisions; the brief should still cap at the limit.
        for i in range(8):
            s.upsert_entity("decision", f"00{i + 10}-extra")
        brief = build_session_brief(self.fixture.store, "build", recent_decisions_limit=3)
        self.assertEqual(len(brief.recent_decisions), 3)

    def test_top_k_seeded_with_phase_tag(self) -> None:
        """top_k pulled from the retriever using current_phase as the
        single seed tag — entities tagged "build" appear ranked."""
        brief = build_session_brief(self.fixture.store, "build")
        names = [r.entity.name for r in brief.top_k]
        # Three "build"-tagged entities present (module, task, decision)
        # plus their 1-hop neighbours (none in this fixture).
        for required in {"core", "T-100", "0002-new"}:
            self.assertIn(required, names)

    def test_no_phase_means_no_phase_artefacts_or_top_k(self) -> None:
        brief = build_session_brief(self.fixture.store, "")
        self.assertEqual(brief.phase_artefacts, ())
        self.assertEqual(brief.top_k, ())
        # Other sections still populate (decisions, verification, handoff).
        self.assertTrue(brief.recent_decisions)
        self.assertIsNotNone(brief.latest_verification)


class SessionBriefSerialisationTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        with GraphStore.open_in_memory() as store:
            store.upsert_entity("decision", "0001")
            brief = build_session_brief(store, "intent")
        payload = brief.to_dict()
        for key in {
            "current_phase",
            "recent_decisions",
            "phase_artefacts",
            "latest_verification",
            "latest_handoff",
            "top_k",
        }:
            self.assertIn(key, payload)
        self.assertEqual(payload["current_phase"], "intent")
        self.assertEqual(len(payload["recent_decisions"]), 1)

    def test_default_recent_decisions_limit_is_five(self) -> None:
        self.assertEqual(DEFAULT_RECENT_DECISIONS, 5)


class RenderBriefTextTests(unittest.TestCase):
    def test_empty_brief_renders_scan_hint(self) -> None:
        brief = SessionBrief(current_phase="build")
        rendered = render_brief_text(brief)
        self.assertIn("graph is empty", rendered)

    def test_populated_brief_renders_each_section(self) -> None:
        fixture = _FixtureStore()
        try:
            brief = build_session_brief(fixture.store, "build")
            rendered = render_brief_text(brief)
        finally:
            fixture.close()
        self.assertIn("Recent decisions", rendered)
        self.assertIn("0002-new", rendered)
        self.assertIn("Phase artefacts", rendered)
        self.assertIn("Latest verification", rendered)
        self.assertIn("Latest handoff", rendered)


if __name__ == "__main__":
    unittest.main()
