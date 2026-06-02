"""Tests for the Reforge Phase 5 SQLite memory spine."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.memory.spine import (
    build_memory_snapshot,
    list_memory,
    memory_db_path,
    record_memory,
    record_session_summary,
    record_shell_exchange,
    render_last_time,
)


class MemorySpineStorageTests(unittest.TestCase):
    def test_record_memory_creates_sqlite_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = record_memory(
                root,
                "task",
                "Wire the memory spine",
                source="test",
                metadata={"phase": 5},
            )
            entries = list_memory(root)

        self.assertEqual(entry.kind, "task")
        self.assertEqual(entry.content, "Wire the memory spine")
        self.assertEqual(entry.metadata["phase"], 5)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].content, "Wire the memory spine")
        self.assertTrue(memory_db_path(root).name.endswith("memory.sqlite"))

    def test_session_summary_records_structured_facets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record_session_summary(
                root,
                summary="Built Phase 5 memory.",
                decisions=["Use SQLite first."],
                tasks=["Add memory last."],
                files_touched=["mythic_vibe_cli/memory/spine.py"],
                failed_attempts=["Initial docs said context engineering."],
                successful_fixes=["Corrected Phase 5 target."],
                next_steps=["Begin Phase 6."],
                source="test",
            )
            snapshot = build_memory_snapshot(root)

        self.assertEqual(snapshot.counts["session_summary"], 1)
        self.assertEqual(snapshot.counts["project_decision"], 1)
        self.assertEqual(snapshot.counts["task"], 1)
        self.assertEqual(snapshot.counts["file_touched"], 1)
        self.assertEqual(snapshot.counts["failed_attempt"], 1)
        self.assertEqual(snapshot.counts["successful_fix"], 1)
        self.assertEqual(snapshot.counts["next_step"], 1)

    def test_shell_exchange_is_resume_renderable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record_shell_exchange(
                root,
                prompt="What are we building?",
                response="A durable memory spine.",
                provider="copy-paste",
                model="manual",
            )
            rendered = render_last_time(root)

        self.assertIn("Last remembered work", rendered)
        self.assertIn("What are we building?", rendered)
        self.assertIn("A durable memory spine.", rendered)

    def test_empty_spine_has_clear_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rendered = render_last_time(Path(tmp))
        self.assertIn("No recorded session memory yet", rendered)


if __name__ == "__main__":
    unittest.main()
