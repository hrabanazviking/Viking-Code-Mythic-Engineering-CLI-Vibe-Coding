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
    EventStreamSnapshot,
    EventTailReader,
    append_event,
    event_log_path_for,
    read_recent,
    resolve_max_entries,
    write_entries,
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


class EventTailReaderTests(unittest.TestCase):
    def test_missing_file_yields_empty_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            reader = EventTailReader(path, window=5)
            snapshot = reader.poll()

        self.assertIsInstance(snapshot, EventStreamSnapshot)
        self.assertEqual(snapshot.entries, ())
        self.assertEqual(snapshot.new_in_last_poll, 0)
        self.assertEqual(snapshot.total_seen, 0)

    def test_warm_start_seeds_buffer_without_counting_new(self) -> None:
        """Existing entries on disk populate the buffer immediately,
        but the first poll reports 0 new (the operator opened the TUI
        mid-stream — those entries already happened)."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            append_event(path, "before_scan", {"path": "/x"})
            append_event(path, "after_scan", {"path": "/x"})

            reader = EventTailReader(path, window=5)
            snapshot = reader.poll()

        self.assertEqual(len(snapshot.entries), 2)
        self.assertEqual(snapshot.new_in_last_poll, 0)
        self.assertEqual(snapshot.total_seen, 0)

    def test_no_growth_between_polls_returns_zero_new(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            append_event(path, "before_scan", {"path": "/x"})

            reader = EventTailReader(path, window=5)
            reader.poll()
            second = reader.poll()

        self.assertEqual(second.new_in_last_poll, 0)
        self.assertEqual(second.total_seen, 0)

    def test_appended_event_appears_in_next_poll_with_pulse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            append_event(path, "before_scan", {"path": "/x"})

            reader = EventTailReader(path, window=5)
            reader.poll()  # consume warm start

            append_event(path, "after_scan", {"path": "/x"})
            snapshot = reader.poll()

        self.assertEqual(snapshot.new_in_last_poll, 1)
        self.assertEqual(snapshot.total_seen, 1)
        self.assertEqual(snapshot.entries[-1].channel, "after_scan")

    def test_multiple_appends_between_polls_collapse_into_one_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            reader = EventTailReader(path, window=10)
            reader.poll()  # file doesn't exist yet

            append_event(path, "before_scan", {"path": "/x"})
            append_event(path, "after_scan", {"path": "/x"})
            append_event(path, "before_verify", {"verification_id": "v1"})
            snapshot = reader.poll()

        self.assertEqual(snapshot.new_in_last_poll, 3)
        self.assertEqual(snapshot.total_seen, 3)
        self.assertEqual(
            [e.channel for e in snapshot.entries],
            ["before_scan", "after_scan", "before_verify"],
        )

    def test_window_trims_buffer_to_configured_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            reader = EventTailReader(path, window=3)
            reader.poll()
            for i in range(5):
                append_event(path, f"step_{i}", {"path": f"/p{i}"})
            snapshot = reader.poll()

        self.assertEqual(len(snapshot.entries), 3)
        self.assertEqual(snapshot.new_in_last_poll, 5)
        self.assertEqual(snapshot.total_seen, 5)
        self.assertEqual(
            [e.channel for e in snapshot.entries],
            ["step_2", "step_3", "step_4"],
        )

    def test_file_rotation_resets_without_counting_new(self) -> None:
        """If the log shrinks (rewritten by the bounded-rotation logic
        in append_event, or any external truncation), the reader
        re-seeds without flagging the surviving entries as 'new'."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            for i in range(4):
                append_event(path, f"step_{i}", {"path": f"/p{i}"})

            reader = EventTailReader(path, window=10)
            reader.poll()  # consume warm start

            # Rewrite (simulates rotation) — fewer bytes than before.
            write_entries(
                path,
                [EventLogEntry(timestamp="2026-04-29T00:00:00Z", channel="reset", summary="")],
            )
            snapshot = reader.poll()

        self.assertEqual(snapshot.new_in_last_poll, 0)
        self.assertEqual(snapshot.total_seen, 0)
        self.assertEqual(len(snapshot.entries), 1)
        self.assertEqual(snapshot.entries[0].channel, "reset")

    def test_malformed_lines_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            # Hand-craft a file with one valid line, one garbage, one valid.
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as fh:
                fh.write(json.dumps({"timestamp": "t1", "channel": "ok", "summary": "a"}) + "\n")
                fh.write("not-json-at-all\n")
                fh.write(json.dumps({"timestamp": "t2", "channel": "ok2", "summary": "b"}) + "\n")

            reader = EventTailReader(path, window=10)
            warm = reader.poll()

        self.assertEqual([e.channel for e in warm.entries], ["ok", "ok2"])

    def test_snapshot_to_dict_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            reader = EventTailReader(path, window=5)
            reader.poll()
            append_event(path, "before_scan", {"path": "/x"})
            payload = reader.poll().to_dict()

        for key in {"entries", "new_in_last_poll", "total_seen"}:
            self.assertIn(key, payload)
        self.assertEqual(payload["new_in_last_poll"], 1)
        self.assertEqual(payload["entries"][0]["channel"], "before_scan")


if __name__ == "__main__":
    unittest.main()
