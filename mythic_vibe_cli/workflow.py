from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import textwrap


PHASES = [
    "intent",
    "constraints",
    "architecture",
    "plan",
    "build",
    "verify",
    "reflect",
]


@dataclass
class MythicRunConfig:
    goal: str
    noob_mode: bool


class MythicWorkflow:
    def __init__(self, root: Path):
        self.root = root
        self.docs_dir = root / "docs"
        self.tasks_dir = root / "tasks"
        self.mythic_dir = root / "mythic"

    def init_project(self, config: MythicRunConfig, method_source: str) -> list[Path]:
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self.mythic_dir.mkdir(parents=True, exist_ok=True)
        (self.docs_dir / "DECISIONS").mkdir(parents=True, exist_ok=True)

        files: dict[Path, str] = {
            self.root / "MYTHIC_ENGINEERING.md": self._mythic_engineering_note(method_source),
            self.docs_dir / "PHILOSOPHY.md": self._philosophy_template(config.goal),
            self.docs_dir / "ARCHITECTURE.md": self._architecture_template(),
            self.docs_dir / "DOMAIN_MAP.md": self._domain_map_template(),
            self.docs_dir / "DATA_FLOW.md": self._data_flow_template(),
            self.docs_dir / "DEVLOG.md": self._devlog_template(),
            self.tasks_dir / "current_GOALS.md": self._goals_template(config.goal),
            self.mythic_dir / "plan.md": self._plan_template(config.goal, config.noob_mode),
            self.mythic_dir / "loop.md": self._loop_template(config.noob_mode),
            self.mythic_dir / "status.json": self._status_template(config.goal),
        }

        written: list[Path] = []
        for path, content in files.items():
            if not path.exists():
                path.write_text(content, encoding="utf-8")
                written.append(path)

        return written

    def check_in(self, phase: str, update: str) -> tuple[Path, Path]:
        normalized = phase.strip().lower()
        if normalized not in PHASES:
            valid = ", ".join(PHASES)
            raise ValueError(f"Invalid phase '{phase}'. Choose one of: {valid}")

        self.mythic_dir.mkdir(parents=True, exist_ok=True)
        status_path = self.mythic_dir / "status.json"
        devlog_path = self.docs_dir / "DEVLOG.md"
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        if status_path.exists():
            state = json.loads(status_path.read_text(encoding="utf-8"))
        else:
            state = json.loads(self._status_template("unspecified goal"))

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        state["current_phase"] = normalized
        state["completed_phases"] = sorted(set(state.get("completed_phases", []) + [normalized]))
        state["last_update"] = timestamp
        history = state.setdefault("history", [])
        history.append({"time": timestamp, "phase": normalized, "update": update})
        status_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

        if not devlog_path.exists():
            devlog_path.write_text(self._devlog_template(), encoding="utf-8")

        with devlog_path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## {timestamp} | {normalized.title()}\n- {update}\n")

        return status_path, devlog_path

    def status_summary(self) -> str:
        status_path = self.mythic_dir / "status.json"
        if not status_path.exists():
            return "No Mythic status found. Run `mythic-vibe init --goal \"...\"` first."

        state = json.loads(status_path.read_text(encoding="utf-8"))
        completed = state.get("completed_phases", [])
        progress = int((len(completed) / len(PHASES)) * 100)
        return textwrap.dedent(
            f"""
            Goal: {state.get('goal', 'n/a')}
            Current phase: {state.get('current_phase', 'intent')}
            Progress: {progress}% ({len(completed)}/{len(PHASES)} phases touched)
            Last update: {state.get('last_update', 'n/a')}
            Next suggested phase: {self._next_phase(completed)}
            """
        ).strip()

    def _next_phase(self, completed: list[str]) -> str:
        for phase in PHASES:
            if phase not in completed:
                return phase
        return "reflect (all phases completed at least once)"

    def _mythic_engineering_note(self, method_source: str) -> str:
        return textwrap.dedent(
            f"""
            # MYTHIC_ENGINEERING

            This repository is being developed using Mythic Engineering practices.

            Canonical source: {method_source}

            Core loop enforced by this CLI:
            1. Intent
            2. Constraints
            3. Architecture
            4. Plan
            5. Build
            6. Verify
            7. Reflect
            """
        ).strip() + "\n"

    def _plan_template(self, goal: str, noob_mode: bool) -> str:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        beginner_tips = "Enabled" if noob_mode else "Disabled"
        return textwrap.dedent(
            f"""
            # Mythic Plan

            - Created: {now}
            - Goal: {goal}
            - Beginner guidance: {beginner_tips}

            ## 1) Intent
            Define the user outcome in one sentence.

            ## 2) Constraints
            - Time box:
            - Tech constraints:
            - Quality / safety constraints:

            ## 3) Architecture
            - What subsystem owns this change?
            - What must remain true (invariants)?

            ## 4) Milestones
            - [ ] Milestone 1:
            - [ ] Milestone 2:
            - [ ] Milestone 3:

            ## 5) Verification strategy
            - Command/check:
            - Expected outcome:

            ## 6) Reflection
            - What worked:
            - What to improve:
            """
        ).strip() + "\n"

    def _loop_template(self, noob_mode: bool) -> str:
        help_line = (
            "For each phase, write one plain-language sentence first, then technical detail."
            if noob_mode
            else "Write concise notes for each phase."
        )
        phases_md = "\n".join(f"## {idx + 1}. {name.title()}\n- Notes:\n" for idx, name in enumerate(PHASES))
        return textwrap.dedent(
            f"""
            # Mythic Execution Loop

            {help_line}

            {phases_md}
            """
        ).strip() + "\n"

    def _status_template(self, goal: str) -> str:
        return json.dumps(
            {
                "goal": goal,
                "current_phase": "intent",
                "completed_phases": [],
                "last_update": None,
                "history": [],
            },
            indent=2,
        )

    def _philosophy_template(self, goal: str) -> str:
        return textwrap.dedent(
            f"""
            # Philosophy

            ## Deep intent
            Build {goal} as a coherent, maintainable system.

            ## Values
            - architecture before patching
            - explicit ownership and boundaries
            - documentation as continuity memory
            - test and verify every meaningful change

            ## Anti-goals
            - random prompt spam
            - hidden logic and undocumented coupling
            - shipping changes without verification
            """
        ).strip() + "\n"

    def _architecture_template(self) -> str:
        return textwrap.dedent(
            """
            # Architecture

            ## Subsystems
            - Interface layer
            - Domain logic layer
            - Data / persistence layer
            - Integrations layer

            ## Boundaries
            Describe what each subsystem owns and does not own.

            ## Invariants
            List truths that must remain true during refactors.
            """
        ).strip() + "\n"

    def _domain_map_template(self) -> str:
        return textwrap.dedent(
            """
            # Domain Map

            ## Core domains
            - Domain A:
            - Domain B:

            ## Ownership
            For each domain, define responsibilities and interfaces.
            """
        ).strip() + "\n"

    def _data_flow_template(self) -> str:
        return textwrap.dedent(
            """
            # Data Flow

            ## Input -> Processing -> Output
            - Input source:
            - Validation:
            - Transformation:
            - Storage / output:

            ## Side effects
            Document external effects (I/O, network, file writes).
            """
        ).strip() + "\n"

    def _goals_template(self, goal: str) -> str:
        return textwrap.dedent(
            f"""
            # Current Goals

            ## Outcome
            {goal}

            ## Acceptance criteria
            - [ ] Criterion 1
            - [ ] Criterion 2
            - [ ] Criterion 3

            ## Risks
            - Risk 1
            - Risk 2
            """
        ).strip() + "\n"

    def _devlog_template(self) -> str:
        return textwrap.dedent(
            """
            # Devlog

            Chronological change notes and reasons.
            """
        ).strip() + "\n"
