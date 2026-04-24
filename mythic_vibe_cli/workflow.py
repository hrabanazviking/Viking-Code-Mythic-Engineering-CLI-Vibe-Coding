from __future__ import annotations

import ast
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

FORBIDDEN_RUNTIME_IMPORT_ROOTS = {
    "ai",
    "core",
    "systems",
    "sessions",
    "yggdrasil",
    "imports",
    "mindspark_thoughtform",
    "ollama",
    "whisper",
    "chatterbox",
}


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
            self.root / "SYSTEM_VISION.md": self._vision_template(config.goal),
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

        state = self._load_status(status_path)

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        state["current_phase"] = normalized
        completed = [p for p in state.get("completed_phases", []) if p in PHASES]
        if normalized not in completed:
            completed.append(normalized)
        state["completed_phases"] = completed
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

        state = self._load_status(status_path)
        completed = [phase for phase in state.get("completed_phases", []) if phase in PHASES]
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

    def doctor(self, repo_boundary: bool = False, project_scaffold: bool = True) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []

        if project_scaffold:
            required = [
                self.root / "MYTHIC_ENGINEERING.md",
                self.root / "SYSTEM_VISION.md",
                self.docs_dir / "PHILOSOPHY.md",
                self.docs_dir / "ARCHITECTURE.md",
                self.docs_dir / "DOMAIN_MAP.md",
                self.docs_dir / "DATA_FLOW.md",
                self.docs_dir / "DEVLOG.md",
                self.tasks_dir / "current_GOALS.md",
                self.mythic_dir / "plan.md",
                self.mythic_dir / "loop.md",
                self.mythic_dir / "status.json",
            ]

            for path in required:
                if not path.exists():
                    errors.append(f"Missing required file: {path.relative_to(self.root)}")

            status_path = self.mythic_dir / "status.json"
            if status_path.exists():
                try:
                    state = json.loads(status_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    errors.append("Invalid JSON in mythic/status.json")
                    state = None

                if state:
                    current = state.get("current_phase")
                    if current and current not in PHASES:
                        errors.append(f"Invalid current_phase in status.json: {current}")

                    completed = state.get("completed_phases", [])
                    invalid = [phase for phase in completed if phase not in PHASES]
                    if invalid:
                        errors.append(f"Invalid completed_phases values: {', '.join(invalid)}")

                    if not state.get("history"):
                        warnings.append("No check-in history yet. Run `mythic-vibe checkin` after your next milestone.")

        if repo_boundary:
            self._doctor_repo_boundary(errors, warnings)

        return errors, warnings

    def _doctor_repo_boundary(self, errors: list[str], warnings: list[str]) -> None:
        required_boundary_docs = [
            self.root / "REPO_BOUNDARY.md",
            self.docs_dir / "ACTIVE_PRODUCT_BOUNDARY.md",
            self.docs_dir / "DORMANT_ISLANDS.md",
            self.docs_dir / "ADRS" / "ADR-0001-active-runtime-boundary.md",
            self.docs_dir / "ADRS" / "ADR-0002-no-direct-vendor-imports.md",
        ]

        for path in required_boundary_docs:
            if not path.exists():
                errors.append(f"Missing repo boundary file: {path.relative_to(self.root)}")

        readme = self.root / "README.md"
        if readme.exists() and "Active Runtime Path" not in readme.read_text(encoding="utf-8", errors="replace"):
            warnings.append("README.md does not include an 'Active Runtime Path' section.")

        active_package = self.root / "mythic_vibe_cli"
        if not active_package.exists():
            errors.append("Missing active runtime package: mythic_vibe_cli")
            return

        for path in sorted(active_package.rglob("*.py")):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                errors.append(f"Cannot parse active runtime file {path.relative_to(self.root)}: {exc.msg}")
                continue

            for module_name, line_no in self._absolute_imports(tree):
                root_name = module_name.split(".", 1)[0]
                if root_name in FORBIDDEN_RUNTIME_IMPORT_ROOTS:
                    errors.append(
                        "Forbidden active runtime import "
                        f"in {path.relative_to(self.root)}:{line_no}: {module_name}"
                    )

    def _absolute_imports(self, tree: ast.AST) -> list[tuple[str, int]]:
        imports: list[tuple[str, int]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    continue
                if node.module:
                    imports.append((node.module, node.lineno))
        return imports

    def _load_status(self, status_path: Path) -> dict:
        if not status_path.exists():
            return json.loads(self._status_template("unspecified goal"))

        try:
            state = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return json.loads(self._status_template("unspecified goal"))

        if not isinstance(state, dict):
            return json.loads(self._status_template("unspecified goal"))

        state.setdefault("goal", "unspecified goal")
        state.setdefault("current_phase", "intent")
        state.setdefault("completed_phases", [])
        state.setdefault("last_update", None)
        state.setdefault("history", [])
        return state

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

    def _vision_template(self, goal: str) -> str:
        return textwrap.dedent(
            f"""
            # SYSTEM_VISION

            ## Why this system exists
            {goal}

            ## Core entities
            - Entity 1:
            - Entity 2:

            ## Non-goals
            - Out of scope 1:
            - Out of scope 2:

            ## Invariants
            - Invariant 1:
            - Invariant 2:
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

            ## Inputs
            List external and internal inputs.

            ## Transformations
            Document processing steps and ownership.

            ## Outputs
            Define side effects, storage, and user-facing results.
            """
        ).strip() + "\n"

    def _devlog_template(self) -> str:
        return textwrap.dedent(
            """
            # Devlog

            Chronological updates from the Mythic loop.
            """
        ).strip() + "\n"

    def _goals_template(self, goal: str) -> str:
        return textwrap.dedent(
            f"""
            # Current Goals

            Primary goal:
            - {goal}

            Success criteria:
            - [ ] Users can complete the key workflow.
            - [ ] Architecture boundaries are documented.
            - [ ] Verification commands are documented and passing.
            """
        ).strip() + "\n"
