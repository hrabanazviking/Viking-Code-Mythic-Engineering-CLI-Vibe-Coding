from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import textwrap

from .context.indexer import ProjectIndexer
from .config import AppConfig, ConfigStore


@dataclass
class CodexPacketRequest:
    task: str
    phase: str
    audience: str
    role: str = "Forge Worker"


@dataclass
class PacketRecord:
    packet_id: str
    created_at: str
    phase: str
    role: str
    task: str
    audience: str
    packet_path: str
    metadata_path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "packet_id": self.packet_id,
            "created_at": self.created_at,
            "phase": self.phase,
            "role": self.role,
            "task": self.task,
            "audience": self.audience,
            "packet_path": self.packet_path,
            "metadata_path": self.metadata_path,
        }


class PacketBuilder:
    def __init__(self, root: Path, config: AppConfig | None = None):
        self.root = root
        self.docs_dir = root / "docs"
        self.tasks_dir = root / "tasks"
        self.mythic_dir = root / "mythic"
        self.packet_dir = self.mythic_dir / "packets"
        self.indexer = ProjectIndexer(root)
        self.config = config or ConfigStore(root).load().config

    def create_packet(self, request: CodexPacketRequest, out_file: Path | None = None) -> Path:
        record = self._create_record(request, out_file=out_file)
        self._write_record(record, request)
        return Path(record.packet_path if out_file is None else out_file)

    def list_packets(self) -> list[PacketRecord]:
        if not self.packet_dir.exists():
            return []
        records: list[PacketRecord] = []
        for path in sorted(self.packet_dir.glob("PKT-*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                records.append(
                    PacketRecord(
                        packet_id=str(payload.get("packet_id", path.stem)),
                        created_at=str(payload.get("created_at", "")),
                        phase=str(payload.get("phase", "")),
                        role=str(payload.get("role", "")),
                        task=str(payload.get("task", "")),
                        audience=str(payload.get("audience", "")),
                        packet_path=str(payload.get("packet_path", "")),
                        metadata_path=str(path),
                    )
                )
        return records

    def load_packet_text(self, packet_id: str) -> str | None:
        packet_path = self.packet_dir / f"{packet_id}.md"
        if packet_path.exists():
            return packet_path.read_text(encoding="utf-8")
        return None

    def load_packet_record(self, packet_id: str) -> PacketRecord | None:
        metadata_path = self.packet_dir / f"{packet_id}.json"
        if not metadata_path.exists():
            return None
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return PacketRecord(
            packet_id=str(payload.get("packet_id", packet_id)),
            created_at=str(payload.get("created_at", "")),
            phase=str(payload.get("phase", "")),
            role=str(payload.get("role", "")),
            task=str(payload.get("task", "")),
            audience=str(payload.get("audience", "")),
            packet_path=str(payload.get("packet_path", "")),
            metadata_path=str(metadata_path),
        )

    def _create_record(self, request: CodexPacketRequest, *, out_file: Path | None = None) -> PacketRecord:
        packet_id = self._next_packet_id()
        packet_path = self.packet_dir / f"{packet_id}.md"
        metadata_path = self.packet_dir / f"{packet_id}.json"
        if out_file is not None:
            packet_output = out_file
        else:
            packet_output = packet_path
        created_at = self._now()
        return PacketRecord(
            packet_id=packet_id,
            created_at=created_at,
            phase=request.phase,
            role=request.role,
            task=request.task,
            audience=request.audience,
            packet_path=str(packet_output),
            metadata_path=str(metadata_path),
        )

    def _write_record(self, record: PacketRecord, request: CodexPacketRequest) -> None:
        canonical_packet = self.packet_dir / f"{record.packet_id}.md"
        canonical_meta = self.packet_dir / f"{record.packet_id}.json"
        canonical_packet.parent.mkdir(parents=True, exist_ok=True)
        canonical_packet.write_text(self._render_packet(request, record.packet_id, record.created_at), encoding="utf-8")
        canonical_meta.write_text(json.dumps(record.to_dict(), indent=2) + "\n", encoding="utf-8")

        out_path = Path(record.packet_path)
        if out_path != canonical_packet:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(self._render_packet(request, record.packet_id, record.created_at), encoding="utf-8")

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
                "last_update": state.get("updated_at") or state.get("last_update"),
            },
            indent=2,
        )

    def _project_index_snapshot(self) -> str:
        index = self.indexer.build(write=True)
        payload = index.to_dict()
        compact = {
            "schema_version": payload["schema_version"],
            "generated_at": payload["generated_at"],
            "root": payload["root"],
            "git": payload["git"],
            "languages": payload["languages"],
            "important_files": payload["important_files"][:8],
            "docs": payload["docs"][:8],
            "tests": payload["tests"][:8],
            "risks": payload["risks"][:8],
            "recommended_context": payload["recommended_context"][:12],
        }
        return json.dumps(compact, indent=2)

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

    def _next_packet_id(self) -> str:
        latest = 0
        for record in self.list_packets():
            suffix = record.packet_id.removeprefix("PKT-")
            try:
                latest = max(latest, int(suffix))
            except ValueError:
                continue
        return f"PKT-{latest + 1:06d}"

    def _now(self) -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _render_packet(
        self,
        request: CodexPacketRequest,
        packet_id: str | None = None,
        created_at: str | None = None,
    ) -> str:
        packet_id = packet_id or "PKT-000000"
        created_at = created_at or self._now()
        sections = {
            "goals": self._safe_excerpt(self._read_optional(self.tasks_dir / "current_GOALS.md")),
            "architecture": self._safe_excerpt(self._read_optional(self.docs_dir / "ARCHITECTURE.md")),
            "plan": self._safe_excerpt(self._read_optional(self.mythic_dir / "plan.md")),
            "loop": self._safe_excerpt(self._read_optional(self.mythic_dir / "loop.md")),
            "project_index": self._project_index_snapshot(),
        }
        status = self._status_snapshot()

        if self.config.auto_compact:
            sections = self._compact_sections(sections, self.config.packet_char_budget)

        goals = sections["goals"]
        architecture = sections["architecture"]
        plan = sections["plan"]
        loop = sections["loop"]
        project_index = sections["project_index"]

        return textwrap.dedent(
            f"""
            # Codex Prompt Packet (ChatGPT Plus Friendly)

            This packet is generated for users on a $20 ChatGPT Plus account.
            Paste the section below into ChatGPT (or Codex in ChatGPT) to continue work.

            ## Prompt To Paste

            You are my Mythic Engineering coding assistant, intentionally chosen for this session.
            Respect user sovereignty: do not claim authority over the user, other AIs, or hardware.
            Session authorization is already granted for this chosen assistant.
            You may operate autonomously within the requested task and stated constraints.
            Use this strict operating sequence:
            1) Restate intent and constraints.
            2) Propose architecture-aware plan.
            3) Suggest smallest safe code change.
            4) Suggest verification commands.
            5) Suggest a concise check-in update.

            Packet ID: {packet_id}
            Created At: {created_at}
            Role: {request.role}
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

            ### PROJECT INDEX
            ```json
            {project_index}
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


CodexBridge = PacketBuilder
