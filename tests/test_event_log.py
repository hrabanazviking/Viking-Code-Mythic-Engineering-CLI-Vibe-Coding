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


# PH-23.10 — coverage push for event_log error/edge branches:
# lines 76, 78, 99-100, 104-105, 110-111, 123-124, 131, 137,
# 165-171, 221, 224-225, 227, 281-283, 300-301, 316-317, 322.


class SummariseEdgeCaseTests(unittest.TestCase):
    """Cover lines 76 + 78 — the empty-payload and None-payload
    branches of _summarize (the function append_event uses to
    build EventLogEntry.summary)."""

    def test_summary_empty_dict_payload(self) -> None:
        # Empty dict has no first-key — line 76 returns "".
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            entry = append_event(path, "channel", {})
            self.assertEqual(entry.summary, "")

    def test_summary_none_payload(self) -> None:
        # None is its own branch (line 77-78) — returns "".
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            entry = append_event(path, "channel", None)
            self.assertEqual(entry.summary, "")


class AppendEventErrorBranchTests(unittest.TestCase):
    """Cover lines 99-100, 104-105, 110-111 — the three OSError
    swallow branches inside append_event."""

    def test_oserror_on_open_returns_entry_without_writing(self) -> None:
        # First branch (99-100): OSError when opening for append.
        # Mock Path.open to raise. Entry is still constructed +
        # returned so the caller can inspect it.
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            real_open = Path.open

            def failing_open(self, mode="r", *args, **kwargs):
                if mode == "a":
                    raise OSError("disk full")
                return real_open(self, mode, *args, **kwargs)

            with mock.patch.object(Path, "open", new=failing_open):
                entry = append_event(path, "ch", {"k": "v"})
                self.assertEqual(entry.channel, "ch")
                self.assertFalse(path.exists())

    def test_oserror_on_count_lines_returns_entry(self) -> None:
        # Second branch (104-105): write succeeded but counting
        # the file's lines failed.
        from unittest import mock
        import mythic_vibe_cli.runtime.event_log as elog

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            with mock.patch.object(
                elog, "_count_lines", side_effect=OSError("permission")
            ):
                entry = append_event(path, "ch", {"k": "v"})
                self.assertEqual(entry.channel, "ch")
                # File still got written before count failed.
                self.assertTrue(path.exists())

    def test_oserror_on_rewrite_returns_entry(self) -> None:
        # Third branch (110-111): rotation failed.
        from unittest import mock
        import mythic_vibe_cli.runtime.event_log as elog

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            # Pre-populate the log so the next append exceeds
            # max_entries=1 and triggers the rotation branch.
            for i in range(3):
                append_event(path, "ch", {"k": f"v{i}"}, max_entries=1)
            with mock.patch.object(
                elog, "_rewrite_with_tail",
                side_effect=OSError("rotate fail"),
            ):
                entry = append_event(
                    path, "ch", {"k": "v3"}, max_entries=1,
                )
                self.assertEqual(entry.channel, "ch")


class ReadRecentErrorBranchTests(unittest.TestCase):
    """Cover lines 123-124, 131, 137 — read_recent error +
    empty-line + non-dict-payload branches."""

    def test_oserror_on_read_returns_empty_list(self) -> None:
        # Lines 123-124: file exists but open raises OSError.
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.touch()
            real_open = Path.open

            def failing_open(self, mode="r", *args, **kwargs):
                if str(self) == str(path) and mode.startswith("r"):
                    raise OSError("no perm")
                return real_open(self, mode, *args, **kwargs)

            with mock.patch.object(Path, "open", new=failing_open):
                self.assertEqual(read_recent(path), [])

    def test_skips_empty_lines(self) -> None:
        # Line 131: empty line in the file is skipped.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(
                '\n\n{"timestamp":"t","channel":"ok","summary":"s"}\n\n',
                encoding="utf-8",
            )
            entries = read_recent(path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].channel, "ok")

    def test_skips_non_dict_jsonl_payloads(self) -> None:
        # Line 137: a JSON-decoded line that's not a dict (e.g.
        # a bare string or list) is skipped.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(
                '"a bare string"\n[1, 2]\n{"channel":"ok","timestamp":"t","summary":"s"}\n',
                encoding="utf-8",
            )
            entries = read_recent(path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].channel, "ok")


