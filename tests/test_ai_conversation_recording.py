"""Tests for the PH-15 sub-slice — auto-recording provider calls.

`cmd_ai_run` and `cmd_ai_ingest_response` now write to the slice-
15.1 conversation log unless the operator opts out via
``--no-record`` or runs in dry-run mode.
"""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from mythic_vibe_cli.ai.providers.base import ProviderResponse
from mythic_vibe_cli.app import build_parser
from mythic_vibe_cli.memory.conversation import (
    list_conversations,
    new_conversation_id,
    read_conversation,
)


def _real_response(content: str = "assistant reply") -> ProviderResponse:
    """Build a non-dry-run ProviderResponse for tests. The shipped
    copy-paste / local providers always set dry_run=True because they
    don't make a real API call; tests that exercise the recording
    path need to simulate a real provider response."""
    return ProviderResponse(
        provider="copy-paste",
        model="m1",
        content=content,
        packet_id="PKT-TEST",
        dry_run=False,
        usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        metadata={"source": "test"},
    )


# ---- argparse ----------------------------------------------------------


class AiRecordingArgparseTests(unittest.TestCase):
    def test_ai_run_accepts_conversation_id(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(
            [
                "ai",
                "run",
                "--provider",
                "copy-paste",
                "--packet",
                "hi",
                "--conversation-id",
                "CV-ABCDEF",
            ]
        )
        self.assertEqual(ns.conversation_id, "CV-ABCDEF")
        self.assertFalse(ns.no_record)

    def test_ai_run_accepts_no_record(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(
            ["ai", "run", "--provider", "copy-paste", "--packet", "hi", "--no-record"]
        )
        self.assertTrue(ns.no_record)

    def test_ai_ingest_accepts_conversation_id_and_no_record(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(
            [
                "ai",
                "ingest-response",
                "--provider",
                "copy-paste",
                "--model",
                "m1",
                "--packet-id",
                "PKT-1",
                "--response",
                "ok",
                "--conversation-id",
                "CV-FEEDFE",
                "--no-record",
            ]
        )
        self.assertEqual(ns.conversation_id, "CV-FEEDFE")
        self.assertTrue(ns.no_record)


# ---- cmd_ai_run --------------------------------------------------------


class AiRunRecordingTests(unittest.TestCase):
    def _run_namespace(self, **overrides: object) -> argparse.Namespace:
        base = dict(
            path=".",
            provider="copy-paste",
            packet="hello",
            json=True,
            dry_run=False,
            conversation_id="",
            no_record=False,
        )
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_real_call_records_user_then_assistant_turn(self) -> None:
        from mythic_vibe_cli.ai.providers.copy_paste import CopyPasteProvider
        from mythic_vibe_cli.commands import cmd_ai_run

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            ns = self._run_namespace(path=str(root), conversation_id=cid)
            buf = io.StringIO()
            with mock.patch.object(
                CopyPasteProvider,
                "run",
                return_value=_real_response("the assistant reply"),
            ):
                with redirect_stdout(buf):
                    cmd_ai_run(ns)
            payload = json.loads(buf.getvalue())
            record = read_conversation(root, cid)
            self.assertEqual(payload["conversation_id"], cid)
            self.assertTrue(payload["recorded"])
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.turn_count, 2)
            self.assertEqual(record.turns[0].role, "user")
            self.assertEqual(record.turns[0].content, "hello")
            self.assertEqual(record.turns[1].role, "assistant")
            self.assertEqual(record.turns[1].content, "the assistant reply")
            self.assertEqual(record.provider, "copy-paste")

    def test_no_conversation_id_auto_generates_fresh_one(self) -> None:
        from mythic_vibe_cli.ai.providers.copy_paste import CopyPasteProvider
        from mythic_vibe_cli.commands import cmd_ai_run

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ns = self._run_namespace(path=str(root))
            buf = io.StringIO()
            with mock.patch.object(
                CopyPasteProvider, "run", return_value=_real_response()
            ):
                with redirect_stdout(buf):
                    cmd_ai_run(ns)
            payload = json.loads(buf.getvalue())
            cid = payload["conversation_id"]
            self.assertTrue(cid.startswith("CV-"))
            record = read_conversation(root, cid)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.turn_count, 2)

    def test_no_record_flag_skips_log(self) -> None:
        from mythic_vibe_cli.ai.providers.copy_paste import CopyPasteProvider
        from mythic_vibe_cli.commands import cmd_ai_run

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ns = self._run_namespace(path=str(root), no_record=True)
            buf = io.StringIO()
            with mock.patch.object(
                CopyPasteProvider, "run", return_value=_real_response()
            ):
                with redirect_stdout(buf):
                    cmd_ai_run(ns)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["conversation_id"], "")
            self.assertFalse(payload["recorded"])
            self.assertEqual(list_conversations(root), [])

    def test_dry_run_skips_log_even_with_explicit_conversation_id(self) -> None:
        """Dry-run is the estimation path — no real conversation
        happens, so we never record. The shipped copy-paste / local
        providers also self-report dry_run=True (the response is just
        the packet text echoed back), so the unmocked path covers
        this; we use the unmocked provider here intentionally."""
        from mythic_vibe_cli.commands import cmd_ai_run

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            ns = self._run_namespace(
                path=str(root),
                conversation_id=cid,
                dry_run=True,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_run(ns)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["dry_run"])
            self.assertFalse(payload["recorded"])
            # Even with a supplied id, dry-run writes nothing.
            self.assertIsNone(read_conversation(root, cid))

    def test_unmocked_copy_paste_provider_skips_recording(self) -> None:
        """The shipped CopyPasteProvider always sets dry_run=True
        because it just packages prompts for manual paste — no real
        AI conversation happens. Recording must skip even without
        --no-record / --dry-run on the CLI, because the provider's
        own dry_run flag governs."""
        from mythic_vibe_cli.commands import cmd_ai_run

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ns = self._run_namespace(path=str(root))
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_run(ns)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["dry_run"])
            self.assertFalse(payload["recorded"])
            self.assertEqual(list_conversations(root), [])


