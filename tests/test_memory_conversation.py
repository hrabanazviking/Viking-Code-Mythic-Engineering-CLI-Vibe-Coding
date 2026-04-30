"""Tests for the conversation log data layer (PH-15 slice 15.1)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.memory.conversation import (
    CONVERSATION_ID_PREFIX,
    ConversationRecord,
    ConversationTurn,
    conversation_path_for,
    latest_conversation,
    list_conversations,
    new_conversation_id,
    read_conversation,
    record_turn,
    render_record_text,
)


class IdAndPathTests(unittest.TestCase):
    def test_new_conversation_id_format(self) -> None:
        cid = new_conversation_id()
        self.assertTrue(cid.startswith(CONVERSATION_ID_PREFIX))
        self.assertEqual(len(cid), len(CONVERSATION_ID_PREFIX) + 6)
        # Hex only.
        self.assertTrue(all(c in "0123456789ABCDEF" for c in cid[len(CONVERSATION_ID_PREFIX):]))

    def test_new_conversation_ids_are_unique(self) -> None:
        ids = {new_conversation_id() for _ in range(50)}
        self.assertEqual(len(ids), 50)

    def test_canonical_path_under_mythic_ai(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = conversation_path_for(Path(tmp), "CV-DEADBE")
        self.assertEqual(
            path,
            Path(tmp) / "mythic" / "ai" / "conversations" / "CV-DEADBE.json",
        )


class RecordTurnTests(unittest.TestCase):
    def test_first_call_creates_record_with_one_turn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            record = record_turn(
                root,
                cid,
                "user",
                "hello",
                provider="copy-paste",
                model="m1",
            )
            on_disk = read_conversation(root, cid)

        self.assertEqual(record.conversation_id, cid)
        self.assertEqual(record.provider, "copy-paste")
        self.assertEqual(record.model, "m1")
        self.assertEqual(record.turn_count, 1)
        self.assertEqual(record.turns[0].content, "hello")
        self.assertEqual(record.turns[0].role, "user")
        self.assertEqual(on_disk.to_dict(), record.to_dict())

    def test_subsequent_calls_append_and_bump_updated_at(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            first = record_turn(root, cid, "user", "hi", provider="p", model="m")
            second = record_turn(root, cid, "assistant", "hello back", model="m")

        self.assertEqual(first.created_at, second.created_at)
        self.assertGreaterEqual(second.updated_at, first.updated_at)
        self.assertEqual(second.turn_count, 2)
        self.assertEqual([t.role for t in second.turns], ["user", "assistant"])
        self.assertEqual(second.turns[1].content, "hello back")
        # provider/model preserved when not overridden.
        self.assertEqual(second.provider, "p")

    def test_unknown_role_falls_back_to_user(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            record = record_turn(root, cid, "wizard", "spell", provider="p", model="m")  # type: ignore[arg-type]
        self.assertEqual(record.turns[0].role, "user")

    def test_metadata_is_per_turn_not_record_level(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            record_turn(root, cid, "user", "hi", provider="p", model="m", metadata={"tokens": 12})
            record = record_turn(root, cid, "assistant", "hello", metadata={"tokens": 28})
        self.assertEqual(record.turns[0].metadata, {"tokens": 12})
        self.assertEqual(record.turns[1].metadata, {"tokens": 28})
        # Record-level metadata stays empty.
        self.assertEqual(record.metadata, {})

    def test_provider_or_model_change_mid_session_updates_record(self) -> None:
        """Multi-provider conversations: passing a non-empty provider
        or model on a later call updates the record's top-level
        fields (callers need this when the model swaps mid-session)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            record_turn(root, cid, "user", "first", provider="copy", model="m1")
            record = record_turn(
                root,
                cid,
                "assistant",
                "switched",
                provider="local",
                model="m2",
            )
        self.assertEqual(record.provider, "local")
        self.assertEqual(record.model, "m2")


