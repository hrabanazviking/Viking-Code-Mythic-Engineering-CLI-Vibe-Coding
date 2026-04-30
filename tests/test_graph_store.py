"""Tests for GraphStore (PH-05 slice 5.2)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.context.graph import (
    Edge,
    Entity,
    GraphStore,
    graph_path_for,
)


# ---- Path + lifecycle -------------------------------------------------


class GraphPathTests(unittest.TestCase):
    def test_path_under_mythic_subdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                graph_path_for(Path(tmp)),
                Path(tmp) / "mythic" / "graph.sqlite3",
            )

    def test_open_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with GraphStore.open(Path(tmp)) as store:
                self.assertTrue(graph_path_for(Path(tmp)).is_file())
                self.assertEqual(store.entity_count(), 0)


# ---- Entity upsert / find ---------------------------------------------


class EntityUpsertTests(unittest.TestCase):
    def test_insert_returns_typed_entity(self) -> None:
        with GraphStore.open_in_memory() as store:
            entity = store.upsert_entity(
                "module",
                "mythic_vibe_cli.app",
                path="mythic_vibe_cli/app.py",
                metadata={"loc": 1100},
            )
        self.assertIsInstance(entity, Entity)
        self.assertEqual(entity.kind, "module")
        self.assertEqual(entity.name, "mythic_vibe_cli.app")
        self.assertEqual(entity.path, "mythic_vibe_cli/app.py")
        self.assertEqual(entity.metadata, {"loc": 1100})
        self.assertTrue(entity.created_at)
        self.assertTrue(entity.updated_at)

    def test_re_upsert_updates_metadata_and_bumps_updated_at(self) -> None:
        with GraphStore.open_in_memory() as store:
            first = store.upsert_entity("module", "x", metadata={"loc": 10})
            second = store.upsert_entity("module", "x", metadata={"loc": 20})
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.metadata, {"loc": 20})
        # created_at preserved; updated_at may equal created_at if the
        # upserts happened in the same second — assert >= rather than >.
        self.assertGreaterEqual(second.updated_at, first.created_at)

    def test_find_entity_returns_none_for_missing(self) -> None:
        with GraphStore.open_in_memory() as store:
            self.assertIsNone(store.find_entity("module", "nope"))

    def test_find_entities_filters_by_kind(self) -> None:
        with GraphStore.open_in_memory() as store:
            store.upsert_entity("module", "a")
            store.upsert_entity("module", "b")
            store.upsert_entity("decision", "0001-foo")
            modules = store.find_entities(kind="module")
        self.assertEqual([e.name for e in modules], ["a", "b"])

    def test_find_entities_substring_match(self) -> None:
        with GraphStore.open_in_memory() as store:
            store.upsert_entity("module", "alpha", path="src/alpha.py")
            store.upsert_entity("module", "beta", path="src/beta.py")
            store.upsert_entity("module", "gamma", path="other/gamma.py")
            results = store.find_entities(name_like="alph")
            paths = store.find_entities(path_like="src/")
        self.assertEqual([e.name for e in results], ["alpha"])
        self.assertEqual([e.name for e in paths], ["alpha", "beta"])


# ---- Edges -------------------------------------------------------------


class EdgeUpsertTests(unittest.TestCase):
    def test_upsert_edge_links_two_entities(self) -> None:
        with GraphStore.open_in_memory() as store:
            mod = store.upsert_entity("module", "mod_x")
            fn = store.upsert_entity("function", "fn_x")
            edge = store.upsert_edge(mod.id, fn.id, "contains")
        self.assertIsInstance(edge, Edge)
        self.assertEqual(edge.src_id, mod.id)
        self.assertEqual(edge.dst_id, fn.id)
        self.assertEqual(edge.kind, "contains")

    def test_re_upsert_edge_is_idempotent(self) -> None:
        with GraphStore.open_in_memory() as store:
            a = store.upsert_entity("module", "a")
            b = store.upsert_entity("module", "b")
            store.upsert_edge(a.id, b.id, "references", metadata={"hits": 1})
            store.upsert_edge(a.id, b.id, "references", metadata={"hits": 5})
            self.assertEqual(store.edge_count(), 1)
            edges = store.find_edges(kind="references")
            self.assertEqual(edges[0].metadata, {"hits": 5})

    def test_find_edges_filters(self) -> None:
        with GraphStore.open_in_memory() as store:
            a = store.upsert_entity("module", "a")
            b = store.upsert_entity("module", "b")
            c = store.upsert_entity("module", "c")
            store.upsert_edge(a.id, b.id, "references")
            store.upsert_edge(b.id, c.id, "references")
            store.upsert_edge(a.id, c.id, "mentions")
            self.assertEqual(len(store.find_edges()), 3)
            self.assertEqual(len(store.find_edges(kind="references")), 2)
            self.assertEqual(len(store.find_edges(src_id=a.id)), 2)

    def test_neighbours_outgoing(self) -> None:
        with GraphStore.open_in_memory() as store:
            mod = store.upsert_entity("module", "m")
            fn1 = store.upsert_entity("function", "f1")
            fn2 = store.upsert_entity("function", "f2")
            store.upsert_edge(mod.id, fn1.id, "contains")
            store.upsert_edge(mod.id, fn2.id, "contains")
            out = store.entity_neighbours(mod.id, direction="out")
        self.assertEqual({e.name for e in out}, {"f1", "f2"})

    def test_neighbours_kind_filter(self) -> None:
        with GraphStore.open_in_memory() as store:
            mod = store.upsert_entity("module", "m")
            fn = store.upsert_entity("function", "f")
            doc = store.upsert_entity("document", "d")
            store.upsert_edge(mod.id, fn.id, "contains")
            store.upsert_edge(mod.id, doc.id, "mentions")
            contains = store.entity_neighbours(mod.id, kind="contains", direction="out")
        self.assertEqual([e.name for e in contains], ["f"])

    def test_neighbours_invalid_direction_raises(self) -> None:
        with GraphStore.open_in_memory() as store:
            mod = store.upsert_entity("module", "m")
            with self.assertRaises(ValueError):
                store.entity_neighbours(mod.id, direction="sideways")

    def test_cascade_delete_removes_edges(self) -> None:
        """Schema declares ON DELETE CASCADE on edges.src_id /
        edges.dst_id; deleting an entity should orphan no edge rows
        (matters for slice 5.7 packet builder when re-scanning)."""
        with GraphStore.open_in_memory() as store:
            a = store.upsert_entity("module", "a")
            b = store.upsert_entity("module", "b")
            store.upsert_edge(a.id, b.id, "references")
            store._conn.execute("DELETE FROM entities WHERE id=?", (a.id,))
            store._conn.commit()
            self.assertEqual(store.edge_count(), 0)


# ---- Tags --------------------------------------------------------------


class TagTests(unittest.TestCase):
    def test_add_tag_round_trip(self) -> None:
        with GraphStore.open_in_memory() as store:
            ent = store.upsert_entity("module", "x")
            store.add_tag(ent.id, "cli", weight=2.0)
            store.add_tag(ent.id, "core", weight=0.5)
            tags = store.tags_for(ent.id)
        self.assertEqual(tags, [("cli", 2.0), ("core", 0.5)])

    def test_re_tag_updates_weight(self) -> None:
        with GraphStore.open_in_memory() as store:
            ent = store.upsert_entity("module", "x")
            store.add_tag(ent.id, "cli", weight=1.0)
            store.add_tag(ent.id, "cli", weight=3.0)
            tags = store.tags_for(ent.id)
        self.assertEqual(tags, [("cli", 3.0)])

    def test_entities_with_tags_returns_summed_weight(self) -> None:
        with GraphStore.open_in_memory() as store:
            a = store.upsert_entity("module", "a")
            b = store.upsert_entity("module", "b")
            store.add_tag(a.id, "cli", weight=1.0)
            store.add_tag(a.id, "core", weight=0.5)
            store.add_tag(b.id, "cli", weight=0.5)
            results = store.entities_with_tags(["cli", "core"])
        names = [(e.name, score) for e, score in results]
        self.assertEqual(names, [("a", 1.5), ("b", 0.5)])

    def test_entities_with_no_tags_returns_empty(self) -> None:
        with GraphStore.open_in_memory() as store:
            self.assertEqual(store.entities_with_tags([]), [])
            self.assertEqual(store.entities_with_tags([""]), [])


# ---- Persistence + introspection --------------------------------------


class PersistenceTests(unittest.TestCase):
    def test_writes_persist_to_disk_across_open_close(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with GraphStore.open(root) as store:
                store.upsert_entity("module", "persist_me", metadata={"k": 1})
                store.add_tag(
                    store.find_entity("module", "persist_me").id, "kept"
                )
            # Re-open and verify both the entity and its tag survived.
            with GraphStore.open(root) as store:
                ent = store.find_entity("module", "persist_me")
                self.assertIsNotNone(ent)
                assert ent is not None  # for type-narrowing
                self.assertEqual(ent.metadata, {"k": 1})
                self.assertEqual(store.tags_for(ent.id), [("kept", 1.0)])

    def test_close_is_idempotent(self) -> None:
        store = GraphStore.open_in_memory()
        store.close()
        store.close()  # must not raise

    def test_count_methods(self) -> None:
        with GraphStore.open_in_memory() as store:
            self.assertEqual(store.entity_count(), 0)
            self.assertEqual(store.edge_count(), 0)
            a = store.upsert_entity("module", "a")
            b = store.upsert_entity("module", "b")
            store.upsert_edge(a.id, b.id, "references")
            self.assertEqual(store.entity_count(), 2)
            self.assertEqual(store.edge_count(), 1)


# ---- Serialisation -----------------------------------------------------


class SerialisationTests(unittest.TestCase):
    def test_entity_to_dict_round_trip(self) -> None:
        with GraphStore.open_in_memory() as store:
            ent = store.upsert_entity(
                "decision",
                "0001-foo",
                path="docs/decisions/0001-foo.md",
                metadata={"status": "accepted"},
            )
            payload = ent.to_dict()
        for key in {"id", "kind", "name", "path", "metadata", "created_at", "updated_at"}:
            self.assertIn(key, payload)
        self.assertEqual(payload["metadata"], {"status": "accepted"})

    def test_edge_to_dict_round_trip(self) -> None:
        with GraphStore.open_in_memory() as store:
            a = store.upsert_entity("module", "a")
            b = store.upsert_entity("module", "b")
            edge = store.upsert_edge(a.id, b.id, "references", metadata={"hits": 7})
            payload = edge.to_dict()
        self.assertEqual(payload["src_id"], a.id)
        self.assertEqual(payload["dst_id"], b.id)
        self.assertEqual(payload["kind"], "references")
        self.assertEqual(payload["metadata"], {"hits": 7})

    def test_corrupt_metadata_is_quarantined_to_empty_dict(self) -> None:
        """Hand-roll an entity row with non-JSON metadata to confirm
        the parser doesn't raise on the read path."""
        with GraphStore.open_in_memory() as store:
            store._conn.execute(
                "INSERT INTO entities(kind, name, path, metadata, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("module", "corrupt", "", "{not-json", "t", "t"),
            )
            store._conn.commit()
            entity = store.find_entity("module", "corrupt")
        self.assertIsNotNone(entity)
        assert entity is not None
        self.assertEqual(entity.metadata, {})


if __name__ == "__main__":
    unittest.main()