# ---- cmd_ai_ingest_response -------------------------------------------


class AiIngestRecordingTests(unittest.TestCase):
    def _ingest_namespace(self, **overrides: object) -> argparse.Namespace:
        base = dict(
            path=".",
            provider="copy-paste",
            model="m1",
            packet_id="PKT-1",
            response="manual paste",
            json=True,
            conversation_id="",
            no_record=False,
        )
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_records_assistant_turn(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_ingest_response

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            ns = self._ingest_namespace(path=str(root), conversation_id=cid)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_ingest_response(ns)
            record = read_conversation(root, cid)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.turn_count, 1)
            self.assertEqual(record.turns[0].role, "assistant")
            self.assertEqual(record.turns[0].content, "manual paste")
            self.assertEqual(record.turns[0].metadata.get("packet_id"), "PKT-1")
            self.assertTrue(record.turns[0].metadata.get("ingest"))

    def test_no_conversation_id_auto_generates(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_ingest_response

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ns = self._ingest_namespace(path=str(root))
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_ingest_response(ns)
            payload = json.loads(buf.getvalue())
            cid = payload["payload"]["conversation_id"]
            self.assertTrue(cid.startswith("CV-"))
            record = read_conversation(root, cid)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.turn_count, 1)

    def test_no_record_skips_log(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_ingest_response

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ns = self._ingest_namespace(path=str(root), no_record=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_ingest_response(ns)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["payload"]["conversation_id"], "")
            self.assertFalse(payload["payload"]["recorded"])
            self.assertEqual(list_conversations(root), [])


# ---- Multi-turn continuation ------------------------------------------


class MultiTurnRecordingTests(unittest.TestCase):
    """Reusing the same `--conversation-id` across calls should grow
    the same conversation file, not overwrite it."""

    def test_two_run_calls_under_same_id_produce_four_turns(self) -> None:
        from mythic_vibe_cli.ai.providers.copy_paste import CopyPasteProvider
        from mythic_vibe_cli.commands import cmd_ai_run

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = new_conversation_id()
            base = dict(
                path=str(root),
                provider="copy-paste",
                json=True,
                dry_run=False,
                conversation_id=cid,
                no_record=False,
            )
            with mock.patch.object(
                CopyPasteProvider, "run", return_value=_real_response()
            ):
                with redirect_stdout(io.StringIO()):
                    cmd_ai_run(argparse.Namespace(**base, packet="first"))
                    cmd_ai_run(argparse.Namespace(**base, packet="second"))
            record = read_conversation(root, cid)
            self.assertIsNotNone(record)
            assert record is not None
            self.assertEqual(record.turn_count, 4)
            self.assertEqual(record.turns[0].content, "first")
            self.assertEqual(record.turns[2].content, "second")


if __name__ == "__main__":
    unittest.main()
