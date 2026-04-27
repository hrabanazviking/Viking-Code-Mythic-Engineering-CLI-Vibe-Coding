from __future__ import annotations

import ast
from dataclasses import dataclass
import json
from pathlib import Path
import textwrap

from .core.state import PHASES, ProjectState, next_phase_after, utc_now, validate_state_payload
from .handoff import load_latest_handoff
from .persistence.json_store import JsonStateStore, StateStoreError
from .persistence.migrations import migrate_project_state

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
            self.docs_dir / "INDEX.md": self._index_template(),
            self.docs_dir / "COMMAND_CONTRACTS.md": self._command_contracts_template(),
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
        if normalized == "reflect":
            self._require_successful_verification()

        self.mythic_dir.mkdir(parents=True, exist_ok=True)
        devlog_path = self.docs_dir / "DEVLOG.md"
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        migrate_project_state(self.root)
        store = JsonStateStore(self.root)
        state = store.load_state()
        timestamp = utc_now()
        state.append_checkin(normalized, update, timestamp=timestamp)
        status_path = store.write_state(state)

        if not devlog_path.exists():
            devlog_path.write_text(self._devlog_template(), encoding="utf-8")

        with devlog_path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## {timestamp} | {normalized.title()}\n- {update}\n")

        return status_path, devlog_path

    def _require_successful_verification(self) -> None:
        latest_path = self.mythic_dir / "verifications" / "latest.json"
        if not latest_path.exists():
            raise ValueError("Reflection is blocked until a successful verification is recorded. Run `mythic-vibe verify --record` first.")

        try:
            payload = json.loads(latest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read latest verification record: {exc}") from exc

        if not isinstance(payload, dict):
            raise ValueError("Latest verification record is invalid.")
        if payload.get("result") != "pass":
            raise ValueError("Reflection is blocked until the latest verification result is `pass`.")

    def status_summary(self) -> str:
        status_path = self.mythic_dir / "status.json"
        if not status_path.exists():
            return "No Mythic status found. Run `mythic-vibe init --goal \"...\"` first."

        try:
            state = JsonStateStore(self.root).load_state()
        except StateStoreError:
            state = ProjectState(goal="unspecified goal")
        completed = [phase for phase in state.completed_phases if phase in PHASES]
        progress = int((len(completed) / len(PHASES)) * 100)
        latest_handoff = load_latest_handoff(self.root)
        handoff_line = ""
        if latest_handoff:
            handoff_line = (
                f"\nLatest handoff: {self.root / 'docs' / 'SESSION_HANDOFF.md'}"
                f"\nLatest handoff ID: {latest_handoff.handoff_id}"
                f"\nNext handoff action: {latest_handoff.next_steps[0] if latest_handoff.next_steps else 'review the handoff'}"
            )
        return textwrap.dedent(
            f"""
            Goal: {state.goal}
            Current phase: {state.current_phase}
            Progress: {progress}% ({len(completed)}/{len(PHASES)} phases touched)
            Last update: {state.updated_at}
            Next suggested phase: {next_phase_after(completed)}{handoff_line}
            """
        ).strip()

    def doctor_report(self, repo_boundary: bool = False, project_scaffold: bool = True) -> dict[str, object]:
        errors: list[str] = []
        warnings: list[str] = []
        sections: dict[str, list[str]] = {
            "required_artifacts": [],
            "state": [],
            "docs": [],
            "boundary": [],
        }

        if project_scaffold:
            required = [
                self.root / "MYTHIC_ENGINEERING.md",
                self.root / "SYSTEM_VISION.md",
                self.docs_dir / "PHILOSOPHY.md",
                self.docs_dir / "ARCHITECTURE.md",
                self.docs_dir / "DOMAIN_MAP.md",
                self.docs_dir / "DATA_FLOW.md",
                self.docs_dir / "DEVLOG.md",
                self.docs_dir / "INDEX.md",
                self.tasks_dir / "current_GOALS.md",
                self.mythic_dir / "plan.md",
                self.mythic_dir / "loop.md",
                self.mythic_dir / "status.json",
            ]

            for path in required:
                if not path.exists():
                    errors.append(f"Missing required file: {path.relative_to(self.root)}")
                else:
                    sections["required_artifacts"].append(path.relative_to(self.root).as_posix())

            status_path = self.mythic_dir / "status.json"
            if status_path.exists():
                try:
                    state = JsonStateStore(self.root).read_payload()
                except StateStoreError:
                    errors.append("Invalid JSON in mythic/status.json")
                    state = None

                if state:
                    validation = validate_state_payload(state)
                    errors.extend(validation.errors)
                    warnings.extend(validation.warnings)
                    if not state.get("history"):
                        warnings.append("No check-in history yet. Run `mythic-vibe checkin` after your next milestone.")
                    state_report_errors, state_report_warnings = self._doctor_state_coherence(state)
                    errors.extend(state_report_errors)
                    warnings.extend(state_report_warnings)
                    sections["state"].append(f"current_phase={state.get('current_phase')}")
                    sections["state"].append(f"completed_phases={len(state.get('completed_phases', []))}")

        if repo_boundary:
            boundary_errors, boundary_warnings, boundary_sections = self._doctor_repo_boundary()
            errors.extend(boundary_errors)
            warnings.extend(boundary_warnings)
            sections["boundary"].extend(boundary_sections)

        if not repo_boundary:
            doc_errors, doc_warnings, doc_sections = self._doctor_docs_drift(project_scaffold=project_scaffold)
            errors.extend(doc_errors)
            warnings.extend(doc_warnings)
            sections["docs"].extend(doc_sections)

        ok = not errors
        return {
            "ok": ok,
            "errors": errors,
            "warnings": warnings,
            "sections": sections,
        }

    def doctor(self, repo_boundary: bool = False, project_scaffold: bool = True) -> tuple[list[str], list[str]]:
        report = self.doctor_report(repo_boundary=repo_boundary, project_scaffold=project_scaffold)
        return list(report["errors"]), list(report["warnings"])

    def _doctor_state_coherence(self, payload: dict[str, object]) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        completed = [str(item) for item in payload.get("completed_phases", []) if str(item) in PHASES]
        current_phase = str(payload.get("current_phase") or "")
        phase_order = {phase: index for index, phase in enumerate(PHASES)}

        for previous, current in zip(completed, completed[1:]):
            if phase_order[current] < phase_order[previous]:
                errors.append(
                    "Phase order regressed in completed_phases: "
                    f"{previous} -> {current}"
                )
                break

        if completed and current_phase and current_phase != completed[-1]:
            warnings.append(
                "current_phase does not match the latest completed phase; "
                "the project state may be stale."
            )

        if payload.get("last_verification_id") and not (self.mythic_dir / "verifications" / "latest.json").exists():
            warnings.append("last_verification_id is set but no verification artifact exists at mythic/verifications/latest.json.")

        return errors, warnings

    def _doctor_repo_boundary(self) -> tuple[list[str], list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        sections: list[str] = []
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
            else:
                sections.append(path.relative_to(self.root).as_posix())

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

        return errors, warnings, sections

    def _doctor_docs_drift(self, *, project_scaffold: bool) -> tuple[list[str], list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        sections: list[str] = []

        index_path = self.docs_dir / "INDEX.md"
        legacy_index_path = self.docs_dir / "index2.md"
        contracts_path = self.docs_dir / "COMMAND_CONTRACTS.md"
        active_doc_candidates = [
            self.docs_dir / "ARCHITECTURE.md",
            self.docs_dir / "DOMAIN_MAP.md",
            self.docs_dir / "DATA_FLOW.md",
            self.docs_dir / "PHILOSOPHY.md",
            index_path,
            contracts_path,
        ]
        active_docs_present = project_scaffold or any(path.exists() for path in active_doc_candidates)

        if active_docs_present:
            if index_path.exists():
                sections.append(index_path.relative_to(self.root).as_posix())
            else:
                errors.append("Missing canonical docs index: docs/INDEX.md")

            if legacy_index_path.exists() and index_path.exists():
                warnings.append("Legacy docs/index2.md is still present; prefer docs/INDEX.md as the canonical hub.")

            if contracts_path.exists():
                sections.append(contracts_path.relative_to(self.root).as_posix())
                contract_text = contracts_path.read_text(encoding="utf-8", errors="replace")
                required_terms = ["doctor", "scry", "verify", "packet", "ai", "plunder"]
                missing_terms = [term for term in required_terms if term not in contract_text]
                if missing_terms:
                    warnings.append(
                        "docs/COMMAND_CONTRACTS.md may be drifting from the current command surface: "
                        + ", ".join(missing_terms)
                    )
            else:
                errors.append("Missing command contract doc: docs/COMMAND_CONTRACTS.md")

            for adr_path in [
                self.docs_dir / "ADRS" / "ADR-0003-verification-gates.md",
                self.docs_dir / "ADRS" / "ADR-0004-doctor-diagnostics.md",
            ]:
                if adr_path.exists():
                    sections.append(adr_path.relative_to(self.root).as_posix())
                else:
                    errors.append(f"Missing major-change ADR: {adr_path.relative_to(self.root)}")

            if (self.docs_dir / "SYSTEM_VISION.md").exists() and (self.docs_dir / "PHILOSOPHY.md").exists():
                sections.append("vision-and-philosophy-linked")

        return errors, warnings, sections

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
        next_phase = next_phase_after(completed)
        if len([phase for phase in completed if phase in PHASES]) == len(PHASES):
            return "reflect (all phases completed at least once)"
        return next_phase

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
        now = utc_now()
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
        return json.dumps(ProjectState(goal=goal).to_dict(), indent=2)

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

    def _index_template(self) -> str:
        return textwrap.dedent(
            """
            # Documentation Hub

            This hub orients contributors to the active Mythic Vibe CLI product and the surrounding mythic engineering workspace.

            ## Start Here

            - `REPO_BOUNDARY.md` - repository-level active runtime and dormant island law.
            - `docs/ACTIVE_PRODUCT_BOUNDARY.md` - exact product paths and runtime contract.
            - `docs/DORMANT_ISLANDS.md` - quarantined reference, research, and vendor surfaces.
            - `docs/ARCHITECTURE.md` - active runtime architecture and dependency direction.
            - `docs/DOMAIN_MAP.md` - ownership map and routing rules.
            - `docs/COMMAND_CONTRACTS.md` - CLI entrypoints, dispatch registry, aliases, and exit codes.
            - `docs/DATA_FLOW.md` - state and artifact movement through the active CLI.
            """
        ).strip() + "\n"

    def _command_contracts_template(self) -> str:
        return textwrap.dedent(
            """
            # Command Contracts

            This document records the active Mythic Vibe CLI command-kernel contract.

            ## Entrypoints

            - `mythic-vibe --help`
            - `mythic --help`
            - `python -m mythic_vibe_cli --help`
            - `python -m mythic_vibe_cli.cli --help`

            ## Dispatch Contract

            New commands and ritual aliases must add parser support in `mythic_vibe_cli.app`, implementation in `mythic_vibe_cli.commands`, and registry wiring in `COMMAND_HANDLERS`.

            Current compatibility aliases:

            - `start` -> `init`
            - `imbue` -> `init`
            - `evoke` -> `codex-pack`
            - `scry` -> `doctor`

            ## Exit-Code Policy

            Commands should return the named exit-code constants from `mythic_vibe_cli.exit_codes`.
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