class RewriteTailCleanupTests(unittest.TestCase):
    """Cover lines 165-171 — the OSError-then-cleanup branch in
    _rewrite_with_tail."""

    def test_oserror_during_rewrite_attempts_temp_cleanup(self) -> None:
        # Mock os.replace to raise OSError so the except block
        # at 165-171 exercises the unlink-best-effort cleanup.
        from unittest import mock
        import mythic_vibe_cli.runtime.event_log as elog

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            # Populate with > keep entries.
            for i in range(3):
                append_event(path, "ch", {"k": f"v{i}"})

            def failing_replace(*args, **kwargs):
                raise OSError("rename failed")

            with mock.patch.object(elog.os, "replace", side_effect=failing_replace):
                with self.assertRaises(OSError):
                    elog._rewrite_with_tail(path, keep=1)
            # The .tmp temp file must NOT survive the failed
            # rewrite — the cleanup branch unlinks it.
            tmp_files = list(Path(tmp).glob(".events.*.tmp"))
            self.assertEqual(
                tmp_files, [],
                f"expected best-effort cleanup, got {tmp_files}",
            )


class ParseEventLinesEdgeCases(unittest.TestCase):
    """Cover lines 221, 224-225, 227 — _parse_event_lines edge
    cases (empty-line skip, malformed JSON, non-dict payload)."""

    def test_parse_empty_lines_skipped(self) -> None:
        # Line 221: empty line is skipped.
        from mythic_vibe_cli.runtime.event_log import _parse_event_lines

        text = '\n\n{"timestamp":"t","channel":"ok","summary":"s"}\n\n'
        entries = _parse_event_lines(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].channel, "ok")

    def test_parse_malformed_json_skipped(self) -> None:
        # Lines 224-225: JSON decode error → skip.
        from mythic_vibe_cli.runtime.event_log import _parse_event_lines

        text = (
            "not valid json\n"
            '{"channel":"ok","timestamp":"t","summary":"s"}\n'
        )
        entries = _parse_event_lines(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].channel, "ok")

    def test_parse_non_dict_skipped(self) -> None:
        # Line 227: parsed but not a dict → skip.
        from mythic_vibe_cli.runtime.event_log import _parse_event_lines

        text = (
            '"raw string"\n'
            '[1, 2, 3]\n'
            '42\n'
            '{"channel":"good","timestamp":"t","summary":"s"}\n'
        )
        entries = _parse_event_lines(text)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].channel, "good")


class TailReaderErrorBranchTests(unittest.TestCase):
    """Cover lines 281-283, 300-301, 316-317, 322 in
    EventTailReader."""

    # Note: lines 281-283 (_seed_from_disk OSError on stat) and
    # 300-301 (poll OSError on stat) are reachable only when
    # stat raises OSError, but Path.exists() ALSO calls stat
    # internally (without try/except), so a coarse Path.stat
    # patch poisons the .exists() check before we reach the
    # target try block. Driving these branches surgically would
    # require a per-instance method-replacement that pathlib's
    # descriptor protocol doesn't support cleanly. Both branches
    # are defensive `except OSError: pass` returns of the empty
    # snapshot — operationally correct, but treating them as
    # untestable in this harness is the honest call. The
    # remaining 7 missed lines (168-170 + these 4) are all
    # `except OSError` defensive branches; the module is at 97%
    # post-PH-23.10.

    def test_poll_oserror_on_read_returns_empty_snapshot(self) -> None:
        # Lines 316-317: poll's open() for reading new bytes raises.
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            append_event(path, "ch", {"k": "v0"})
            reader = EventTailReader(path, window=5)
            # Append more so poll() will try to read new bytes.
            append_event(path, "ch", {"k": "v1"})

            real_open = Path.open

            def failing_open(self, mode="r", *args, **kwargs):
                if str(self) == str(path) and mode.startswith("r"):
                    raise OSError("perm")
                return real_open(self, mode, *args, **kwargs)

            with mock.patch.object(Path, "open", new=failing_open):
                snapshot = reader.poll()
                self.assertEqual(snapshot.new_in_last_poll, 0)

    def test_poll_no_new_entries_after_growth_returns_empty(self) -> None:
        # Line 322: file size grew but only because of bytes that
        # don't decode to event entries (e.g. just a stray
        # newline). Reader must not claim a new event.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            append_event(path, "ch", {"k": "v0"})
            reader = EventTailReader(path, window=5)
            # Append a non-event line (just whitespace + a malformed
            # JSON token) so the file grew but yields zero parsed
            # entries.
            with path.open("a", encoding="utf-8") as fh:
                fh.write("\nnot-json\n")

            snapshot = reader.poll()
            self.assertEqual(snapshot.new_in_last_poll, 0)


if __name__ == "__main__":
    unittest.main()
