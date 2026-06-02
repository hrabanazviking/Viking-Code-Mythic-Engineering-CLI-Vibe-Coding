"""Tests for the Reforge Phase 6 private knowledge reader."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.knowledge.reader import (
    knowledge_status,
    render_search,
    search_knowledge,
)


def _seed_knowledge_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE notes (
                title TEXT,
                body TEXT,
                source TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO notes(title, body, source) VALUES (?, ?, ?)",
            (
                "Hermes recall",
                "Earlier ideas connected Hermes agent memory to durable session summaries.",
                "private-notes",
            ),
        )
        conn.execute(
            "INSERT INTO notes(title, body, source) VALUES (?, ?, ?)",
            ("Other note", "Unrelated provider routing thought.", "private-notes"),
        )


def _write_config(root: Path, db_path: Path) -> None:
    (root / ".mythic-vibe.json").write_text(
        json.dumps(
            {
                "knowledge": {
                    "sources": [
                        {
                            "name": "private-notes",
                            "type": "sqlite",
                            "path": str(db_path),
                            "host": "tailscale-host",
                            "table": "notes",
                            "title_column": "title",
                            "body_column": "body",
                            "source_column": "source",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )


class KnowledgeReaderTests(unittest.TestCase):
    def test_status_reports_no_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            statuses = knowledge_status(Path(tmp))
        self.assertEqual(len(statuses), 1)
        self.assertFalse(statuses[0].configured)
        self.assertIn("No knowledge sources", statuses[0].details[0])

    def test_sqlite_source_searches_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "knowledge.sqlite"
            _seed_knowledge_db(db_path)
            _write_config(root, db_path)

            status = knowledge_status(root)[0]
            result = search_knowledge(root, "Hermes memory", limit=3)

        self.assertTrue(status.configured)
        self.assertTrue(status.searchable)
        self.assertEqual(result.results[0].title, "Hermes recall")
        self.assertIn("durable session summaries", result.results[0].snippet)
        self.assertEqual(result.results[0].source_ref, "private-notes")

    def test_search_without_configured_table_discovers_text_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "knowledge.sqlite"
            _seed_knowledge_db(db_path)
            (root / ".mythic-vibe.json").write_text(
                json.dumps({"knowledge": {"sources": [{"name": "auto", "type": "sqlite", "path": str(db_path)}]}}),
                encoding="utf-8",
            )

            result = search_knowledge(root, "session summaries", limit=2)

        self.assertEqual(len(result.results), 1)
        self.assertEqual(result.results[0].table, "notes")

    def test_postgres_source_is_reported_not_searched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".mythic-vibe.json").write_text(
                json.dumps({"knowledge": {"sources": [{"name": "pg", "type": "postgres", "host": "tailnet-db"}]}}),
                encoding="utf-8",
            )
            status = knowledge_status(root)[0]
            result = search_knowledge(root, "Hermes", limit=2)

        self.assertTrue(status.configured)
        self.assertFalse(status.searchable)
        self.assertEqual(result.results, ())

    def test_render_search_includes_source_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "knowledge.sqlite"
            _seed_knowledge_db(db_path)
            _write_config(root, db_path)
            rendered = render_search(search_knowledge(root, "Hermes", limit=1))

        self.assertIn("Knowledge search: Hermes", rendered)
        self.assertIn("private-notes/notes", rendered)


if __name__ == "__main__":
    unittest.main()
