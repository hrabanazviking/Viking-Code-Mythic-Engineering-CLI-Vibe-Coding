"""
Phase 7 test suite — Chat history + multi-turn conversation tests.

Tests ChatHistory management, context rendering, persistence, and
ThoughtForgeCore.think() with history injection.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from thoughtforge.cognition.chat_history import ChatHistory, ChatMessage


# ── ChatMessage dataclass ─────────────────────────────────────────────────────

class TestChatMessage:
    def test_creates_with_required_fields(self):
        msg = ChatMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"

    def test_auto_generates_turn_id(self):
        msg = ChatMessage(role="user", content="hi")
        assert isinstance(msg.turn_id, str)
        assert len(msg.turn_id) > 0

    def test_auto_generates_timestamp(self):
        msg = ChatMessage(role="user", content="hi")
        assert isinstance(msg.timestamp, str)
        assert "T" in msg.timestamp or len(msg.timestamp) > 0

    def test_two_messages_have_different_turn_ids(self):
        m1 = ChatMessage(role="user", content="a")
        m2 = ChatMessage(role="user", content="b")
        assert m1.turn_id != m2.turn_id


# ── ChatHistory construction ──────────────────────────────────────────────────

class TestChatHistoryConstruction:
    def test_empty_on_creation(self):
        h = ChatHistory()
        assert len(h) == 0
        assert h.messages == []

    def test_default_max_turns(self):
        h = ChatHistory()
        assert h.max_turns == 20

    def test_custom_max_turns(self):
        h = ChatHistory(max_turns=5)
        assert h.max_turns == 5

    def test_system_prompt_stored(self):
        h = ChatHistory(system_prompt="You are a skald.")
        assert h.system_prompt == "You are a skald."

    def test_clear_empties_messages(self):
        h = ChatHistory()
        h.add_user("hello")
        h.add_assistant("hi")
        h.clear()
        assert len(h) == 0


# ── add_user / add_assistant ──────────────────────────────────────────────────

class TestChatHistoryMutation:
    def test_add_user_returns_turn_id(self):
        h = ChatHistory()
        tid = h.add_user("hello")
        assert isinstance(tid, str)
        assert len(tid) > 0

    def test_add_user_increments_length(self):
        h = ChatHistory()
        h.add_user("a")
        assert len(h) == 1
        h.add_user("b")
        assert len(h) == 2

    def test_add_assistant_increments_length(self):
        h = ChatHistory()
        h.add_user("hi")
        h.add_assistant("hello")
        assert len(h) == 2

    def test_messages_in_correct_order(self):
        h = ChatHistory()
        h.add_user("first")
        h.add_assistant("second")
        h.add_user("third")
        assert h.messages[0].role == "user"
        assert h.messages[1].role == "assistant"
        assert h.messages[2].role == "user"

    def test_two_users_have_different_turn_ids(self):
        h = ChatHistory()
        t1 = h.add_user("a")
        t2 = h.add_user("b")
        assert t1 != t2

    def test_add_assistant_with_explicit_turn_id(self):
        h = ChatHistory()
        h.add_assistant("reply", turn_id="abc123")
        assert h.messages[0].turn_id == "abc123"

    def test_add_assistant_auto_turn_id_when_empty(self):
        h = ChatHistory()
        h.add_assistant("reply")
        assert len(h.messages[0].turn_id) > 0


# ── to_messages (OpenAI format) ───────────────────────────────────────────────

class TestToMessages:
    def test_empty_history_no_system_returns_empty(self):
        h = ChatHistory()
        msgs = h.to_messages()
        assert msgs == []

    def test_system_prompt_prepended(self):
        h = ChatHistory(system_prompt="You are a skald.")
        h.add_user("hello")
        msgs = h.to_messages()
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "You are a skald."

    def test_user_message_present(self):
        h = ChatHistory()
        h.add_user("What is Yggdrasil?")
        msgs = h.to_messages()
        assert any(m["role"] == "user" and "Yggdrasil" in m["content"] for m in msgs)

    def test_all_messages_have_role_and_content(self):
        h = ChatHistory()
        h.add_user("q")
        h.add_assistant("a")
        for m in h.to_messages():
            assert "role" in m
            assert "content" in m

    def test_respects_max_turns_window(self):
        h = ChatHistory(max_turns=2)
        for i in range(10):
            h.add_user(f"q{i}")
            h.add_assistant(f"a{i}")
        msgs = h.to_messages()
        # max_turns=2 → at most 4 messages (2 pairs)
        non_system = [m for m in msgs if m["role"] != "system"]
        assert len(non_system) <= 4


# ── to_prompt_context ─────────────────────────────────────────────────────────

class TestToPromptContext:
    def test_empty_returns_empty_string(self):
        h = ChatHistory()
        assert h.to_prompt_context() == ""

    def test_contains_user_content(self):
        h = ChatHistory()
        h.add_user("What is Yggdrasil?")
        ctx = h.to_prompt_context()
        assert "Yggdrasil" in ctx

    def test_contains_assistant_content(self):
        h = ChatHistory()
        h.add_user("hi")
        h.add_assistant("Hello, skald!")
        ctx = h.to_prompt_context()
        assert "Hello, skald!" in ctx

    def test_respects_max_chars(self):
        h = ChatHistory()
        for i in range(50):
            h.add_user("x" * 100)
            h.add_assistant("y" * 100)
        ctx = h.to_prompt_context(max_chars=500)
        assert len(ctx) <= 600  # small slack for line endings

    def test_most_recent_content_preserved(self):
        h = ChatHistory()
        for i in range(20):
            h.add_user(f"old message {i}")
        h.add_user("VERY RECENT MESSAGE")
        ctx = h.to_prompt_context(max_chars=200)
        assert "VERY RECENT MESSAGE" in ctx


# ── trim_to_budget ────────────────────────────────────────────────────────────

class TestTrimToBudget:
    def test_trim_reduces_to_max(self):
        h = ChatHistory(max_turns=10)
        for _ in range(20):
            h.add_user("q")
            h.add_assistant("a")
        h.trim_to_budget(max_turns=3)
        assert len(h) <= 6  # 3 pairs = 6 messages

    def test_trim_keeps_most_recent(self):
        h = ChatHistory()
        for i in range(10):
            h.add_user(f"msg_{i}")
        h.trim_to_budget(max_turns=2)
        contents = [m.content for m in h.messages]
        assert "msg_9" in contents
        assert "msg_0" not in contents

    def test_trim_to_zero_clears(self):
        h = ChatHistory()
        h.add_user("hi")
        h.trim_to_budget(max_turns=0)
        assert len(h) == 0


# ── save / load persistence ───────────────────────────────────────────────────

class TestChatHistoryPersistence:
    def test_save_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.json"
            h = ChatHistory(system_prompt="test")
            h.add_user("hello")
            h.save(path)
            assert path.exists()

    def test_save_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.json"
            h = ChatHistory(system_prompt="You are a skald.", max_turns=15)
            h.add_user("What is Yggdrasil?")
            h.add_assistant("It is the world tree.", turn_id="abc")
            h.save(path)

            h2 = ChatHistory.load(path)
            assert len(h2) == 2
            assert h2.messages[0].content == "What is Yggdrasil?"
            assert h2.messages[1].content == "It is the world tree."

    def test_load_preserves_system_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.json"
            h = ChatHistory(system_prompt="Norse skald mode.")
            h.add_user("hi")
            h.save(path)
            h2 = ChatHistory.load(path)
            assert h2.system_prompt == "Norse skald mode."

    def test_load_preserves_turn_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.json"
            h = ChatHistory()
            tid = h.add_user("hello")
            h.save(path)
            h2 = ChatHistory.load(path)
            assert h2.messages[0].turn_id == tid

    def test_save_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.json"
            h = ChatHistory()
            h.add_user("test")
            h.save(path)
            data = json.loads(path.read_text(encoding="utf-8"))
            assert isinstance(data, dict)

    def test_load_nonexistent_raises(self):
        with pytest.raises(Exception):
            ChatHistory.load(Path("/nonexistent/path/history.json"))


# ── ThoughtForgeCore with chat history ───────────────────────────────────────

class TestThoughtForgeCoreWithHistory:
    @pytest.fixture(scope="module")
    def core(self):
        import tempfile
        from thoughtforge.cognition.core import ThoughtForgeCore
        tmp = tempfile.mkdtemp()
        return ThoughtForgeCore(
            memory_dir=Path(tmp) / "memory",
            db_path=Path(tmp) / "test.db",
            model_path=None,
        )

    def test_think_accepts_history_kwarg(self, core):
        h = ChatHistory()
        h.add_user("What is Yggdrasil?")
        result = core.think("Tell me more.", history=h)
        from thoughtforge.knowledge.models import FinalResponseRecord
        assert isinstance(result, FinalResponseRecord)

    def test_think_without_history_still_works(self, core):
        from thoughtforge.knowledge.models import FinalResponseRecord
        result = core.think("What is frith?")
        assert isinstance(result, FinalResponseRecord)

    def test_history_does_not_mutate_between_calls(self, core):
        h = ChatHistory()
        h.add_user("Hello")
        initial_len = len(h)
        core.think("Follow-up question.", history=h)
        # think() should not add messages to the history — that's the caller's job
        assert len(h) == initial_len

    def test_multi_turn_stability(self, core):
        h = ChatHistory()
        from thoughtforge.knowledge.models import FinalResponseRecord
        queries = [
            "What is Yggdrasil?",
            "Who are the Norns?",
            "What is frith?",
        ]
        for q in queries:
            h.add_user(q)
            result = core.think(q, history=h)
            assert isinstance(result, FinalResponseRecord)
            h.add_assistant(result.text, turn_id=result.turn_id)

        assert len(h) == 6  # 3 user + 3 assistant

    def test_history_context_injected_in_scaffold(self, core):
        """History should reach the scaffold without crashing."""
        h = ChatHistory(system_prompt="Respond as a Norse skald.")
        for _ in range(5):
            h.add_user("Tell me of Odin.")
            h.add_assistant("Odin is the Allfather.")
        from thoughtforge.knowledge.models import FinalResponseRecord
        result = core.think("And what of Thor?", history=h)
        assert isinstance(result, FinalResponseRecord)
