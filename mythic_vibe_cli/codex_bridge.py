from __future__ import annotations

from dataclasses import dataclass
import difflib
import json
from pathlib import Path
import textwrap

from .context.indexer import ProjectIndexer
from .config import AppConfig, ConfigStore
from .ai.prompts.roles import PACKET_ROLES, ROLE_PRESETS
from .method_excerpt import (
    DEFAULT_METHOD_CORPUS_DIR,
    MethodExcerpt,
    select_method_excerpts,
    sections_for,
)
from .runtime.file_mutation_queue import file_mutation_queue

PACKET_OUTPUT_FORMATS = [
    "markdown",
    "copy-paste",
    "json",
    "claude",
    "aider",
    "gemini",
    "roo",
    "goose",
]


@dataclass
class CodexPacketRequest:
    task: str
    phase: str
    audience: str
    role: str = "Forge Worker"
    output_format: str = "markdown"
    workflow_id: str | None = None
    workflow_step_id: str | None = None


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
    source_path: str | None = None
    source_packet_id: str | None = None
    output_format: str = "markdown"
    workflow_id: str | None = None
    workflow_step_id: str | None = None

    def to_dict(self) -> dict[str, str]:
        payload: dict[str, str] = {
            "packet_id": self.packet_id,
            "created_at": self.created_at,
            "phase": self.phase,
            "role": self.role,
            "task": self.task,
            "audience": self.audience,
            "packet_path": self.packet_path,
            "metadata_path": self.metadata_path,
            "output_format": self.output_format,
        }
        if self.source_path is not None:
            payload["source_path"] = self.source_path
        if self.source_packet_id is not None:
            payload["source_packet_id"] = self.source_packet_id
        if self.workflow_id is not None:
            payload["workflow_id"] = self.workflow_id
        if self.workflow_step_id is not None:
            payload["workflow_step_id"] = self.workflow_step_id
        return payload


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
        self._validate_request(request)
        self.packet_dir.mkdir(parents=True, exist_ok=True)
        with file_mutation_queue(self.packet_dir):
            record = self._create_record(request, out_file=out_file)
            self._write_record(record, request)
        return Path(record.packet_path if out_file is None else out_file)

    def ingest_packet(self, source: Path) -> PacketRecord:
        source_path = self._resolve_path(source)
        if not source_path.exists():
            raise FileNotFoundError(source_path)

        packet_text, source_metadata = self._read_ingest_source(source_path)
        self.packet_dir.mkdir(parents=True, exist_ok=True)
        with file_mutation_queue(self.packet_dir):
            packet_id = self._next_packet_id()
            record = PacketRecord(
                packet_id=packet_id,
                created_at=self._now(),
                phase=str(source_metadata.get("phase") or "build"),
                role=str(source_metadata.get("role") or "Forge Worker"),
                task=str(source_metadata.get("task") or source_path.name),
                audience=str(source_metadata.get("audience") or "beginner"),
                packet_path=str(self.packet_dir / f"{packet_id}.md"),
                metadata_path=str(self.packet_dir / f"{packet_id}.json"),
                source_path=str(source_path),
                source_packet_id=str(source_metadata.get("packet_id")) if source_metadata.get("packet_id") else None,
                output_format=str(source_metadata.get("output_format") or "markdown"),
                workflow_id=str(source_metadata.get("workflow_id")) if source_metadata.get("workflow_id") else None,
                workflow_step_id=str(source_metadata.get("workflow_step_id")) if source_metadata.get("workflow_step_id") else None,
            )
            self._write_ingested_record(record, packet_text, source_metadata)
        return record

    def list_packets(self) -> list[PacketRecord]:
        if not self.packet_dir.exists():
            return []
        records: list[PacketRecord] = []
        for path in sorted(self.packet_dir.glob("PKT-*.meta.json")):
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
                        output_format=str(payload.get("output_format", "markdown")),
                        workflow_id=str(payload["workflow_id"]) if payload.get("workflow_id") else None,
                        workflow_step_id=str(payload["workflow_step_id"]) if payload.get("workflow_step_id") else None,
                    )
                )
        return records

    def find_packet_by_workflow_step(self, workflow_id: str, step_id: str) -> PacketRecord | None:
        if not workflow_id or not step_id:
            return None
        match: PacketRecord | None = None
        for record in self.list_packets():
            if record.workflow_id == workflow_id and record.workflow_step_id == step_id:
                if match is None or record.created_at >= match.created_at:
                    match = record
        return match

    def load_packet_text(self, packet_id: str) -> str | None:
        for suffix in (".md", ".json"):
            packet_path = self.packet_dir / f"{packet_id}{suffix}"
            if packet_path.exists():
                return packet_path.read_text(encoding="utf-8")
        return None

    def load_packet_record(self, packet_id: str) -> PacketRecord | None:
        metadata_path = self.packet_dir / f"{packet_id}.meta.json"
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
            source_path=str(payload.get("source_path")) if payload.get("source_path") else None,
            source_packet_id=str(payload.get("source_packet_id")) if payload.get("source_packet_id") else None,
            output_format=str(payload.get("output_format", "markdown")),
            workflow_id=str(payload["workflow_id"]) if payload.get("workflow_id") else None,
            workflow_step_id=str(payload["workflow_step_id"]) if payload.get("workflow_step_id") else None,
        )

    def diff_packets(self, left_packet_id: str, right_packet_id: str) -> str:
        left_text = self.load_packet_text(left_packet_id)
        right_text = self.load_packet_text(right_packet_id)
        if left_text is None:
            raise FileNotFoundError(self.packet_dir / f"{left_packet_id}.md")
        if right_text is None:
            raise FileNotFoundError(self.packet_dir / f"{right_packet_id}.md")

        diff = difflib.unified_diff(
            left_text.splitlines(),
            right_text.splitlines(),
            fromfile=f"{left_packet_id}.md",
            tofile=f"{right_packet_id}.md",
            lineterm="",
        )
        rendered = "\n".join(diff)
        return rendered or "No differences."

    def _create_record(self, request: CodexPacketRequest, *, out_file: Path | None = None) -> PacketRecord:
        packet_id = self._next_packet_id()
        default_suffix = ".json" if request.output_format == "json" else ".md"
        packet_path = self.packet_dir / f"{packet_id}{default_suffix}"
        metadata_path = self.packet_dir / f"{packet_id}.meta.json"
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
            output_format=request.output_format,
            workflow_id=request.workflow_id,
            workflow_step_id=request.workflow_step_id,
        )

    def _write_record(self, record: PacketRecord, request: CodexPacketRequest) -> None:
        canonical_packet = self.packet_dir / f"{record.packet_id}{Path(record.packet_path).suffix or '.md'}"
        canonical_meta = self.packet_dir / f"{record.packet_id}.meta.json"
        canonical_packet.parent.mkdir(parents=True, exist_ok=True)
        rendered = self._render_packet(request, record.packet_id, record.created_at)
        with file_mutation_queue(canonical_packet):
            canonical_packet.write_text(rendered, encoding="utf-8")
        with file_mutation_queue(canonical_meta):
            canonical_meta.write_text(json.dumps(record.to_dict(), indent=2) + "\n", encoding="utf-8")
        self._write_context_manifest(record, rendered)

        out_path = Path(record.packet_path)
        if out_path != canonical_packet:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with file_mutation_queue(out_path):
                out_path.write_text(rendered, encoding="utf-8")

    def _write_ingested_record(self, record: PacketRecord, packet_text: str, source_metadata: dict[str, object]) -> None:
        canonical_packet = self.packet_dir / f"{record.packet_id}{Path(record.packet_path).suffix or '.md'}"
        canonical_meta = self.packet_dir / f"{record.packet_id}.meta.json"
        canonical_packet.parent.mkdir(parents=True, exist_ok=True)
        with file_mutation_queue(canonical_packet):
            canonical_packet.write_text(packet_text, encoding="utf-8")
        payload = record.to_dict()
        payload["source_metadata"] = source_metadata if isinstance(source_metadata, dict) else {}
        with file_mutation_queue(canonical_meta):
            canonical_meta.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self._write_context_manifest(record, packet_text)

    def _read_ingest_source(self, source_path: Path) -> tuple[str, dict[str, object]]:
        if source_path.suffix.lower() == ".json":
            metadata = json.loads(source_path.read_text(encoding="utf-8"))
            if not isinstance(metadata, dict):
                metadata = {}
            text = self._ingest_text_from_metadata(source_path, metadata)
            return text, metadata

        text = source_path.read_text(encoding="utf-8")
        metadata = self._parse_packet_metadata(text)
        sidecar = source_path.with_suffix(".json")
        if sidecar.exists():
            try:
                payload = json.loads(sidecar.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    metadata = {**payload, **metadata}
            except json.JSONDecodeError:
                pass
        return text, metadata

    def _validate_request(self, request: CodexPacketRequest) -> None:
        if request.role not in PACKET_ROLES:
            raise ValueError(f"Unsupported packet role: {request.role}")
        if request.output_format not in PACKET_OUTPUT_FORMATS:
            raise ValueError(f"Unsupported packet output format: {request.output_format}")

    def _write_context_manifest(self, record: PacketRecord, packet_text: str) -> None:
        manifest_path = self.mythic_dir / "context_sources.json"
        payload = {
            "packet_id": record.packet_id,
            "created_at": record.created_at,
            "role": record.role,
            "phase": record.phase,
            "task": record.task,
            "output_format": record.output_format,
            "packet_path": record.packet_path,
            "source_path": record.source_path,
            "source_packet_id": record.source_packet_id,
            "selected_sources": self._selected_sources_snapshot(packet_text),
        }
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with file_mutation_queue(manifest_path):
            manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _selected_sources_snapshot(self, packet_text: str) -> list[dict[str, str]]:
        index = self.indexer.build(write=True)
        sources: list[dict[str, str]] = [
            {"path": "mythic/status.json", "kind": "status"},
            {"path": "mythic/project_index.json", "kind": "project_index"},
            {"path": "mythic/context_sources.json", "kind": "context_manifest"},
            {"path": "tasks/current_GOALS.md", "kind": "goals"},
            {"path": "docs/ARCHITECTURE.md", "kind": "architecture"},
            {"path": "mythic/plan.md", "kind": "plan"},
            {"path": "mythic/loop.md", "kind": "loop"},
        ]
        for path in index.recommended_context:
            sources.append({"path": path, "kind": "recommended"})
        if len(packet_text) > 0:
            sources.append({"path": "mythic/packets", "kind": "packet_store"})
        deduped: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in sources:
            path = item["path"]
            if path in seen:
                continue
            seen.add(path)
            deduped.append(item)
        return deduped

    def _ingest_text_from_metadata(self, source_path: Path, metadata: dict[str, object]) -> str:
        packet_text_path = metadata.get("packet_path")
        if isinstance(packet_text_path, str):
            candidate = Path(packet_text_path)
            if not candidate.is_absolute():
                candidate = (source_path.parent / candidate).resolve()
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")

        candidate = source_path.with_suffix(".md")
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
        candidate_json = source_path.with_suffix(".json")
        if candidate_json.exists():
            return candidate_json.read_text(encoding="utf-8")

        packet_text = metadata.get("text")
        if isinstance(packet_text, str):
            return packet_text

        raise FileNotFoundError(f"No packet text found for ingest source: {source_path}")

    def _parse_packet_metadata(self, text: str) -> dict[str, object]:
        metadata: dict[str, object] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("Packet ID:"):
                metadata["packet_id"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Created At:"):
                metadata["created_at"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Role:"):
                metadata["role"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("My audience level:"):
                metadata["audience"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Current phase:"):
                metadata["phase"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("Task request:"):
                metadata["task"] = stripped.split(":", 1)[1].strip()
        return metadata

    def _resolve_path(self, source: Path) -> Path:
        return source if source.is_absolute() else (self.root / source).resolve()

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

        weights = {
            "goals": 2,
            "architecture": 4,
            "plan": 3,
            "loop": 1,
            "project_index": 5,
            "allowed_files": 2,
            "forbidden_files": 2,
            "invariants": 4,
            "verification": 4,
        }
        minimums = {
            "goals": 120,
            "architecture": 220,
            "plan": 180,
            "loop": 80,
            "project_index": 260,
            "allowed_files": 120,
            "forbidden_files": 120,
            "invariants": 160,
            "verification": 160,
        }
        keys = list(sections.keys())
        active_weights = {key: weights.get(key, 1) for key in keys}
        active_mins = {key: minimums.get(key, 100) for key in keys}
        min_total = sum(active_mins.values())

        if min_total >= budget:
            scale = budget / max(1, min_total)
            active_mins = {key: max(40, int(value * scale)) for key, value in active_mins.items()}
            min_total = sum(active_mins.values())

        remaining = max(0, budget - min_total)
        weight_total = sum(active_weights.values()) or 1

        compacted: dict[str, str] = {}
        for key in keys:
            allotment = active_mins[key] + int(remaining * (active_weights[key] / weight_total))
            compacted[key] = self._safe_excerpt(sections[key], limit=max(40, allotment))

        return compacted

    def _role_profile(self, role: str) -> dict[str, list[str]]:
        return ROLE_PRESETS.get(role, ROLE_PRESETS["Forge Worker"])

    def _files_in_scope(self) -> list[str]:
        return [
            "tasks/current_GOALS.md",
            "docs/ARCHITECTURE.md",
            "mythic/plan.md",
            "mythic/loop.md",
            "mythic/status.json",
            "mythic/project_index.json",
            "mythic/context_sources.json",
        ]

    def _files_out_of_scope(self) -> list[str]:
        index = self.indexer.build(write=True)
        forbidden = [entry["path"] for entry in index.ignored[:8] if isinstance(entry, dict) and entry.get("path")]
        if not forbidden:
            forbidden = [
                ".git/",
                "vendor/",
                "node_modules/",
                "ai/",
                "systems/",
                "sessions/",
                "whisper/",
            ]
        return forbidden

    def _required_output_format(self, format_name: str) -> str:
        format_name = format_name.lower()
        if format_name in {"json"}:
            return "strict JSON"
        if format_name in {"claude"}:
            return "Claude Code task"
        if format_name in {"aider"}:
            return "Aider prompt"
        if format_name in {"gemini"}:
            return "Gemini CLI task"
        if format_name in {"roo"}:
            return "Roo prompt"
        if format_name in {"goose"}:
            return "Goose prompt"
        if format_name in {"copy-paste"}:
            return "ChatGPT/Codex copy-paste"
        return "generic Markdown"

    def _packet_header(self, request: CodexPacketRequest, packet_id: str, created_at: str) -> str:
        return textwrap.dedent(
            f"""
            # Mythic Engineering Task Packet

            Packet ID: {packet_id}
            Created At: {created_at}
            Role: {request.role}
            Phase: {request.phase}
            Audience: {request.audience}
            Task: {request.task}
            Format: {request.output_format}
            """
        ).strip()

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

    def _method_excerpts(self, request: CodexPacketRequest) -> list[MethodExcerpt]:
        keywords = sections_for(request.role, request.phase)
        if not keywords:
            return []
        return select_method_excerpts(self.root / DEFAULT_METHOD_CORPUS_DIR, keywords)

    def _render_method_excerpts_markdown(self, excerpts: list[MethodExcerpt]) -> str:
        if not excerpts:
            return ""
        lines: list[str] = []
        for excerpt in excerpts:
            lines.append(f"### {excerpt.heading} — `{excerpt.source_path}`")
            lines.append(excerpt.text)
            lines.append("")
        return "\n".join(lines).rstrip()

    def _render_packet(
        self,
        request: CodexPacketRequest,
        packet_id: str | None = None,
        created_at: str | None = None,
    ) -> str:
        packet_id = packet_id or "PKT-000000"
        created_at = created_at or self._now()
        role_profile = self._role_profile(request.role)
        method_excerpts = self._method_excerpts(request)
        sections = {
            "goals": self._safe_excerpt(self._read_optional(self.tasks_dir / "current_GOALS.md")),
            "architecture": self._safe_excerpt(self._read_optional(self.docs_dir / "ARCHITECTURE.md")),
            "plan": self._safe_excerpt(self._read_optional(self.mythic_dir / "plan.md")),
            "loop": self._safe_excerpt(self._read_optional(self.mythic_dir / "loop.md")),
            "project_index": self._project_index_snapshot(),
            "allowed_files": "\n".join(f"- {item}" for item in self._files_in_scope()),
            "forbidden_files": "\n".join(f"- {item}" for item in self._files_out_of_scope()),
            "invariants": "\n".join(f"- {item}" for item in role_profile["invariants"]),
            "verification": "\n".join(f"- {item}" for item in role_profile["verification"]),
        }
        status = self._status_snapshot()

        if self.config.auto_compact:
            sections = self._compact_sections(sections, self.config.packet_char_budget)

        goals = sections["goals"]
        architecture = sections["architecture"]
        plan = sections["plan"]
        loop = sections["loop"]
        project_index = sections["project_index"]
        allowed_files = sections["allowed_files"]
        forbidden_files = sections["forbidden_files"]
        invariants = sections["invariants"]
        verification = sections["verification"]
        required_output = self._required_output_format(request.output_format)

        if request.output_format == "json":
            payload = {
                "packet_id": packet_id,
                "created_at": created_at,
                "phase": request.phase,
                "role": request.role,
                "task": request.task,
                "audience": request.audience,
                "format": request.output_format,
                "current_state": json.loads(status) if status.startswith("{") else status,
                "goals": goals,
                "architecture": architecture,
                "plan": plan,
                "loop": loop,
                "project_index": json.loads(project_index) if project_index.startswith("{") else project_index,
                "files_in_scope": self._files_in_scope(),
                "files_out_of_scope": self._files_out_of_scope(),
                "invariants": role_profile["invariants"],
                "verification_commands": role_profile["verification"],
                "required_output_format": required_output,
                "method_excerpts": [excerpt.to_dict() for excerpt in method_excerpts],
                "checkin_summary_format": [
                    "Phase: <phase>",
                    "Update: <one sentence>",
                    "Files changed: <list>",
                ],
            }
            return json.dumps(payload, indent=2) + "\n"

        method_block = self._render_method_excerpts_markdown(method_excerpts)
        method_section = f"\n\n## 12. Method Excerpts\n{method_block}" if method_block else ""

        return textwrap.dedent(
            f"""
            {self._packet_header(request, packet_id, created_at)}

            ## 1. Role
            {request.role}

            ## 2. Intent
            {request.task}

            ## 3. Constraints
            - Audience: {request.audience}
            - Phase: {request.phase}
            - Format: {required_output}

            ## 4. Architecture Context
            {architecture}

            ## 5. Files In Scope
            {allowed_files}

            ## 6. Files Out of Scope
            {forbidden_files}

            ## 7. Current State
            ```json
            {status}
            ```

            ### PROJECT INDEX
            ```json
            {project_index}
            ```

            ## 8. Requested Change
            {plan}

            ## 9. Verification Commands
            {verification}

            ## 10. Required Output Format
            {required_output}

            ## 11. Check-in Summary
            - Phase: {request.phase}
            - Update: one sentence
            - Files changed: list only what changed
            """
        ).strip() + method_section + textwrap.dedent(
            f"""

            ### SAFETY
            - Invariants:
            {invariants}
            - Files allowed:
            {allowed_files}
            - Files forbidden:
            {forbidden_files}
            - Verification commands:
            {verification}
            """
        ).rstrip() + "\n"


CodexBridge = PacketBuilder
