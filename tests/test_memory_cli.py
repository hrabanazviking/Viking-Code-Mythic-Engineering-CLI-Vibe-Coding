"""Tests for `mythic-vibe memory` subcommands (PH-15 slices 15.3 + 15.4)."""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mythic_vibe_cli.app import build_parser
from mythic_vibe_cli.commands import COMMAND_HANDLERS
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.memory.conversation import (
    new_conversation_id,
    record_turn,
)
from mythic_vibe_cli.runtime.slash_commands import BUILTIN_SLASH_COMMANDS


def _seed_conversation(root: Path) -> str:
    cid = new_conversation_id()
    record_turn(root, cid, "user", "thoughts?", provider="copy", model="m1")
    record_turn(root, cid, "assistant", "Decision: ship it.")
    record_turn(root, cid, "user", "ok")
    return cid


# ---- argparse ----------------------------------------------------------


class MemoryArgparseTests(unittest.TestCase):
    def test_list_subcommand_parses(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["memory", "list"])
        self.assertEqual(ns.command, "memory")
        self.assertEqual(ns.memory_command, "list")

    def test_show_requires_id(self) -> None:
        parser = build_parser()
        # argparse exits non-zero when --id is missing.
        with self.assertRaises(SystemExit):
            from contextlib import redirect_stderr

            with redirect_stderr(io.StringIO()):
                parser.parse_args(["memory", "show"])

    def test_compact_supports_keep_recent_and_dry_run(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(
            ["memory", "compact", "--id", "CV-ABCDEF", "--keep-recent", "5", "--dry-run"]
        )
        self.assertEqual(ns.memory_command, "compact")
        self.assertEqual(ns.id, "CV-ABCDEF")
        self.assertEqual(ns.keep_recent, 5)
        self.assertTrue(ns.dry_run)

    def test_rehydrate_phase_default(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["memory", "rehydrate"])
        self.assertEqual(ns.memory_command, "rehydrate")
        self.assertEqual(ns.phase, "build")

    def test_last_and_spine_subcommands_parse(self) -> None:
        parser = build_parser()
        last = parser.parse_args(["memory", "last"])
        spine = parser.parse_args(["memory", "spine", "--limit", "5"])
        self.assertEqual(last.memory_command, "last")
        self.assertEqual(spine.memory_command, "spine")
        self.assertEqual(spine.limit, 5)


# ---- Dispatch + outputs ------------------------------------------------


class MemoryDispatchTests(unittest.TestCase):
    def test_handler_registered(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_dispatch

        self.assertIs(COMMAND_HANDLERS["memory"], cmd_memory_dispatch)

    def test_unknown_subcommand_returns_user_input_error(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_dispatch

        ns = argparse.Namespace(memory_command="bogus")
        self.assertEqual(cmd_memory_dispatch(ns), USER_INPUT_ERROR)

    def test_list_empty_text_output(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_list

        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, json=False)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_memory_list(ns)
            self.assertEqual(exit_code, SUCCESS)
            self.assertIn("no conversations", buf.getvalue())

    def test_list_json_envelope(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_list

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = _seed_conversation(root)
            ns = argparse.Namespace(path=str(root), json=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_memory_list(ns)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["command"], "memory list")
            self.assertEqual(len(payload["conversations"]), 1)
            self.assertEqual(payload["conversations"][0]["conversation_id"], cid)

    def test_show_unknown_id_user_input_error(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_show

        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, id="CV-NOPE12", json=False)
            self.assertEqual(cmd_memory_show(ns), USER_INPUT_ERROR)

    def test_show_text_renders_record(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_show

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = _seed_conversation(root)
            ns = argparse.Namespace(path=str(root), id=cid, json=False)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_memory_show(ns)
            rendered = buf.getvalue()
            self.assertIn(f"Conversation {cid}", rendered)
            self.assertIn("Decision: ship it.", rendered)

    def test_compact_writes_summary(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_compact

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = _seed_conversation(root)
            ns = argparse.Namespace(
                path=str(root),
                id=cid,
                keep_recent=2,
                json=True,
                dry_run=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_memory_compact(ns)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["command"], "memory compact")
            self.assertTrue(payload["result"]["written"])
            self.assertTrue(Path(payload["result"]["markdown_path"]).is_file())

    def test_compact_dry_run(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_compact

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = _seed_conversation(root)
            ns = argparse.Namespace(
                path=str(root),
                id=cid,
                keep_recent=2,
                json=False,
                dry_run=True,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_memory_compact(ns)
            self.assertIn("dry run", buf.getvalue().lower())
            self.assertFalse((Path(tmp) / "mythic" / "ai" / "summaries").exists())

    def test_compact_unknown_id(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_compact

        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(
                path=tmp,
                id="CV-NOPE12",
                keep_recent=3,
                json=False,
                dry_run=False,
            )
            self.assertEqual(cmd_memory_compact(ns), USER_INPUT_ERROR)

    def test_memory_last_json_uses_sqlite_spine(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_last
        from mythic_vibe_cli.memory.spine import record_memory

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record_memory(root, "session_summary", "Phase 5 was underway.")
            ns = argparse.Namespace(path=str(root), json=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_memory_last(ns)
            payload = json.loads(buf.getvalue())

        self.assertEqual(exit_code, SUCCESS)
        self.assertEqual(payload["command"], "memory last")
        self.assertIn("Phase 5 was underway.", payload["answer"])

    def test_memory_spine_text_initializes_database(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_spine

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ns = argparse.Namespace(path=str(root), limit=10, json=False)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_memory_spine(ns)
            rendered = buf.getvalue()
            db_exists = (root / ".mythic" / "memory.sqlite").is_file()

        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("Memory spine", rendered)
        self.assertTrue(db_exists)


# ---- Slice 15.4: rehydrate --------------------------------------------


class MemoryRehydrateTests(unittest.TestCase):
    def test_rehydrate_empty_project(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_rehydrate

        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, phase="build", json=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_memory_rehydrate(ns)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["command"], "memory rehydrate")
            self.assertEqual(payload["phase"], "build")
            self.assertEqual(payload["session_brief"], {})
            self.assertIsNone(payload["latest_conversation"])
            self.assertEqual(payload["conversation_summary"], "")
            self.assertIsNone(payload["latest_handoff"])

    def test_rehydrate_with_conversation_and_summary(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_rehydrate
        from mythic_vibe_cli.memory.compaction import compact_conversation

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cid = _seed_conversation(root)
            compact_conversation(root, cid, keep_recent=2)
            ns = argparse.Namespace(path=str(root), phase="build", json=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_memory_rehydrate(ns)
            payload = json.loads(buf.getvalue())
            self.assertEqual(
                payload["latest_conversation"]["conversation_id"], cid
            )
            self.assertIn("Compacted summary", payload["conversation_summary"])

    def test_rehydrate_text_output(self) -> None:
        from mythic_vibe_cli.commands import cmd_memory_rehydrate

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_conversation(root)
            ns = argparse.Namespace(path=str(root), phase="build", json=False)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_memory_rehydrate(ns)
            rendered = buf.getvalue()
            self.assertIn("Rehydration brief", rendered)
            self.assertIn("phase: build", rendered)
            self.assertIn("Latest conversation:", rendered)


# ---- Slash catalog + TUI runner ---------------------------------------


class MemorySlashCatalogTests(unittest.TestCase):
    def test_slash_catalog_contains_memory(self) -> None:
        names = {entry.name for entry in BUILTIN_SLASH_COMMANDS}
        self.assertIn("memory", names)

    def test_tui_runner_forwards_path_for_memory(self) -> None:
        from mythic_vibe_cli.tui.runner import command_for_builtin

        with tempfile.TemporaryDirectory() as tmp:
            spec = command_for_builtin("memory", project_root=Path(tmp))
        self.assertIn("--path", spec.argv)
        self.assertIn(str(Path(tmp)), spec.argv)


if __name__ == "__main__":
    unittest.main()
