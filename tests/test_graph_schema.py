"""Tests for the knowledge-graph schema + migration runner (PH-05 slice 5.1)."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.context.schema import (
    CURRENT_SCHEMA_VERSION,
    EDGE_KINDS,
    ENTITY_KINDS,
    MIGRATIONS,
    SCHEMA_V1_SQL,
    apply_migrations,
    get_current_version,
)


class SchemaConstantsTests(unittest.TestCase):
    def test_current_version_is_one(self) -> None:
        self.assertEqual(CURRENT_SCHEMA_VERSION, 1)

    def test_migrations_are_sorted_and_match_current(self) -> None:
        versions = [target for target, _ in MIGRATIONS]
        self.assertEqual(versions, sorted(versions))
        self.assertEqual(versions[-1], CURRENT_SCHEMA_VERSION)

    def test_entity_and_edge_kinds_disjoint(self) -> None:
        self.assertEqual(set(ENTITY_KINDS) & set(EDGE_KINDS), set())

    def test_schema_includes_required_tables(self) -> None:
        for table in ("schema_version", "entities", "edges", "entity_tags"):
            self.assertIn(table, SCHEMA_V1_SQL)


class ApplyMigrationsTests(unittest.TestCase):
    def _open_fresh(self) -> sqlite3.Connection:
        return sqlite3.connect(":memory:")

    def test_apply_to_empty_db_creates_schema_at_v1(self) -> None:
        conn = self._open_fresh()
        try:
            self.assertEqual(get_current_version(conn), 0)
            applied = apply_migrations(conn)
            self.assertEqual(applied, CURRENT_SCHEMA_VERSION)
            self.assertEqual(get_current_version(conn), CURRENT_SCHEMA_VERSION)
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            for required in {"schema_version", "entities", "edges", "entity_tags"}:
                self.assertIn(required, tables)
        finally:
            conn.close()

    def test_idempotent_re_apply_does_not_duplicate_version_rows(self) -> None:
        conn = self._open_fresh()
        try:
            apply_migrations(conn)
            apply_migrations(conn)
            apply_migrations(conn)
            row_count = conn.execute(
                "SELECT COUNT(*) FROM schema_version"
            ).fetchone()[0]
            self.assertEqual(row_count, 1)
        finally:
            conn.close()

    def test_foreign_keys_enforced_after_apply(self) -> None:
        conn = self._open_fresh()
        try:
            apply_migrations(conn)
            # Insert a phantom edge with a non-existent src — should
            # fail thanks to the FK pragma being on.
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO edges(src_id, dst_id, kind, created_at) "
                    "VALUES (999, 1000, 'contains', '2026-01-01T00:00:00Z')"
                )
        finally:
            conn.close()

    def test_unique_constraint_on_entities(self) -> None:
        conn = self._open_fresh()
        try:
            apply_migrations(conn)
            conn.execute(
                "INSERT INTO entities(kind, name, created_at, updated_at) "
                "VALUES ('module', 'mythic_vibe_cli.app', "
                "'2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
            )
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO entities(kind, name, created_at, updated_at) "
                    "VALUES ('module', 'mythic_vibe_cli.app', "
                    "'2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
                )
        finally:
            conn.close()

    def test_persists_across_connections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "graph.sqlite3"
            conn1 = sqlite3.connect(str(db_path))
            try:
                apply_migrations(conn1)
            finally:
                conn1.close()

            conn2 = sqlite3.connect(str(db_path))
            try:
                self.assertEqual(get_current_version(conn2), CURRENT_SCHEMA_VERSION)
            finally:
                conn2.close()


if __name__ == "__main__":
    unittest.main()
