"""Multi-turn conversation history with OpenAI-format export and persistence."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChatMessage:
    role: str           # "user" | "assistant" | "system"
    content: str
    turn_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: str = field(default_factory=_now_iso)


class ChatHistory:
    def __init__(self, max_turns: int = 20, system_prompt: str = "") -> None:
        self.messages: list[ChatMessage] = []
        self.max_turns = max_turns
        self.system_prompt = system_prompt.strip()

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add_user(self, text: str) -> str:
        """Append a user message and return the assigned turn_id."""
        msg = ChatMessage(role="user", content=text)
        self.messages.append(msg)
        return msg.turn_id

    def add_assistant(self, text: str, turn_id: str = "") -> None:
        msg = ChatMessage(
            role="assistant",
            content=text,
            turn_id=turn_id or uuid.uuid4().hex[:8],
        )
        self.messages.append(msg)

    def clear(self) -> None:
        self.messages = []

    # ── Context rendering ─────────────────────────────────────────────────────

    def to_messages(self) -> list[dict]:
        """
        Return an OpenAI-format messages list.
        System prompt is prepended if set.  Applies the max_turns window.
        """
        window = self.messages[-(self.max_turns * 2):]
        result: list[dict] = []
        if self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})
        result.extend({"role": m.role, "content": m.content} for m in window)
        return result

    def to_prompt_context(self, max_chars: int = 2000) -> str:
        """
        Render conversation as plain text for non-chat backends.
        Walks from oldest to newest; drops oldest entries to stay under max_chars.
        """
        lines: list[str] = []
        # Build full list then trim from the front until we're within budget
        all_lines = [
            f"{m.role.upper()}: {m.content}"
            for m in self.messages
        ]
        total = 0
        kept: list[str] = []
        for line in reversed(all_lines):
            if total + len(line) + 1 > max_chars:
                break
            kept.insert(0, line)
            total += len(line) + 1
        return "\n".join(kept)

    def trim_to_budget(self, max_turns: int | None = None) -> None:
        """Keep only the most recent max_turns conversation pairs."""
        limit = max_turns if max_turns is not None else self.max_turns
        max_messages = limit * 2
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:] if max_messages > 0 else []

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "max_turns": self.max_turns,
            "system_prompt": self.system_prompt,
            "messages": [asdict(m) for m in self.messages],
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.debug("ChatHistory saved to %s (%d messages)", path, len(self.messages))

    @classmethod
    def load(cls, path: Path) -> ChatHistory:
        with path.open("r", encoding="utf-8") as f:
            payload: dict = json.load(f)
        history = cls(
            max_turns=payload.get("max_turns", 20),
            system_prompt=payload.get("system_prompt", ""),
        )
        for raw in payload.get("messages", []):
            history.messages.append(
                ChatMessage(
                    role=raw["role"],
                    content=raw.get("content", raw.get("text", "")),
                    turn_id=raw.get("turn_id", uuid.uuid4().hex[:8]),
                    timestamp=raw.get("timestamp", _now_iso()),
                )
            )
        logger.debug("ChatHistory loaded from %s (%d messages)", path, len(history.messages))
        return history

    # ── Convenience ───────────────────────────────────────────────────────────

    def format_for_display(self) -> str:
        if not self.messages:
            return "(no history)"
        lines = []
        for m in self.messages:
            prefix = "You   >" if m.role == "user" else "Forge >"
            lines.append(f"{prefix} {m.content}")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self.messages)
