"""Tests for the bounded JSONL event log primitive."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import os

from mythic_vibe_cli.runtime.event_log import (
    DEFAULT_MAX_ENTRIES,
    EVENT_LOG_LIMIT_ENV,
    EventLogEntry,
    append_event,
    event_log_path_for,
    read_recent,
    resolve_max_entries,
)


class EventLogTests(unittest.TestCase):
    def test_append_creates_jsonl_file_with_one_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            entry = append_event(path, "before_scan", {"path": "/some/project"})

            self.assertIsInstance(entry, EventLogEntry)
            self.assertEqual(entry.channel, "before_scan")
            self.assertIn("path=/some/project", entry.summary)

            self.assertTrue(path.exists())
            with path.open("r", encoding="utf-8") as fh:
                payload = json.loads(fh.readline())
            self.assertEqual(payload["channel"], "before_scan")
            self.assertEqual(payload["summary"], "path=/some/project")

    def test_append_summary_falls_back_to_first_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            entry = append_event(path, "after_packet", {"unrelated": "value"})
            self.assertEqual(entry.summary, "unrelated=value")

    def test_append_handles_non_dict_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            entry = append_event(path, "before_scan", "scalar payload")
            self.assertEqual(entry.summary, "scalar payload")

    def test_read_recent_returns_newest_last(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            for i in range(5):
                append_event(path, "before_scan", {"path": f"/p{i}"})
            entries = read_recent(path, limit=3)

            self.assertEqual(len(entries), 3)
            self.assertEqual(entries[-1].summary, "path=/p4")
            self.assertEqual(entries[0].summary, "path=/p2")

    def test_read_recent_returns_empty_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(read_recent(Path(tmp) / "nope.jsonl"), [])

    def test_read_recent_skips_invalid_json_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(
                "not-json\n"
                + json.dumps({"timestamp": "t", "channel": "c", "summary": "s"})
                + "\n",
                encoding="utf-8",
            )
            entries = read_recent(path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].channel, "c")

    def test_rotation_caps_total_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            for i in range(DEFAULT_MAX_ENTRIES + 25):
                append_event(path, "before_scan", {"path": f"/p{i:04d}"})

            with path.open("r", encoding="utf-8") as fh:
                lines = [line for line in fh if line.strip()]
            self.assertEqual(len(lines), DEFAULT_MAX_ENTRIES)

            entries = read_recent(path, limit=DEFAULT_MAX_ENTRIES)
            self.assertEqual(len(entries), DEFAULT_MAX_ENTRIES)
            self.assertEqual(entries[-1].summary, f"path=/p{DEFAULT_MAX_ENTRIES + 24:04d}")

    def test_rotation_with_custom_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            for i in range(20):
                append_event(path, "before_scan", {"path": f"/p{i:04d}"}, max_entries=10)

            with path.open("r", encoding="utf-8") as fh:
                lines = [line for line in fh if line.strip()]
            self.assertLessEqual(len(lines), 10)

    def test_event_log_path_for_returns_expected_location(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = event_log_path_for(Path(tmp))
            self.assertEqual(path, Path(tmp) / "mythic" / "events.jsonl")

    def test_resolve_max_entries_default_when_env_unset(self) -> None:
        previous = os.environ.pop(EVENT_LOG_LIMIT_ENV, None)
        try:
            self.assertEqual(resolve_max_entries(), DEFAULT_MAX_ENTRIES)
        finally:
            if previous is not None:
                os.environ[EVENT_LOG_LIMIT_ENV] = previous

    def test_resolve_max_entries_honors_positive_env_override(self) -> None:
        previous = os.environ.get(EVENT_LOG_LIMIT_ENV)
        os.environ[EVENT_LOG_LIMIT_ENV] = "42"
        try:
            self.assertEqual(resolve_max_entries(), 42)
        finally:
            if previous is None:
                os.environ.pop(EVENT_LOG_LIMIT_ENV, None)
            else:
                os.environ[EVENT_LOG_LIMIT_ENV] = previous

    def test_resolve_max_entries_ignores_invalid_values(self) -> None:
        previous = os.environ.get(EVENT_LOG_LIMIT_ENV)
        try:
            for bogus in ("not-a-number", "", "0", "-5"):
                os.environ[EVENT_LOG_LIMIT_ENV] = bogus
                self.assertEqual(resolve_max_entries(), DEFAULT_MAX_ENTRIES)
        finally:
            if previous is None:
                os.environ.pop(EVENT_LOG_LIMIT_ENV, None)
            else:
                os.environ[EVENT_LOG_LIMIT_ENV] = previous


if __name__ == "__main__":
    unittest.main()
