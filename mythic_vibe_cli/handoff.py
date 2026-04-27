from __future__ import annotations

from dataclasses import dataclass, field
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .core.state import ProjectState
from .persistence.json_store import JsonStateStore
from .verify import load_latest_verification


@dataclass
class HandoffRecord:
    handoff_id: str
    timestamp: str
    objective: str
    intent: str
    constraints: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    tests_run: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    prompt_packet_suggestion: str = ""
    session_type: str = "reflect"
    branch: str = "unknown"
    verification_id: str | None = None
    verification_result: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "handoff_id": self.handoff_id,
            "timestamp": self.timestamp,
            "objective": self.objective,
            "intent": self.intent,
            "constraints": list(self.constraints),
            "decisions": list(self.decisions),
            "files_changed": list(self.files_changed),
            "tests_run": list(self.tests_run),
            "failures": list(self.failures),
            "next_steps": list(self.next_steps),
            "prompt_packet_suggestion": self.prompt_packet_suggestion,
            "session_type": self.session_type,
            "branch": self.branch,
            "verification_id": self.verification_id,
            "verification_result": self.verification_result,
            "notes": list(self.notes),
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_handoff_id() -> str:
    return f"HND-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:6].upper()}"


def handoff_dir(root: Path) -> Path:
    return root / "mythic" / "handoffs"


def handoff_json_path(root: Path, handoff_id: str) -> Path:
    return handoff_dir(root) / f"{handoff_id}.json"


def handoff_markdown_path(root: Path, handoff_id: str) -> Path:
    return handoff_dir(root) / f"{handoff_id}.md"


def latest_handoff_json_path(root: Path) -> Path:
    return handoff_dir(root) / "latest.json"


def latest_handoff_markdown_path(root: Path) -> Path:
    return handoff_dir(root) / "latest.md"


def session_handoff_doc_path(root: Path) -> Path:
    return root / "docs" / "SESSION_HANDOFF.md"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)


def _git_metadata(root: Path) -> tuple[str, list[str], list[str]]:
    branch = "unknown"
    files_changed: list[str] = []
    warnings: list[str] = []

    branch_proc = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch_proc.returncode == 0:
        branch = branch_proc.stdout.strip() or "unknown"
    else:
        warnings.append("No git branch detected for this workspace.")

    status_proc = _git(root, "status", "--porcelain")
    if status_proc.returncode == 0:
        for line in status_proc.stdout.splitlines():
            if len(line) >= 4:
                files_changed.append(line[3:].strip())
    else:
        warnings.append("No git status could be collected for this workspace.")

    return branch, files_changed, warnings


def _state_summary(state: ProjectState) -> tuple[list[str], list[str]]:
    constraints: list[str] = []
    decisions: list[str] = []

    if state.open_risks:
        constraints.extend(f"Open risk: {item}" for item in state.open_risks)
    if state.open_decisions:
        decisions.extend(state.open_decisions)
    if state.history:
        for item in state.history[-3:]:
            phase = str(item.get("phase") or "unknown")
            summary = str(item.get("summary") or "").strip()
            if summary:
                decisions.append(f"{phase}: {summary}")

    if not constraints:
        constraints.append("Keep the current phase boundaries explicit.")

    if not decisions:
        decisions.append("No recent decisions recorded in project state.")

    return constraints, decisions


def _verification_summary(root: Path) -> tuple[str | None, str | None, list[str], list[str], list[str]]:
    latest = load_latest_verification(root)
    if not latest:
        return None, None, ["No verification record found."], [], ["Run `mythic-vibe verify --commands --docs --invariants --record` before closing."]

    verification_id = str(latest.get("verification_id") or "")
    result = str(latest.get("result") or "blocked")
    commands = latest.get("commands", [])
    tests_run: list[str] = []
    if isinstance(commands, list):
        for item in commands:
            if isinstance(item, dict):
                command = item.get("command", [])
                if isinstance(command, list):
                    tests_run.append(" ".join(str(part) for part in command))

    failures = [str(item) for item in latest.get("errors", []) if str(item)]
    blocked = [str(item) for item in latest.get("blocked_reasons", []) if str(item)]
    if not failures and not blocked and result != "pass":
        failures.append(f"Latest verification result: {result}")

    next_steps: list[str] = []
    if result == "pass":
        next_steps.append("Continue the current work stream or pick the next focused task.")
    else:
        next_steps.append("Resolve verification issues, then rerun `mythic-vibe verify --record`.")
        next_steps.extend(f"Blocked: {item}" for item in blocked)

    return verification_id or None, result, tests_run or ["No commands recorded."], failures, next_steps


def build_handoff_record(
    root: Path,
    *,
    objective: str | None = None,
    next_step: str | None = None,
    note: str | None = None,
    session_type: str = "reflect",
) -> HandoffRecord:
    state = JsonStateStore(root).load_state()
    branch, files_changed, git_warnings = _git_metadata(root)
    verification_id, verification_result, tests_run, failures, verification_next_steps = _verification_summary(root)
    constraints, decisions = _state_summary(state)

    if note:
        constraints.append(note)

    if git_warnings:
        constraints.extend(git_warnings)

    objective_text = objective or state.goal or "Preserve the current work and hand off clearly."
    intent = f"Carry forward the current work on {state.goal}."

    next_steps = [next_step] if next_step else []
    if verification_next_steps:
        next_steps.extend(verification_next_steps)
    if not next_steps:
        next_steps.append("Review the latest handoff and continue from the current state.")

    prompt_packet_suggestion = (
        f'mythic-vibe packet create --task "{objective_text}" --phase "{state.current_phase}" --role "Scribe"'
    )

    return HandoffRecord(
        handoff_id=new_handoff_id(),
        timestamp=utc_now(),
        objective=objective_text,
        intent=intent,
        constraints=constraints,
        decisions=decisions,
        files_changed=files_changed or ["No git changes detected."],
        tests_run=tests_run,
        failures=failures,
        next_steps=next_steps,
        prompt_packet_suggestion=prompt_packet_suggestion,
        session_type=session_type,
        branch=branch,
        verification_id=verification_id,
        verification_result=verification_result,
        notes=[f"Current phase: {state.current_phase}", f"Completed phases: {', '.join(state.completed_phases) or 'none'}"],
    )


