from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .ai.prompts.roles import ROLE_PROMPTS, RolePrompt
from .codex_bridge import CodexPacketRequest
from .core.state import utc_now


DEFAULT_ROLE_SEQUENCE = (
    "Skald",
    "Architect",
    "Cartographer",
    "Forge Worker",
    "Auditor",
    "Scribe",
)

ROLE_PHASES = {
    "Skald": "intent",
    "Architect": "architecture",
    "Cartographer": "plan",
    "Forge Worker": "build",
    "Auditor": "verify",
    "Scribe": "reflect",
    "Debugger": "verify",
    "Refactorer": "build",
}

ROLE_OBJECTIVES = {
    "Skald": "Name the deeper purpose and frame the desired outcome.",
    "Architect": "Define ownership, boundaries, dependency direction, and invariants.",
    "Cartographer": "Map affected files, data flow, relationships, and likely blast radius.",
    "Forge Worker": "Implement the smallest working change that fits the plan.",
    "Auditor": "Verify behavior, inspect edge cases, and surface regressions.",
    "Scribe": "Record what changed, why it matters, and what should happen next.",
    "Debugger": "Reproduce, isolate, repair, and prove the failure is gone.",
    "Refactorer": "Improve internal shape while preserving behavior.",
}


@dataclass(frozen=True)
class WorkflowStep:
    step_id: str
    role: str
    phase: str
    objective: str
    identity: str
    focus: str
    system_prompt: str
    invariants: tuple[str, ...]
    verification: tuple[str, ...]
    handoff_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "role": self.role,
            "phase": self.phase,
            "objective": self.objective,
            "identity": self.identity,
            "focus": self.focus,
            "system_prompt": self.system_prompt,
            "invariants": list(self.invariants),
            "verification": list(self.verification),
            "handoff_to": self.handoff_to,
        }

    def packet_request(self, task: str, audience: str = "advanced") -> CodexPacketRequest:
        return CodexPacketRequest(
            task=f"{task}\n\nStep objective: {self.objective}",
            phase=self.phase,
            audience=audience,
            role=self.role,
        )


@dataclass(frozen=True)
class WorkflowPlan:
    task: str
    created_at: str
    steps: tuple[WorkflowStep, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "created_at": self.created_at,
            "steps": [step.to_dict() for step in self.steps],
        }

    def packet_requests(self, audience: str = "advanced") -> list[CodexPacketRequest]:
        return [step.packet_request(self.task, audience=audience) for step in self.steps]


class WorkflowEngine:
    def __init__(self, root: Path):
        self.root = root
        self.mythic_dir = root / "mythic"

    def build_plan(
        self,
        task: str,
        *,
        role_sequence: tuple[str, ...] = DEFAULT_ROLE_SEQUENCE,
    ) -> WorkflowPlan:
        normalized_task = task.strip()
        if not normalized_task:
            raise ValueError("Workflow task is required.")
        if not role_sequence:
            raise ValueError("Workflow role_sequence must include at least one role.")

        unknown_roles = [role for role in role_sequence if role not in ROLE_PROMPTS]
        if unknown_roles:
            raise ValueError(f"Unsupported workflow roles: {', '.join(unknown_roles)}")

        steps: list[WorkflowStep] = []
        for index, role in enumerate(role_sequence, start=1):
            prompt = ROLE_PROMPTS[role]
            handoff_to = role_sequence[index] if index < len(role_sequence) else None
            steps.append(self._build_step(index, prompt, handoff_to=handoff_to))

        return WorkflowPlan(task=normalized_task, created_at=utc_now(), steps=tuple(steps))

    def write_plan(
        self,
        task: str,
        *,
        role_sequence: tuple[str, ...] = DEFAULT_ROLE_SEQUENCE,
        out_file: Path | None = None,
    ) -> Path:
        plan = self.build_plan(task, role_sequence=role_sequence)
        target = out_file or self.mythic_dir / "workflow_plan.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(plan.to_dict(), indent=2) + "\n", encoding="utf-8")
        return target

    def _build_step(self, index: int, prompt: RolePrompt, *, handoff_to: str | None) -> WorkflowStep:
        return WorkflowStep(
            step_id=f"step-{index:02d}",
            role=prompt.name,
            phase=ROLE_PHASES[prompt.name],
            objective=ROLE_OBJECTIVES[prompt.name],
            identity=prompt.identity,
            focus=prompt.focus,
            system_prompt=prompt.system_prompt,
            invariants=prompt.invariants,
            verification=prompt.verification,
            handoff_to=handoff_to,
        )
