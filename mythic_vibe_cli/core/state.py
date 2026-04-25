from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


CURRENT_STATE_SCHEMA_VERSION = 1

PHASES = [
    "intent",
    "constraints",
    "architecture",
    "plan",
    "build",
    "verify",
    "reflect",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class StateValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class CheckinRecord:
    checkin_id: str
    timestamp: str
    phase: str
    summary: str
    schema_version: int = CURRENT_STATE_SCHEMA_VERSION
    task_id: str | None = None
    files_changed: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    next_phase: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "checkin_id": self.checkin_id,
            "timestamp": self.timestamp,
            "phase": self.phase,
            "task_id": self.task_id,
            "summary": self.summary,
            "files_changed": list(self.files_changed),
            "decisions": list(self.decisions),
            "risks": list(self.risks),
            "next_phase": self.next_phase,
        }


@dataclass
class DecisionRecord:
    decision_id: str
    title: str
    status: str
    context: str
    decision: str
    schema_version: int = CURRENT_STATE_SCHEMA_VERSION
    consequences: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "decision_id": self.decision_id,
            "title": self.title,
            "status": self.status,
            "context": self.context,
            "decision": self.decision,
            "consequences": list(self.consequences),
            "links": list(self.links),
        }


@dataclass
class VerificationRecord:
    verification_id: str
    timestamp: str
    result: str
    schema_version: int = CURRENT_STATE_SCHEMA_VERSION
    task_id: str | None = None
    commands: list[dict[str, Any]] = field(default_factory=list)
    diff_reviewed: bool = False
    docs_updated: bool = False
    invariants_checked: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "verification_id": self.verification_id,
            "timestamp": self.timestamp,
            "task_id": self.task_id,
            "commands": list(self.commands),
            "diff_reviewed": self.diff_reviewed,
            "docs_updated": self.docs_updated,
            "invariants_checked": list(self.invariants_checked),
            "result": self.result,
        }


@dataclass
class ProjectState:
    goal: str
    schema_version: int = CURRENT_STATE_SCHEMA_VERSION
    project_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    current_phase: str = "intent"
    completed_phases: list[str] = field(default_factory=list)
    active_task_id: str | None = None
    open_risks: list[str] = field(default_factory=list)
    open_decisions: list[str] = field(default_factory=list)
    last_packet_id: str | None = None
    last_verification_id: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "goal": self.goal,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_phase": self.current_phase,
            "completed_phases": list(self.completed_phases),
            "active_task_id": self.active_task_id,
            "open_risks": list(self.open_risks),
            "open_decisions": list(self.open_decisions),
            "last_packet_id": self.last_packet_id,
            "last_verification_id": self.last_verification_id,
            "history": list(self.history),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ProjectState:
        now = utc_now()
        return cls(
            schema_version=int(payload.get("schema_version", CURRENT_STATE_SCHEMA_VERSION)),
            project_id=str(payload.get("project_id") or uuid4()),
            goal=str(payload.get("goal") or "unspecified goal"),
            created_at=str(payload.get("created_at") or now),
            updated_at=str(payload.get("updated_at") or payload.get("last_update") or now),
            current_phase=str(payload.get("current_phase") or "intent"),
            completed_phases=_string_list(payload.get("completed_phases", [])),
            active_task_id=_optional_string(payload.get("active_task_id")),
            open_risks=_string_list(payload.get("open_risks", [])),
            open_decisions=_string_list(payload.get("open_decisions", [])),
            last_packet_id=_optional_string(payload.get("last_packet_id")),
            last_verification_id=_optional_string(payload.get("last_verification_id")),
            history=_dict_list(payload.get("history", [])),
        )

    @classmethod
    def from_legacy_status(cls, payload: dict[str, Any]) -> ProjectState:
        now = utc_now()
        updated_at = str(payload.get("updated_at") or payload.get("last_update") or now)
        state = cls(
            goal=str(payload.get("goal") or "unspecified goal"),
            created_at=str(payload.get("created_at") or updated_at),
            updated_at=updated_at,
            current_phase=str(payload.get("current_phase") or "intent"),
            completed_phases=_string_list(payload.get("completed_phases", [])),
        )

        legacy_history = payload.get("history", [])
        if isinstance(legacy_history, list):
            for index, item in enumerate(legacy_history, start=1):
                if isinstance(item, dict):
                    timestamp = str(item.get("timestamp") or item.get("time") or updated_at)
                    phase = str(item.get("phase") or state.current_phase)
                    summary = str(item.get("summary") or item.get("update") or "")
                else:
                    timestamp = updated_at
                    phase = state.current_phase
                    summary = str(item)
                state.history.append(
                    CheckinRecord(
                        checkin_id=f"CHK-{index:06d}",
                        timestamp=timestamp,
                        phase=phase,
                        summary=summary,
                        next_phase=next_phase_after(state.completed_phases),
                    ).to_dict()
                )

        return state

    def append_checkin(self, phase: str, summary: str, *, timestamp: str | None = None) -> CheckinRecord:
        stamp = timestamp or utc_now()
        self.current_phase = phase
        if phase not in self.completed_phases:
            self.completed_phases.append(phase)
        self.updated_at = stamp
        record = CheckinRecord(
            checkin_id=f"CHK-{len(self.history) + 1:06d}",
            timestamp=stamp,
            phase=phase,
            summary=summary,
            next_phase=next_phase_after(self.completed_phases),
        )
        self.history.append(record.to_dict())
        return record

    def validate(self) -> StateValidationResult:
        return validate_state_payload(self.to_dict())


def coerce_project_state(payload: dict[str, Any]) -> ProjectState:
    if payload.get("schema_version") == CURRENT_STATE_SCHEMA_VERSION:
        return ProjectState.from_dict(payload)
    return ProjectState.from_legacy_status(payload)


def validate_state_payload(payload: dict[str, Any]) -> StateValidationResult:
    result = StateValidationResult()

    schema_version = payload.get("schema_version")
    if schema_version is None:
        result.warnings.append("Legacy status schema detected. Run `mythic-vibe db migrate`.")
    elif schema_version != CURRENT_STATE_SCHEMA_VERSION:
        result.errors.append(f"Unsupported schema_version: {schema_version}")

    if not str(payload.get("project_id") or "").strip() and schema_version is not None:
        result.errors.append("Missing project_id.")

    if not str(payload.get("goal") or "").strip():
        result.errors.append("Missing goal.")

    current_phase = str(payload.get("current_phase") or "")
    if current_phase not in PHASES:
        result.errors.append(f"Invalid current_phase: {current_phase}")

    completed = payload.get("completed_phases", [])
    if not isinstance(completed, list):
        result.errors.append("completed_phases must be a list.")
    else:
        invalid_completed = [str(phase) for phase in completed if str(phase) not in PHASES]
        if invalid_completed:
            result.errors.append(f"Invalid completed_phases values: {', '.join(invalid_completed)}")

    history = payload.get("history", [])
    if not isinstance(history, list):
        result.errors.append("history must be a list.")
    else:
        for index, item in enumerate(history, start=1):
            if not isinstance(item, dict):
                result.errors.append(f"history[{index}] must be an object.")
                continue
            phase = str(item.get("phase") or "")
            if phase and phase not in PHASES:
                result.errors.append(f"Invalid history[{index}].phase: {phase}")

    return result


def next_phase_after(completed_phases: list[str]) -> str:
    for phase in PHASES:
        if phase not in completed_phases:
            return phase
    return "reflect"


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _dict_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]