def render_handoff_markdown(record: HandoffRecord) -> str:
    def bullets(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "- None"

    return (
        "# Session Handoff\n\n"
        "## Where the work stands\n\n"
        f"- Handoff ID: {record.handoff_id}\n"
        f"- Timestamp: {record.timestamp}\n"
        f"- Branch: {record.branch}\n"
        f"- Session type: {record.session_type}\n"
        f"- Objective: {record.objective}\n"
        f"- Intent: {record.intent}\n"
        f"- Verification: {record.verification_result or 'none'}"
        f"{f' ({record.verification_id})' if record.verification_id else ''}\n\n"
        "## What changed\n\n"
        f"- Files changed:\n{bullets(record.files_changed)}\n"
        f"- Tests run:\n{bullets(record.tests_run)}\n\n"
        "## Decisions made\n\n"
        f"{bullets(record.decisions)}\n\n"
        "## Files touched\n\n"
        f"{bullets(record.files_changed)}\n\n"
        "## Verification run\n\n"
        f"{bullets(record.tests_run)}\n\n"
        "## Known risks\n\n"
        f"{bullets(record.failures or record.constraints)}\n\n"
        "## Next recommended action\n\n"
        f"{bullets(record.next_steps)}\n\n"
        "## Prompt packet suggestion\n\n"
        f"- {record.prompt_packet_suggestion}\n"
    )


def write_handoff_record(root: Path, record: HandoffRecord, *, promote_latest: bool = True) -> tuple[Path, Path]:
    dir_path = handoff_dir(root)
    dir_path.mkdir(parents=True, exist_ok=True)
    json_path = handoff_json_path(root, record.handoff_id)
    md_path = handoff_markdown_path(root, record.handoff_id)
    markdown = render_handoff_markdown(record)
    json_path.write_text(json.dumps(record.to_dict(), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    session_handoff_doc_path(root).parent.mkdir(parents=True, exist_ok=True)
    session_handoff_doc_path(root).write_text(markdown, encoding="utf-8")

    if promote_latest:
        latest_handoff_json_path(root).write_text(json.dumps(record.to_dict(), indent=2) + "\n", encoding="utf-8")
        latest_handoff_markdown_path(root).write_text(markdown, encoding="utf-8")

    return json_path, md_path


def load_handoff_record(root: Path, handoff_id: str) -> HandoffRecord | None:
    path = handoff_json_path(root, handoff_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return HandoffRecord(
        handoff_id=str(payload.get("handoff_id", handoff_id)),
        timestamp=str(payload.get("timestamp", "")),
        objective=str(payload.get("objective", "")),
        intent=str(payload.get("intent", "")),
        constraints=[str(item) for item in payload.get("constraints", []) if str(item)],
        decisions=[str(item) for item in payload.get("decisions", []) if str(item)],
        files_changed=[str(item) for item in payload.get("files_changed", []) if str(item)],
        tests_run=[str(item) for item in payload.get("tests_run", []) if str(item)],
        failures=[str(item) for item in payload.get("failures", []) if str(item)],
        next_steps=[str(item) for item in payload.get("next_steps", []) if str(item)],
        prompt_packet_suggestion=str(payload.get("prompt_packet_suggestion", "")),
        session_type=str(payload.get("session_type", "reflect")),
        branch=str(payload.get("branch", "unknown")),
        verification_id=payload.get("verification_id"),
        verification_result=payload.get("verification_result"),
        notes=[str(item) for item in payload.get("notes", []) if str(item)],
    )


def load_latest_handoff(root: Path) -> HandoffRecord | None:
    path = latest_handoff_json_path(root)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    handoff_id = str(payload.get("handoff_id") or "")
    if handoff_id:
        record = load_handoff_record(root, handoff_id)
        if record is not None:
            return record
    return HandoffRecord(
        handoff_id=str(payload.get("handoff_id", "latest")),
        timestamp=str(payload.get("timestamp", "")),
        objective=str(payload.get("objective", "")),
        intent=str(payload.get("intent", "")),
        constraints=[str(item) for item in payload.get("constraints", []) if str(item)],
        decisions=[str(item) for item in payload.get("decisions", []) if str(item)],
        files_changed=[str(item) for item in payload.get("files_changed", []) if str(item)],
        tests_run=[str(item) for item in payload.get("tests_run", []) if str(item)],
        failures=[str(item) for item in payload.get("failures", []) if str(item)],
        next_steps=[str(item) for item in payload.get("next_steps", []) if str(item)],
        prompt_packet_suggestion=str(payload.get("prompt_packet_suggestion", "")),
        session_type=str(payload.get("session_type", "reflect")),
        branch=str(payload.get("branch", "unknown")),
        verification_id=payload.get("verification_id"),
        verification_result=payload.get("verification_result"),
        notes=[str(item) for item in payload.get("notes", []) if str(item)],
    )


def list_handoffs(root: Path) -> list[HandoffRecord]:
    dir_path = handoff_dir(root)
    if not dir_path.exists():
        return []
    records: list[HandoffRecord] = []
    for path in sorted(dir_path.glob("HND-*.json")):
        record = load_handoff_record(root, path.stem)
        if record is not None:
            records.append(record)
    return sorted(records, key=lambda item: item.timestamp)
