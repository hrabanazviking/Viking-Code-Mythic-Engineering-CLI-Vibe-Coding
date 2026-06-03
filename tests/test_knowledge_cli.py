"""Tests for `mythic-vibe knowledge` commands."""

from __future__ import annotations

import argparse
import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mythic_vibe_cli.app import build_parser
from mythic_vibe_cli.commands import COMMAND_HANDLERS
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.runtime.slash_commands import BUILTIN_SLASH_COMMANDS


def _seed(root: Path) -> None:
    db_path = root / "private.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE notes(title TEXT, body TEXT, source TEXT)")
        conn.execute(
            "INSERT INTO notes(title, body, source) VALUES (?, ?, ?)",
            (
                "Hermes memory",
                "Earlier Hermes memory ideas used private coding notes.",
                "tailnet",
            ),
        )
    (root / ".mythic-vibe.json").write_text(
        json.dumps(
            {
                "knowledge": {
                    "sources": [
                        {
                            "name": "tailnet-notes",
                            "type": "sqlite",
                            "path": str(db_path),
                            "table": "notes",
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )


class KnowledgeArgparseTests(unittest.TestCase):
    def test_subcommands_parse(self) -> None:
        parser = build_parser()
        status = parser.parse_args(["knowledge", "status"])
        sources = parser.parse_args(["knowledge", "sources"])
        search = parser.parse_args(["knowledge", "search", "Hermes", "memory", "--limit", "3"])
        self.assertEqual(status.knowledge_command, "status")
        self.assertEqual(sources.knowledge_command, "sources")
        self.assertEqual(search.knowledge_command, "search")
        self.assertEqual(search.query, ["Hermes", "memory"])
        self.assertEqual(search.limit, 3)


class KnowledgeDispatchTests(unittest.TestCase):
    def test_handler_registered(self) -> None:
        from mythic_vibe_cli.commands import cmd_knowledge_dispatch

        self.assertIs(COMMAND_HANDLERS["knowledge"], cmd_knowledge_dispatch)

    def test_unknown_subcommand_returns_user_input_error(self) -> None:
        from mythic_vibe_cli.commands import cmd_knowledge_dispatch

        ns = argparse.Namespace(knowledge_command="bogus")
        self.assertEqual(cmd_knowledge_dispatch(ns), USER_INPUT_ERROR)

    def test_status_json_reports_configured_source(self) -> None:
        from mythic_vibe_cli.commands import cmd_knowledge_status

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed(root)
            ns = argparse.Namespace(path=str(root), json=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_knowledge_status(ns)
            payload = json.loads(buf.getvalue())

        self.assertEqual(exit_code, SUCCESS)
        self.assertEqual(payload["command"], "knowledge status")
        self.assertTrue(payload["sources"][0]["searchable"])

    def test_sources_text_lists_source(self) -> None:
        from mythic_vibe_cli.commands import cmd_knowledge_sources

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed(root)
            ns = argparse.Namespace(path=str(root), json=False)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_knowledge_sources(ns)
            rendered = buf.getvalue()

        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("tailnet-notes", rendered)

    def test_search_text_returns_summary(self) -> None:
        from mythic_vibe_cli.commands import cmd_knowledge_search

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed(root)
            ns = argparse.Namespace(
                path=str(root),
                query=["Hermes", "memory"],
                limit=5,
                json=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_knowledge_search(ns)
            rendered = buf.getvalue()

        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("Knowledge search: Hermes memory", rendered)
        self.assertIn("Earlier Hermes memory ideas", rendered)

    def test_search_empty_query_returns_user_input_error(self) -> None:
        from mythic_vibe_cli.commands import cmd_knowledge_search

        ns = argparse.Namespace(path=".", query=[], limit=5, json=False)
        self.assertEqual(cmd_knowledge_search(ns), USER_INPUT_ERROR)


class KnowledgeSlashCatalogTests(unittest.TestCase):
    def test_slash_catalog_contains_knowledge(self) -> None:
        names = {entry.name for entry in BUILTIN_SLASH_COMMANDS}
        self.assertIn("knowledge", names)


if __name__ == "__main__":
    unittest.main()
