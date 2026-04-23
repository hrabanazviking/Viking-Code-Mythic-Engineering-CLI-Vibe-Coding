from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import textwrap

from .config import AppConfig, ConfigStore


@dataclass
class CodexPacketRequest:
    task: str
    phase: str
    audience: str


class CodexBridge:
    def __init__(self, root: Path, config: AppConfig | None = None):
        self.root = root
        self.docs_dir = root / "docs"
        self.tasks_dir = root / "tasks"
        self.mythic_dir = root / "mythic"
        self.config = config or ConfigStore(root).load().config

    def create_packet(self, request: CodexPacketRequest, out_file: Path | None = None) -> Path:
        out = out_file or (self.mythic_dir / "codex_prompt.md")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self._render_packet(request), encoding="utf-8")
        return out

    def _read_optional(self, path: Path, fallback: str = "(missing)") -> str:
        if not path.exists():
            return fallback
        return path.read_text(encoding="utf-8")

    def _safe_excerpt(self, text: str, limit: int | None = None) -> str:
        effective_limit = limit or self.config.excerpt_limit
        compact = text.strip()
        if len(compact) <= effective_limit:
            return compact
        return compact[:effective_limit] + "\n... [truncated by mythic-vibe]"

    def _status_snapshot(self) -> str:
        path = self.mythic_dir / "status.json"
        if not path.exists():
            return "No status.json found."
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return "status.json exists but contains invalid JSON."

        return json.dumps(
            {
                "goal": state.get("goal"),
                "current_phase": state.get("current_phase"),
                "completed_phases": state.get("completed_phases", []),
                "last_update": state.get("last_update"),
            },
            indent=2,
        )

    def _compact_sections(self, sections: dict[str, str], budget: int) -> dict[str, str]:
        total = sum(len(value) for value in sections.values())
        if total <= budget:
            return sections

        keys = list(sections.keys())
        share = max(200, budget // max(1, len(keys)))

        compacted: dict[str, str] = {}
        for key in keys:
            compacted[key] = self._safe_excerpt(sections[key], limit=share)

        return compacted

    def _render_packet(self, request: CodexPacketRequest) -> str:
        sections = {
            "goals": self._safe_excerpt(self._read_optional(self.tasks_dir / "current_GOALS.md")),
            "architecture": self._safe_excerpt(self._read_optional(self.docs_dir / "ARCHITECTURE.md")),
            "plan": self._safe_excerpt(self._read_optional(self.mythic_dir / "plan.md")),
            "loop": self._safe_excerpt(self._read_optional(self.mythic_dir / "loop.md")),
        }
        status = self._status_snapshot()

        if self.config.auto_compact:
            sections = self._compact_sections(sections, self.config.packet_char_budget)

        goals = sections["goals"]
        architecture = sections["architecture"]
        plan = sections["plan"]
        loop = sections["loop"]

        return textwrap.dedent(
            f"""
            # Codex Prompt Packet (ChatGPT Plus Friendly)

            This packet is generated for users on a $20 ChatGPT Plus account.
            Paste the section below into ChatGPT (or Codex in ChatGPT) to continue work.

            ## Prompt To Paste

            You are my Mythic Engineering coding assistant.
            Use this strict operating sequence:
            1) Restate intent and constraints.
            2) Propose architecture-aware plan.
            3) Suggest smallest safe code change.
            4) Suggest verification commands.
            5) Suggest a concise check-in update.

            My audience level: {request.audience}
            Current phase: {request.phase}
            Task request: {request.task}

            Project context below:

            ### STATUS SNAPSHOT
            ```json
            {status}
            ```

            ### GOALS
            ```markdown
            {goals}
            ```

            ### ARCHITECTURE
            ```markdown
            {architecture}
            ```

            ### PLAN
            ```markdown
            {plan}
            ```

            ### LOOP NOTES
            ```markdown
            {loop}
            ```

            Return output in this exact format:

            ## Mythic Plan Update
            <bullet points>

            ## File Changes
            <ordered steps>

            ## Verification
            <commands + expected outputs>

            ## Checkin
            Phase: {request.phase}
            Update: <one sentence for mythic-vibe checkin>
            """
        ).strip() + "\n"
