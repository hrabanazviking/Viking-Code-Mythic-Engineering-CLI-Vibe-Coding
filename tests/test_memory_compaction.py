"""Tests for the conversation compaction summariser (PH-15 slice 15.2)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.memory.compaction import (
    DEFAULT_KEEP_RECENT,
    SALIENT_PREFIXES,
    CompactionPayload,
    compact_conversation,
    latest_summary_for,
    summarize_conversation,
)
from mythic_vibe_cli.memory.conversation import (
    ConversationRecord,
    ConversationTurn,
    new_conversation_id,
    record_turn,
)


def _build_record(turns: list[tuple[str, str]]) -> ConversationRecord:
    """Helper that builds an in-memory ConversationRecord from
    (role, content) tuples."""
    return ConversationRecord(
        conversation_id="CV-FAKEID",
        provider="copy-paste",
        model="m1",
        created_at="2026-04-29T00:00:00Z",
        updated_at="2026-04-29T01:00:00Z",
        turns=tuple(
            ConversationTurn(role=role, content=content, timestamp="t")  # type: ignore[arg-type]
            for role, content in turns
        ),
    )


# ---- summarize_conversation -------------------------------------------


class SummarizeConversationTests(unittest.TestCase):
    def test_constants_documented(self) -> None:
        self.assertEqual(DEFAULT_KEEP_RECENT, 3)
        # Sanity: SALIENT_PREFIXES is non-empty and well-formed.
        self.assertTrue(SALIENT_PREFIXES)
        for prefix, heading in SALIENT_PREFIXES:
            self.assertIsInstance(prefix, str)
            self.assertIsInstance(heading, str)

    def test_empty_conversation_renders_placeholder(self) -> None:
        record = _build_record([])
        rendered = summarize_conversation(record)
        self.assertIn("Compacted summary", rendered)
        self.assertIn("no turns yet", rendered)

    def test_recent_turns_appear_verbatim(self) -> None:
        record = _build_record([
            ("user", "old turn 1"),
            ("assistant", "old reply 1"),
            ("user", "old turn 2"),
            ("assistant", "old reply 2"),
            ("user", "recent question"),
            ("assistant", "recent answer"),
        ])
        rendered = summarize_conversation(record, keep_recent=2)
        self.assertIn("recent question", rendered)
        self.assertIn("recent answer", rendered)
        self.assertIn("Recent 2 turn(s)", rendered)
        # The "old" turns roll up into the "Earlier turns" block
        # rather than appearing verbatim under their own heading.
        self.assertIn("Earlier turns (collapsed)", rendered)

    def test_decision_lines_preserved_verbatim(self) -> None:
        record = _build_record([
            ("user", "shall we go with sqlite?"),
            ("assistant", "Decision: SQLite for the graph store.\nRationale: stdlib only."),
            ("user", "any constraints?"),
            ("assistant", "Constraint: no external services.\nRisk: WAL mode on SMB shares."),
            ("user", "recent question"),
            ("assistant", "recent answer"),
        ])
        rendered = summarize_conversation(record, keep_recent=2)
        self.assertIn("## Decisions", rendered)
        self.assertIn("Decision: SQLite for the graph store.", rendered)
        self.assertIn("## Constraints", rendered)
        self.assertIn("Constraint: no external services.", rendered)
        self.assertIn("## Risks", rendered)
        self.assertIn("Risk: WAL mode on SMB shares.", rendered)

    def test_imperative_lines_caught_via_must_should_prefix(self) -> None:
        record = _build_record([
            ("assistant", "Must lint before commit.\nShould add a test."),
            ("user", "ok"),
            ("assistant", "got it"),
            ("user", "anything else?"),
            ("assistant", "no"),
        ])
        rendered = summarize_conversation(record, keep_recent=2)
        self.assertIn("## Imperatives", rendered)
        self.assertIn("Must lint before commit.", rendered)
        self.assertIn("Should add a test.", rendered)

    def test_recent_turns_excluded_from_salient_extraction(self) -> None:
        """A decision in the most-recent kept turn should appear in
        the verbatim Recent section, NOT also under Decisions —
        otherwise the summary would duplicate."""
        record = _build_record([
            ("user", "thoughts?"),
            ("assistant", "Decision: ship it."),
        ])
        rendered = summarize_conversation(record, keep_recent=2)
        # Decision text appears verbatim in the recent block.
        self.assertIn("Decision: ship it.", rendered)
        # ...but no "## Decisions" heading because everything is
        # within the keep-recent window.
        self.assertNotIn("## Decisions", rendered)

    def test_dedup_within_a_heading(self) -> None:
        record = _build_record([
            ("assistant", "Decision: cache it.\nDecision: cache it.\nDecision: also queue it."),
            ("assistant", "filler"),
            ("assistant", "filler"),
            ("assistant", "filler"),
            ("assistant", "filler"),
        ])
        rendered = summarize_conversation(record, keep_recent=1)
        # Only one occurrence of "cache it."
        self.assertEqual(rendered.count("Decision: cache it."), 1)
        self.assertIn("Decision: also queue it.", rendered)

    def test_keep_recent_zero_collapses_everything(self) -> None:
        record = _build_record([
            ("user", "Decision: use SQLite."),
            ("assistant", "ok"),
        ])
        rendered = summarize_conversation(record, keep_recent=0)
        self.assertIn("## Decisions", rendered)
        # No "Recent" section because keep_recent=0.
        self.assertNotIn("## Recent", rendered)


# ---- compact_conversation ---------------------------------------------


class CompactConversationTests(unittest.TestCase):
    def test_missing_conversation_returns_payload_with_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = compact_conversation(Path(tmp), "CV-MISSING")
        self.assertFalse(payload.written)
        self.assertEqual(payload.metadata.get("error"), "conversation not found")

    def test_writes_markdown_and_json_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            record_turn(
                root, cid, "user", "thoughts?", provider="p", model="m"
            )
            record_turn(
                root, cid, "assistant", "Decision: ship it."
            )
            record_turn(
                root, cid, "user", "any constraints?"
            )
            record_turn(
                root,
                cid,
                "assistant",
                "Constraint: keep it backwards-compatible.",
            )
            payload = compact_conversation(root, cid, keep_recent=2)
            md_path = Path(payload.markdown_path)
            json_path = Path(payload.json_path)
            md_text = md_path.read_text(encoding="utf-8")
            json_payload = json.loads(json_path.read_text(encoding="utf-8"))

            self.assertTrue(payload.written)
            self.assertTrue(md_path.is_file())
            self.assertTrue(json_path.is_file())
            self.assertIn("## Decisions", md_text)
            self.assertIn("Decision: ship it.", md_text)
            self.assertEqual(json_payload["conversation_id"], cid)
            self.assertGreaterEqual(json_payload["recent_turns_count"], 2)

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            record_turn(root, cid, "user", "hi", provider="p", model="m")
            payload = compact_conversation(root, cid, dry_run=True)
        self.assertTrue(payload.dry_run)
        self.assertFalse(payload.written)
        self.assertFalse(Path(payload.markdown_path).exists())
        self.assertFalse(Path(payload.json_path).exists())

    def test_compaction_does_not_mutate_original(self) -> None:
        """The original conversation file must remain byte-identical
        after compaction — slice 15.2 is additive-only."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            record_turn(root, cid, "user", "hi", provider="p", model="m")
            from mythic_vibe_cli.memory.conversation import conversation_path_for

            original_bytes = conversation_path_for(root, cid).read_bytes()
            compact_conversation(root, cid)
            after_bytes = conversation_path_for(root, cid).read_bytes()

        self.assertEqual(original_bytes, after_bytes)

    def test_idempotent_re_run(self) -> None:
        """Re-running compaction over a conversation that already has
        a summary writes a fresh summary (idempotent on on-disk
        state; markdown content matches)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            record_turn(root, cid, "user", "hi", provider="p", model="m")
            first = compact_conversation(root, cid)
            md_first = Path(first.markdown_path).read_text(encoding="utf-8")
            second = compact_conversation(root, cid)
            md_second = Path(second.markdown_path).read_text(encoding="utf-8")
        self.assertTrue(first.written)
        self.assertTrue(second.written)
        # Same content (timestamp metadata in JSON sidecar may differ
        # but the markdown body is content-derived).
        self.assertEqual(md_first, md_second)


class LatestSummaryForTests(unittest.TestCase):
    def test_no_summary_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(latest_summary_for(Path(tmp), "CV-NOPE12"), "")

    def test_returns_markdown_after_compaction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            record_turn(root, cid, "user", "hi", provider="p", model="m")
            compact_conversation(root, cid)
            text = latest_summary_for(root, cid)
        self.assertIn("Compacted summary", text)


# ---- CompactionPayload --------------------------------------------------


class CompactionPayloadTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        payload = CompactionPayload(
            conversation_id="CV-X",
            generated_at="t",
            keep_recent=3,
            salient_buckets={"Decisions": ["a"]},
            recent_turns_count=2,
            earlier_turns_count=5,
            markdown_path="/x.md",
            json_path="/x.json",
            written=True,
            dry_run=False,
            summary_markdown="# x",
            metadata={"k": 1},
        )
        d = payload.to_dict()
        self.assertEqual(d["conversation_id"], "CV-X")
        self.assertEqual(d["salient_buckets"], {"Decisions": ["a"]})
        self.assertEqual(d["written"], True)


if __name__ == "__main__":
    unittest.main()