class ReadConversationTests(unittest.TestCase):
    def test_missing_file_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(read_conversation(Path(tmp), "CV-NOPE12"))

    def test_corrupt_json_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = "CV-BADBAD"
            path = conversation_path_for(root, cid)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{not-json", encoding="utf-8")
            self.assertIsNone(read_conversation(root, cid))

    def test_non_dict_payload_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = "CV-LISTLI"
            path = conversation_path_for(root, cid)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
            self.assertIsNone(read_conversation(root, cid))

    def test_unknown_role_in_persisted_turn_falls_back_to_user(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = "CV-WEIRDR"
            path = conversation_path_for(root, cid)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "conversation_id": cid,
                        "provider": "p",
                        "model": "m",
                        "created_at": "t",
                        "updated_at": "t",
                        "turns": [
                            {"role": "wizard", "content": "spell", "timestamp": "t"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            record = read_conversation(root, cid)
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.turns[0].role, "user")


class ListConversationsTests(unittest.TestCase):
    def test_empty_dir_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(list_conversations(Path(tmp)), [])

    def test_returns_records_sorted_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid_old = new_conversation_id()
            cid_new = new_conversation_id()
            record_turn(root, cid_old, "user", "old", provider="p", model="m")
            # Force the older record's updated_at to a clearly past value.
            old_path = conversation_path_for(root, cid_old)
            payload = json.loads(old_path.read_text(encoding="utf-8"))
            payload["updated_at"] = "2026-01-01T00:00:00Z"
            old_path.write_text(json.dumps(payload), encoding="utf-8")
            record_turn(root, cid_new, "user", "fresh", provider="p", model="m")
            records = list_conversations(root)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].conversation_id, cid_new)

    def test_malformed_files_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid_ok = new_conversation_id()
            record_turn(root, cid_ok, "user", "hi", provider="p", model="m")
            # Drop a corrupt JSON file alongside.
            bad_path = conversation_path_for(root, "CV-BADCAT")
            bad_path.write_text("{not-json", encoding="utf-8")
            records = list_conversations(root)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].conversation_id, cid_ok)


class LatestConversationTests(unittest.TestCase):
    def test_no_conversations_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(latest_conversation(Path(tmp)))

    def test_returns_newest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid_a = new_conversation_id()
            cid_b = new_conversation_id()
            record_turn(root, cid_a, "user", "first", provider="p", model="m")
            record_turn(root, cid_b, "user", "newer", provider="p", model="m")
            # Force older's updated_at into the past.
            old_path = conversation_path_for(root, cid_a)
            payload = json.loads(old_path.read_text(encoding="utf-8"))
            payload["updated_at"] = "2026-01-01T00:00:00Z"
            old_path.write_text(json.dumps(payload), encoding="utf-8")
            latest = latest_conversation(root)
        assert latest is not None
        self.assertEqual(latest.conversation_id, cid_b)


class SerialisationTests(unittest.TestCase):
    def test_turn_to_dict_round_trip(self) -> None:
        turn = ConversationTurn(
            role="assistant",
            content="hi",
            timestamp="2026-04-29T12:00:00Z",
            metadata={"tokens": 10},
        )
        clone = ConversationTurn.from_dict(turn.to_dict())
        self.assertEqual(clone, turn)

    def test_record_to_dict_round_trip(self) -> None:
        record = ConversationRecord(
            conversation_id="CV-ABCDEF",
            provider="copy",
            model="m1",
            created_at="t",
            updated_at="t",
            turns=(
                ConversationTurn(
                    role="user", content="hi", timestamp="t", metadata={}
                ),
            ),
            metadata={"phase": "build"},
        )
        clone = ConversationRecord.from_dict(record.to_dict())
        self.assertEqual(clone, record)

    def test_render_record_text(self) -> None:
        record = ConversationRecord(
            conversation_id="CV-ABCDEF",
            provider="p",
            model="m",
            created_at="2026-04-29T00:00:00Z",
            updated_at="2026-04-29T00:01:00Z",
            turns=(
                ConversationTurn(role="user", content="hi", timestamp="t1"),
                ConversationTurn(role="assistant", content="hello", timestamp="t2"),
            ),
        )
        rendered = render_record_text(record)
        self.assertIn("Conversation CV-ABCDEF", rendered)
        self.assertIn("turns: 2", rendered)
        self.assertIn("--- turn 1 [user]", rendered)
        self.assertIn("--- turn 2 [assistant]", rendered)


if __name__ == "__main__":
    unittest.main()
