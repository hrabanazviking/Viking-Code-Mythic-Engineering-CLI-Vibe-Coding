from __future__ import annotations

import argparse
from collections.abc import Callable
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import sqlite3
import urllib.error

from .codex_bridge import CodexBridge, CodexPacketRequest, PacketRecord
from .ai.registry import ProviderRegistry
from .context.indexer import ProjectIndexer
from .config import ConfigStore
from .errors import CliError, format_error
from .exit_codes import OPERATIONAL_FAILURE, SUCCESS, UNSAFE_OPERATION_BLOCKED, USER_INPUT_ERROR, VERIFICATION_FAILURE
from .handoff import (
    HandoffRecord,
    build_handoff_record,
    load_latest_handoff,
    load_handoff_record,
    render_handoff_markdown,
    write_handoff_record,
)
from .mythic_data import MethodStore
from .output import write_bullet, write_error, write_json, write_key_value, write_line, write_verbose
from .plunder.github import GitHubClient
from .plunder.license import classify_license
from .plunder.provenance import (
    PlunderPlan,
    append_record,
    cache_path_for,
    load_plan,
    record_from_plan,
    update_notice,
    write_plan,
)
from .plugins.api import PLUGIN_HOOKS
from .plugins.dispatcher import PluginHookDispatcher
from .plugins.loader import inspect_plugin
from .plugins.registry import PluginRegistry
from .runtime.slash_commands import BUILTIN_SLASH_COMMANDS, BuiltinSlashCommand, SlashCommandInfo
from .core.state import PHASES, VerificationRecord, coerce_project_state, utc_now, validate_state_payload
from .persistence.json_store import JsonStateStore, StateStoreError
from .persistence.migrations import migrate_project_state
from .ux import (
    ARTIFACT_GUIDE,
    EXAMPLES,
    PHASE_GUIDE,
    bash_completion,
    next_phase_from_completed,
    phase_names,
    powershell_completion,
    zsh_completion,
)
from .workflow import MythicRunConfig, MythicWorkflow
from .workflow_engine import (
    DEFAULT_ROLE_SEQUENCE,
    WORKFLOW_PLAN_FILENAME,
    WorkflowEngine,
    WorkflowPlan,
)
from .verify import VerificationArtifact, load_latest_verification, new_verification_id, write_verification_artifact
from .verify.doc_checker import check_docs
from .verify.git_diff import review_changed_files
from .verify.invariant_checker import check_invariants
from .verify.test_runner import discover_default_commands, run_command, run_default_commands
from .forge import cmd_forge_dispatch


CommandHandler = Callable[[argparse.Namespace], int]


def _flag(args: argparse.Namespace, name: str) -> bool:
    return bool(getattr(args, name, False))


def _status_payload(root: Path) -> dict[str, object]:
    store = JsonStateStore(root)
    if not store.status_path.exists():
        return {
            "status_found": False,
            "path": str(store.status_path),
            "message": 'No Mythic status found. Run `mythic-vibe init --goal "..."` first.',
        }

    try:
        payload = store.read_payload()
    except StateStoreError as exc:
        return {
            "status_found": True,
            "valid": False,
            "path": str(store.status_path),
            "error": str(exc),
        }

    if payload is None:
        return {
            "status_found": False,
            "path": str(store.status_path),
            "message": 'No Mythic status found. Run `mythic-vibe init --goal "..."` first.',
        }

    state = coerce_project_state(payload)
    validation = validate_state_payload(payload)
    completed = [phase for phase in state.completed_phases if phase in PHASES]
    progress = int((len(completed) / len(PHASES)) * 100)
    latest_handoff = load_latest_handoff(root)
    return {
        "status_found": True,
        "valid": validation.ok,
        "path": str(store.status_path),
        "schema_version": state.schema_version,
        "goal": state.goal,
        "current_phase": state.current_phase,
        "completed_phases": completed,
        "progress_percent": progress,
        "last_update": state.updated_at,
        "latest_handoff_id": latest_handoff.handoff_id if latest_handoff else None,
        "latest_handoff_path": str(root / "docs" / "SESSION_HANDOFF.md") if latest_handoff else None,
        "latest_handoff_next_step": latest_handoff.next_steps[0] if latest_handoff and latest_handoff.next_steps else None,
        "errors": validation.errors,
        "warnings": validation.warnings,
    }


def _command_name(args: argparse.Namespace, fallback: str) -> str:
    command = getattr(args, "command", "")
    subcommand_attr = None
    if command == "packet":
        subcommand_attr = getattr(args, "packet_command", "")
    elif command == "db":
        subcommand_attr = getattr(args, "db_command", "")
    elif command == "state":
        subcommand_attr = getattr(args, "state_command", "")
    elif command == "config":
        subcommand_attr = getattr(args, "config_command", "")
    elif command == "grimoire":
        subcommand_attr = getattr(args, "grimoire_command", "")
    elif command == "plugin":
        subcommand_attr = getattr(args, "plugin_command", "")
    elif command == "handoff":
        subcommand_attr = getattr(args, "handoff_command", "")
    elif command == "explain":
        subcommand_attr = getattr(args, "explain_command", "")
    elif command == "method":
        subcommand_attr = getattr(args, "method_command", "")
    elif command == "workflow":
        subcommand_attr = getattr(args, "workflow_command", "")

    if subcommand_attr:
        return f"{command} {subcommand_attr}"
    if command:
        return command
    return fallback


def _method_store(root: Path | None = None) -> MethodStore:
    loaded = ConfigStore(root).load() if root else ConfigStore().load()
    return MethodStore(method_source=loaded.config.method_source)


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    interactive = _flag(args, "interactive")
    force = _flag(args, "force")

    # Phase 20.0 (audit remediation 2026-05-02): --goal is no longer
    # argparse-required because --interactive prompts for it. Validate
    # the "must have one path to a goal" invariant here so callers
    # without either flag get a clear USER_INPUT_ERROR instead of a
    # downstream NoneType crash.
    if not interactive and not (args.goal and str(args.goal).strip()):
        write_error(
            "init requires --goal <text> OR --interactive. "
            "Pass --goal to run non-interactively (the original behaviour) "
            "or --interactive to launch the Q&A wizard."
        )
        return USER_INPUT_ERROR

    if _flag(args, "dry_run"):
        write_line("Dry run: no project files will be written.")
        write_key_value("Project path", root)
        if interactive:
            write_line("Would launch the --interactive wizard.")
        else:
            write_key_value("Goal", args.goal)
        write_line("Would create Mythic docs, tasks, and runtime state if missing.")
        return SUCCESS

    root.mkdir(parents=True, exist_ok=True)

    # Phase 20.0 (additive): wizard branch.
    wizard_settings_path: Path | None = None
    wizard_scaffolded: list[Path] = []
    if interactive:
        from .init_wizard import (
            WizardAbortedError,
            WizardConfig,
            run_wizard,
            scaffold_sample_artifacts,
            write_project_settings,
        )

        try:
            answers = run_wizard(
                WizardConfig(root=root, initial_goal=args.goal),
            )
            wizard_settings_path = write_project_settings(
                root, answers, force=force
            )
            wizard_scaffolded = scaffold_sample_artifacts(root, answers)
        except WizardAbortedError as exc:
            write_error(str(exc))
            return USER_INPUT_ERROR

        # Hand the wizard's resolved goal forward to the existing
        # init_project pipeline so the scaffold matches the answers.
        args.goal = answers.goal

    store = _method_store(root)
    method = store.load()
    workflow = MythicWorkflow(root)
    created = workflow.init_project(
        MythicRunConfig(goal=args.goal, noob_mode=args.noob),
        method_source=method.source,
    )

    write_line("Mythic Engineering project scaffolding ready.")
    write_key_value("Method source", method.source)
    if created:
        write_line("Created files:")
        for path in created:
            write_bullet(str(path))
    else:
        write_line("No new files were created (scaffold already existed).")

    if wizard_settings_path is not None:
        write_key_value("Project settings", wizard_settings_path)
    if wizard_scaffolded:
        write_line("Sample artefacts (delete when no longer needed):")
        for path in wizard_scaffolded:
            write_bullet(str(path))

    write_line("Next step: run `mythic-vibe import-md` to copy the full Mythic markdown corpus locally.")
    return SUCCESS


def cmd_checkin(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if _flag(args, "dry_run"):
        write_line("Dry run: no check-in will be written.")
        write_key_value("Project path", root)
        write_key_value("Phase", args.phase)
        write_key_value("Update", args.update)
        return SUCCESS

    workflow = MythicWorkflow(root)

    try:
        status_file, devlog_file = workflow.check_in(phase=args.phase, update=args.update)
    except ValueError as exc:
        write_error(str(exc))
        return USER_INPUT_ERROR

    # PH-05 follow-up: graph auto-population. Best-effort — any
    # sqlite / I/O failure logs into the result and never crashes
    # the parent command.
    from .context.autopopulate import populate_from_checkin
    populate_from_checkin(
        root,
        phase=args.phase,
        update_text=args.update,
        timestamp=utc_now(),
        status_path=status_file,
        devlog_path=devlog_file,
    )

    write_line("Mythic check-in recorded.")
    write_key_value("Status", status_file)
    write_key_value("Devlog", devlog_file)
    write_line("- Summary:")
    write_line(workflow.status_summary())
    return SUCCESS


def cmd_import_md(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    target = root / args.target
    if _flag(args, "dry_run"):
        write_line("Dry run: no method markdown files will be imported.")
        write_key_value("Project path", root)
        write_key_value("Target", target)
        return SUCCESS

    store = _method_store(root)
    try:
        manifest = store.import_all_markdown(target)
    except Exception as exc:  # noqa: BLE001 - surface remote import issues in CLI.
        write_error(format_error(CliError(f"Import failed: {exc}")))
        return OPERATIONAL_FAILURE

    write_line("Imported Mythic Engineering markdown files.")
    write_key_value("Destination", target)
    write_key_value("Files imported", len(manifest.files))
    write_key_value("Manifest", manifest.manifest_path)
    write_key_value("Index", target / "_import_index.json")
    return SUCCESS


def cmd_scan(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    indexer = ProjectIndexer(root)
    if _flag(args, "dry_run"):
        payload = {
            "command": "scan",
            "dry_run": True,
            "path": str(root),
            "index_path": str(indexer.index_path),
            "changed_only": _flag(args, "changed"),
            "docs_only": _flag(args, "docs"),
            "include_patterns": list(getattr(args, "include", []) or []),
            "exclude_patterns": list(getattr(args, "exclude", []) or []),
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no project index will be written.")
            write_key_value("Project path", root)
            write_key_value("Index", indexer.index_path)
        return SUCCESS

    with PluginHookDispatcher(root) as dispatcher:
        dispatcher.load_and_subscribe()
        dispatcher.emit(
            "before_scan",
            {
                "path": str(root),
                "changed_only": _flag(args, "changed"),
                "docs_only": _flag(args, "docs"),
                "include_patterns": list(getattr(args, "include", []) or []),
                "exclude_patterns": list(getattr(args, "exclude", []) or []),
            },
        )

        index = indexer.build(
            changed_only=_flag(args, "changed"),
            docs_only=_flag(args, "docs"),
            include_patterns=getattr(args, "include", []) or [],
            exclude_patterns=getattr(args, "exclude", []) or [],
        )

        # PH-05 follow-up: graph auto-population. Best-effort.
        from .context.autopopulate import populate_from_scan
        populate_from_scan(root, index)

        dispatcher.emit(
            "after_scan",
            {
                "path": str(root),
                "index_path": str(indexer.index_path),
                "changed_files": len(index.git.get("changed_files", [])),
                "languages": len(index.languages),
                "docs": len(index.docs),
                "tests": len(index.tests),
                "risks": len(index.risks),
            },
        )

    if _flag(args, "json"):
        write_json(
            {
                "command": "scan",
                "dry_run": False,
                "path": str(root),
                "index_path": str(indexer.index_path),
                "changed_only": _flag(args, "changed"),
                "docs_only": _flag(args, "docs"),
                "index": index.to_dict(),
            }
        )
        return SUCCESS

    write_line("Project context scan complete.")
    write_key_value("Index", indexer.index_path)
    write_key_value("Changed files", len(index.git.get("changed_files", [])))
    write_key_value("Languages", len(index.languages))
    write_key_value("Docs", len(index.docs))
    write_key_value("Tests", len(index.tests))
    write_key_value("Risks", len(index.risks))
    if index.recommended_context:
        write_line("- Recommended context:")
        for item in index.recommended_context:
            write_bullet(item, indent=2)
    return SUCCESS


def cmd_codex_pack(args: argparse.Namespace) -> int:
    return cmd_packet_create(args)


def cmd_packet_create(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    default_ext = ".json" if args.format == "json" else ".md"
    out_path = Path(args.out).resolve() if args.out else root / "mythic" / f"codex_prompt{default_ext}"
    if _flag(args, "dry_run"):
        payload = {
            "command": _command_name(args, "packet create"),
            "dry_run": True,
            "path": str(root),
            "output_file": str(out_path),
            "phase": args.phase,
            "task": args.task,
            "role": args.role,
            "format": args.format,
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no Codex packet will be written.")
            write_key_value("File", out_path)
            write_key_value("Packet role", args.role)
            write_key_value("Phase", args.phase)
            write_key_value("Task", args.task)
        return SUCCESS

    source_name = _command_name(args, "packet create")
    base_payload = {
        "source": source_name,
        "path": str(root),
        "phase": args.phase,
        "role": args.role,
        "task": args.task,
        "audience": args.audience,
        "format": args.format,
    }
    bridge = CodexBridge(root)
    with PluginHookDispatcher(root) as dispatcher:
        dispatcher.load_and_subscribe()
        dispatcher.emit("before_packet", dict(base_payload))
        packet = bridge.create_packet(
            request=CodexPacketRequest(
                task=args.task,
                phase=args.phase,
                audience=args.audience,
                role=args.role,
                output_format=args.format,
            ),
            out_file=out_path,
        )
        records = bridge.list_packets()
        record = records[-1] if records else None
        after_payload = dict(base_payload)
        after_payload["packet_id"] = record.packet_id if record else packet.stem
        after_payload["packet_path"] = str(record.packet_path) if record else str(packet)
        dispatcher.emit("after_packet", after_payload)
    if _flag(args, "json"):
        write_json(
            {
                "command": _command_name(args, "packet create"),
                "dry_run": False,
                "path": str(root),
                "output_file": str(packet),
                "phase": args.phase,
                "task": args.task,
                "role": args.role,
                "format": args.format,
            }
        )
        return SUCCESS

    write_line("Codex packet generated.")
    write_key_value("File", packet)
    write_key_value("Packet role", args.role)
    write_key_value("Format", args.format)
    write_line("Paste the 'Prompt To Paste' section into ChatGPT/Codex.")
    return SUCCESS


def cmd_packet_show(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    bridge = CodexBridge(root)
    packet_id = getattr(args, "packet_id", "") or ""
    workflow_id = (getattr(args, "workflow", "") or "").strip()
    step_id = (getattr(args, "step", "") or "").strip()
    latest_workflow = bool(_flag(args, "latest_workflow"))
    previous_workflow = bool(_flag(args, "previous_workflow"))

    if packet_id and (workflow_id or step_id or latest_workflow or previous_workflow):
        write_error("--packet-id cannot be combined with --workflow, --step, --latest-workflow, or --previous-workflow.")
        return USER_INPUT_ERROR
    if latest_workflow and previous_workflow:
        write_error("--latest-workflow cannot be combined with --previous-workflow.")
        return USER_INPUT_ERROR
    if (latest_workflow or previous_workflow) and workflow_id:
        write_error("--latest-workflow and --previous-workflow cannot be combined with --workflow.")
        return USER_INPUT_ERROR
    if latest_workflow and not step_id:
        write_error("--latest-workflow requires --step.")
        return USER_INPUT_ERROR
    if previous_workflow and not step_id:
        write_error("--previous-workflow requires --step.")
        return USER_INPUT_ERROR
    if (workflow_id and not step_id) or (step_id and not workflow_id and not latest_workflow and not previous_workflow):
        write_error("Workflow addressing requires both --workflow and --step (or --latest-workflow / --previous-workflow with --step).")
        return USER_INPUT_ERROR

    if latest_workflow:
        resolved, error = _resolve_latest_workflow_id(root)
        if error or resolved is None:
            write_error(error or "Could not resolve latest workflow plan.")
            return USER_INPUT_ERROR
        workflow_id = resolved
    elif previous_workflow:
        resolved, error = _resolve_previous_workflow_id(root)
        if error or resolved is None:
            write_error(error or "Could not resolve previous workflow.")
            return USER_INPUT_ERROR
        workflow_id = resolved

    if workflow_id and step_id:
        record = bridge.find_packet_by_workflow_step(workflow_id, step_id)
        if record is None:
            write_error(f"No packet stamped with workflow {workflow_id} step {step_id}.")
            return USER_INPUT_ERROR
        packet_id = record.packet_id

    if not packet_id:
        records = bridge.list_packets()
        if not records:
            write_error("No packet records found. Run `mythic-vibe packet create` first.")
            return USER_INPUT_ERROR
        packet_id = records[-1].packet_id

    text = bridge.load_packet_text(packet_id)
    if text is None:
        write_error(f"Packet not found: {packet_id}")
        return USER_INPUT_ERROR

    if _flag(args, "json"):
        record = bridge.load_packet_record(packet_id)
        write_json(
            {
                "command": "packet show",
                "packet_id": packet_id,
                "packet": record.to_dict() if record else None,
                "text": text,
            }
        )
        return SUCCESS

    write_line(text)
    return SUCCESS


def cmd_packet_list(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    workflow_filter = (getattr(args, "workflow", "") or "").strip()
    step_filter = (getattr(args, "step", "") or "").strip()
    latest_workflow = bool(_flag(args, "latest_workflow"))
    latest_workflow_id: str | None = None

    if latest_workflow and workflow_filter:
        write_error("--latest-workflow cannot be combined with --workflow.")
        return USER_INPUT_ERROR

    if latest_workflow:
        resolved, error = _resolve_latest_workflow_id(root)
        if error or resolved is None:
            write_error(error or "Could not resolve latest workflow plan.")
            return USER_INPUT_ERROR
        latest_workflow_id = resolved
        workflow_filter = resolved

    if step_filter and not workflow_filter:
        write_error("--step requires --workflow or --latest-workflow.")
        return USER_INPUT_ERROR

    bridge = CodexBridge(root)
    records = bridge.list_packets()
    if workflow_filter:
        records = [record for record in records if record.workflow_id == workflow_filter]
        if step_filter:
            records = [record for record in records if record.workflow_step_id == step_filter]

    if _flag(args, "json"):
        write_json(
            {
                "command": "packet list",
                "path": str(root),
                "latest_workflow_id": latest_workflow_id,
                "filters": {
                    "workflow_id": workflow_filter or None,
                    "workflow_step_id": step_filter or None,
                },
                "packets": [record.to_dict() for record in records],
            }
        )
        return SUCCESS

    if not records:
        if workflow_filter:
            write_line(f"No packet records match workflow {workflow_filter}.")
        else:
            write_line("No packet records found.")
        return SUCCESS

    if workflow_filter:
        write_line(f"Packet records for workflow {workflow_filter}")
    else:
        write_line("Packet records")
    for record in records:
        write_key_value(record.packet_id, f"{record.phase} | {record.role} | {record.created_at}", indent=2)
        write_bullet(record.task, indent=4)
        if record.workflow_step_id:
            write_bullet(f"step: {record.workflow_step_id}", indent=4)
    return SUCCESS


def cmd_packet_ingest(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    source = Path(args.source)
    bridge = CodexBridge(root)
    if _flag(args, "dry_run"):
        payload = {
            "command": _command_name(args, "packet ingest"),
            "dry_run": True,
            "path": str(root),
            "source": str(source),
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no packet will be ingested.")
            write_key_value("Source", source)
        return SUCCESS

    source_name = _command_name(args, "packet ingest")
    with PluginHookDispatcher(root) as dispatcher:
        dispatcher.load_and_subscribe()
        dispatcher.emit(
            "before_packet",
            {
                "source": source_name,
                "path": str(root),
                "ingest_source": str(source),
            },
        )
        try:
            record = bridge.ingest_packet(source)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
            write_error(str(exc))
            return USER_INPUT_ERROR
        dispatcher.emit(
            "after_packet",
            {
                "source": source_name,
                "path": str(root),
                "ingest_source": str(source),
                "phase": record.phase,
                "role": record.role,
                "task": record.task,
                "audience": record.audience,
                "format": record.output_format,
                "packet_id": record.packet_id,
                "packet_path": record.packet_path,
            },
        )

    if _flag(args, "json"):
        write_json(
            {
                "command": _command_name(args, "packet ingest"),
                "dry_run": False,
                "path": str(root),
                "source": str(source),
                "packet": record.to_dict(),
            }
        )
        return SUCCESS

    write_line("Packet ingested.")
    write_key_value("Packet ID", record.packet_id)
    write_key_value("Source", source)
    return SUCCESS


def _resolve_latest_workflow_id(root: Path) -> tuple[str | None, str | None]:
    engine = WorkflowEngine(root)
    try:
        plan = engine.load_plan()
    except ValueError as exc:
        return None, str(exc)
    if not plan.workflow_id:
        return None, "Latest saved workflow plan has no workflow_id; re-run `mythic-vibe workflow plan` to refresh."
    return plan.workflow_id, None


def _resolve_previous_workflow_id(root: Path) -> tuple[str | None, str | None]:
    engine = WorkflowEngine(root)
    history = engine.load_history()
    if len(history) < 2:
        return None, "No previous workflow recorded; need at least two saved plans before --previous-workflow can resolve."
    entry = history[-2]
    workflow_id = entry.get("workflow_id")
    if not workflow_id:
        return None, "Previous workflow entry has no workflow_id."
    return str(workflow_id), None


def _resolve_packet_ref(
    bridge: CodexBridge,
    ref: str,
    *,
    latest_workflow_id: str | None = None,
    root: Path | None = None,
) -> tuple[str | None, str | None]:
    if not ref:
        return None, "Packet reference is empty."
    if ref.startswith("LATEST:") and root is not None:
        _, _, step_id = ref.partition(":")
        if not step_id:
            return None, "LATEST shorthand requires a step id (LATEST:<step_id>)."
        resolved, error = _resolve_latest_workflow_id(root)
        if error or resolved is None:
            return None, error or "Could not resolve LATEST workflow."
        record = bridge.find_packet_by_workflow_step(resolved, step_id)
        if record is None:
            return None, f"No packet stamped with workflow {resolved} step {step_id}."
        return record.packet_id, None
    if ref.startswith("PREVIOUS:") and root is not None:
        _, _, step_id = ref.partition(":")
        if not step_id:
            return None, "PREVIOUS shorthand requires a step id (PREVIOUS:<step_id>)."
        resolved, error = _resolve_previous_workflow_id(root)
        if error or resolved is None:
            return None, error or "Could not resolve PREVIOUS workflow."
        record = bridge.find_packet_by_workflow_step(resolved, step_id)
        if record is None:
            return None, f"No packet stamped with workflow {resolved} step {step_id}."
        return record.packet_id, None
    if ref.startswith("WF-") and ":" in ref:
        workflow_id, _, step_id = ref.partition(":")
        record = bridge.find_packet_by_workflow_step(workflow_id, step_id)
        if record is None:
            return None, f"No packet stamped with workflow {workflow_id} step {step_id}."
        return record.packet_id, None
    if latest_workflow_id and ref.startswith("step-"):
        record = bridge.find_packet_by_workflow_step(latest_workflow_id, ref)
        if record is None:
            return None, f"No packet stamped with workflow {latest_workflow_id} step {ref}."
        return record.packet_id, None
    return ref, None


def cmd_packet_diff(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    bridge = CodexBridge(root)

    latest_workflow_id: str | None = None
    if _flag(args, "latest_workflow"):
        resolved, error = _resolve_latest_workflow_id(root)
        if error or resolved is None:
            write_error(error or "Could not resolve latest workflow plan.")
            return USER_INPUT_ERROR
        latest_workflow_id = resolved

    left_id, left_error = _resolve_packet_ref(bridge, args.left, latest_workflow_id=latest_workflow_id, root=root)
    if left_error or left_id is None:
        write_error(left_error or "Could not resolve --left packet reference.")
        return USER_INPUT_ERROR
    right_id, right_error = _resolve_packet_ref(bridge, args.right, latest_workflow_id=latest_workflow_id, root=root)
    if right_error or right_id is None:
        write_error(right_error or "Could not resolve --right packet reference.")
        return USER_INPUT_ERROR

    try:
        diff = bridge.diff_packets(left_id, right_id)
    except FileNotFoundError as exc:
        write_error(str(exc))
        return USER_INPUT_ERROR

    if _flag(args, "json"):
        write_json(
            {
                "command": _command_name(args, "packet diff"),
                "path": str(root),
                "left": left_id,
                "right": right_id,
                "left_ref": args.left,
                "right_ref": args.right,
                "latest_workflow_id": latest_workflow_id,
                "diff": diff,
            }
        )
        return SUCCESS

    write_line(diff)
    return SUCCESS


def cmd_packet_lint(args: argparse.Namespace) -> int:
    """Phase 20.1 — heuristic packet quality lint. Loads a
    packet (default: latest) and runs the rules in
    ``mythic_vibe_cli/packet_lint.py``. Exit code is SUCCESS
    when no error-severity findings fired (warnings + infos
    are advisory)."""
    from .packet_lint import lint_packet_text

    root = Path(args.path).resolve()

    # Resolve the packet source. Operators can pass either an
    # explicit --file PATH (for ad-hoc lint of a not-yet-stored
    # packet) or --packet-id PKT-NNNNNN, defaulting to "latest".
    file_arg = getattr(args, "file", "") or ""
    packet_id = getattr(args, "packet_id", "") or ""
    if file_arg:
        text_path = Path(file_arg)
        if not text_path.is_absolute():
            text_path = (root / text_path).resolve()
        if not text_path.is_file():
            write_error(f"Packet file not found: {text_path}")
            return USER_INPUT_ERROR
        try:
            text = text_path.read_text(encoding="utf-8")
        except OSError as exc:
            write_error(f"Cannot read {text_path}: {exc}")
            return OPERATIONAL_FAILURE
        source_label = str(text_path)
    else:
        bridge = CodexBridge(root)
        resolved_id, error = _resolve_packet_ref(
            bridge,
            packet_id or "LATEST",
            latest_workflow_id=None,
            root=root,
        )
        if error or resolved_id is None:
            write_error(
                error or "Could not resolve a packet to lint."
            )
            return USER_INPUT_ERROR
        # Locate the packet on disk via the bridge's directory.
        packet_path = bridge.packet_dir / f"{resolved_id}.md"
        if not packet_path.is_file():
            # JSON-format packets don't go through the markdown
            # linter — surface a clear message rather than failing
            # silently with no findings.
            write_error(
                f"Packet markdown not found at {packet_path} — "
                "packet lint requires markdown packets"
            )
            return USER_INPUT_ERROR
        try:
            text = packet_path.read_text(encoding="utf-8")
        except OSError as exc:
            write_error(f"Cannot read {packet_path}: {exc}")
            return OPERATIONAL_FAILURE
        source_label = str(packet_path)

    report = lint_packet_text(text)

    if _flag(args, "json"):
        payload = {
            "command": _command_name(args, "packet lint"),
            "path": str(root),
            "source": source_label,
            **report.to_dict(),
        }
        write_json(payload)
        return SUCCESS if report.ok else OPERATIONAL_FAILURE

    write_line(f"Packet lint: {source_label}")
    write_key_value("Errors", len(report.errors))
    write_key_value("Warnings", len(report.warnings))
    write_key_value("Infos", len(report.infos))
    if report.findings:
        write_line("Findings:")
        for finding in report.findings:
            write_bullet(
                f"[{finding.severity}] {finding.rule_id}: "
                f"{finding.message}",
                indent=2,
            )
    else:
        write_line("- No findings.")
    return SUCCESS if report.ok else OPERATIONAL_FAILURE


def cmd_workflow_plan(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    role_sequence = tuple(getattr(args, "role", []) or DEFAULT_ROLE_SEQUENCE)
    engine = WorkflowEngine(root)
    output_format = getattr(args, "format", "markdown")

    try:
        plan = engine.build_plan(args.task, role_sequence=role_sequence)
    except ValueError as exc:
        write_error(str(exc))
        return USER_INPUT_ERROR

    out_file = Path(args.out).resolve() if getattr(args, "out", "") else None
    output_path = out_file or root / "mythic" / WORKFLOW_PLAN_FILENAME
    packet_requests = plan.packet_requests(audience=args.audience)
    for request in packet_requests:
        request.output_format = output_format
    payload = {
        "command": "workflow plan",
        "dry_run": _flag(args, "dry_run"),
        "output_file": str(output_path),
        "packets_requested": _flag(args, "packets"),
        "packet_artifacts": [],
        "workflow_id": plan.workflow_id,
        "plan": plan.to_dict(),
        "packet_requests": [request.__dict__ for request in packet_requests],
    }

    if _flag(args, "dry_run"):
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no workflow plan will be written.")
            write_key_value("Project path", root)
            write_key_value("Output", output_path)
            write_key_value("Task", plan.task)
            if plan.workflow_id:
                write_key_value("Workflow ID", plan.workflow_id)
            write_line("Role sequence:")
            for step in plan.steps:
                write_bullet(f"{step.step_id}: {step.role} -> {step.phase} ({step.handoff_to or 'done'})")
            if _flag(args, "packets"):
                write_line("Packet preview:")
                for request in packet_requests:
                    write_bullet(f"{request.role} packet ({request.phase}, {request.output_format})")
        return SUCCESS

    path = engine.write_plan(args.task, role_sequence=role_sequence, out_file=out_file)
    payload["output_file"] = str(path)
    if _flag(args, "packets"):
        builder = CodexBridge(root)
        packet_artifacts = []
        source_name = _command_name(args, "workflow plan")
        with PluginHookDispatcher(root) as dispatcher:
            dispatcher.load_and_subscribe()
            for request in packet_requests:
                base_payload = {
                    "source": source_name,
                    "path": str(root),
                    "phase": request.phase,
                    "role": request.role,
                    "task": request.task,
                    "audience": request.audience,
                    "format": request.output_format,
                    "workflow_id": request.workflow_id,
                    "workflow_step_id": request.workflow_step_id,
                }
                dispatcher.emit("before_packet", dict(base_payload))
                packet_path = builder.create_packet(request)
                record = builder.load_packet_record(packet_path.stem)
                after_payload = dict(base_payload)
                after_payload["packet_id"] = record.packet_id if record else packet_path.stem
                after_payload["packet_path"] = str(record.packet_path) if record else str(packet_path)
                dispatcher.emit("after_packet", after_payload)
                packet_artifacts.append(
                    record.to_dict()
                    if record
                    else {
                        "packet_id": packet_path.stem,
                        "packet_path": str(packet_path),
                    }
                )
        payload["packet_artifacts"] = packet_artifacts

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line("Workflow orchestration plan written.")
    write_key_value("Output", path)
    write_key_value("Task", plan.task)
    if plan.workflow_id:
        write_key_value("Workflow ID", plan.workflow_id)
    write_line("Role sequence:")
    for step in plan.steps:
        write_bullet(f"{step.step_id}: {step.role} -> {step.phase} ({step.handoff_to or 'done'})")
    if payload["packet_artifacts"]:
        write_line("Packet artifacts:")
        for artifact in payload["packet_artifacts"]:
            write_bullet(f"{artifact['packet_id']}: {artifact['packet_path']}")
    return SUCCESS


def _workflow_packet_status(root: Path, plan: WorkflowPlan, *, audience: str = "advanced", output_format: str = "markdown") -> list[dict[str, object]]:
    bridge = CodexBridge(root)
    records = bridge.list_packets()
    requests = plan.packet_requests(audience=audience)
    statuses: list[dict[str, object]] = []
    for request in requests:
        request.output_format = output_format
        match: PacketRecord | None = None
        match_strategy: str | None = None
        if request.workflow_id and request.workflow_step_id:
            match = next(
                (
                    record
                    for record in records
                    if record.workflow_id == request.workflow_id
                    and record.workflow_step_id == request.workflow_step_id
                ),
                None,
            )
            if match is not None:
                match_strategy = "id"
        if match is None:
            match = next(
                (
                    record
                    for record in records
                    if record.role == request.role
                    and record.phase == request.phase
                    and record.task == request.task
                    and record.audience == request.audience
                    and record.output_format == request.output_format
                ),
                None,
            )
            if match is not None:
                match_strategy = "text"
        statuses.append(
            {
                "role": request.role,
                "phase": request.phase,
                "task": request.task,
                "audience": request.audience,
                "output_format": request.output_format,
                "workflow_id": request.workflow_id,
                "workflow_step_id": request.workflow_step_id,
                "found": match is not None,
                "match_strategy": match_strategy,
                "packet_id": match.packet_id if match else None,
                "packet_path": match.packet_path if match else None,
                "metadata_path": match.metadata_path if match else None,
            }
        )
    return statuses


def _workflow_plan_from_args(args: argparse.Namespace, engine: WorkflowEngine) -> tuple[WorkflowPlan, str]:
    role_sequence = tuple(getattr(args, "role", []) or DEFAULT_ROLE_SEQUENCE)
    if getattr(args, "task", ""):
        return engine.build_plan(args.task, role_sequence=role_sequence), "generated"

    plan_file = Path(args.plan).resolve() if getattr(args, "plan", "") else None
    plan = engine.load_plan(plan_file=plan_file)
    return plan, str(plan_file or engine.root / "mythic" / WORKFLOW_PLAN_FILENAME)


def _ai_registry(root: Path | None = None) -> ProviderRegistry:
    return ProviderRegistry(root=root)


def _resolve_ai_packet(root: Path, packet: str) -> dict[str, str]:
    bridge = CodexBridge(root)
    text = packet
    packet_id = "inline"
    source = "inline"

    if packet.startswith("PKT-"):
        loaded = bridge.load_packet_text(packet)
        if loaded is not None:
            text = loaded
            record = bridge.load_packet_record(packet)
            packet_id = packet
            source = record.packet_path if record else packet
    else:
        packet_path = Path(packet)
        if packet_path.exists():
            text = packet_path.read_text(encoding="utf-8")
            packet_id = packet_path.stem if packet_path.stem.startswith("PKT-") else packet_path.stem
            source = str(packet_path)

    return {
        "text": text,
        "packet_id": packet_id,
        "source": source,
    }


def _verification_level(selected: dict[str, bool], *, commands_ran: bool, docs_ok: bool, invariants_ok: bool, changed_files_checked: bool) -> str:
    if not any(selected.values()):
        return "none"
    if commands_ran and docs_ok and invariants_ok and changed_files_checked:
        return "integration"
    if commands_ran:
        return "unit"
    if changed_files_checked or docs_ok or invariants_ok:
        return "smoke"
    return "none"


def cmd_ai_providers(args: argparse.Namespace) -> int:
    root = Path(getattr(args, "path", ".")).resolve()
    registry = _ai_registry(root)
    providers = registry.providers()
    if _flag(args, "json"):
        write_json(
            {
                "command": "ai providers",
                "path": str(root),
                "providers": {
                    name: {
                        "name": provider.name,
                        "configured": (status := provider.validate_config()).configured,
                        "details": status.details,
                    }
                    for name, provider in providers.items()
                },
            }
        )
        return SUCCESS

    write_line("AI providers")
    for name, provider in providers.items():
        status = provider.validate_config()
        write_key_value(name, "configured" if status.configured else "not configured", indent=2)
        for detail in status.details:
            write_bullet(detail, indent=4)
    return SUCCESS


def cmd_ai_test(args: argparse.Namespace) -> int:
    root = Path(getattr(args, "path", ".")).resolve()
    registry = _ai_registry(root)
    provider_name = args.provider
    providers = registry.providers()
    provider = providers.get(provider_name)
    if provider is None:
        write_error(f"Unknown provider: {provider_name}")
        return USER_INPUT_ERROR

    status = provider.validate_config()
    packet = _resolve_ai_packet(root, args.packet)
    estimate = provider.estimate(packet)
    response = provider.run(packet, dry_run=True)

    payload = {
        "command": "ai test",
        "path": str(root),
        "provider": provider.name,
        "configured": status.configured,
        "details": status.details,
        "packet": packet,
        "estimate": {
            "input_tokens": estimate.input_tokens,
            "output_tokens": estimate.output_tokens,
            "cost_usd": estimate.cost_usd,
        },
        "response": {
            "provider": response.provider,
            "model": response.model,
            "packet_id": response.packet_id,
            "dry_run": response.dry_run,
            "content": response.content,
            "usage": response.usage,
            "metadata": response.metadata,
        },
    }
    write_json(payload)
    return SUCCESS


def cmd_ai_run(args: argparse.Namespace) -> int:
    """Run a provider in explicit provider mode.

    PH-15 sub-slice: when ``--no-record`` is unset and the call is
    not a dry-run, the packet text is recorded as a ``user`` turn
    and the response content as an ``assistant`` turn under the
    operator-supplied ``--conversation-id`` (or a fresh
    ``CV-XXXXXX`` if absent). Dry-runs are never recorded — they
    are estimation passes, not real conversations.

    PH-08 follow-up: by default the call is routed through
    :func:`run_with_fallback` so a primary failure falls forward
    onto ``copy-paste`` rather than crashing the CLI. Pass
    ``--no-fallback`` to preserve the legacy direct-``provider.run``
    path.
    """
    from .ai.cost_guard import check_budget
    from .ai.router import RouteDecision
    from .ai.routing_runtime import run_with_fallback
    from .memory.conversation import new_conversation_id, record_turn

    root = Path(getattr(args, "path", ".")).resolve()
    registry = _ai_registry(root)
    provider = registry.providers().get(args.provider)
    if provider is None:
        write_error(f"Unknown provider: {args.provider}")
        return USER_INPUT_ERROR

    use_fallback = not _flag(args, "no_fallback")

    status = provider.validate_config()
    # When fallback is off, an unconfigured provider is a hard error
    # (legacy behaviour). When fallback is on, the routing runtime
    # walks past unconfigured providers onto copy-paste, so we don't
    # block here — the operator gets a fell_back=True payload instead.
    if not use_fallback and not status.configured and not _flag(args, "dry_run"):
        write_error(f"Provider not configured: {args.provider}. Use --dry-run or set the required API key.")
        return USER_INPUT_ERROR

    packet = _resolve_ai_packet(root, args.packet)

    # PH-08 slice 8.2: cost-guard gate. Only fires for live calls;
    # dry-runs go straight through. The estimate is taken from the
    # operator's chosen provider — that's the cost they consented to.
    # If fallback fires, the actual call lands on copy-paste (free),
    # but we still respect the cap on the planned spend.
    if not _flag(args, "dry_run"):
        try:
            estimate = provider.estimate(packet)
            projected = float(getattr(estimate, "cost_usd", 0.0) or 0.0)
        except Exception:  # noqa: BLE001 — estimator failure shouldn't block the call
            projected = 0.0
        budget = check_budget(root, projected)
        if not budget.allowed:
            write_error(f"Daily AI cost cap blocked the call: {budget.reason}")
            return OPERATIONAL_FAILURE

    used_provider = provider.name
    fell_back = False
    attempts_payload: list[dict[str, object]] = []

    if use_fallback:
        decision = RouteDecision(
            provider=args.provider,
            model="",
            rule_matched=None,
            fallbacks=(),
            reasons=(),
            role="",
            task_type="*",
        )
        result = run_with_fallback(
            decision,
            packet,
            resolver=lambda name: registry.providers().get(name),
            root=root,
            dry_run=_flag(args, "dry_run"),
        )
        response = result.response
        used_provider = result.used_provider
        fell_back = result.fell_back
        attempts_payload = [a.to_dict() for a in result.attempts]
    else:
        response = provider.run(packet, dry_run=_flag(args, "dry_run"))

    # PH-15 sub-slice: conversation auto-record.
    no_record = bool(_flag(args, "no_record"))
    is_dry_run = bool(_flag(args, "dry_run") or response.dry_run)
    conversation_id = ""
    recorded = False
    if not no_record and not is_dry_run:
        conversation_id = (
            getattr(args, "conversation_id", "") or new_conversation_id()
        )
        # `packet` is the resolved-and-normalised dict; the operator's
        # raw input lives at `args.packet`. Record the raw text so the
        # log reads naturally — packet metadata is in the turn's
        # `metadata` field for callers that need the structured form.
        user_content = str(getattr(args, "packet", "") or "")
        try:
            record_turn(
                root,
                conversation_id,
                "user",
                user_content,
                provider=provider.name,
                model=response.model,
                metadata={"packet_id": response.packet_id},
            )
            record_turn(
                root,
                conversation_id,
                "assistant",
                response.content,
                provider=provider.name,
                model=response.model,
                metadata={
                    "packet_id": response.packet_id,
                    "usage": response.usage,
                },
            )
            recorded = True
        except Exception:  # noqa: BLE001 — never crash the CLI on a log write
            recorded = False

    payload = {
        "command": "ai run",
        "path": str(root),
        "provider": provider.name,
        "dry_run": is_dry_run,
        "packet_id": response.packet_id,
        "model": response.model,
        "configured": status.configured,
        "details": status.details,
        "packet": packet,
        "response": {
            "provider": response.provider,
            "model": response.model,
            "packet_id": response.packet_id,
            "dry_run": response.dry_run,
            "content": response.content,
            "usage": response.usage,
            "metadata": response.metadata,
        },
        "conversation_id": conversation_id,
        "recorded": recorded,
        "fallback_enabled": use_fallback,
        "primary_provider": provider.name,
        "used_provider": used_provider,
        "fell_back": fell_back,
        "fallback_attempts": attempts_payload,
    }
    write_json(payload)
    return SUCCESS


def cmd_ai_ingest_response(args: argparse.Namespace) -> int:
    """Record a provider response as metadata only.

    PH-15 sub-slice: also append the response as an ``assistant``
    turn in the slice-15.1 conversation log (under
    ``--conversation-id`` or a fresh id) unless ``--no-record`` is
    set. ``ingest-response`` is the manual paste-back flow; the
    matching user turn typically lives elsewhere (the operator
    submitted the packet to the AI by hand) so we record only the
    assistant side.
    """
    from .memory.conversation import new_conversation_id, record_turn

    root = Path(args.path).resolve()
    out_dir = root / "mythic" / "ai"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "latest_response.json"

    no_record = bool(_flag(args, "no_record"))
    conversation_id = ""
    recorded = False
    if not no_record:
        conversation_id = (
            getattr(args, "conversation_id", "") or new_conversation_id()
        )
        try:
            record_turn(
                root,
                conversation_id,
                "assistant",
                args.response,
                provider=args.provider,
                model=args.model,
                metadata={"packet_id": args.packet_id, "ingest": True},
            )
            recorded = True
        except Exception:  # noqa: BLE001 — never crash the CLI on a log write
            recorded = False

    payload = {
        "provider": args.provider,
        "model": args.model,
        "packet_id": args.packet_id,
        "response": args.response,
        "applied": False,
        "conversation_id": conversation_id,
        "recorded": recorded,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if _flag(args, "json"):
        write_json({"command": "ai ingest-response", "path": str(out_path), "payload": payload})
        return SUCCESS
    write_line("AI response ingested as metadata only.")
    write_key_value("Path", out_path)
    write_key_value("Applied", "false")
    if conversation_id:
        write_key_value("Conversation", conversation_id)
    return SUCCESS


def cmd_verify(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    selected = {
        "commands": _flag(args, "commands"),
        "changed_files": _flag(args, "changed_files"),
        "docs": _flag(args, "docs"),
        "invariants": _flag(args, "invariants"),
    }
    if not any(selected.values()):
        selected = {key: True for key in selected}

    dispatcher = PluginHookDispatcher(root)
    dispatcher.load_and_subscribe()
    dispatcher.emit(
        "before_verify",
        {
            "path": str(root),
            "selected": dict(selected),
        },
    )

    command_runs: list[dict[str, object]] = []
    warnings: list[str] = []
    errors: list[str] = []
    blocked_reasons: list[str] = []
    changed_files: list[str] = []
    docs_checked: list[str] = []
    invariants_checked: list[str] = []
    diff_reviewed = False
    docs_updated = False
    commands_ran = False
    docs_ok = False
    invariants_ok = False
    changed_files_checked = False

    if selected["commands"]:
        runner = run_default_commands(root)
        warnings.extend(runner.warnings)
        if runner.commands:
            commands_ran = True
            command_runs.extend(item.to_dict() for item in runner.commands)
            for item in runner.commands:
                if item.exit_code != 0:
                    errors.append(
                        f"Verification command failed: {' '.join(item.command)} (exit {item.exit_code})"
                    )
        else:
            blocked_reasons.append("No verification commands were discovered.")

    if selected["changed_files"]:
        diff_result = review_changed_files(root)
        warnings.extend(diff_result.warnings)
        changed_files = diff_result.changed_files
        diff_reviewed = True
        changed_files_checked = True

    if selected["docs"]:
        doc_result = check_docs(root)
        warnings.extend(doc_result.warnings)
        docs_checked = doc_result.checked
        docs_updated = not doc_result.missing
        docs_ok = not doc_result.missing
        if doc_result.missing:
            blocked_reasons.append("Missing documentation files: " + ", ".join(doc_result.missing))

    if selected["invariants"]:
        invariant_result = check_invariants(root)
        warnings.extend(invariant_result.warnings)
        invariants_checked = invariant_result.checked
        invariants_ok = invariant_result.ok
        if invariant_result.errors:
            errors.extend(invariant_result.errors)

    if not command_runs and not changed_files_checked and not docs_checked and not invariants_checked:
        blocked_reasons.append("No verification checks were able to run.")

    result = "pass"
    if errors:
        result = "fail"
    elif blocked_reasons:
        result = "blocked"

    level = _verification_level(
        selected,
        commands_ran=commands_ran,
        docs_ok=docs_ok,
        invariants_ok=invariants_ok,
        changed_files_checked=changed_files_checked,
    )
    if result == "blocked" and level == "none":
        level = "none"

    verification_id = new_verification_id()
    state_snapshot = JsonStateStore(root).load_state()
    record = VerificationRecord(
        verification_id=verification_id,
        timestamp=utc_now(),
        result=result,
        task_id=state_snapshot.active_task_id,
        commands=command_runs,
        diff_reviewed=diff_reviewed,
        docs_updated=docs_updated,
        invariants_checked=invariants_checked,
    ).to_dict()
    artifact = VerificationArtifact(
        schema_version=record["schema_version"],
        verification_id=record["verification_id"],
        timestamp=record["timestamp"],
        task_id=record["task_id"],
        commands=record["commands"],
        diff_reviewed=record["diff_reviewed"],
        docs_updated=record["docs_updated"],
        invariants_checked=record["invariants_checked"],
        result=record["result"],
        level=level,
        warnings=warnings,
        errors=errors,
        blocked_reasons=blocked_reasons,
        changed_files=changed_files,
        docs_checked=docs_checked,
    )
    artifact_path = write_verification_artifact(root, artifact, promote_latest=True)

    store = JsonStateStore(root)
    state = state_snapshot
    state.last_verification_id = verification_id
    state.updated_at = utc_now()
    store.write_state(state)

    dispatcher.emit(
        "after_verify",
        {
            "path": str(root),
            "result": result,
            "level": level,
            "verification_id": verification_id,
            "artifact_path": str(artifact_path),
            "errors_count": len(errors),
            "warnings_count": len(warnings),
            "blocked_count": len(blocked_reasons),
        },
    )
    dispatcher.teardown()

    # PH-07 follow-up: TTS phase-transition hook. No-op unless
    # MYTHIC_VOICE_TTS_ENABLED is set.
    from .voice.notify import notify_phase as _notify_phase
    _notify_phase("verify", result)

    if _flag(args, "json"):
        write_json(
            {
                "command": "verify",
                "path": str(root),
                "record_requested": _flag(args, "record"),
                "result": result,
                "level": level,
                "verification_id": verification_id,
                "artifact_path": str(artifact_path),
                "latest_path": str(root / "mythic" / "verifications" / "latest.json"),
                "selected": selected,
                "warnings": warnings,
                "errors": errors,
                "blocked_reasons": blocked_reasons,
                "commands": command_runs,
                "changed_files": changed_files,
                "docs_checked": docs_checked,
                "invariants_checked": invariants_checked,
            }
        )
        return SUCCESS if result == "pass" else (VERIFICATION_FAILURE if result == "fail" else OPERATIONAL_FAILURE)

    write_line("Verification complete.")
    write_key_value("Result", result)
    write_key_value("Level", level)
    write_key_value("Verification ID", verification_id)
    write_key_value("Artifact", artifact_path)
    if warnings:
        write_line("- Warnings:")
        for warning in warnings:
            write_bullet(warning, indent=2)
    if errors:
        write_line("- Errors:")
        for error in errors:
            write_bullet(error, indent=2)
    if blocked_reasons:
        write_line("- Blocked:")
        for reason in blocked_reasons:
            write_bullet(reason, indent=2)
    return SUCCESS if result == "pass" else (VERIFICATION_FAILURE if result == "fail" else OPERATIONAL_FAILURE)


def cmd_codex_log(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if _flag(args, "dry_run"):
        write_line("Dry run: no Codex response check-in will be written.")
        write_key_value("Project path", root)
        write_key_value("Phase", args.phase)
        write_key_value("Response", args.response)
        return SUCCESS

    workflow = MythicWorkflow(root)
    try:
        status_file, devlog_file = workflow.check_in(phase=args.phase, update=args.response)
    except ValueError as exc:
        write_error(str(exc))
        return USER_INPUT_ERROR
    write_line("Codex response logged into Mythic workflow.")
    write_key_value("Status", status_file)
    write_key_value("Devlog", devlog_file)
    return SUCCESS


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if _flag(args, "json"):
        write_json(_status_payload(root))
        return SUCCESS

    workflow = MythicWorkflow(root)
    write_line(workflow.status_summary())
    return SUCCESS


def cmd_examples(args: argparse.Namespace) -> int:
    if _flag(args, "json"):
        write_json({"command": "examples", "examples": EXAMPLES})
        return SUCCESS

    write_line("Mythic Vibe examples")
    for example in EXAMPLES:
        write_line("")
        write_key_value("What happened", example["name"])
        write_key_value("Command", example["command"])
        write_key_value("What should I do next", example["next"])
        write_key_value("How do I verify it", "Run the command with `--help` first if you are unsure.")
    return SUCCESS


def cmd_guide(args: argparse.Namespace) -> int:
    payload = {
        "command": "guide",
        "loop": phase_names(),
        "next": "Use `mythic-vibe next --path .` inside a project.",
        "verify": "Run `mythic-vibe doctor --path .` and `pytest -q`.",
    }
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line("Mythic Vibe guide")
    write_key_value("What happened", "Loaded the operator guide for the Mythic loop.")
    write_line("- Phase loop:")
    for phase in phase_names():
        write_bullet(phase, indent=2)
    write_key_value("What should I do next", payload["next"])
    write_key_value("How do I verify it", payload["verify"])
    return SUCCESS


def _verification_failed_commands(latest_verification: dict[str, object] | None) -> list[str]:
    if not latest_verification:
        return []
    commands = latest_verification.get("commands", [])
    if not isinstance(commands, list):
        return []

    failed: list[str] = []
    for item in commands:
        if not isinstance(item, dict):
            continue
        try:
            exit_code = int(item.get("exit_code", 0))
        except (TypeError, ValueError):
            exit_code = 0
        if exit_code == 0:
            continue
        command = item.get("command", [])
        if isinstance(command, list):
            rendered = " ".join(str(part) for part in command if str(part))
        else:
            rendered = str(command)
        failed.append(f"{rendered} (exit {exit_code})")
    return failed


def cmd_next(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    payload = _status_payload(root)
    latest_verification = load_latest_verification(root)
    verification_result = str(latest_verification.get("result") or "") if latest_verification else ""
    handoff_next_step = str(payload.get("latest_handoff_next_step") or "").strip()
    if not payload.get("status_found"):
        next_phase = "intent"
        action = 'Run `mythic-vibe init --goal "..." --path .`.'
        source = "scaffold"
    elif latest_verification and verification_result != "pass":
        next_phase = "verify"
        action = "Resolve the latest verification issues, then rerun `mythic-vibe verify --commands --docs --invariants --record`."
        source = "verification"
    else:
        completed = [str(item) for item in payload.get("completed_phases", [])]
        next_phase = next_phase_from_completed(completed)
        action = handoff_next_step or PHASE_GUIDE[next_phase].next_action
        source = "handoff" if handoff_next_step else "phase"
    result = {
        "command": "next",
        "path": str(root),
        "next_phase": next_phase,
        "source": source,
        "purpose": PHASE_GUIDE[next_phase].purpose,
        "next_action": action,
        "verification": PHASE_GUIDE[next_phase].verification,
        "latest_verification_result": verification_result or None,
        "latest_verification_id": str(latest_verification.get("verification_id") or "") if latest_verification else None,
        "latest_handoff_next_step": handoff_next_step or None,
    }
    if latest_verification and verification_result != "pass":
        result["verification_errors"] = [str(item) for item in latest_verification.get("errors", []) if str(item)]
        result["blocked_reasons"] = [str(item) for item in latest_verification.get("blocked_reasons", []) if str(item)]
        result["failed_verification_commands"] = _verification_failed_commands(latest_verification)
    if _flag(args, "json"):
        write_json(result)
        return SUCCESS

    write_line("Next recommended action")
    write_key_value("What happened", f"Resolved the next phase as `{next_phase}`.")
    if source == "verification":
        write_key_value("Why this comes first", f"Latest verification result is `{verification_result or 'unknown'}`.")
        failed_commands = result.get("failed_verification_commands", [])
        if failed_commands:
            write_line("- Failed commands:")
            for item in failed_commands:
                write_bullet(str(item), indent=2)
        if result.get("verification_errors"):
            write_line("- Verification errors:")
            for item in result["verification_errors"]:
                write_bullet(str(item), indent=2)
        if result.get("blocked_reasons"):
            write_line("- Blocked reasons:")
            for item in result["blocked_reasons"]:
                write_bullet(str(item), indent=2)
    elif source == "handoff":
        write_key_value("Why this comes first", "Latest handoff names a concrete next step.")
    write_key_value("What should I do next", action)
    write_key_value("How do I verify it", PHASE_GUIDE[next_phase].verification)
    return SUCCESS


def cmd_explain_phase(args: argparse.Namespace) -> int:
    phase = args.phase
    details = PHASE_GUIDE[phase]
    payload = {"command": "explain phase", "phase": details.__dict__}
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line(f"Phase: {details.name}")
    write_key_value("What happened", details.purpose)
    write_key_value("What should I do next", details.next_action)
    write_key_value("How do I verify it", details.verification)
    return SUCCESS


def cmd_explain_artifact(args: argparse.Namespace) -> int:
    artifact = args.artifact
    details = ARTIFACT_GUIDE[artifact]
    payload = {"command": "explain artifact", "artifact": artifact, **details}
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line(f"Artifact: {artifact}")
    write_key_value("Where was it written", details["path"])
    write_key_value("What happened", details["purpose"])
    write_key_value("How do I verify it", details["verify"])
    return SUCCESS


def cmd_explain_dispatch(args: argparse.Namespace) -> int:
    if args.explain_command == "phase":
        return cmd_explain_phase(args)
    if args.explain_command == "artifact":
        return cmd_explain_artifact(args)
    return USER_INPUT_ERROR


def cmd_tutorial(args: argparse.Namespace) -> int:
    steps = [
        'mythic-vibe init --goal "Build something useful" --noob',
        "mythic-vibe next --path .",
        "mythic-vibe scan --path .",
        'mythic-vibe packet create --task "Implement the first slice" --phase build',
        "mythic-vibe verify --commands --docs --invariants --record",
        'mythic-vibe reflect --summary "First slice complete"',
        "mythic-vibe resume --path .",
    ]
    payload = {
        "command": "tutorial",
        "steps": steps,
        "verify": "The tutorial is healthy when `mythic-vibe resume --path .` gives a clear next action.",
    }
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line("Mythic Vibe tutorial")
    for index, step in enumerate(steps, start=1):
        write_key_value(f"Step {index}", step)
    write_key_value("How do I verify it", payload["verify"])
    return SUCCESS


def cmd_completion(args: argparse.Namespace) -> int:
    shell = args.shell
    if shell == "bash":
        script = bash_completion()
    elif shell == "zsh":
        script = zsh_completion()
    elif shell == "powershell":
        script = powershell_completion()
    else:
        write_error(f"Unsupported shell: {shell}")
        return USER_INPUT_ERROR

    if _flag(args, "json"):
        write_json({"command": "completion", "shell": shell, "script": script})
    else:
        write_line(script, force=True)
    return SUCCESS


def _run_tool(
    args: argparse.Namespace,
    *,
    label: str,
    default_argv: list[str],
    description: str,
) -> int:
    """Shared body for ``test`` / ``lint`` / ``typecheck`` shortcuts.

    Each shortcut is a thin wrapper around :func:`runtime.exec.exec_command`
    that runs an external developer tool (pytest / ruff / mypy) on the
    project root. ``--command`` overrides the default invocation; the tool's
    exit code is returned verbatim so CI integrations behave identically to
    invoking the underlying tool directly.
    """
    root = Path(getattr(args, "path", ".")).resolve()
    override = getattr(args, "override_command", None)
    argv = list(override) if override else list(default_argv)

    if _flag(args, "dry_run"):
        if _flag(args, "json"):
            write_json(
                {
                    "command": label,
                    "dry_run": True,
                    "tool": argv[0] if argv else "",
                    "argv": argv,
                    "cwd": str(root),
                    "description": description,
                }
            )
        else:
            write_line(f"Dry run: would run {label}")
            write_key_value("Tool", argv[0] if argv else "(none)")
            write_key_value("Argv", " ".join(argv))
            write_key_value("Cwd", root)
        return SUCCESS

    if not argv:
        write_error(f"No command supplied for {label}.")
        return USER_INPUT_ERROR

    result = run_command(argv, cwd=root)

    if _flag(args, "json"):
        write_json(
            {
                "command": label,
                "tool": argv[0],
                "argv": argv,
                "cwd": str(root),
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "ok": result.exit_code == 0,
            }
        )
        return SUCCESS if result.exit_code == 0 else VERIFICATION_FAILURE

    if result.stdout:
        write_line(result.stdout, force=True)
    if result.stderr:
        write_line(result.stderr, stream=__import__("sys").stderr, force=True)
    if result.exit_code == 0:
        write_line(f"{label}: ok")
        return SUCCESS
    write_error(f"{label} failed (exit code {result.exit_code})")
    return VERIFICATION_FAILURE


def cmd_test(args: argparse.Namespace) -> int:
    """Run the project's test suite via pytest.

    Without ``--command``, auto-discovers a sensible default
    (``python -m pytest -q`` if a tests/ directory with test*.py exists).
    """
    root = Path(getattr(args, "path", ".")).resolve()
    discovered = discover_default_commands(root)
    default_argv = discovered[0] if discovered else [__import__("sys").executable, "-m", "pytest", "-q"]
    return _run_tool(
        args,
        label="test",
        default_argv=default_argv,
        description="Run the project's test suite (pytest).",
    )


def cmd_lint(args: argparse.Namespace) -> int:
    """Run ruff check on the project."""
    return _run_tool(
        args,
        label="lint",
        default_argv=["ruff", "check", "."],
        description="Run ruff check across the project.",
    )


def cmd_typecheck(args: argparse.Namespace) -> int:
    """Run mypy on the project."""
    return _run_tool(
        args,
        label="typecheck",
        default_argv=["mypy", "."],
        description="Run mypy across the project.",
    )


_ADR_TEMPLATE = """# {title}

- ID: ADR-{number:04d}
- Status: proposed
- Date: {date}
- Author:

## Context

(Why this decision is being made — the situation, constraints, and forces.)

## Decision

(What we are doing.)

## Consequences

- Positive:
- Negative:
- Neutral:

## Links

- (related ADRs, issues, or roadmap slices)
"""


# --- Additive expansion 2026-05-02 -------------------------------------------
# The four artefact types task/interface/invariant/risk were originally
# advertised by ``cmd_scaffold`` as "land in PH-10 slice 10.4" but that slice
# closed without delivering them. The audit on 2026-05-02 surfaced the gap.
# These templates + dispatcher land them. Existing ``_ADR_TEMPLATE`` and the
# ADR scaffold path remain untouched.
# ---------------------------------------------------------------------------

_TASK_TEMPLATE = """# {title}

- ID: TASK-{number:04d}
- Status: open
- Date: {date}
- Owner:
- Phase:

## Goal

(What outcome counts as done.)

## Subtasks

- [ ]

## Verification

(How we will know this task is complete — tests, observable behaviour, sign-off.)

## Notes

"""


_INTERFACE_TEMPLATE = """# {title}

- ID: INT-{number:04d}
- Status: draft
- Date: {date}
- Owner:

## Purpose

(What this interface is for and which boundary it crosses.)

## Contract

(Inputs, outputs, error conditions, and invariants the interface upholds.)

## Producers / Consumers

- Producers:
- Consumers:

## Notes

"""


_INVARIANT_TEMPLATE = """# {title}

- ID: INV-{number:04d}
- Status: active
- Date: {date}
- Owner:

## Invariant

(The condition that must always hold.)

## Rationale

(Why this invariant exists and what it protects.)

## Enforcement

(How this invariant is enforced — tests, gates, types, runtime checks, ADR cross-links.)

## Violation Cost

(What happens if this is broken — incident class, blast radius, recovery work.)

## Notes

"""


_RISK_TEMPLATE = """# {title}

- ID: RISK-{number:04d}
- Status: open
- Date: {date}
- Severity:
- Likelihood:
- Owner:

## Description

(What the risk is.)

## Impact

(What happens if it materialises — operational, security, reputational, compliance.)

## Mitigation

(What is being done to reduce likelihood or impact.)

## Trigger / Detection

(How we will know if this risk is materialising — alerts, audits, leading indicators.)

## Notes

"""


# Specification table for the additive artefact types. ``cmd_scaffold``
# routes through this table before the legacy adr-only branch.
_ARTEFACT_SPECS: dict[str, dict[str, object]] = {
    "task": {
        "directory_parts": ("mythic", "tasks"),
        "file_prefix": "TASK-",
        "id_label": "TASK",
        "template": _TASK_TEMPLATE,
    },
    "interface": {
        "directory_parts": ("docs", "interfaces"),
        "file_prefix": "INT-",
        "id_label": "INT",
        "template": _INTERFACE_TEMPLATE,
    },
    "invariant": {
        "directory_parts": ("docs", "invariants"),
        "file_prefix": "INV-",
        "id_label": "INV",
        "template": _INVARIANT_TEMPLATE,
    },
    "risk": {
        "directory_parts": ("docs", "risks"),
        "file_prefix": "RISK-",
        "id_label": "RISK",
        "template": _RISK_TEMPLATE,
    },
}


def _next_adr_number(adr_dir: Path) -> int:
    if not adr_dir.exists():
        return 1
    highest = 0
    for path in adr_dir.glob("ADR-*.md"):
        prefix = path.stem
        digits = ""
        for ch in prefix[len("ADR-"):]:
            if ch.isdigit():
                digits += ch
            else:
                break
        if digits:
            try:
                highest = max(highest, int(digits))
            except ValueError:
                continue
    return highest + 1


def _slugify_adr_title(title: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in title.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "untitled"


# Additive 2026-05-02: generic artefact-number helper used by the new
# task/interface/invariant/risk scaffold paths. Mirrors ``_next_adr_number``
# but takes the file prefix as an argument so it can scan ``TASK-*.md``,
# ``INT-*.md``, ``INV-*.md``, or ``RISK-*.md`` directories. The original
# ``_next_adr_number`` is left in place (it remains the entry point for the
# adr scaffold path) per the additive-only rule.
def _next_artefact_number(directory: Path, file_prefix: str) -> int:
    if not directory.exists():
        return 1
    highest = 0
    for path in directory.glob(f"{file_prefix}*.md"):
        prefix = path.stem
        digits = ""
        for ch in prefix[len(file_prefix):]:
            if ch.isdigit():
                digits += ch
            else:
                break
        if digits:
            try:
                highest = max(highest, int(digits))
            except ValueError:
                continue
    return highest + 1


def cmd_scaffold(args: argparse.Namespace) -> int:
    """Add a new artefact to an existing Mythic project.

    Supported artefact types (additive 2026-05-02): adr, task, interface,
    invariant, risk. The original adr path is unchanged; the four new
    types route through ``_cmd_scaffold_extended`` via ``_ARTEFACT_SPECS``.
    """
    root = Path(getattr(args, "path", ".")).resolve()
    artefact = getattr(args, "artefact", None)

    # Additive 2026-05-02: dispatch the four new artefact types before the
    # legacy rejection branch. The legacy branch is preserved below as the
    # USER_INPUT_ERROR path for any genuinely unknown artefact.
    if artefact in _ARTEFACT_SPECS:
        return _cmd_scaffold_extended(args, root, artefact, _ARTEFACT_SPECS[artefact])

    if artefact != "adr":
        # Note (2026-05-02 additive patch): the "not yet implemented" prefix
        # is retained for back-compat with existing tests that key on the
        # substring; the trailing prose was refreshed to reflect the now-
        # supported set, since the prior reference to "PH-10 slice 10.4"
        # was stale once the four types landed above.
        write_error(
            f"Scaffold artefact {artefact!r} not yet implemented. "
            "Recognised types: adr, task, interface, invariant, risk."
        )
        return USER_INPUT_ERROR

    title = (getattr(args, "title", "") or "").strip()
    if not title:
        write_error("scaffold adr requires --title <text>.")
        return USER_INPUT_ERROR

    adr_dir = root / "docs" / "ADRS"
    number = _next_adr_number(adr_dir)
    slug = _slugify_adr_title(title)
    target = adr_dir / f"ADR-{number:04d}-{slug}.md"

    if _flag(args, "dry_run"):
        payload = {
            "command": "scaffold adr",
            "dry_run": True,
            "target": str(target),
            "number": number,
            "title": title,
            "slug": slug,
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no ADR file will be written.")
            write_key_value("Target", target)
            write_key_value("Number", number)
            write_key_value("Title", title)
        return SUCCESS

    if target.exists():
        write_error(f"Refusing to overwrite existing ADR: {target}")
        return UNSAFE_OPERATION_BLOCKED

    adr_dir.mkdir(parents=True, exist_ok=True)
    rendered = _ADR_TEMPLATE.format(title=title, number=number, date=utc_now())
    target.write_text(rendered, encoding="utf-8")

    if _flag(args, "json"):
        write_json(
            {
                "command": "scaffold adr",
                "dry_run": False,
                "target": str(target),
                "number": number,
                "title": title,
                "slug": slug,
            }
        )
    else:
        write_line("ADR scaffold written.")
        write_key_value("Path", target)
        write_key_value("Number", number)
        write_key_value("Title", title)
    return SUCCESS


# Additive 2026-05-02: handler for the four new artefact types
# (task / interface / invariant / risk). Mirrors the adr scaffold flow
# above but parameterises directory, file prefix, id label, and template
# from ``_ARTEFACT_SPECS``. The adr path above is intentionally left as
# its own dedicated handler — it has the longest history and any drift
# from this generic helper is a smaller blast radius than collapsing
# both into one.
def _cmd_scaffold_extended(
    args: argparse.Namespace,
    root: Path,
    artefact: str,
    spec: dict[str, object],
) -> int:
    title = (getattr(args, "title", "") or "").strip()
    if not title:
        write_error(f"scaffold {artefact} requires --title <text>.")
        return USER_INPUT_ERROR

    directory_parts = spec["directory_parts"]  # type: ignore[index]
    file_prefix = spec["file_prefix"]  # type: ignore[index]
    id_label = spec["id_label"]  # type: ignore[index]
    template = spec["template"]  # type: ignore[index]
    assert isinstance(directory_parts, tuple)
    assert isinstance(file_prefix, str)
    assert isinstance(id_label, str)
    assert isinstance(template, str)

    target_dir = root.joinpath(*directory_parts)
    number = _next_artefact_number(target_dir, file_prefix)
    slug = _slugify_adr_title(title)
    target = target_dir / f"{file_prefix}{number:04d}-{slug}.md"

    if _flag(args, "dry_run"):
        payload = {
            "command": f"scaffold {artefact}",
            "dry_run": True,
            "target": str(target),
            "number": number,
            "title": title,
            "slug": slug,
            "id_label": id_label,
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line(f"Dry run: no {id_label} file will be written.")
            write_key_value("Target", target)
            write_key_value("Number", number)
            write_key_value("Title", title)
        return SUCCESS

    if target.exists():
        write_error(f"Refusing to overwrite existing {id_label}: {target}")
        return UNSAFE_OPERATION_BLOCKED

    target_dir.mkdir(parents=True, exist_ok=True)
    rendered = template.format(title=title, number=number, date=utc_now())
    target.write_text(rendered, encoding="utf-8")

    if _flag(args, "json"):
        write_json(
            {
                "command": f"scaffold {artefact}",
                "dry_run": False,
                "target": str(target),
                "number": number,
                "title": title,
                "slug": slug,
                "id_label": id_label,
            }
        )
    else:
        write_line(f"{id_label} scaffold written.")
        write_key_value("Path", target)
        write_key_value("Number", number)
        write_key_value("Title", title)
    return SUCCESS


def _changelog_unreleased_section(text: str) -> tuple[str, list[str]]:
    """Return ``(section_text, warnings)`` for the [Unreleased] block.

    Walks the markdown in linear order. The block ends at the next top-level
    ``## `` header or end-of-file, whichever comes first.
    """
    lines = text.splitlines()
    in_block = False
    section: list[str] = []
    warnings: list[str] = []
    for line in lines:
        if line.startswith("## ") and "[Unreleased]" in line:
            in_block = True
            section.append(line)
            continue
        if in_block and line.startswith("## "):
            break
        if in_block:
            section.append(line)
    if not section:
        warnings.append("CHANGELOG.md does not contain an [Unreleased] section.")
    return "\n".join(section).rstrip() + "\n" if section else "", warnings


def cmd_changelog(args: argparse.Namespace) -> int:
    """Print the CHANGELOG.md [Unreleased] section.

    With ``--check``, runs ``scripts/check_changelog.py`` if present and
    returns its exit code.
    """
    root = Path(getattr(args, "path", ".")).resolve()
    changelog = root / "CHANGELOG.md"

    if not changelog.exists():
        message = f"CHANGELOG.md not found at {changelog}"
        if _flag(args, "json"):
            write_json({"command": "changelog", "ok": False, "errors": [message]})
        else:
            write_error(message)
        return USER_INPUT_ERROR

    section, warnings = _changelog_unreleased_section(changelog.read_text(encoding="utf-8"))

    if _flag(args, "check"):
        check_script = root / "scripts" / "check_changelog.py"
        if not check_script.exists():
            if _flag(args, "json"):
                write_json(
                    {
                        "command": "changelog",
                        "check": True,
                        "ok": False,
                        "errors": [f"Validator script not found: {check_script}"],
                    }
                )
            else:
                write_error(f"Validator script not found: {check_script}")
            return USER_INPUT_ERROR
        result = run_command(
            [__import__("sys").executable, str(check_script)],
            cwd=root,
        )
        if _flag(args, "json"):
            write_json(
                {
                    "command": "changelog",
                    "check": True,
                    "ok": result.exit_code == 0,
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }
            )
            return SUCCESS if result.exit_code == 0 else VERIFICATION_FAILURE
        if result.stdout:
            write_line(result.stdout, force=True)
        if result.stderr:
            write_line(result.stderr, stream=__import__("sys").stderr, force=True)
        return SUCCESS if result.exit_code == 0 else VERIFICATION_FAILURE

    if _flag(args, "json"):
        write_json(
            {
                "command": "changelog",
                "path": str(changelog),
                "unreleased": section,
                "warnings": warnings,
            }
        )
        return SUCCESS

    if warnings:
        for warning in warnings:
            write_error(warning)
        return USER_INPUT_ERROR if not section else SUCCESS
    write_line(section, force=True)
    return SUCCESS


def cmd_version(args: argparse.Namespace) -> int:
    """Print the CLI version (and Python interpreter info on --verbose).

    The root ``--version`` flag still works for argparse-style invocation;
    this subcommand exists so the slash surface (``/version``) and the
    argparse layer expose the same shape.
    """
    import platform
    import sys as _sys

    from . import __version__ as cli_version

    payload: dict[str, object] = {
        "command": "version",
        "mythic_vibe_cli": cli_version,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "executable": _sys.executable,
    }

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_key_value("mythic-vibe", cli_version)
    if _flag(args, "verbose"):
        write_key_value("Python", platform.python_version())
        write_key_value("Platform", platform.platform())
        write_key_value("Executable", _sys.executable)
    return SUCCESS


# --- PH-02 slice 2.3: workflow-phase capture commands ---------------------

PHASE_CAPTURE_PHASES: tuple[str, ...] = (
    "intent",
    "constraints",
    "architecture",
    "plan",
    "build",
)

_PHASE_TEMPLATE = """# Mythic Phase Record

- Phase: {phase}
- Task: {task}
- Timestamp: {timestamp}
- Operator: {operator}
- Confidence: {confidence}
- Risk: {risk}

## Summary

{summary}

## Notes

{notes_block}

## Action Taken

(filled in during the build phase or after this capture)

## Verification

(filled in during the verify phase)

## Reflection

(filled in during the reflect phase)

## Next Step

{next_step}
"""


def _filename_safe_timestamp(timestamp: str) -> str:
    """Make an ISO timestamp safe to use as part of a filename.

    ``utc_now()`` returns ``2026-04-29T18:30:00Z``; colons are illegal in
    Windows file paths, so we swap them for hyphens. Cross-platform safe.
    """
    return timestamp.replace(":", "-")


def _render_notes_block(notes: list[str]) -> str:
    cleaned = [note.strip() for note in notes if note and note.strip()]
    if not cleaned:
        return "(none)"
    return "\n".join(f"- {item}" for item in cleaned)


def _resolve_operator(args: argparse.Namespace) -> str:
    candidate = getattr(args, "operator", None)
    if candidate:
        return str(candidate)
    return os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"


def _write_phase_record(
    args: argparse.Namespace,
    *,
    phase: str,
) -> int:
    """Capture a Mythic Phase Record to ``mythic/checkins/<ts>-<phase>.md``.

    Shared body for the five capture handlers (intent / constraints /
    architecture / plan / build). Each handler is a one-liner that
    forwards its phase string here.
    """
    if phase not in PHASE_CAPTURE_PHASES:
        write_error(f"Unsupported capture phase: {phase!r}")
        return USER_INPUT_ERROR

    root = Path(getattr(args, "path", ".")).resolve()
    task = (getattr(args, "task", "") or "").strip()
    summary = (getattr(args, "summary", "") or "").strip()
    if not task:
        write_error(f"{phase} capture requires --task <text>.")
        return USER_INPUT_ERROR
    if not summary:
        write_error(f"{phase} capture requires --summary <text>.")
        return USER_INPUT_ERROR

    notes: list[str] = list(getattr(args, "note", None) or [])
    confidence = (getattr(args, "confidence", None) or "unspecified").strip() or "unspecified"
    risk = (getattr(args, "risk", "") or "").strip() or "unspecified"
    next_step = (getattr(args, "next_step", "") or "").strip() or "(not specified)"
    operator = _resolve_operator(args)
    timestamp = utc_now()
    safe_ts = _filename_safe_timestamp(timestamp)
    target = root / "mythic" / "checkins" / f"{safe_ts}-{phase}.md"

    rendered = _PHASE_TEMPLATE.format(
        phase=phase,
        task=task,
        timestamp=timestamp,
        operator=operator,
        confidence=confidence,
        risk=risk,
        summary=summary,
        notes_block=_render_notes_block(notes),
        next_step=next_step,
    )

    payload = {
        "command": f"{phase} capture",
        "phase": phase,
        "task": task,
        "summary": summary,
        "notes": notes,
        "confidence": confidence,
        "risk": risk,
        "next_step": next_step,
        "operator": operator,
        "timestamp": timestamp,
        "target": str(target),
    }

    if _flag(args, "dry_run"):
        if _flag(args, "json"):
            write_json({**payload, "dry_run": True})
        else:
            write_line(f"Dry run: no {phase} capture record will be written.")
            write_key_value("Target", target)
            write_key_value("Task", task)
            write_key_value("Summary", summary)
            write_key_value("Notes", len(notes))
        return SUCCESS

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")

    # PH-07 follow-up: TTS phase-transition hook. No-op unless
    # MYTHIC_VOICE_TTS_ENABLED is set.
    from .voice.notify import notify_phase as _notify_phase
    _notify_phase(phase, "captured")

    if _flag(args, "json"):
        write_json({**payload, "dry_run": False})
        return SUCCESS

    write_line(f"{phase.capitalize()} capture recorded.")
    write_key_value("Path", target)
    write_key_value("Task", task)
    write_key_value("Operator", operator)
    return SUCCESS


def cmd_intent_capture(args: argparse.Namespace) -> int:
    return _write_phase_record(args, phase="intent")


def cmd_constraints_capture(args: argparse.Namespace) -> int:
    return _write_phase_record(args, phase="constraints")


def cmd_architecture_capture(args: argparse.Namespace) -> int:
    return _write_phase_record(args, phase="architecture")


def cmd_plan_capture(args: argparse.Namespace) -> int:
    return _write_phase_record(args, phase="plan")


def cmd_build_capture(args: argparse.Namespace) -> int:
    return _write_phase_record(args, phase="build")


def _phase_capture_dispatch(args: argparse.Namespace, *, phase: str, dest: str) -> int:
    """Shared dispatcher body for the five phase parents.

    Each parent has a single ``capture`` subcommand today. Future
    slices may add ``show``, ``list``, etc.; the dispatcher protects
    against unknown subcommands the same way ``cmd_ai_dispatch`` does
    (visible error before USER_INPUT_ERROR).
    """
    sub = getattr(args, dest, None)
    if sub == "capture":
        return _write_phase_record(args, phase=phase)
    write_error(
        f"Unknown {phase} subcommand: {sub!r}. Try `mythic-vibe {phase} capture --help`."
    )
    return USER_INPUT_ERROR


def cmd_intent_dispatch(args: argparse.Namespace) -> int:
    return _phase_capture_dispatch(args, phase="intent", dest="intent_command")


def cmd_constraints_dispatch(args: argparse.Namespace) -> int:
    return _phase_capture_dispatch(args, phase="constraints", dest="constraints_command")


def cmd_architecture_dispatch(args: argparse.Namespace) -> int:
    return _phase_capture_dispatch(args, phase="architecture", dest="architecture_command")


def cmd_plan_dispatch(args: argparse.Namespace) -> int:
    return _phase_capture_dispatch(args, phase="plan", dest="plan_command")


def cmd_build_dispatch(args: argparse.Namespace) -> int:
    return _phase_capture_dispatch(args, phase="build", dest="build_command")


def cmd_config(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    loaded = ConfigStore(root).load()
    if _flag(args, "json"):
        write_json(
            {
                "project_path": str(root),
                "sources": [str(src) for src in loaded.sources],
                "config": {
                    "codex.excerpt_limit": loaded.config.excerpt_limit,
                    "codex.packet_char_budget": loaded.config.packet_char_budget,
                    "codex.auto_compact": loaded.config.auto_compact,
                    "method.source": loaded.config.method_source,
                    "ai.provider": loaded.config.ai_provider,
                    "ai.model": loaded.config.ai_model,
                    "knowledge.sources": loaded.config.knowledge_sources,
                },
            }
        )
        return SUCCESS

    write_line("Resolved mythic-vibe configuration")
    write_key_value("Project path", root)
    if loaded.sources:
        write_line("- Loaded sources (low -> high precedence):")
        for src in loaded.sources:
            write_bullet(str(src), indent=2)
    else:
        write_line("- Loaded sources: none (using defaults + env vars)")

    write_line("- Effective values:")
    write_key_value("codex.excerpt_limit", loaded.config.excerpt_limit, indent=2)
    write_key_value("codex.packet_char_budget", loaded.config.packet_char_budget, indent=2)
    write_key_value("codex.auto_compact", str(loaded.config.auto_compact).lower(), indent=2)
    write_key_value("method.source", loaded.config.method_source, indent=2)
    write_key_value("ai.provider", loaded.config.ai_provider, indent=2)
    write_key_value("ai.model", loaded.config.ai_model, indent=2)
    write_key_value("knowledge.sources", len(loaded.config.knowledge_sources), indent=2)
    return SUCCESS


def cmd_doctor(args: argparse.Namespace) -> int:
    """Run project diagnostics — file/scaffold checks plus PH-13
    drift findings. JSON output gains a ``drift`` section listing
    every finding the slice-13.1 scanner produced; text output adds
    a Drift-findings list (empty case suppressed).

    Drift severity does not currently bump the doctor exit code —
    the heuristics today emit only ``info`` / ``warning``. A future
    detector that emits ``error`` would naturally promote a doctor
    run to non-zero exit via the existing ``report["errors"]`` path
    once it's wired through there.
    """
    from .drift import scan_for_drift
    # Phase 19.8 (audit remediation 2026-05-02): stale-catalog
    # watchdog. Surfaced as a doctor warning (text + JSON) so
    # operators / CI see catalog drift before users do. Pure
    # additive — does NOT promote doctor exit code; existing
    # callers see the same return value.
    from .ai.providers.model_catalog import evaluate_catalog_freshness
    # Phase 20.2 (additive 2026-05-02): doctor --fix runs two
    # tightly-scoped auto-remediations (mythic/ subdirs +
    # CHANGELOG [Unreleased]). --fix-dry-run previews. Hard-rule:
    # never edits user-authored content (constraints/oaths/ADRs/
    # packets/decisions).
    from .doctor_fix import FixReport, run_doctor_fix

    root = Path(args.path).resolve()
    workflow = MythicWorkflow(root)
    repo_boundary = _flag(args, "repo_boundary")
    report = workflow.doctor_report(
        repo_boundary=repo_boundary,
        project_scaffold=not repo_boundary,
    )
    drift_findings = scan_for_drift(root)
    drift_payload = [f.to_dict() for f in drift_findings]
    catalog_freshness = evaluate_catalog_freshness()

    fix_report: FixReport | None = None
    fix_requested = _flag(args, "fix")
    fix_dry_run = _flag(args, "fix_dry_run")
    if fix_requested or fix_dry_run:
        fix_report = run_doctor_fix(root, dry_run=fix_dry_run)

    if _flag(args, "json"):
        json_payload: dict[str, object] = {
            "path": str(root),
            "repo_boundary": repo_boundary,
            "ok": bool(report["ok"]),
            "errors": list(report["errors"]),
            "warnings": list(report["warnings"]),
            "sections": report["sections"],
            "drift": drift_payload,
            "model_catalog": catalog_freshness.to_dict(),
        }
        if fix_report is not None:
            json_payload["fixes"] = fix_report.to_dict()
        write_json(json_payload)
        return OPERATIONAL_FAILURE if report["errors"] else SUCCESS

    write_line("Mythic project diagnostics")
    write_key_value("Path", root)
    if repo_boundary:
        write_line("- Repo boundary checks: enabled")

    if report["errors"]:
        write_line("- Errors:")
        for item in report["errors"]:
            write_bullet(item, indent=2)
    else:
        write_line("- Errors: none")

    if report["warnings"]:
        write_line("- Warnings:")
        for item in report["warnings"]:
            write_bullet(item, indent=2)
    else:
        write_line("- Warnings: none")

    if drift_findings:
        write_line(f"- Drift findings: {len(drift_findings)}")
        for finding in drift_findings:
            write_bullet(
                f"[{finding.severity}] {finding.category}: {finding.path}",
                indent=2,
            )
    else:
        write_line("- Drift findings: none")

    # Phase 19.8 (additive 2026-05-02): catalog freshness line.
    if catalog_freshness.parse_error is not None:
        write_line(
            f"- Model catalog: malformed last_updated "
            f"({catalog_freshness.parse_error!r}) — treating as stale"
        )
    elif catalog_freshness.is_stale:
        write_line(
            f"- Model catalog: STALE — last_updated "
            f"{catalog_freshness.last_updated} "
            f"({catalog_freshness.days_since_update} days ago, "
            f"threshold {catalog_freshness.threshold_days})"
        )
    else:
        write_line(
            f"- Model catalog: fresh — last_updated "
            f"{catalog_freshness.last_updated} "
            f"({catalog_freshness.days_since_update} days ago)"
        )

    # Phase 20.2 (additive 2026-05-02): fix report.
    if fix_report is not None:
        mode_label = "dry-run" if fix_report.dry_run else "applied"
        write_line(
            f"- Auto-fix ({mode_label}): "
            f"{len(fix_report.fixed)} fixed, "
            f"{len(fix_report.would_fix)} would-fix, "
            f"{len(fix_report.skipped)} skipped"
        )
        for action in fix_report.actions:
            write_bullet(
                f"[{action.status}] {action.rule_id}: "
                f"{action.message} ({action.target})",
                indent=2,
            )

    return OPERATIONAL_FAILURE if report["errors"] else SUCCESS


def _handoff_payload(root: Path, record: HandoffRecord) -> dict[str, object]:
    return {
        "handoff_id": record.handoff_id,
        "timestamp": record.timestamp,
        "branch": record.branch,
        "session_type": record.session_type,
        "objective": record.objective,
        "intent": record.intent,
        "constraints": record.constraints,
        "decisions": record.decisions,
        "files_changed": record.files_changed,
        "tests_run": record.tests_run,
        "failures": record.failures,
        "next_steps": record.next_steps,
        "prompt_packet_suggestion": record.prompt_packet_suggestion,
        "verification_id": record.verification_id,
        "verification_result": record.verification_result,
        "notes": record.notes,
        "markdown_path": str(root / "docs" / "SESSION_HANDOFF.md"),
        "json_path": str(root / "mythic" / "handoffs" / f"{record.handoff_id}.json"),
        "markdown": render_handoff_markdown(record),
    }


def _create_handoff(
    root: Path,
    *,
    objective: str | None = None,
    next_step: str | None = None,
    note: str | None = None,
    session_type: str = "reflect",
) -> tuple[HandoffRecord, Path, Path]:
    record = build_handoff_record(
        root,
        objective=objective,
        next_step=next_step,
        note=note,
        session_type=session_type,
    )
    json_path, md_path = write_handoff_record(root, record)
    try:
        from .memory.spine import record_handoff_memory

        record_handoff_memory(root, record)
    except Exception:
        pass
    # PH-07 follow-up: TTS phase-transition hook. No-op unless
    # MYTHIC_VOICE_TTS_ENABLED is set.
    from .voice.notify import notify_phase as _notify_phase
    _notify_phase("handoff", "written")
    return record, json_path, md_path


def cmd_handoff_create(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if _flag(args, "dry_run"):
        record = build_handoff_record(
            root,
            objective=getattr(args, "summary", None) or getattr(args, "objective", None),
            next_step=getattr(args, "next_step", None),
            note=getattr(args, "note", None),
            session_type=getattr(args, "session_type", "handoff"),
        )
        payload = _handoff_payload(root, record)
        payload["dry_run"] = True
        if _flag(args, "json"):
            write_json({"command": "handoff create", "path": str(root), "handoff": payload})
        else:
            write_line("Dry run: no session handoff will be written.")
            write_key_value("Handoff ID", record.handoff_id)
            write_key_value("Markdown", payload["markdown_path"])
            write_key_value("JSON", payload["json_path"])
            write_key_value("Next recommended action", record.next_steps[0] if record.next_steps else "review the handoff")
        return SUCCESS

    record, json_path, md_path = _create_handoff(
        root,
        objective=getattr(args, "summary", None) or getattr(args, "objective", None),
        next_step=getattr(args, "next_step", None),
        note=getattr(args, "note", None),
        session_type=getattr(args, "session_type", "handoff"),
    )
    if _flag(args, "json"):
        write_json({"command": "handoff create", "path": str(root), "handoff": _handoff_payload(root, record)})
        return SUCCESS

    write_line("Session handoff created.")
    write_key_value("Handoff ID", record.handoff_id)
    write_key_value("Markdown", md_path)
    write_key_value("JSON", json_path)
    write_key_value("Next recommended action", record.next_steps[0] if record.next_steps else "review the handoff")
    return SUCCESS


def cmd_handoff_show(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    handoff_id = getattr(args, "handoff_id", "") or ""
    record = load_handoff_record(root, handoff_id) if handoff_id else load_latest_handoff(root)
    if record is None:
        write_error("No handoff record found. Run `mythic-vibe reflect` first.")
        return USER_INPUT_ERROR

    if _flag(args, "json"):
        write_json({"command": _command_name(args, "handoff show"), "path": str(root), "handoff": _handoff_payload(root, record)})
        return SUCCESS

    write_line(render_handoff_markdown(record))
    return SUCCESS


def cmd_handoff_latest(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    record = load_latest_handoff(root)
    if record is None:
        write_error("No handoff record found. Run `mythic-vibe reflect` first.")
        return USER_INPUT_ERROR
    if _flag(args, "json"):
        write_json({"command": "handoff latest", "path": str(root), "handoff": _handoff_payload(root, record)})
        return SUCCESS

    write_line(render_handoff_markdown(record))
    return SUCCESS


def cmd_reflect(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if _flag(args, "dry_run"):
        record = build_handoff_record(
            root,
            objective=getattr(args, "summary", None) or getattr(args, "objective", None),
            next_step=getattr(args, "next_step", None),
            note=getattr(args, "note", None),
            session_type="reflect",
        )
        payload = _handoff_payload(root, record)
        payload["dry_run"] = True
        if _flag(args, "json"):
            write_json({"command": "reflect", "path": str(root), "handoff": payload})
        else:
            write_line("Dry run: no reflection handoff will be written.")
            write_key_value("Handoff ID", record.handoff_id)
            write_key_value("Markdown", payload["markdown_path"])
            write_key_value("JSON", payload["json_path"])
            write_key_value("Next recommended action", record.next_steps[0] if record.next_steps else "review the handoff")
        return SUCCESS

    summary_value = getattr(args, "summary", None) or getattr(args, "objective", None)
    next_step_value = getattr(args, "next_step", None)
    note_value = getattr(args, "note", None)
    base_payload = {
        "path": str(root),
        "summary": summary_value,
        "next_step": next_step_value,
        "note": note_value,
    }
    with PluginHookDispatcher(root) as dispatcher:
        dispatcher.load_and_subscribe()
        dispatcher.emit("before_reflect", dict(base_payload))
        record, json_path, md_path = _create_handoff(
            root,
            objective=summary_value,
            next_step=next_step_value,
            note=note_value,
            session_type="reflect",
        )
        next_recommended = record.next_steps[0] if record.next_steps else "review the handoff"
        after_payload = dict(base_payload)
        after_payload["handoff_id"] = record.handoff_id
        after_payload["json_path"] = str(json_path)
        after_payload["markdown_path"] = str(md_path)
        after_payload["next_recommended_action"] = next_recommended
        dispatcher.emit("after_reflect", after_payload)

    if _flag(args, "json"):
        write_json({"command": "reflect", "path": str(root), "handoff": _handoff_payload(root, record)})
        return SUCCESS

    write_line("Reflection handoff created.")
    write_key_value("Handoff ID", record.handoff_id)
    write_key_value("Markdown", md_path)
    write_key_value("JSON", json_path)
    write_key_value("Next recommended action", next_recommended)
    return SUCCESS


def cmd_resume(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    record = load_latest_handoff(root)
    if record is None:
        write_line("No handoff exists yet. Run `mythic-vibe reflect` to create one.")
        return SUCCESS

    payload = _handoff_payload(root, record)
    if _flag(args, "json"):
        write_json(
            {
                "command": "resume",
                "path": str(root),
                "handoff": payload,
                "next_recommended_action": record.next_steps[0] if record.next_steps else "review the handoff",
            }
        )
        return SUCCESS

    write_line("Resume summary")
    write_key_value("Handoff ID", record.handoff_id)
    write_key_value("Next recommended action", record.next_steps[0] if record.next_steps else "review the handoff")
    write_key_value("Prompt packet suggestion", record.prompt_packet_suggestion)
    return SUCCESS


def cmd_handoff_dispatch(args: argparse.Namespace) -> int:
    if args.handoff_command == "create":
        return cmd_handoff_create(args)
    if args.handoff_command == "show":
        return cmd_handoff_show(args)
    if args.handoff_command == "latest":
        return cmd_handoff_latest(args)
    return USER_INPUT_ERROR


def cmd_sync(_args: argparse.Namespace) -> int:
    root = Path(getattr(_args, "path", ".")).resolve()
    if _flag(_args, "dry_run"):
        store = _method_store(root)
        if _flag(_args, "json"):
            write_json(
                {
                    "command": _command_name(_args, "sync"),
                    "dry_run": True,
                    "source": store.method_source.source,
                    "cache_file": str(store.cache_file),
                    "message": "Dry run: no method sync will be performed.",
                }
            )
            return SUCCESS
        write_line("Dry run: no method sync will be performed.")
        write_key_value("Cache", store.cache_file)
        return SUCCESS

    store = _method_store(root)
    try:
        bundle = store.sync()
    except Exception as exc:  # noqa: BLE001 - CLI should show actionable message and continue.
        write_error(format_error(CliError(f"Sync failed: {exc}")))
        return OPERATIONAL_FAILURE

    if _flag(_args, "json"):
        write_json(
            {
                "command": _command_name(_args, "sync"),
                "dry_run": False,
                "source": bundle.source,
                "cache_file": str(store.cache_file),
                "message": "Synced Mythic method notes.",
            }
        )
        return SUCCESS

    write_line("Synced Mythic method notes.")
    write_key_value("Source", bundle.source)
    write_key_value("Cache", store.cache_file)
    return SUCCESS


def cmd_method_status(args: argparse.Namespace) -> int:
    root = Path(getattr(args, "path", ".")).resolve()
    store = _method_store(root)
    status = store.status()
    payload = {"command": _command_name(args, "method status"), "method": status.to_dict()}
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line("Mythic method profile:")
    write_key_value("Source", status.source)
    write_key_value("Profile", status.profile)
    write_key_value("Version", status.version)
    write_key_value("Cache", status.cache_file)
    write_key_value("Freshness", status.freshness)
    write_key_value("Pinned", "yes" if status.pinned else "no")
    write_line("Method sections:")
    for section in status.sections:
        write_bullet(section)
    if not status.cached:
        write_line("Freshness warning: no cached canonical method corpus found; using fallback profile.")
    return SUCCESS


def cmd_method(_args: argparse.Namespace) -> int:
    root = Path(getattr(_args, "path", ".")).resolve()
    store = _method_store(root)
    bundle = store.load_cached_or_fallback()[0]
    if _flag(_args, "json"):
        status = store.status()
        write_json(
            {
                "command": _command_name(_args, "method show"),
                "method": status.to_dict(),
                "content": bundle.content,
            }
        )
        return SUCCESS
    write_verbose(f"Loaded method bundle from {bundle.source}")
    write_key_value("Method source", bundle.source)
    write_line("=" * 72)
    write_line(bundle.content)
    return SUCCESS


def cmd_method_diff(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    target = root / args.target
    store = _method_store(root)
    try:
        diff = store.diff_import_manifest(target)
    except FileNotFoundError:
        write_error(f"No method manifest found at {target / 'method_manifest.json'}. Run `mythic-vibe import-md` first.")
        return USER_INPUT_ERROR

    payload = {"command": "method diff", "path": str(root), "target": str(target), "diff": diff.to_dict()}
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    if diff.clean:
        write_line("Method corpus matches manifest.")
        write_key_value("Manifest", diff.manifest_path)
        return SUCCESS

    write_line("Method corpus differs from manifest.")
    write_key_value("Manifest", diff.manifest_path)
    if diff.missing:
        write_line("Missing files:")
        for path in diff.missing:
            write_bullet(path)
    if diff.changed:
        write_line("Changed files:")
        for path in diff.changed:
            write_bullet(path)
    if diff.untracked:
        write_line("Untracked markdown files:")
        for path in diff.untracked:
            write_bullet(path)
    return SUCCESS


def cmd_method_pin(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    target = root / args.target
    store = _method_store(root)
    try:
        diff = store.diff_import_manifest(target)
    except FileNotFoundError:
        write_error(f"No method manifest found at {target / 'method_manifest.json'}. Run `mythic-vibe import-md` first.")
        return USER_INPUT_ERROR

    if not diff.clean:
        payload = {"command": "method pin", "path": str(root), "target": str(target), "pinned": False, "diff": diff.to_dict()}
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_error("Cannot pin method corpus while it differs from method_manifest.json. Run `mythic-vibe method diff`.")
        return VERIFICATION_FAILURE

    if _flag(args, "dry_run"):
        payload = {
            "command": "method pin",
            "path": str(root),
            "target": str(target),
            "dry_run": True,
            "pinned": False,
            "pin_path": str(target / "method_pin.json"),
            "message": "Dry run: no method pin will be written.",
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no method pin will be written.")
            write_key_value("Pin", target / "method_pin.json")
        return SUCCESS

    pin = store.pin_import_manifest(target, note=getattr(args, "note", "") or "")
    payload = {"command": "method pin", "path": str(root), "target": str(target), "pinned": True, "pin": pin.to_dict()}
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line("Method corpus pinned.")
    write_key_value("Pin", pin.pin_path)
    write_key_value("Source", pin.source)
    write_key_value("Ref", pin.ref)
    write_key_value("Manifest SHA-256", pin.manifest_sha256)
    write_key_value("Markdown files", pin.markdown_files)
    return SUCCESS


def cmd_method_dispatch(args: argparse.Namespace) -> int:
    command = getattr(args, "method_command", None)
    if command is None:
        return cmd_method(args)
    if command == "status":
        return cmd_method_status(args)
    if command == "show":
        return cmd_method(args)
    if command == "sync":
        return cmd_sync(args)
    if command == "diff":
        return cmd_method_diff(args)
    if command == "pin":
        return cmd_method_pin(args)
    return USER_INPUT_ERROR


def cmd_oath(args: argparse.Namespace) -> int:
    """Recite the operator's standing oath. PH-14 Slice 14.2 wires
    the policy gate as a demonstration: if blocking constraints
    exist in mythic/oaths.md / constraints.md / docs/ADRS/, the
    command requires ``--override "<reason>"`` to proceed."""
    from .policy.policy_gate import enforce_policy

    oath = "I understand that AI may generate incorrect or insecure code. I will review all changes before committing to the Sacred Grove."
    root = Path(getattr(args, "path", ".")).resolve()
    override_reason = str(getattr(args, "override", "") or "").strip()

    proceed, decision = enforce_policy(
        root,
        action="write",
        command="oath",
        override_reason=override_reason or None,
    )

    if not proceed:
        write_error(
            f"Policy gate blocks `oath` — {len(decision.violations)} blocking "
            "constraint(s). Re-run with --override \"<reason>\" to bypass:"
        )
        for constraint in decision.violations:
            write_bullet(
                f"[{constraint.severity}] {constraint.text} "
                f"(from {constraint.source_path})",
                indent=2,
            )
        return UNSAFE_OPERATION_BLOCKED

    if override_reason and decision.violations:
        write_line(
            f"Policy override accepted ({len(decision.violations)} blocking "
            "violation(s)) — reason recorded to mythic/policy_overrides.jsonl."
        )

    write_line(oath)
    if args.yes:
        write_line("Oath accepted.")
    return SUCCESS


def cmd_policy_report(args: argparse.Namespace) -> int:
    """PH-14 Slice 14.4 — list current constraints + override
    history. JSON and text modes."""
    from .policy.constraint_store import load_constraints
    from .policy.override_log import read_overrides

    root = Path(getattr(args, "path", ".")).resolve()
    load_result = load_constraints(root)
    overrides = read_overrides(root)

    severity_counts: dict[str, int] = {}
    for constraint in load_result.constraints:
        severity_counts[constraint.severity] = (
            severity_counts.get(constraint.severity, 0) + 1
        )
    kind_counts: dict[str, int] = {}
    for constraint in load_result.constraints:
        kind_counts[constraint.kind] = kind_counts.get(constraint.kind, 0) + 1

    payload = {
        "command": "policy report",
        "path": str(root),
        "constraints": [c.to_dict() for c in load_result.constraints],
        "overrides": [o.to_dict() for o in overrides],
        "counts": {
            "constraints": len(load_result.constraints),
            "overrides": len(overrides),
            "severity": severity_counts,
            "kind": kind_counts,
        },
        "notes": list(load_result.notes),
    }

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line("Mythic policy report")
    write_key_value("Path", root)
    write_key_value("Constraints", len(load_result.constraints))
    write_key_value("Overrides", len(overrides))
    if not load_result.constraints:
        write_line(
            "  (no constraints loaded — populate mythic/oaths.md, "
            "mythic/constraints.md, or docs/ADRS/ to enable the gate)"
        )
        return SUCCESS

    write_line("- Constraints by kind:")
    for kind, count in kind_counts.items():
        write_bullet(f"{kind}: {count}", indent=2)
    write_line("- Constraints by severity:")
    for severity, count in severity_counts.items():
        write_bullet(f"{severity}: {count}", indent=2)
    write_line("- Active constraints:")
    for constraint in load_result.constraints:
        write_bullet(
            f"[{constraint.severity}] {constraint.id}: {constraint.text} "
            f"(from {constraint.source_path})",
            indent=2,
        )
    if overrides:
        write_line("- Recent overrides:")
        for override in overrides[-10:]:  # last 10
            write_bullet(
                f"{override.timestamp}  {override.command}  by {override.actor}: {override.reason}",
                indent=2,
            )
    return SUCCESS


def cmd_policy_dispatch(args: argparse.Namespace) -> int:
    sub = getattr(args, "policy_command", "")
    if sub == "report":
        return cmd_policy_report(args)
    write_error(
        f"Unknown policy subcommand: {sub!r}. Try `mythic-vibe policy report --help`."
    )
    return USER_INPUT_ERROR


def cmd_protocols_mcp_server(args: argparse.Namespace) -> int:
    """PH-16 Slice 16.1 — bind the MCP server to stdio.

    Reads JSON-RPC 2.0 frames on stdin, writes responses on
    stdout until stdin closes. Operators wire this into their
    MCP-aware client (Claude Desktop, Cursor, etc.) via the
    client's server config.
    """
    from .protocols.mcp_server import run_stdio_server

    return run_stdio_server()


def cmd_protocols_acp_bridge(args: argparse.Namespace) -> int:
    """PH-16 Slice 16.3 — bind the ACP bridge to stdio."""
    from .protocols.acp_bridge import run_stdio_server

    return run_stdio_server()


def cmd_protocols_otel_status(args: argparse.Namespace) -> int:
    """PH-16 Slice 16.4 — print the OpenTelemetry tracing
    status. Diagnostic only — never enables tracing."""
    from .protocols.otel import status

    snapshot = status()
    payload = {
        "command": "protocols otel-status",
        "status": snapshot.to_dict(),
    }
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line("OpenTelemetry status")
    write_key_value("Active", snapshot.active)
    write_key_value("Enabled (env)", snapshot.enabled_env)
    write_key_value("SDK available", snapshot.sdk_available)
    for note in snapshot.notes:
        write_bullet(note, indent=2)
    return SUCCESS


def cmd_protocols_dispatch(args: argparse.Namespace) -> int:
    sub = getattr(args, "protocols_command", "")
    if sub == "mcp-server":
        return cmd_protocols_mcp_server(args)
    if sub == "acp-bridge":
        return cmd_protocols_acp_bridge(args)
    if sub == "otel-status":
        return cmd_protocols_otel_status(args)
    write_error(
        f"Unknown protocols subcommand: {sub!r}. "
        "Try `mythic-vibe protocols mcp-server | acp-bridge | otel-status`."
    )
    return USER_INPUT_ERROR


def cmd_surface_web(args: argparse.Namespace) -> int:
    """PH-17 Slice 17.1 — launch the web terminal HTTP server.

    Binds to 127.0.0.1 by default. External exposure requires
    --bind 0.0.0.0 + (responsibly) a TLS reverse proxy.
    """
    from .surfaces.web_terminal import (
        DEFAULT_HOST,
        DEFAULT_PORT,
        WebTerminalConfig,
        WebTerminalServer,
    )
    import secrets as _secrets

    host = str(getattr(args, "bind", "") or DEFAULT_HOST)
    port = int(getattr(args, "port", 0) or DEFAULT_PORT)
    token = str(getattr(args, "token", "") or "").strip()
    if not token:
        token = _secrets.token_urlsafe(32)
    config = WebTerminalConfig(host=host, port=port, token=token)

    if _flag(args, "json"):
        write_json(
            {
                "command": "surface web",
                "host": config.host,
                "port": config.port,
                "token": config.token,
                "url": f"http://{config.host}:{config.port}/",
            }
        )
        return SUCCESS

    write_line("Mythic Vibe CLI - Web Terminal launching")
    write_key_value("URL", f"http://{config.host}:{config.port}/")
    write_key_value("Token", config.token)
    write_line(
        "  Paste the token into the browser field. Press Ctrl-C to stop."
    )
    server = WebTerminalServer(config=config)
    try:
        server.start()
    except KeyboardInterrupt:
        write_line("Web terminal stopped.")
        server.stop()
    return SUCCESS


def cmd_surface_ssh_doctor(args: argparse.Namespace) -> int:
    """PH-17 Slice 17.3 - SSH-readiness diagnostic."""
    from .surfaces.ssh_doctor import run_ssh_doctor

    report = run_ssh_doctor()
    payload = {
        "command": "surface ssh-doctor",
        "report": report.to_dict(),
    }
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line("SSH readiness check")
    write_key_value("Total checks", payload["report"]["total"])
    write_key_value("Passed", payload["report"]["passed"])
    write_key_value("Warnings", payload["report"]["warnings"])
    for check in report.checks:
        marker = "PASS" if check.passed else f"WARN ({check.severity})"
        write_bullet(f"[{marker}] {check.name}: {check.detail}")
    return SUCCESS


def cmd_surface_chat(args: argparse.Namespace) -> int:
    """PH-17 Slice 17.4 + Phase E (audit remediation 2026-05-02) -
    chat bridge surface.

    Default behaviour (no ``--run`` flag): the original 17.4
    scaffolding-and-exit entry — prints a notice and returns
    SUCCESS. Preserved verbatim for back-compat with the original
    slice contract.

    With ``--run``: starts the long-poll loop for the chosen
    backend (Matrix ``/sync`` or Telegram ``getUpdates``). Requires
    the master gate ``MYTHIC_CHAT_BRIDGE_ENABLED=1`` (default off,
    durable rule) plus an explicit allowlist via
    ``MYTHIC_CHAT_<BACKEND>_ALLOWED_*`` env vars or a ``--config``
    file. Honours SIGINT / SIGTERM for clean shutdown.
    """
    backend = str(getattr(args, "backend", "") or "").lower()
    if backend not in {"matrix", "telegram"}:
        write_error(
            "surface chat requires --backend matrix|telegram. "
            "Both are open-source-friendly; Matrix is the default."
        )
        return USER_INPUT_ERROR

    # Phase E.3 2026-05-02 (audit remediation, finding #2): if the
    # operator passed --run, dispatch the long-poll loop for the
    # chosen backend. The legacy scaffolding-and-exit body below
    # this branch is preserved unchanged.
    if bool(_flag(args, "run")):
        return _cmd_surface_chat_run(args, backend)

    from .surfaces.chat_bridge import COMMAND_PREFIX

    payload = {
        "command": "surface chat",
        "backend": backend,
        "trigger_prefix": COMMAND_PREFIX,
        "scaffolded": True,
        "note": (
            "This is the slice 17.4 scaffolding entry. The chat "
            "bridge's poll loop expects credentials supplied by "
            "your own deployment script (e.g. systemd EnvironmentFile, "
            "1Password CLI, vault). See docs/SSH_DEPLOYMENT.md. "
            "Pass --run to start the long-poll loop (Phase E)."
        ),
    }
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line(f"Chat bridge ({backend}) - scaffolding entry")
    write_line(payload["note"])
    return SUCCESS


# Additive 2026-05-02 (Phase E.3): the long-poll dispatch path.
# Kept as a private helper so the scaffolding-and-exit body of
# cmd_surface_chat above remains a pure read-only diagnostic.
def _cmd_surface_chat_run(args: argparse.Namespace, backend: str) -> int:
    import signal
    import threading

    from .surfaces.chat_bridge import (
        CHAT_BRIDGE_ENABLED_ENV,
        ChatBridgeConfigError,
        MatrixConfig,
        TelegramConfig,
        is_chat_bridge_enabled,
    )
    from .surfaces.chat_bridge_loop import run_matrix_loop, run_telegram_loop

    # Master gate — operator must explicitly opt in to the bridge
    # surface (durable rule for default-off feature gates).
    if not is_chat_bridge_enabled():
        write_error(
            f"Chat bridge surface is disabled. Set "
            f"{CHAT_BRIDGE_ENABLED_ENV}=1 in the environment to enable. "
            "(Default-off per the chat-bridge security policy.)"
        )
        return USER_INPUT_ERROR

    config_path_str = str(getattr(args, "config", "") or "").strip()
    config_path = Path(config_path_str) if config_path_str else None
    max_iterations = getattr(args, "max_iterations", None)

    # Build + validate the per-backend config.
    try:
        if backend == "matrix":
            config = MatrixConfig.from_sources(config_path=config_path)
            config.validate()
        else:  # telegram
            config = TelegramConfig.from_sources(config_path=config_path)
            config.validate()
    except ChatBridgeConfigError as exc:
        write_error(f"Chat bridge config error: {exc}")
        return USER_INPUT_ERROR

    # Signal handlers → stop_event for clean shutdown. SIGINT is
    # always available; SIGTERM exists on POSIX. We install whatever
    # the platform provides.
    stop_event = threading.Event()
    previous_handlers: dict[int, object] = {}

    def _on_signal(signum: int, frame: object) -> None:  # noqa: ANN001
        write_line(f"(chat-bridge {backend}) signal {signum} received; stopping...")
        stop_event.set()

    for sig_name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            previous_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, _on_signal)
        except (ValueError, OSError):
            # signal.signal must be called from the main thread; tests
            # / TUI invocations may not have that luxury. Skip the
            # registration; loop still honours stop_event when set
            # programmatically.
            previous_handlers.pop(sig, None)

    write_line(f"Chat bridge ({backend}) — running. Ctrl+C to stop.")
    try:
        if backend == "matrix":
            dispatched = run_matrix_loop(
                config,
                stop_event=stop_event,
                max_iterations=max_iterations,
            )
        else:  # telegram
            dispatched = run_telegram_loop(
                config,
                stop_event=stop_event,
                max_iterations=max_iterations,
            )
    except ChatBridgeConfigError as exc:
        write_error(f"Chat bridge config error: {exc}")
        return USER_INPUT_ERROR
    except Exception as exc:  # noqa: BLE001 - terminal HTTP / unexpected
        write_error(f"Chat bridge ({backend}) terminal error: {exc}")
        return OPERATIONAL_FAILURE
    finally:
        # Restore previous signal handlers (best-effort).
        for sig, prev in previous_handlers.items():
            try:
                signal.signal(sig, prev)
            except (ValueError, OSError):
                pass

    if _flag(args, "json"):
        write_json(
            {
                "command": "surface chat --run",
                "backend": backend,
                "dispatched": dispatched,
                "stopped_cleanly": stop_event.is_set(),
            }
        )
    else:
        write_line(
            f"Chat bridge ({backend}) stopped cleanly. Dispatched "
            f"{dispatched} command(s)."
        )
    return SUCCESS


def cmd_surface_dispatch(args: argparse.Namespace) -> int:
    sub = getattr(args, "surface_command", "")
    if sub == "web":
        return cmd_surface_web(args)
    if sub == "ssh-doctor":
        return cmd_surface_ssh_doctor(args)
    if sub == "chat":
        return cmd_surface_chat(args)
    # v1.0 / Hermes: agent control plane HTTP server.
    if sub == "hermes":
        return cmd_surface_hermes(args)
    write_error(
        f"Unknown surface subcommand: {sub!r}. "
        "Try `mythic-vibe surface web | ssh-doctor | chat | hermes --help`."
    )
    return USER_INPUT_ERROR


def cmd_surface_hermes(args: argparse.Namespace) -> int:
    """v1.0 / Hermes — launch the agent control-plane HTTP server.

    Token-protected JSON API exposing the curated tool registry.
    Default bind ``127.0.0.1``; external exposure requires
    explicit ``--bind 0.0.0.0`` + (responsibly) a TLS reverse proxy.
    """
    import secrets as _secrets
    from .agent_api.http_api import (
        DEFAULT_HOST as HERMES_DEFAULT_HOST,
        DEFAULT_PORT as HERMES_DEFAULT_PORT,
        HermesHttpConfig,
        HermesHttpServer,
    )
    from .agent_api.tcl import build_default_agent

    root = Path(getattr(args, "path", ".")).resolve()
    host = str(getattr(args, "bind", "") or HERMES_DEFAULT_HOST)
    port = int(getattr(args, "port", 0) or HERMES_DEFAULT_PORT)
    token = str(getattr(args, "token", "") or "").strip()
    if not token:
        token = _secrets.token_urlsafe(32)

    agent = build_default_agent(root=root)
    config = HermesHttpConfig(core=agent.core, host=host, port=port, token=token)

    if _flag(args, "json"):
        write_json(
            {
                "command": "surface hermes",
                "host": config.host,
                "port": config.port,
                "token": config.token,
                "url": f"http://{config.host}:{config.port}/api/health",
                "tool_count": len(agent.list_tools()),
            }
        )
        return SUCCESS

    write_line("Mythic Vibe CLI - Hermes Agent surface launching")
    write_key_value("URL", f"http://{config.host}:{config.port}/api/health")
    write_key_value("Token", config.token)
    write_key_value("Tool count", len(agent.list_tools()))
    write_line(
        "  Pass the token in the X-Hermes-Token header OR as a 'token' "
        "field in POST bodies. Press Ctrl-C to stop."
    )
    server = HermesHttpServer(config=config)
    try:
        server.start()
    except KeyboardInterrupt:
        write_line("Hermes surface stopped.")
        server.stop()
    return SUCCESS


def cmd_hermes(args: argparse.Namespace) -> int:
    """v1.0 / Hermes — top-level introspection command. Three
    subcommands:

    - ``hermes tools`` — list registered tools (text or JSON)
    - ``hermes invoke --tool NAME [--args JSON]`` — invoke one tool
      directly from the CLI without spinning up the HTTP server
    - ``hermes inspect --tool NAME`` — show one tool's full spec
    """
    sub = getattr(args, "hermes_command", "") or ""
    if sub == "tools":
        return cmd_hermes_tools(args)
    if sub == "invoke":
        return cmd_hermes_invoke(args)
    if sub == "inspect":
        return cmd_hermes_inspect(args)
    write_error(
        f"Unknown hermes subcommand: {sub!r}. "
        "Try `mythic-vibe hermes tools | invoke | inspect --help`."
    )
    return USER_INPUT_ERROR


def cmd_hermes_tools(args: argparse.Namespace) -> int:
    from .agent_api.tcl import build_default_agent

    root = Path(getattr(args, "path", ".")).resolve()
    agent = build_default_agent(root=root)
    tools = agent.list_tools()
    if _flag(args, "json"):
        write_json({"command": "hermes tools", "path": str(root), "tools": tools})
        return SUCCESS
    write_line("Hermes registered tools")
    write_key_value("Path", root)
    write_key_value("Total", len(tools))
    for tool in tools:
        write_bullet(
            f"{tool['name']} — {tool['description']}",
            indent=2,
        )
        if tool.get("capabilities"):
            write_bullet(
                f"capabilities: {', '.join(tool['capabilities'])}",
                indent=4,
            )
        if tool.get("side_effects"):
            for se in tool["side_effects"]:
                write_bullet(f"side-effect: {se}", indent=4)
    return SUCCESS


def cmd_hermes_invoke(args: argparse.Namespace) -> int:
    import json as _json
    from .agent_api import Invocation
    from .agent_api.tcl import build_default_agent

    root = Path(getattr(args, "path", ".")).resolve()
    tool = (getattr(args, "tool", "") or "").strip()
    if not tool:
        write_error("--tool is required")
        return USER_INPUT_ERROR
    raw_args = (getattr(args, "args", "") or "").strip()
    parsed_args: dict[str, object] = {}
    if raw_args:
        try:
            parsed_args = _json.loads(raw_args)
            if not isinstance(parsed_args, dict):
                raise ValueError("--args must decode to a JSON object")
        except (ValueError, _json.JSONDecodeError) as exc:
            write_error(f"--args is not valid JSON object: {exc}")
            return USER_INPUT_ERROR

    agent = build_default_agent(root=root)
    result = agent.core.invoke(Invocation(tool=tool, args=parsed_args))

    if _flag(args, "json"):
        write_json({
            "command": "hermes invoke",
            "path": str(root),
            **result.to_dict(),
        })
        return SUCCESS if result.ok else OPERATIONAL_FAILURE

    write_line("Hermes invoke")
    write_key_value("Path", root)
    write_key_value("Tool", tool)
    write_key_value("Status", result.status)
    write_key_value("Elapsed (ms)", round(result.elapsed_ms, 2))
    if result.error:
        write_key_value("Error", result.error)
    if result.ok:
        write_line("Result:")
        write_line(_json.dumps(result.value, indent=2, default=str))
    return SUCCESS if result.ok else OPERATIONAL_FAILURE


def cmd_hermes_inspect(args: argparse.Namespace) -> int:
    from .agent_api.tcl import build_default_agent

    root = Path(getattr(args, "path", ".")).resolve()
    tool = (getattr(args, "tool", "") or "").strip()
    if not tool:
        write_error("--tool is required")
        return USER_INPUT_ERROR
    agent = build_default_agent(root=root)
    matches = [t for t in agent.list_tools() if t["name"] == tool]
    if not matches:
        write_error(
            f"Unknown tool: {tool!r}. "
            f"Available: {sorted(t['name'] for t in agent.list_tools())}"
        )
        return USER_INPUT_ERROR
    spec = matches[0]
    if _flag(args, "json"):
        write_json({"command": "hermes inspect", "tool": spec})
        return SUCCESS
    import json as _json
    write_line(f"Tool: {spec['name']}")
    write_key_value("Description", spec["description"])
    write_key_value(
        "Capabilities",
        ", ".join(spec["capabilities"]) or "(none — read-own-context only)",
    )
    if spec.get("side_effects"):
        write_line("Side effects:")
        for se in spec["side_effects"]:
            write_bullet(se, indent=2)
    write_line("Input schema:")
    write_line(_json.dumps(spec["input_schema"], indent=2))
    return SUCCESS


def cmd_simulate(args: argparse.Namespace) -> int:
    """PH-18 Slice 18.4 — `mythic-vibe simulate`. Runs canonical
    failure scenarios and reports pass/fail per scenario.

    Read-only against the host filesystem — every scenario
    operates inside a TemporaryDirectory.
    """
    from .robustness.simulate import run_simulation

    report = run_simulation()
    payload = {
        "command": "simulate",
        "report": report.to_dict(),
    }

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS if report.ok else OPERATIONAL_FAILURE

    write_line("Mythic resilience simulation")
    write_key_value("Total scenarios", len(report.outcomes))
    write_key_value("Passed", report.passed)
    write_key_value("Failed", report.failed)
    for outcome in report.outcomes:
        marker = "PASS" if outcome.passed else "FAIL"
        write_bullet(
            f"[{marker}] {outcome.name} -> exit={outcome.actual_exit_code} "
            f"({outcome.detail})"
        )
    if not report.ok:
        write_error(
            f"Simulation reported {report.failed} failure(s). "
            "Re-run with --json for full payloads."
        )
        return OPERATIONAL_FAILURE
    return SUCCESS


def cmd_grimoire(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    registry = PluginRegistry(root)
    store_file = registry.path
    if _flag(args, "dry_run") and args.grimoire_command == "add":
        payload = {
            "command": "grimoire add",
            "dry_run": True,
            "registry": str(store_file),
            "plugin": args.plugin,
            "hooks": getattr(args, "hook", []) or [],
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no plugin registry entry will be written.")
            write_key_value("Registry", store_file)
            write_key_value("Plugin", args.plugin)
        return SUCCESS

    if args.grimoire_command == "add":
        try:
            record, created = registry.add(
                args.plugin,
                hooks=getattr(args, "hook", []) or [],
                version=getattr(args, "version", "unknown"),
            )
        except ValueError as exc:
            write_error(str(exc))
            return USER_INPUT_ERROR
        if created:
            message = f"Registered plugin: {args.plugin}"
        else:
            message = f"Plugin already registered: {args.plugin}"
        plugins = [item.entrypoint for item in registry.list()]
        if _flag(args, "json"):
            write_json(
                {
                    "command": "grimoire add",
                    "dry_run": False,
                    "registry": str(store_file),
                    "plugin": args.plugin,
                    "plugin_record": record.to_dict(),
                    "plugins": plugins,
                    "sandbox_warning": "Plugins are local Python extension points. Inspect and trust them before enabling.",
                }
            )
            return SUCCESS
        write_line(message)
        write_key_value("Registry", store_file)
        return SUCCESS

    records = registry.list()
    plugins = [record.entrypoint for record in records]
    if _flag(args, "json"):
        write_json(
            {
                "command": "grimoire list",
                "registry": str(store_file),
                "plugins": plugins,
                "plugin_records": [record.to_dict() for record in records],
                "available_hooks": PLUGIN_HOOKS,
            }
        )
        return SUCCESS

    if not plugins:
        write_line("No plugins registered.")
        return SUCCESS
    write_line("Registered plugins:")
    for plugin in plugins:
        write_bullet(plugin)
    return SUCCESS


def cmd_plugin_list(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    registry = PluginRegistry(root)
    records = registry.list(include_disabled=_flag(args, "all"))
    inspections = [inspect_plugin(record, import_plugin=False) for record in records]
    payload = {
        "command": "plugin list",
        "registry": str(registry.path),
        "available_hooks": PLUGIN_HOOKS,
        "sandbox_warning": "Plugins are local Python extension points. Inspect and trust them before enabling.",
        "plugins": inspections,
    }
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    if not inspections:
        write_line("No plugins registered.")
        return SUCCESS
    write_line("Registered plugins:")
    for item in inspections:
        health = item["health"] if isinstance(item.get("health"), dict) else {}
        write_bullet(f"{item['entrypoint']} [{health.get('status', 'unknown')}]")
    return SUCCESS


def cmd_plugin_inspect(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    registry = PluginRegistry(root)
    record = registry.get(args.plugin)
    if record is None:
        write_error(f"Plugin is not registered: {args.plugin}")
        return USER_INPUT_ERROR
    inspection = inspect_plugin(record, import_plugin=not _flag(args, "metadata_only"))
    payload = {
        "command": "plugin inspect",
        "registry": str(registry.path),
        "plugin": inspection,
    }
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    health = inspection["health"] if isinstance(inspection.get("health"), dict) else {}
    write_line("Plugin inspection")
    write_key_value("Plugin", inspection["entrypoint"])
    write_key_value("Status", health.get("status", "unknown"))
    write_key_value("Version", inspection.get("version", "unknown"))
    if inspection.get("hooks"):
        write_line("- Hooks:")
        for hook in inspection["hooks"]:
            write_bullet(str(hook), indent=2)
    for warning in health.get("warnings", []):
        write_key_value("Warning", warning)
    for error in health.get("errors", []):
        write_key_value("Error", error)
    return SUCCESS


def cmd_plugin_disable(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    registry = PluginRegistry(root)
    if _flag(args, "dry_run"):
        payload = {
            "command": "plugin disable",
            "dry_run": True,
            "registry": str(registry.path),
            "plugin": args.plugin,
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no plugin will be disabled.")
            write_key_value("Plugin", args.plugin)
        return SUCCESS

    record = registry.disable(args.plugin)
    if record is None:
        write_error(f"Plugin is not registered: {args.plugin}")
        return USER_INPUT_ERROR
    payload = {
        "command": "plugin disable",
        "registry": str(registry.path),
        "plugin": record.to_dict(),
    }
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS
    write_line("Plugin disabled.")
    write_key_value("Plugin", record.entrypoint)
    write_key_value("Registry", registry.path)
    return SUCCESS


def cmd_plugin_discover(args: argparse.Namespace) -> int:
    """PH-10 Slice 10.1 — list every installed entry-point in the
    `mythic_vibe.plugins` group, regardless of whether it's
    registered in the project. Pure read-only discovery.
    """
    from .plugins.entry_points import discover_entry_points

    records = discover_entry_points()
    payload = {
        "command": "plugin discover",
        "group": "mythic_vibe.plugins",
        "entry_points": [r.to_dict() for r in records],
        "count": len(records),
    }
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    if not records:
        write_line(
            "No installed entry-points in group 'mythic_vibe.plugins'."
        )
        write_line(
            "  Plugins declare themselves via [project.entry-points] in "
            "their pyproject.toml; install them via pip first."
        )
        return SUCCESS
    write_line(f"Discovered {len(records)} entry-point(s):")
    for record in records:
        suffix = (
            f" (from {record.distribution} {record.version})"
            if record.distribution
            else ""
        )
        write_bullet(f"{record.name} → {record.entrypoint_string}{suffix}")
    return SUCCESS


def cmd_plugin_install(args: argparse.Namespace) -> int:
    """PH-10 Slice 10.1 — register a discovered entry-point in the
    project's plugin registry. Operators specify either the
    friendly entry-point name (e.g. ``my_plugin``) or the full
    ``module:attr`` string.
    """
    from .plugins.entry_points import find_entry_point

    root = Path(args.path).resolve()
    name_or_entrypoint = str(getattr(args, "name", "") or "").strip()
    if not name_or_entrypoint:
        write_error("plugin install requires a name or module:attr argument.")
        return USER_INPUT_ERROR

    record = find_entry_point(name_or_entrypoint)
    if record is None:
        write_error(
            f"Entry-point not found: {name_or_entrypoint!r}. "
            "Run `mythic-vibe plugin discover` to list installed plugins."
        )
        return USER_INPUT_ERROR

    registry = PluginRegistry(root)
    if _flag(args, "dry_run"):
        payload = {
            "command": "plugin install",
            "dry_run": True,
            "registry": str(registry.path),
            "entry_point": record.to_dict(),
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no plugin will be installed.")
            write_key_value("Plugin", record.entrypoint_string)
            write_key_value("Source", record.distribution or "(unknown)")
        return SUCCESS

    plugin_record, added = registry.add(
        record.entrypoint_string,
        hooks=[],
        version=record.version or "unknown",
    )
    payload = {
        "command": "plugin install",
        "registry": str(registry.path),
        "added": added,
        "entry_point": record.to_dict(),
        "plugin": plugin_record.to_dict(),
    }
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS
    if added:
        write_line("Plugin installed.")
    else:
        write_line("Plugin already registered (no change).")
    write_key_value("Plugin", plugin_record.entrypoint)
    write_key_value("Registry", registry.path)
    return SUCCESS


def cmd_security_audit(args: argparse.Namespace) -> int:
    """PH-11 Slice 11.7 — `mythic-vibe security audit`.

    Walks the repo and runs every PH-11 detector:
    - secret scanner (slice 11.3)
    - dangerous-pattern scanner (slice 11.5)

    Plus reports the active config:
    - approval mode (slice 11.1)
    - privacy policy (slice 11.6)
    - sandbox execution policy (slice 11.4)
    - redaction engine summary (slice 11.2)

    Returns severity-tagged JSON when --json. Non-zero exit code
    when any "critical" or "high" finding lands.
    """
    from .security.approval import resolve_mode, load_security_config
    from .security.dangerous_patterns import scan_paths as scan_dangerous_paths
    from .security.exec_policy import resolve_sandbox_policy
    from .security.privacy import resolve_privacy_policy
    from .security.redaction import RedactionEngine, engine_from_config
    from .security.secret_scanner import scan_paths as scan_secret_paths

    root = Path(args.path).resolve()
    config = load_security_config(root)
    redaction_engine: RedactionEngine = engine_from_config(config)
    privacy_policy = resolve_privacy_policy(root)
    sandbox_policy = resolve_sandbox_policy(root)
    approval_mode = resolve_mode(root, cli_override=getattr(args, "approval", None))

    # Walk the repo (best-effort) and gather scannable paths.
    candidates: list[Path] = []
    skip_dirs = {".git", "__pycache__", "node_modules", ".mypy_cache", ".ruff_cache", "dist", "build", "mythic"}
    text_extensions = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".sql",
        ".md", ".toml", ".yaml", ".yml", ".json", ".cfg", ".ini",
        ".env",  # included so the scanner reports it as forbidden
    }
    for path in root.rglob("*"):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part in skip_dirs for part in relative.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in text_extensions or path.name in {".env"}:
            candidates.append(path)

    secret_result = scan_secret_paths(
        candidates, root=root, engine=redaction_engine
    )
    danger_result = scan_dangerous_paths(candidates, root=root)

    severity_counts: dict[str, int] = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "advisory": 0,
    }
    for finding in secret_result.findings:
        severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
    for finding in danger_result.findings:
        severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

    has_blocking = severity_counts.get("critical", 0) + severity_counts.get("high", 0) > 0

    payload = {
        "command": "security audit",
        "path": str(root),
        "approval_mode": approval_mode,
        "redaction": redaction_engine.to_dict(),
        "privacy": privacy_policy.to_dict(),
        "sandbox": sandbox_policy.to_dict(),
        "secret_scan": secret_result.to_dict(),
        "dangerous_pattern_scan": danger_result.to_dict(),
        "severity_counts": severity_counts,
        "blocking": has_blocking,
        "files_audited": len(candidates),
    }

    if _flag(args, "json"):
        write_json(payload)
        return OPERATIONAL_FAILURE if has_blocking else SUCCESS

    write_line("Mythic security audit")
    write_key_value("Path", root)
    write_key_value("Approval mode", approval_mode)
    write_key_value("Privacy enabled", privacy_policy.enabled)
    write_key_value("Sandbox enabled", sandbox_policy.enabled)
    write_key_value("Files audited", len(candidates))
    write_line("- Secret scan:")
    write_key_value("  Findings", len(secret_result.findings), indent=2)
    write_key_value("  Forbidden paths skipped", len(secret_result.forbidden_paths), indent=2)
    write_line("- Dangerous patterns:")
    write_key_value("  Findings", len(danger_result.findings), indent=2)
    write_line("- Severity counts:")
    for severity, count in severity_counts.items():
        if count:
            write_bullet(f"{severity}: {count}", indent=2)
    if has_blocking:
        write_error(
            f"Audit reports {severity_counts.get('critical', 0)} critical "
            f"+ {severity_counts.get('high', 0)} high finding(s). Re-run "
            "with --json for the full payload."
        )
        return OPERATIONAL_FAILURE
    return SUCCESS


def cmd_ci_scaffold(args: argparse.Namespace) -> int:
    """PH-12 Slice 12.1 — generate a GitHub Actions workflow tuned
    to the detected stack."""
    from .cicd.ci_scaffold import scaffold_ci_workflow

    root = Path(args.path).resolve()
    force = bool(_flag(args, "force"))
    dry_run = bool(_flag(args, "dry_run"))
    result = scaffold_ci_workflow(root, force=force, dry_run=dry_run)

    payload: dict[str, object] = {
        "command": "ci scaffold",
        "path": str(root),
        "result": result.to_dict(),
    }
    if dry_run:
        payload["preview"] = result.body

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    if dry_run:
        write_line(f"Dry run: would write {result.target}")
        write_key_value("Stack", result.stack.primary_language)
        write_line("- Preview (first 20 lines):")
        for line in result.body.splitlines()[:20]:
            write_bullet(line, indent=2)
        return SUCCESS

    if result.skipped_reason:
        write_error(result.skipped_reason)
        return USER_INPUT_ERROR

    write_line("CI workflow scaffolded.")
    write_key_value("Path", result.target)
    write_key_value("Stack", result.stack.primary_language)
    return SUCCESS


def cmd_ci_dispatch(args: argparse.Namespace) -> int:
    sub = getattr(args, "ci_command", "")
    if sub == "scaffold":
        return cmd_ci_scaffold(args)
    write_error(
        f"Unknown ci subcommand: {sub!r}. Try `mythic-vibe ci scaffold --help`."
    )
    return USER_INPUT_ERROR


def cmd_docker_scaffold(args: argparse.Namespace) -> int:
    """PH-12 Slice 12.2 — generate Dockerfile + .dockerignore +
    docker-compose.yml tuned to the detected stack."""
    from .cicd.docker_scaffold import scaffold_docker

    root = Path(args.path).resolve()
    force = bool(_flag(args, "force"))
    dry_run = bool(_flag(args, "dry_run"))
    result = scaffold_docker(root, force=force, dry_run=dry_run)

    payload: dict[str, object] = {
        "command": "docker scaffold",
        "path": str(root),
        "result": result.to_dict(),
    }
    if dry_run:
        payload["previews"] = {
            str(f.target.name): f.body for f in result.files
        }

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    if dry_run:
        write_line("Dry run: would write the following files:")
        for entry in result.files:
            write_bullet(f"{entry.target.name} ({len(entry.body)} bytes)")
        return SUCCESS

    skipped = [f for f in result.files if f.skipped_reason]
    if skipped:
        for entry in skipped:
            write_error(entry.skipped_reason)
        if result.written_count == 0:
            return USER_INPUT_ERROR

    write_line(f"Docker scaffold complete ({result.written_count} file(s) written).")
    write_key_value("Stack", result.stack.primary_language)
    for entry in result.files:
        marker = "wrote" if entry.written else "skipped"
        write_bullet(f"{marker}: {entry.target}")
    return SUCCESS


def cmd_docker_dispatch(args: argparse.Namespace) -> int:
    sub = getattr(args, "docker_command", "")
    if sub == "scaffold":
        return cmd_docker_scaffold(args)
    write_error(
        f"Unknown docker subcommand: {sub!r}. Try `mythic-vibe docker scaffold --help`."
    )
    return USER_INPUT_ERROR


def cmd_release(args: argparse.Namespace) -> int:
    """PH-12 Slice 12.3 — semver-aware release helper.

    Computes the next version, renders a changelog stub, and
    optionally writes pyproject.toml + creates a git tag. **Never
    pushes** — operators own the publish step.
    """
    from .cicd.release import prepare_release

    root = Path(args.path).resolve()
    bump = str(getattr(args, "bump", "patch") or "patch")
    if bump not in {"major", "minor", "patch"}:
        write_error(f"--bump must be major | minor | patch, got {bump!r}")
        return USER_INPUT_ERROR

    apply = bool(_flag(args, "apply"))
    create_tag = bool(_flag(args, "tag"))
    summary = str(getattr(args, "summary", "") or "")

    result = prepare_release(
        root,
        bump=bump,  # type: ignore[arg-type]
        apply=apply,
        create_tag=create_tag,
        summary=summary,
    )

    payload = {
        "command": "release",
        "path": str(root),
        "result": result.to_dict(),
    }

    if _flag(args, "json"):
        write_json(payload)
        if result.current_version is None:
            return USER_INPUT_ERROR
        return SUCCESS

    if result.current_version is None:
        write_error(
            "Could not read a [project] version from pyproject.toml. "
            "Add `version = \"x.y.z\"` to [project] first."
        )
        return USER_INPUT_ERROR

    write_line(
        f"Release plan: {result.current_version} → {result.new_version} "
        f"(bump={bump}, dry_run={result.dry_run})"
    )
    write_key_value("pyproject_updated", result.pyproject_updated)
    if result.tag is not None:
        write_key_value("tag_created", result.tag.created)
        if result.tag.error:
            write_key_value("tag_error", result.tag.error)
    write_line("- Changelog stub:")
    for line in result.changelog_entry.splitlines():
        write_bullet(line, indent=2)
    for note in result.notes:
        write_key_value("note", note)
    return SUCCESS


def cmd_rollback(args: argparse.Namespace) -> int:
    """PH-12 Slice 12.4 — read-only rollback summariser. Reports
    commits + files between a baseline ref and HEAD; never
    actually reverts anything."""
    from .cicd.rollback import summarise_rollback

    root = Path(args.path).resolve()
    since = str(getattr(args, "since", "") or "")
    report = summarise_rollback(root, since_ref=since)

    payload = {
        "command": "rollback",
        "path": str(root),
        "report": report.to_dict(),
    }

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS if report.ok else OPERATIONAL_FAILURE

    if not report.ok:
        write_error(report.error)
        return OPERATIONAL_FAILURE

    write_line(
        f"Rollback summary: {report.since_ref}..HEAD "
        f"({len(report.commits)} commit(s), {len(report.files)} file(s))"
    )
    if report.commits:
        write_line("- Commits:")
        for commit in report.commits:
            write_bullet(
                f"{commit.short_sha}  {commit.subject}  ({commit.author})",
                indent=2,
            )
    if report.files:
        write_line("- Files touched:")
        for path in report.files:
            write_bullet(path, indent=2)
    for note in report.notes:
        write_key_value("note", note)
    write_line(
        "  This helper does NOT revert anything. To revert, run "
        "`git revert <sha>` or `git reset --hard <ref>` manually."
    )
    return SUCCESS


def cmd_security_dispatch(args: argparse.Namespace) -> int:
    sub = getattr(args, "security_command", "")
    if sub == "audit":
        return cmd_security_audit(args)
    write_error(
        f"Unknown security subcommand: {sub!r}. Try `mythic-vibe security audit --help`."
    )
    return USER_INPUT_ERROR


def cmd_plugin_dispatch(args: argparse.Namespace) -> int:
    if args.plugin_command == "list":
        return cmd_plugin_list(args)
    if args.plugin_command == "inspect":
        return cmd_plugin_inspect(args)
    if args.plugin_command == "disable":
        return cmd_plugin_disable(args)
    if args.plugin_command == "discover":
        return cmd_plugin_discover(args)
    if args.plugin_command == "install":
        return cmd_plugin_install(args)
    # Phase 20.3 (additive 2026-05-02): plugin doctor — audits
    # capability declarations, manifest health, circuit-breaker
    # state. Read-only.
    if args.plugin_command == "doctor":
        return cmd_plugin_doctor(args)
    return USER_INPUT_ERROR


def cmd_plugin_doctor(args: argparse.Namespace) -> int:
    """Phase 20.3 — audit installed plugins. Reads the registry,
    validates declared capabilities against the known
    vocabulary, and surfaces any active circuit-breaker
    failures from the in-process state. Read-only — does not
    modify the manifest or disable plugins."""
    from .plugins.capabilities import (
        DEFAULT_CAPABILITIES,
        audit_capabilities,
    )
    from .plugins.circuit_breaker import (
        DEFAULT_THRESHOLD,
        THRESHOLD_ENV,
    )

    root = Path(args.path).resolve()
    registry = PluginRegistry(root)
    records = registry.list(include_disabled=True)

    audited: list[dict[str, object]] = []
    plugin_warnings: list[str] = []
    for record in records:
        cap_audit = audit_capabilities(tuple(record.capabilities))
        audited.append(
            {
                "entrypoint": record.entrypoint,
                "enabled": record.enabled,
                "version": record.version,
                "hooks": list(record.hooks),
                "capabilities": cap_audit.to_dict(),
            }
        )
        for unknown in cap_audit.unknown:
            plugin_warnings.append(
                f"{record.entrypoint}: unknown capability "
                f"{unknown!r} (typo? see "
                "mythic_vibe_cli/plugins/capabilities.py)"
            )

    breaker_threshold_env = (
        os.environ.get(THRESHOLD_ENV) or str(DEFAULT_THRESHOLD)
    )

    if _flag(args, "json"):
        write_json(
            {
                "command": "plugin doctor",
                "registry": str(registry.path),
                "default_capabilities": list(DEFAULT_CAPABILITIES),
                "breaker_threshold": breaker_threshold_env,
                "warnings": plugin_warnings,
                "plugins": audited,
            }
        )
        return SUCCESS

    write_line("Plugin doctor")
    write_key_value("Registry", registry.path)
    write_key_value("Breaker threshold", breaker_threshold_env)
    write_key_value(
        "Default capabilities",
        ", ".join(DEFAULT_CAPABILITIES) or "(none — read-own-context only)",
    )
    if not audited:
        write_line("- No plugins registered.")
        return SUCCESS

    write_line("Plugins:")
    for entry in audited:
        cap = entry["capabilities"]
        if not isinstance(cap, dict):
            continue
        cap_label = (
            ", ".join(cap.get("declared", []))
            if cap.get("declared")
            else "default-deny"
        )
        unknown = cap.get("unknown") or []
        marker = " (UNKNOWN: " + ", ".join(unknown) + ")" if unknown else ""
        enabled_label = "enabled" if entry.get("enabled") else "disabled"
        write_bullet(
            f"{entry['entrypoint']} [{enabled_label}] "
            f"capabilities=[{cap_label}]{marker}",
            indent=2,
        )

    if plugin_warnings:
        write_line("Warnings:")
        for warning in plugin_warnings:
            write_bullet(warning, indent=2)
    return SUCCESS


def cmd_config_set(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    config_file = root / "mythic" / "config.toml"
    if _flag(args, "dry_run"):
        payload = {
            "command": "config set",
            "dry_run": True,
            "config_file": str(config_file),
            "key": args.key,
            "value": args.value,
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no config file will be written.")
            write_key_value("Config file", config_file)
            write_bullet(f"{args.key} = {args.value}")
        return SUCCESS

    config_file.parent.mkdir(parents=True, exist_ok=True)
    with config_file.open("a", encoding="utf-8") as fh:
        fh.write(f'{args.key} = "{args.value}"\n')
    if _flag(args, "json"):
        write_json(
            {
                "command": "config set",
                "dry_run": False,
                "config_file": str(config_file),
                "key": args.key,
                "value": args.value,
            }
        )
        return SUCCESS

    write_key_value("Updated config", config_file)
    write_bullet(f"{args.key} = {args.value}")
    return SUCCESS


def cmd_state_show(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    store = JsonStateStore(root)

    try:
        payload = store.read_payload()
    except StateStoreError as exc:
        if _flag(args, "json"):
            write_json({"ok": False, "path": str(store.status_path), "errors": [str(exc)], "warnings": []})
        else:
            write_error(str(exc))
        return VERIFICATION_FAILURE

    if payload is None:
        message = "No mythic/status.json found. Run `mythic-vibe init` or `mythic-vibe db migrate` first."
        if _flag(args, "json"):
            write_json({"ok": False, "path": str(store.status_path), "errors": [message], "warnings": []})
        else:
            write_error(message)
        return USER_INPUT_ERROR

    state = coerce_project_state(payload)
    validation = validate_state_payload(payload)
    if _flag(args, "json"):
        write_json(
            {
                "ok": validation.ok,
                "path": str(store.status_path),
                "legacy": payload.get("schema_version") is None,
                "errors": validation.errors,
                "warnings": validation.warnings,
                "state": state.to_dict(),
            }
        )
        return VERIFICATION_FAILURE if validation.errors else SUCCESS

    write_line("Mythic project state")
    write_key_value("Path", store.status_path)
    write_key_value("Schema version", state.schema_version)
    write_key_value("Project ID", state.project_id)
    write_key_value("Goal", state.goal)
    write_key_value("Current phase", state.current_phase)
    write_key_value("Completed phases", ", ".join(state.completed_phases) or "none")
    write_key_value("Updated", state.updated_at)
    write_key_value("History records", len(state.history))
    if validation.warnings:
        write_line("- Warnings:")
        for warning in validation.warnings:
            write_bullet(warning, indent=2)
    if validation.errors:
        write_line("- Errors:")
        for error in validation.errors:
            write_bullet(error, indent=2)
        return VERIFICATION_FAILURE
    return SUCCESS


def cmd_state_validate(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    store = JsonStateStore(root)

    try:
        payload = store.read_payload()
    except StateStoreError as exc:
        errors = [str(exc)]
        if _flag(args, "json"):
            write_json({"ok": False, "path": str(store.status_path), "errors": errors, "warnings": []})
        else:
            write_line("Mythic state validation")
            write_key_value("Path", store.status_path)
            write_line("- Errors:")
            for error in errors:
                write_bullet(error, indent=2)
        return VERIFICATION_FAILURE

    if payload is None:
        errors = ["No mythic/status.json found. Run `mythic-vibe init` or `mythic-vibe db migrate` first."]
        if _flag(args, "json"):
            write_json({"ok": False, "path": str(store.status_path), "errors": errors, "warnings": []})
        else:
            write_error(errors[0])
        return USER_INPUT_ERROR

    validation = validate_state_payload(payload)
    if _flag(args, "json"):
        write_json(
            {
                "ok": validation.ok,
                "path": str(store.status_path),
                "errors": validation.errors,
                "warnings": validation.warnings,
            }
        )
        return SUCCESS if validation.ok else VERIFICATION_FAILURE

    write_line("Mythic state validation")
    write_key_value("Path", store.status_path)
    if validation.errors:
        write_line("- Errors:")
        for error in validation.errors:
            write_bullet(error, indent=2)
    else:
        write_line("- Errors: none")
    if validation.warnings:
        write_line("- Warnings:")
        for warning in validation.warnings:
            write_bullet(warning, indent=2)
    else:
        write_line("- Warnings: none")
    return SUCCESS if validation.ok else VERIFICATION_FAILURE


def _plunder_client(args: argparse.Namespace) -> GitHubClient | None:
    token = os.getenv(getattr(args, "token_env", "GITHUB_TOKEN"), "").strip()
    if not token:
        write_error(
            format_error(
                CliError(
                    f"Missing token. Set {getattr(args, 'token_env', 'GITHUB_TOKEN')} and retry (repo access is required).",
                    exit_code=USER_INPUT_ERROR,
                )
            )
        )
        return None
    return GitHubClient(token)


def _write_plunder_plan_output(args: argparse.Namespace, payload: dict[str, object]) -> int:
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    plan = payload.get("plan")
    write_line(str(payload.get("message", "Plunder plan ready.")))
    if isinstance(plan, dict):
        write_key_value("Repo", f"{plan.get('repo')}@{plan.get('ref')}")
        write_key_value("Source", plan.get("source_file"))
        write_key_value("Destination", plan.get("destination"))
        license_payload = plan.get("license") if isinstance(plan.get("license"), dict) else {}
        write_key_value("License", license_payload.get("spdx_id", "Unknown"))
        if license_payload.get("warning"):
            write_key_value("Warning", license_payload["warning"])
    return SUCCESS


def cmd_plunder_inspect(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if _flag(args, "dry_run"):
        payload = {
            "command": "plunder inspect",
            "dry_run": True,
            "repo": args.repo,
            "ref": args.ref,
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no GitHub repository metadata will be fetched.")
            write_key_value("Repo", f"{args.repo}@{args.ref}")
        return SUCCESS

    client = _plunder_client(args)
    if client is None:
        return USER_INPUT_ERROR

    try:
        info = client.inspect_repo(args.repo, args.ref)
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        write_error(format_error(CliError(f"GitHub API error ({exc.code}): {message}")))
        return OPERATIONAL_FAILURE
    except Exception as exc:  # noqa: BLE001
        write_error(format_error(CliError(f"Plunder inspect failed: {exc}")))
        return OPERATIONAL_FAILURE

    posture = classify_license(info.license_spdx_id, info.license_name)
    payload = {
        "command": "plunder inspect",
        "path": str(root),
        "repo": info.to_dict(),
        "license": posture.to_dict(),
    }
    if _flag(args, "json"):
        write_json(payload)
    else:
        write_line("Plunder inspection complete.")
        write_key_value("Repo", f"{info.repo}@{info.ref}")
        write_key_value("Resolved SHA", info.sha)
        write_key_value("License", posture.spdx_id)
        if posture.warning:
            write_key_value("Warning", posture.warning)
    return SUCCESS


def cmd_plunder_plan(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    dest_path = Path(args.dest)
    destination = str(dest_path if dest_path.is_absolute() else (root / dest_path).resolve())
    if _flag(args, "dry_run"):
        payload = {
            "command": "plunder plan",
            "dry_run": True,
            "repo": args.repo,
            "source": args.source,
            "ref": args.ref,
            "destination": destination,
        }
        return _write_plunder_plan_output(args, {"message": "Dry run: no plunder plan will be written.", "plan": payload})

    client = _plunder_client(args)
    if client is None:
        return USER_INPUT_ERROR

    try:
        info = client.inspect_repo(args.repo, args.ref)
        source_file = client.get_file(args.repo, args.source, info.sha)
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        write_error(format_error(CliError(f"GitHub API error ({exc.code}): {message}")))
        return OPERATIONAL_FAILURE
    except Exception as exc:  # noqa: BLE001
        write_error(format_error(CliError(f"Plunder plan failed: {exc}")))
        return OPERATIONAL_FAILURE

    posture = classify_license(info.license_spdx_id, info.license_name)
    plan = PlunderPlan(
        repo=args.repo,
        source_file=args.source,
        destination=destination,
        ref=info.sha,
        source_sha=source_file.sha,
        license_spdx_id=posture.spdx_id,
        license_name=posture.name,
        license_compatible=posture.compatible,
        license_warning=posture.warning,
        notes=posture.notes,
        modifications=args.modifications,
    )
    path = write_plan(root, plan)
    payload = {
        "command": "plunder plan",
        "path": str(root),
        "plan_path": str(path),
        "plan": plan.to_dict(),
    }
    return _write_plunder_plan_output(args, {"message": "Plunder plan written.", **payload})


def cmd_plunder_fetch(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if _flag(args, "dry_run"):
        payload = {
            "command": "plunder fetch",
            "dry_run": True,
            "repo": args.repo,
            "source": args.source,
            "ref": args.ref,
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no source file will be fetched into the cache.")
            write_key_value("Repo", f"{args.repo}@{args.ref}")
            write_key_value("Source", args.source)
        return SUCCESS

    client = _plunder_client(args)
    if client is None:
        return USER_INPUT_ERROR

    try:
        github_file, cache_path = client.fetch_to_cache(root, args.repo, args.source, args.ref)
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        write_error(format_error(CliError(f"GitHub API error ({exc.code}): {message}")))
        return OPERATIONAL_FAILURE
    except Exception as exc:  # noqa: BLE001
        write_error(format_error(CliError(f"Plunder fetch failed: {exc}")))
        return OPERATIONAL_FAILURE

    payload = {
        "command": "plunder fetch",
        "path": str(root),
        "source": github_file.to_dict(),
        "cache_path": str(cache_path),
    }
    if _flag(args, "json"):
        write_json(payload)
    else:
        write_line("Plunder source fetched.")
        write_key_value("Source", f"{args.repo}/{args.source}@{args.ref}")
        write_key_value("Cache", cache_path)
    return SUCCESS


def cmd_plunder_apply(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    try:
        plan = load_plan(root, Path(args.plan).resolve() if getattr(args, "plan", "") else None)
    except Exception as exc:  # noqa: BLE001
        write_error(format_error(CliError(f"Cannot load plunder plan: {exc}")))
        return USER_INPUT_ERROR

    destination = Path(plan.destination)
    if not destination.is_absolute():
        destination = (root / destination).resolve()
    source_cache = cache_path_for(root, plan.repo, plan.source_file, plan.ref)

    if not plan.license_compatible and not _flag(args, "force"):
        write_error(format_error(CliError(plan.license_warning or "Do not plunder: license is not compatible.")))
        return USER_INPUT_ERROR
    if destination.exists() and not _flag(args, "force"):
        write_error(format_error(CliError(f"Destination already exists; refusing to overwrite: {destination}")))
        return USER_INPUT_ERROR
    if not source_cache.exists():
        write_error(format_error(CliError(f"Fetched source is missing. Run `mythic-vibe plunder fetch` first: {source_cache}")))
        return USER_INPUT_ERROR

    if _flag(args, "dry_run"):
        payload = {
            "command": "plunder apply",
            "dry_run": True,
            "destination": str(destination),
            "source_cache": str(source_cache),
            "license": plan.license_spdx_id,
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no plundered file will be applied.")
            write_key_value("Source cache", source_cache)
            write_key_value("Destination", destination)
        return SUCCESS

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source_cache.read_text(encoding="utf-8"), encoding="utf-8")
    record = record_from_plan(plan, modifications=getattr(args, "modifications", "") or None)
    manifest = append_record(root, record)
    notice = update_notice(root, record) if _flag(args, "notice") else None
    payload = {
        "command": "plunder apply",
        "path": str(root),
        "destination": str(destination),
        "manifest": str(manifest),
        "notice": str(notice) if notice else None,
        "record": record.to_dict(),
    }
    if _flag(args, "json"):
        write_json(payload)
    else:
        write_line("Plunder applied and provenance recorded.")
        write_key_value("Destination", destination)
        write_key_value("Manifest", manifest)
        if notice:
            write_key_value("NOTICE", notice)
    return SUCCESS


def cmd_plunder_record(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    try:
        plan = load_plan(root, Path(args.plan).resolve() if getattr(args, "plan", "") else None)
    except Exception as exc:  # noqa: BLE001
        write_error(format_error(CliError(f"Cannot load plunder plan: {exc}")))
        return USER_INPUT_ERROR

    if _flag(args, "dry_run"):
        payload = {
            "command": "plunder record",
            "dry_run": True,
            "record": record_from_plan(plan, modifications=getattr(args, "modifications", "") or None).to_dict(),
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no plunder provenance will be recorded.")
        return SUCCESS

    record = record_from_plan(plan, modifications=getattr(args, "modifications", "") or None)
    manifest = append_record(root, record)
    notice = update_notice(root, record) if _flag(args, "notice") else None
    payload = {
        "command": "plunder record",
        "path": str(root),
        "manifest": str(manifest),
        "notice": str(notice) if notice else None,
        "record": record.to_dict(),
    }
    if _flag(args, "json"):
        write_json(payload)
    else:
        write_line("Plunder provenance recorded.")
        write_key_value("Manifest", manifest)
        if notice:
            write_key_value("NOTICE", notice)
    return SUCCESS


def cmd_plunder_legacy(args: argparse.Namespace) -> int:
    if not args.repo or not args.source or not args.dest:
        write_error("Legacy plunder mode requires --repo, --source, and --dest. Prefer `mythic-vibe plunder plan` for new work.")
        return USER_INPUT_ERROR

    out_path = Path(args.dest).resolve()
    if _flag(args, "dry_run"):
        payload = {
            "command": "plunder",
            "dry_run": True,
            "repo": args.repo,
            "source": args.source,
            "ref": args.ref,
            "destination": str(out_path),
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no GitHub file will be fetched or written.")
            write_key_value("Repo", f"{args.repo}@{args.ref}")
            write_key_value("Source", args.source)
            write_key_value("Destination", out_path)
        return SUCCESS

    client = _plunder_client(args)
    if client is None:
        return USER_INPUT_ERROR

    try:
        github_file = client.get_file(args.repo, args.source, args.ref)
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        write_error(format_error(CliError(f"GitHub API error ({exc.code}): {message}")))
        return OPERATIONAL_FAILURE
    except Exception as exc:  # noqa: BLE001
        write_error(format_error(CliError(f"Plunder failed: {exc}")))
        return OPERATIONAL_FAILURE

    if out_path.exists() and not _flag(args, "force"):
        write_error(format_error(CliError(f"Destination already exists; refusing to overwrite: {out_path}")))
        return USER_INPUT_ERROR
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(github_file.text, encoding="utf-8")
    if _flag(args, "json"):
        write_json(
            {
                "command": "plunder",
                "dry_run": False,
                "repo": args.repo,
                "source": args.source,
                "ref": args.ref,
                "source_sha": github_file.sha,
                "destination": str(out_path),
            }
        )
        return SUCCESS

    write_line("Plunder complete.")
    write_key_value("Repo", f"{args.repo}@{args.ref}")
    write_key_value("Source", args.source)
    write_key_value("Destination", out_path)
    return SUCCESS


def cmd_plunder(args: argparse.Namespace) -> int:
    command = getattr(args, "plunder_command", None)
    if command == "inspect":
        return cmd_plunder_inspect(args)
    if command == "plan":
        return cmd_plunder_plan(args)
    if command == "fetch":
        return cmd_plunder_fetch(args)
    if command == "apply":
        return cmd_plunder_apply(args)
    if command == "record":
        return cmd_plunder_record(args)
    return cmd_plunder_legacy(args)


def cmd_provenance(args: argparse.Namespace) -> int:
    """Phase 20.6 — top-level provenance commands. Currently two
    subcommands: ``verify`` (PH-20.6) and ``attest`` (PH-20.G)."""
    command = getattr(args, "provenance_command", None)
    if command == "verify":
        return cmd_provenance_verify(args)
    # Phase 20.G (additive 2026-05-03): per-line modification
    # attestation against an explicit original.
    if command == "attest":
        return cmd_provenance_attest(args)
    write_error(
        f"Unknown provenance subcommand: {command!r}. Valid: verify | attest."
    )
    return USER_INPUT_ERROR


def cmd_provenance_attest(args: argparse.Namespace) -> int:
    """Phase 20.G — compute per-line modification attestation
    between a local file and an explicit original. The original
    is read from ``--original PATH``; the operator supplies it
    (e.g. by checking out an upstream ref into a separate
    location, or pointing at a cached plunder import)."""
    from .plunder.attestation import attest_file

    root = Path(args.path).resolve()
    destination = getattr(args, "destination", "") or ""
    original_path = getattr(args, "original", "") or ""
    if not destination:
        write_error("--destination is required")
        return USER_INPUT_ERROR
    if not original_path:
        write_error("--original is required")
        return USER_INPUT_ERROR

    original = Path(original_path)
    if not original.is_absolute():
        original = (root / original).resolve()
    if not original.is_file():
        write_error(f"Original file not found: {original}")
        return USER_INPUT_ERROR
    try:
        original_text = original.read_text(encoding="utf-8")
    except OSError as exc:
        write_error(f"Cannot read original {original}: {exc}")
        return OPERATIONAL_FAILURE

    dest_path = Path(destination)
    if not dest_path.is_absolute():
        dest_path = (root / dest_path).resolve()
    if not dest_path.is_file():
        write_error(f"Destination file not found: {dest_path}")
        return USER_INPUT_ERROR

    try:
        attestation = attest_file(
            destination=Path(destination),
            original_text=original_text,
            project_root=root,
        )
    except OSError as exc:
        write_error(f"Cannot read destination {dest_path}: {exc}")
        return OPERATIONAL_FAILURE

    if _flag(args, "json"):
        write_json(
            {
                "command": "provenance attest",
                "path": str(root),
                "destination": destination,
                "original": str(original),
                **attestation.to_dict(),
            }
        )
        return SUCCESS

    write_line("Provenance modification attestation")
    write_key_value("Destination", attestation.destination)
    write_key_value("Original SHA-256", attestation.original_sha256)
    write_key_value("Local SHA-256", attestation.local_sha256)
    write_key_value("Modified", attestation.modified)
    write_key_value("Added lines", attestation.added)
    write_key_value("Removed lines", attestation.removed)
    write_key_value("Unchanged lines", attestation.unchanged)
    return SUCCESS


def cmd_review(args: argparse.Namespace) -> int:
    """Phase 20.H — top-level review commands. Currently one
    subcommand: ``architecture`` (quarterly governance pass)."""
    command = getattr(args, "review_command", None)
    if command == "architecture":
        return cmd_review_architecture(args)
    write_error(
        f"Unknown review subcommand: {command!r}. Valid: architecture."
    )
    return USER_INPUT_ERROR


def cmd_review_architecture(args: argparse.Namespace) -> int:
    """Phase 20.H — emit the quarterly architecture review
    checklist for ``--path``. Read-only; mutates nothing."""
    from .architecture_review import build_review_report, render_review_markdown

    root = Path(args.path).resolve()
    report = build_review_report(root)

    if _flag(args, "json"):
        write_json(
            {
                "command": "review architecture",
                "path": str(root),
                **report.to_dict(),
            }
        )
        return SUCCESS

    write_line(render_review_markdown(report))
    return SUCCESS


def cmd_persona(args: argparse.Namespace) -> int:
    """Phase 20.A — opt-in persona presets. Two subcommands:
    ``apply`` (writes mythic/persona.json) and ``show`` (prints
    the active persona, if any). Default behavior across the
    rest of the CLI is preserved when no persona is applied."""
    command = getattr(args, "persona_command", None)
    if command == "apply":
        return cmd_persona_apply(args)
    if command == "show":
        return cmd_persona_show(args)
    write_error(
        f"Unknown persona subcommand: {command!r}. Valid: apply | show."
    )
    return USER_INPUT_ERROR


def cmd_persona_apply(args: argparse.Namespace) -> int:
    from .personas import PRESET_NAMES, apply_preset

    preset_name = getattr(args, "preset", None) or ""
    if preset_name not in PRESET_NAMES:
        write_error(
            f"--preset must be one of {PRESET_NAMES} "
            f"(got {preset_name!r})"
        )
        return USER_INPUT_ERROR
    root = Path(args.path).resolve()
    force = _flag(args, "force")
    try:
        applied = apply_preset(root, preset_name, force=force)
    except FileExistsError as exc:
        write_error(str(exc))
        return USER_INPUT_ERROR

    if _flag(args, "json"):
        write_json(
            {
                "command": "persona apply",
                "path": str(root),
                **applied.to_dict(),
            }
        )
        return SUCCESS

    write_line(f"Applied persona preset: {applied.preset.name}")
    write_key_value("Description", applied.preset.description)
    write_key_value("Approval mode", applied.preset.approval_mode)
    write_key_value("Audience", applied.preset.audience)
    write_key_value("Audit cadence (days)", applied.preset.audit_cadence_days)
    write_key_value(
        "Plugin review required", applied.preset.require_plugin_review
    )
    write_key_value("Path", applied.path)
    return SUCCESS


def cmd_persona_show(args: argparse.Namespace) -> int:
    from .personas import load_active_persona

    root = Path(args.path).resolve()
    state = load_active_persona(root)

    if _flag(args, "json"):
        write_json(
            {
                "command": "persona show",
                "path": str(root),
                **state.to_dict(),
            }
        )
        return SUCCESS

    write_line("Active persona")
    write_key_value("Path", state.path)
    if state.preset is None:
        if state.error:
            write_key_value("Status", f"error — {state.error}")
        else:
            write_key_value("Status", "none (no persona file present)")
        return SUCCESS

    write_key_value("Preset", state.preset.name)
    write_key_value("Description", state.preset.description)
    write_key_value("Approval mode", state.preset.approval_mode)
    write_key_value("Audience", state.preset.audience)
    write_key_value("Audit cadence (days)", state.preset.audit_cadence_days)
    write_key_value(
        "Plugin review required", state.preset.require_plugin_review
    )
    return SUCCESS


def cmd_provenance_verify(args: argparse.Namespace) -> int:
    """Verify checksums of every plunder-imported file against
    the recorded ``source_sha`` in
    ``mythic/imports/plunder_manifest.json``."""
    from .plunder.verify import verify_provenance

    root = Path(args.path).resolve()
    report = verify_provenance(root)

    if _flag(args, "json"):
        write_json(
            {
                "command": "provenance verify",
                "path": str(root),
                **report.to_dict(),
            }
        )
        return SUCCESS

    write_line("Provenance verification")
    write_key_value("Path", root)
    write_key_value("Total entries", len(report.entries))
    write_key_value("Match", len(report.matches))
    write_key_value("Drift", len(report.drifts))
    write_key_value("Missing", len(report.missing))

    if not report.entries:
        write_line(
            "- No plunder manifest entries found (no imports to verify)."
        )
        return SUCCESS

    if report.drifts:
        write_line("Drifted (local file SHA does not match recorded source SHA):")
        for entry in report.drifts:
            write_bullet(
                f"{entry.destination} (recorded={entry.source_sha[:12]}, "
                f"actual={entry.actual_sha[:12]})",
                indent=2,
            )
    if report.missing:
        write_line("Missing destinations:")
        for entry in report.missing:
            write_bullet(entry.destination, indent=2)
    return SUCCESS


def cmd_db_migrate(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    db_path = root / "mythic" / "weave.db"
    if _flag(args, "dry_run"):
        payload = {
            "command": "db migrate",
            "dry_run": True,
            "database": str(db_path),
            "status_path": str(root / "mythic" / "status.json"),
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no database migration will be performed.")
            write_key_value("Database", db_path)
            write_key_value("State", root / "mythic" / "status.json")
        return SUCCESS

    state_migration = migrate_project_state(root)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rituals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ritual TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    if _flag(args, "json"):
        write_json(
            {
                "command": "db migrate",
                "dry_run": False,
                "database": str(db_path),
                "state_migration": state_migration.to_dict(),
            }
        )
        return SUCCESS

    write_key_value("Database migrated", db_path)
    write_key_value("State", state_migration.status_path)
    if state_migration.backup_path:
        write_key_value("State backup", state_migration.backup_path)
    return SUCCESS


def cmd_weave(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if _flag(args, "dry_run"):
        write_line("Dry run: no weave checkpoint will be written.")
        write_key_value("Project path", root)
        return SUCCESS

    workflow = MythicWorkflow(root)
    try:
        status_file, devlog_file = workflow.check_in(
            phase="reflect",
            update="Ran mythic weave doc synchronization checkpoint.",
        )
    except ValueError as exc:
        write_error(str(exc))
        return USER_INPUT_ERROR
    write_line("Weave synchronization checkpoint recorded.")
    write_key_value("Status", status_file)
    write_key_value("Devlog", devlog_file)
    return SUCCESS


def cmd_prune(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    write_line("Prune ritual scaffold ready.")
    write_key_value("Project", root)
    write_line("Next: run your linter/dead-code tool and remove one safe item at a time.")
    return SUCCESS


def cmd_heal(args: argparse.Namespace) -> int:
    """PH-13 slice 13.3: ``heal`` v2 — generate an additive Scribe
    reconciliation packet from current drift findings.

    Behaviour:

    1. Run :func:`scan_for_drift`.
    2. Group findings by category.
    3. Write a Scribe-targeted markdown packet to
       ``mythic/heal/<timestamp>-reconciliation.md`` plus a JSON
       sidecar at ``<timestamp>-reconciliation.json``.
    4. Print the packet path on stdout (or the full payload under
       ``--json``).

    The packet describes **additive** reconciliations only — never
    proposes overwriting or deleting existing content. The Scribe
    agent reading the packet is the one that turns the proposals
    into real edits, and only when the operator approves.

    ``--dry-run`` computes the packet but does not write it.
    """
    from datetime import datetime, timezone

    from .drift import render_findings_text, scan_for_drift, summarize_findings

    root = Path(args.path).resolve()
    findings = scan_for_drift(root)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    packet_dir = root / "mythic" / "heal"
    md_path = packet_dir / f"{timestamp}-reconciliation.md"
    json_path = packet_dir / f"{timestamp}-reconciliation.json"

    grouped: dict[str, list[dict[str, str]]] = {}
    for finding in findings:
        grouped.setdefault(finding.category, []).append(finding.to_dict())

    summary = summarize_findings(findings)
    failing_test = getattr(args, "failing_test", "") or ""

    md_lines: list[str] = [
        "# Scribe reconciliation packet",
        "",
        f"- Generated: {timestamp}",
        f"- Project: {root}",
        f"- Findings: {len(findings)} ({summary['warning']} warning, {summary['info']} info)",
    ]
    if failing_test:
        md_lines.append(f"- Failing test (informational): {failing_test}")
    md_lines.extend([
        "",
        "## Reconciliation principles",
        "",
        "1. Additive only — propose new content; never overwrite or delete.",
        "2. Operator-gated — write nothing without explicit approval.",
        "3. Per-category grouping — a Scribe agent can prioritise by kind.",
        "",
        "## Findings by category",
        "",
    ])
    if not findings:
        md_lines.append("No drift detected — packet is informational only.")
    else:
        for category, items in grouped.items():
            md_lines.append(f"### {category} ({len(items)})")
            md_lines.append("")
            for item in items:
                md_lines.append(
                    f"- [{item['severity']}] `{item['path']}` — "
                    f"{item['description']}"
                )
            md_lines.append("")
            md_lines.extend(_heal_proposal_for_category(category))
            md_lines.append("")

    md_text = "\n".join(md_lines).rstrip() + "\n"

    payload = {
        "command": "heal",
        "timestamp": timestamp,
        "path": str(root),
        "failing_test": failing_test,
        "summary": summary,
        "findings": [f.to_dict() for f in findings],
        "markdown_path": str(md_path),
        "json_path": str(json_path),
        "markdown_preview": render_findings_text(findings),
    }

    if not _flag(args, "dry_run"):
        try:
            packet_dir.mkdir(parents=True, exist_ok=True)
            md_path.write_text(md_text, encoding="utf-8")
            json_path.write_text(
                json.dumps(payload, indent=2, sort_keys=False) + "\n",
                encoding="utf-8",
            )
            payload["written"] = True
        except OSError as exc:
            payload["written"] = False
            payload["error"] = str(exc)
    else:
        payload["written"] = False
        payload["dry_run"] = True

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line("Heal — Scribe reconciliation packet")
    write_key_value("Project", root)
    write_key_value("Findings", str(len(findings)))
    if failing_test:
        write_key_value("Failing test", failing_test)
    if payload.get("dry_run"):
        write_line("- Dry run: no files written.")
    elif payload.get("written"):
        write_key_value("Markdown", md_path)
        write_key_value("JSON sidecar", json_path)
    else:
        write_error(
            f"Failed to write packet: {payload.get('error', 'unknown error')}"
        )
    return SUCCESS


def _heal_proposal_for_category(category: str) -> list[str]:
    """Hard-coded proposal stanzas for each known drift category.

    Each stanza is intentionally additive — the Scribe agent reading
    the packet sees a "Proposal" block telling it exactly what kind
    of new content to draft. Categories the table doesn't cover get
    a generic stanza so the packet still reads cleanly."""
    table: dict[str, list[str]] = {
        "undocumented_handler": [
            "**Proposal:** Draft a one-line docstring for each listed",
            "handler describing what the command does and any side",
            "effects. The docstring is the primary source for `slash",
            "inspect` and `--help` — keep it user-facing, not",
            "implementation-focused.",
        ],
        "undocumented_module": [
            "**Proposal:** Add a short module docstring explaining the",
            "module's purpose and the public surface it exposes. One",
            "paragraph is enough; deeper context belongs in DEVLOG /",
            "decisions.",
        ],
        "superseded_decision_referenced": [
            "**Proposal:** For each external reference, decide:",
            "(a) update the citing file to reference the replacement",
            "decision, or (b) remove the citation if the context no",
            "longer applies. Do not modify the superseded decision",
            "itself — its archival value depends on staying as-is.",
        ],
    }
    return table.get(
        category,
        [
            "**Proposal:** Draft an additive reconciliation that",
            "addresses each listed finding. Do not overwrite existing",
            "content; produce new docs / sidecars / annotations only.",
        ],
    )


def cmd_workflow_run(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    engine = WorkflowEngine(root)

    if not _flag(args, "dry_run"):
        write_error("Real workflow execution is not enabled yet. Re-run with `--dry-run` to preview the role sequence.")
        return UNSAFE_OPERATION_BLOCKED

    try:
        plan, plan_source = _workflow_plan_from_args(args, engine)
        steps = engine.dry_run_steps(plan)
    except ValueError as exc:
        write_error(str(exc))
        return USER_INPUT_ERROR

    packet_status = []
    packets_ready = None
    if _flag(args, "packets_only"):
        packet_status = _workflow_packet_status(
            root,
            plan,
            audience=getattr(args, "audience", "advanced"),
            output_format=getattr(args, "format", "markdown"),
        )
        packets_ready = all(item["found"] for item in packet_status)

    payload = {
        "command": "workflow run",
        "dry_run": True,
        "path": str(root),
        "plan_source": plan_source,
        "workflow_id": plan.workflow_id,
        "plan": plan.to_dict(),
        "steps": steps,
        "provider_execution": "disabled",
        "packets_only": _flag(args, "packets_only"),
        "packets_ready": packets_ready,
        "packet_status": packet_status,
    }
    if _flag(args, "packets_only") and not packets_ready:
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_error("Workflow packets are missing. Run `mythic-vibe workflow plan --packets` for this task first.")
            write_line("Missing packet steps:")
            for item in packet_status:
                if not item["found"]:
                    write_bullet(f"{item['role']} -> {item['phase']}")
        return USER_INPUT_ERROR

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line("Dry run: workflow provider execution is disabled.")
    write_key_value("Project path", root)
    write_key_value("Plan source", plan_source)
    write_key_value("Task", plan.task)
    if plan.workflow_id:
        write_key_value("Workflow ID", plan.workflow_id)
    write_line("Execution preview:")
    for step in steps:
        write_bullet(f"{step['step_id']}: {step['role']} -> {step['phase']} ({step['handoff_to'] or 'done'})")
    if packet_status:
        write_line("Packet readiness:")
        for item in packet_status:
            status = "ready" if item["found"] else "missing"
            via = f" via {item['match_strategy']}" if item["match_strategy"] else ""
            write_bullet(f"{item['role']} -> {item['phase']}: {status}{via}")
    return SUCCESS


def cmd_workflow_packets(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    engine = WorkflowEngine(root)

    try:
        plan, plan_source = _workflow_plan_from_args(args, engine)
    except ValueError as exc:
        write_error(str(exc))
        return USER_INPUT_ERROR

    packet_status = _workflow_packet_status(
        root,
        plan,
        audience=getattr(args, "audience", "advanced"),
        output_format=getattr(args, "format", "markdown"),
    )
    if _flag(args, "missing_only"):
        packet_status = [item for item in packet_status if not item["found"]]

    payload = {
        "command": "workflow packets",
        "path": str(root),
        "plan_source": plan_source,
        "workflow_id": plan.workflow_id,
        "packets_ready": all(item["found"] for item in packet_status) if not _flag(args, "missing_only") else not packet_status,
        "packet_status": packet_status,
    }
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line("Workflow packet readiness")
    write_key_value("Project path", root)
    write_key_value("Plan source", plan_source)
    if plan.workflow_id:
        write_key_value("Workflow ID", plan.workflow_id)
    if not packet_status:
        write_line("No matching workflow packet steps to show.")
        return SUCCESS
    for item in packet_status:
        status = "ready" if item["found"] else "missing"
        packet_id = f" ({item['packet_id']})" if item["packet_id"] else ""
        via = f" via {item['match_strategy']}" if item["match_strategy"] else ""
        write_bullet(f"{item['role']} -> {item['phase']}: {status}{packet_id}{via}")
    return SUCCESS


def cmd_config_dispatch(args: argparse.Namespace) -> int:
    if args.config_command == "set":
        return cmd_config_set(args)
    return cmd_config(args)


def cmd_db_dispatch(args: argparse.Namespace) -> int:
    return cmd_db_migrate(args)


def cmd_state_dispatch(args: argparse.Namespace) -> int:
    if args.state_command == "show":
        return cmd_state_show(args)
    if args.state_command == "validate":
        return cmd_state_validate(args)
    return USER_INPUT_ERROR


def cmd_packet_dispatch(args: argparse.Namespace) -> int:
    if args.packet_command == "create":
        return cmd_packet_create(args)
    if args.packet_command == "show":
        return cmd_packet_show(args)
    if args.packet_command == "list":
        return cmd_packet_list(args)
    if args.packet_command == "ingest":
        return cmd_packet_ingest(args)
    if args.packet_command == "diff":
        return cmd_packet_diff(args)
    # Phase 20.1 (additive): packet lint subcommand.
    if args.packet_command == "lint":
        return cmd_packet_lint(args)
    return USER_INPUT_ERROR


def cmd_workflow_history(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    engine = WorkflowEngine(root)
    entries = engine.load_history()
    limit = int(getattr(args, "limit", 0) or 0)
    ordered = list(reversed(entries))
    if limit > 0:
        ordered = ordered[:limit]

    payload = {
        "command": "workflow history",
        "path": str(root),
        "history_path": str(engine.history_path()),
        "count": len(ordered),
        "total": len(entries),
        "entries": ordered,
    }

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    if not ordered:
        write_line("No workflow history recorded yet. Run `mythic-vibe workflow plan` to populate it.")
        return SUCCESS

    write_line("Workflow history (newest first)")
    write_key_value("Project path", root)
    write_key_value("Ledger", engine.history_path())
    for entry in ordered:
        write_key_value(
            entry.get("workflow_id", "?"),
            f"{entry.get('created_at', '')} | {entry.get('task', '')}",
            indent=2,
        )
        roles = entry.get("role_sequence") or []
        if roles:
            write_bullet("roles: " + " -> ".join(str(role) for role in roles), indent=4)
    return SUCCESS


def cmd_workflow_dispatch(args: argparse.Namespace) -> int:
    if args.workflow_command == "plan":
        return cmd_workflow_plan(args)
    if args.workflow_command == "run":
        return cmd_workflow_run(args)
    if args.workflow_command == "packets":
        return cmd_workflow_packets(args)
    if args.workflow_command == "history":
        return cmd_workflow_history(args)
    # Phase 20.C (additive 2026-05-03): workflow lineage viewer.
    if args.workflow_command == "lineage":
        return cmd_workflow_lineage(args)
    return USER_INPUT_ERROR


def cmd_workflow_lineage(args: argparse.Namespace) -> int:
    """Phase 20.C — emit a lineage view of one workflow.
    Reads forge_ledger entries (and resolves duplicates via
    most-recent-per-step). Renders Mermaid markdown by default;
    ``--json`` returns the structured payload."""
    from .workflow_lineage import build_lineage, render_markdown

    root = Path(args.path).resolve()
    workflow_id = (getattr(args, "workflow", "") or "").strip() or None
    graph = build_lineage(root, workflow_id)

    if graph is None:
        if _flag(args, "json"):
            write_json(
                {
                    "command": "workflow lineage",
                    "path": str(root),
                    "workflow_id": workflow_id or "",
                    "found": False,
                    "error": "no workflows in ledger or unknown workflow id",
                }
            )
            return SUCCESS
        write_line("Workflow lineage")
        write_key_value("Path", root)
        write_key_value("Workflow", workflow_id or "(latest)")
        write_line(
            "- No workflows found in mythic/forge_ledger.json "
            "or the supplied --workflow id is not in the ledger."
        )
        return SUCCESS

    if _flag(args, "json"):
        write_json(
            {
                "command": "workflow lineage",
                "path": str(root),
                "found": True,
                **graph.to_dict(),
            }
        )
        return SUCCESS

    write_line(render_markdown(graph))
    return SUCCESS


def cmd_slash_list(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    source_filter = (getattr(args, "source", "") or "").strip().lower()

    builtin_payload = [entry.to_dict() for entry in BUILTIN_SLASH_COMMANDS]

    contributed: list[SlashCommandInfo] = []
    if source_filter != "builtin":
        with PluginHookDispatcher(root) as dispatcher:
            dispatcher.load_and_subscribe()
            contributed = dispatcher.discover_slash_commands()

    if source_filter and source_filter != "builtin":
        contributed = [item for item in contributed if item.source == source_filter]

    contributed_payload = [item.to_dict() for item in contributed]

    if _flag(args, "json"):
        write_json(
            {
                "command": "slash list",
                "path": str(root),
                "source_filter": source_filter or None,
                "builtin": [] if source_filter and source_filter != "builtin" else builtin_payload,
                "contributed": contributed_payload,
            }
        )
        return SUCCESS

    if not source_filter or source_filter == "builtin":
        write_line("Builtin slash commands:")
        for entry in BUILTIN_SLASH_COMMANDS:
            write_bullet(f"/{entry.name} — {entry.description}", indent=2)

    if source_filter == "builtin":
        return SUCCESS

    if not contributed:
        if not source_filter:
            write_line("Contributed slash commands: none registered.")
        else:
            write_line(f"No contributed slash commands match source '{source_filter}'.")
        return SUCCESS

    by_source: dict[str, list[SlashCommandInfo]] = {}
    for item in contributed:
        by_source.setdefault(item.source, []).append(item)
    write_line("Contributed slash commands:")
    for source_name in sorted(by_source):
        write_line(f"- {source_name}:")
        for item in by_source[source_name]:
            description = item.description or "(no description)"
            write_bullet(f"/{item.name} — {description} [{item.source_info.path}]", indent=4)
    return SUCCESS


def _resolve_argparse_subparser(name: str) -> argparse.ArgumentParser | None:
    """Return the subparser for ``name`` from the live ``build_parser`` tree.

    Walks ``parser._actions`` to find the ``_SubParsersAction`` and looks
    up ``name`` in its ``choices`` mapping. Returns ``None`` if the name is
    not a registered top-level subcommand. Uses a documented argparse
    private API surface; there is no public alternative.
    """
    from .app import build_parser

    parser = build_parser()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action.choices.get(name)
    return None


SLASH_LOCALS_WITHOUT_ARGPARSE = {"help", "model", "reload", "quit"}


def cmd_slash_inspect(args: argparse.Namespace) -> int:
    """Show provenance + argparse help for one slash entry.

    Resolution order: builtin catalog → plugin-contributed entries.
    For builtin entries that map onto a top-level argparse subcommand
    (i.e. everything except the three interactive locals
    ``help``/``reload``/``quit``), the underlying parser's
    ``--help`` text is rendered so the operator sees exactly what
    ``mythic-vibe <name> --help`` would print.
    """
    root = Path(getattr(args, "path", ".")).resolve()
    name = (getattr(args, "name", "") or "").strip()
    if not name:
        write_error("slash inspect requires a command name.")
        return USER_INPUT_ERROR
    if name.startswith("/"):
        name = name[1:]

    builtin_match: BuiltinSlashCommand | None = None
    for entry in BUILTIN_SLASH_COMMANDS:
        if entry.name == name:
            builtin_match = entry
            break

    contributed_match: SlashCommandInfo | None = None
    if builtin_match is None:
        with PluginHookDispatcher(root) as dispatcher:
            dispatcher.load_and_subscribe()
            for item in dispatcher.discover_slash_commands():
                if item.name == name:
                    contributed_match = item
                    break

    if builtin_match is None and contributed_match is None:
        message = (
            f"No slash command named '{name}' is registered. "
            "Run `mythic-vibe slash list` to see available commands."
        )
        if _flag(args, "json"):
            write_json({"command": "slash inspect", "ok": False, "errors": [message]})
        else:
            write_error(message)
        return USER_INPUT_ERROR

    argparse_help: str | None = None
    if builtin_match is not None and name not in SLASH_LOCALS_WITHOUT_ARGPARSE:
        subparser = _resolve_argparse_subparser(name)
        if subparser is not None:
            argparse_help = subparser.format_help().rstrip() + "\n"

    if _flag(args, "json"):
        payload: dict[str, object] = {
            "command": "slash inspect",
            "name": name,
            "ok": True,
            "argparse_help": argparse_help,
        }
        if builtin_match is not None:
            payload["source"] = "builtin"
            payload["entry"] = builtin_match.to_dict()
            payload["interactive_local"] = name in SLASH_LOCALS_WITHOUT_ARGPARSE
        else:
            assert contributed_match is not None
            payload["source"] = contributed_match.source
            payload["entry"] = contributed_match.to_dict()
            payload["interactive_local"] = False
        write_json(payload)
        return SUCCESS

    write_line(f"/{name}")
    if builtin_match is not None:
        write_key_value("Source", "builtin")
        write_key_value("Description", builtin_match.description or "(none)")
        if name in SLASH_LOCALS_WITHOUT_ARGPARSE:
            write_line("(interactive-local — handled by the REPL/TUI directly; no argparse subcommand)")
        elif argparse_help:
            write_line("")
            write_line("Argparse help:")
            write_line(argparse_help, force=True)
    else:
        assert contributed_match is not None
        write_key_value("Source", contributed_match.source)
        write_key_value("Description", contributed_match.description or "(none)")
        write_key_value("Origin path", contributed_match.source_info.path)
        write_key_value("Scope", contributed_match.source_info.scope)
    return SUCCESS


def cmd_slash_dispatch(args: argparse.Namespace) -> int:
    if args.slash_command == "list":
        return cmd_slash_list(args)
    if args.slash_command == "inspect":
        return cmd_slash_inspect(args)
    write_error(
        f"Unknown slash subcommand: {args.slash_command!r}. Try `mythic-vibe slash list` or `mythic-vibe slash inspect <name>`."
    )
    return USER_INPUT_ERROR


def cmd_shell(args: argparse.Namespace) -> int:
    from .interactive_shell import run_interactive_shell

    project_root = Path(getattr(args, "path", ".")).resolve()
    return run_interactive_shell(project_root=project_root)


def cmd_tui(args: argparse.Namespace) -> int:
    project_root = Path(getattr(args, "path", ".")).resolve()
    theme = getattr(args, "theme", None)
    # Phase 20.I (additive 2026-05-03): parse opt-in panels.
    # Pre-resolved here so the textual code path stays as
    # narrow as possible.
    from .tui_panels import parse_panels
    panels = parse_panels(getattr(args, "panels", "") or "")
    try:
        from .tui.app import run_tui
    except ImportError as exc:
        write_error(
            "Textual is not installed. Install the optional TUI extra with: "
            "pip install \"mythic-vibe-cli[tui]\"  (or: pip install textual)"
        )
        write_error(f"Underlying import error: {exc}")
        return OPERATIONAL_FAILURE
    # Forward the panels selection to run_tui via a kwarg if it
    # accepts one; otherwise stash on os.environ so widget code
    # can pick it up at render time without changing function
    # signatures across the TUI module boundary.
    try:
        return run_tui(project_root, theme=theme, panels=panels)  # type: ignore[call-arg]
    except TypeError:
        # run_tui hasn't grown the panels kwarg yet — fall back
        # to env var. Non-blocking; TUI still renders.
        if panels:
            os.environ["MYTHIC_TUI_PANELS"] = ",".join(panels)
        return run_tui(project_root, theme=theme)


def cmd_ai_stream(args: argparse.Namespace) -> int:
    """PH-06 Slice 6.4 — emit a streaming provider response chunk
    by chunk to stdout. Falls back to single_chunk_stream for
    providers that don't natively stream.

    Cancellation contract: SIGINT (Ctrl-C) sets a threading.Event
    the provider checks between chunks. The first Ctrl-C triggers
    a clean stop; a second one bubbles out as KeyboardInterrupt.
    """
    import signal
    import threading

    from .ai.providers.base import stream_provider_response

    root = Path(getattr(args, "path", ".")).resolve()
    registry = _ai_registry(root)
    provider = registry.providers().get(args.provider)
    if provider is None:
        write_error(f"Unknown provider: {args.provider}")
        return USER_INPUT_ERROR

    status = provider.validate_config()
    dry_run = bool(_flag(args, "dry_run"))
    if not status.configured and not dry_run:
        write_error(
            f"Provider not configured: {args.provider}. "
            "Use --dry-run or set the required API key."
        )
        return USER_INPUT_ERROR

    packet = _resolve_ai_packet(root, args.packet)

    cancel_event = threading.Event()
    json_mode = bool(_flag(args, "json"))

    previous_handler = signal.getsignal(signal.SIGINT)

    def _on_sigint(signum: int, frame: object) -> None:  # noqa: ANN001
        # First Ctrl-C: signal cooperative cancel. Second Ctrl-C
        # restores the default handler so the next signal propagates
        # as a real KeyboardInterrupt.
        cancel_event.set()
        signal.signal(signal.SIGINT, signal.default_int_handler)

    try:
        signal.signal(signal.SIGINT, _on_sigint)
    except (ValueError, OSError):
        # signal.signal must be called from the main thread; tests
        # / TUI invocations may not have that luxury. Skip the SIGINT
        # wiring in that case — caller can still set cancel_event
        # programmatically via args (not exposed today).
        previous_handler = None

    accumulated_text: list[str] = []
    final_chunk: object = None
    chunk_count = 0
    try:
        for chunk in stream_provider_response(
            provider, packet, dry_run=dry_run, cancel_event=cancel_event
        ):
            chunk_count += 1
            if json_mode:
                # NDJSON line per chunk so consumers can parse
                # incrementally.
                write_line(json.dumps(chunk.to_dict(), ensure_ascii=False))
            else:
                if chunk.text:
                    # Render delta to stdout WITHOUT newline so
                    # the operator sees a flowing response.
                    print(chunk.text, end="", flush=True)
                if chunk.text:
                    accumulated_text.append(chunk.text)
            if chunk.done:
                final_chunk = chunk
                break
    finally:
        if previous_handler is not None:
            try:
                signal.signal(signal.SIGINT, previous_handler)
            except (ValueError, OSError):
                pass

    if not json_mode:
        # Trailing newline so the prompt lands on its own line.
        if accumulated_text:
            print("", flush=True)
        usage = (
            getattr(final_chunk, "usage", {}) if final_chunk is not None else {}
        )
        cancelled = (
            bool(getattr(final_chunk, "metadata", {}).get("cancelled", False))
            if final_chunk is not None
            else False
        )
        write_line("- Stream summary:")
        write_key_value("Provider", provider.name, indent=2)
        write_key_value("Chunks", chunk_count, indent=2)
        write_key_value("Cancelled", cancelled, indent=2)
        if usage:
            write_key_value("Usage", usage, indent=2)

    return SUCCESS


def cmd_ai_dispatch(args: argparse.Namespace) -> int:
    if args.ai_command == "providers":
        return cmd_ai_providers(args)
    if args.ai_command == "test":
        return cmd_ai_test(args)
    if args.ai_command == "run":
        return cmd_ai_run(args)
    if args.ai_command == "stream":
        return cmd_ai_stream(args)
    if args.ai_command == "ingest-response":
        return cmd_ai_ingest_response(args)
    if args.ai_command == "models":
        return cmd_ai_models(args)
    if args.ai_command == "telemetry":
        return cmd_ai_telemetry(args)
    if args.ai_command == "route":
        return cmd_ai_route(args)
    # Phase 20.4 (additive 2026-05-03): ai recommend — pure-policy
    # model recommendation against the static catalog.
    if args.ai_command == "recommend":
        return cmd_ai_recommend(args)
    write_error(
        f"Unknown ai subcommand: {args.ai_command!r}. "
        "Valid: providers | test | run | stream | ingest-response | models | telemetry | route | recommend."
    )
    return USER_INPUT_ERROR


def cmd_ai_recommend(args: argparse.Namespace) -> int:
    """Phase 20.4 — score models from the static catalog
    against operator-supplied criteria. Zero provider calls;
    deterministic for the same inputs."""
    from .ai.recommend import (
        COST_CLASSES,
        RecommendationCriteria,
        recommend_models,
    )

    cost_class = getattr(args, "cost_class", None)
    if cost_class and cost_class not in COST_CLASSES:
        write_error(
            f"--cost-class must be one of {COST_CLASSES} "
            f"(got {cost_class!r})"
        )
        return USER_INPUT_ERROR

    family = getattr(args, "family", None) or None
    top_n = int(getattr(args, "top", 0) or 3)
    if top_n < 0:
        write_error("--top must be a non-negative integer")
        return USER_INPUT_ERROR

    criteria = RecommendationCriteria(
        task=str(getattr(args, "task", "") or ""),
        max_context=int(getattr(args, "max_context", 0) or 0),
        vision_required=bool(getattr(args, "vision", False)),
        cost_class=cost_class,
        family=family,
    )
    recommendations = recommend_models(criteria, top_n=top_n)

    if _flag(args, "json"):
        write_json(
            {
                "command": "ai recommend",
                "criteria": criteria.to_dict(),
                "top_n": top_n,
                "recommendations": [r.to_dict() for r in recommendations],
            }
        )
        return SUCCESS

    write_line("Model recommendations")
    write_key_value("Task", criteria.task or "(none)")
    write_key_value("Max context", criteria.max_context or "(any)")
    write_key_value("Vision required", criteria.vision_required)
    write_key_value("Cost class", criteria.cost_class or "(any)")
    write_key_value("Family", criteria.family or "(all)")
    write_key_value("Top N", top_n)

    if not recommendations:
        write_line("- No matching models in the static catalog.")
        return SUCCESS

    write_line("Top picks:")
    for rec in recommendations:
        write_bullet(
            f"{rec.model.id} ({rec.model.family}) "
            f"score={rec.score} ctx={rec.model.context_window:,}",
            indent=2,
        )
        for reason in rec.reasons:
            write_bullet(reason, indent=4)
    return SUCCESS


def cmd_ai_route(args: argparse.Namespace) -> int:
    """PH-08 slice 8.4: explain how a ``(role, task_type)`` would
    route through the slice-8.1 provider table.

    Pure routing — never invokes a provider. Operators run this to
    sanity-check their ``mythic/ai/routing.json`` overlay before a
    real ``ai run``.
    """
    from .ai.router import RoutingTable, route
    from .hardware import detect_profile

    root = Path(getattr(args, "path", ".")).resolve()
    role = getattr(args, "role", "Forge Worker") or "Forge Worker"
    task_type = getattr(args, "task", "*") or "*"
    explain = bool(_flag(args, "explain"))
    no_hardware = bool(_flag(args, "no_hardware"))

    table = RoutingTable.load(root)
    hardware = None if no_hardware else detect_profile()
    decision = route(table, role=role, task_type=task_type, hardware=hardware)

    payload = {
        "command": "ai route",
        "path": str(root),
        "role": role,
        "task_type": task_type,
        "decision": decision.to_dict(),
        "hardware": hardware.to_dict() if hardware is not None else None,
        "explain": explain,
    }
    if not explain and "reasons" in payload["decision"]:
        # Keep the JSON envelope tight unless --explain was passed —
        # the rule_matched + provider/model already cover the
        # common-case answer.
        payload["decision"] = {
            k: v for k, v in payload["decision"].items() if k != "reasons"
        }

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line(
        f"Route: role={role!r} task_type={task_type!r}  -> "
        f"provider={decision.provider!r} model={decision.model!r}"
    )
    if decision.fallbacks:
        write_line(f"  fallbacks: {' -> '.join(decision.fallbacks)}")
    else:
        write_line("  fallbacks: (none)")
    if decision.rule_matched is not None and decision.rule_matched.description:
        write_line(f"  matched rule: {decision.rule_matched.description}")
    if explain:
        write_line("  reasons:")
        for reason in decision.reasons:
            write_bullet(reason, indent=4)
    return SUCCESS


def cmd_ai_telemetry(args: argparse.Namespace) -> int:
    """PH-06 slice 6.5: read recent calls from
    ``mythic/ai/provider_calls.jsonl`` (the per-call ledger that
    every provider writes to via ``write_provider_log``).

    Filters: ``--provider`` to a single name; ``--limit`` to bound
    the result count. Output is newest-first regardless of how the
    file is laid out on disk (the ledger is append-only, so newest
    sits at the bottom — the reader reverses it).
    """
    root = Path(getattr(args, "path", ".")).resolve()
    log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
    provider_filter = (getattr(args, "provider", "") or "").strip()
    raw_limit = int(getattr(args, "limit", 20) or 0)
    limit = max(0, raw_limit)

    entries: list[dict[str, object]] = []
    if log_path.is_file():
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            if provider_filter and str(payload.get("provider", "")) != provider_filter:
                continue
            entries.append(payload)

    # Newest first; the file is append-only so reverse-iterating is
    # the cheapest way to surface "most recent N". `limit=0` returns
    # an empty list (the operator asked for zero results); negative
    # values were already clamped to 0 above.
    entries.reverse()
    entries = entries[:limit]

    if _flag(args, "json"):
        write_json(
            {
                "command": "ai telemetry",
                "path": str(log_path),
                "provider_filter": provider_filter,
                "limit": limit,
                "count": len(entries),
                "entries": entries,
            }
        )
        return SUCCESS

    if not entries:
        if not log_path.is_file():
            write_line(
                f"AI telemetry: no log yet at {log_path} (run an AI call first)."
            )
        elif provider_filter:
            write_line(
                f"AI telemetry: no entries for provider {provider_filter!r}."
            )
        else:
            write_line("AI telemetry: log is empty.")
        return SUCCESS

    write_line(f"AI telemetry: {len(entries)} entry / entries (newest first).")
    for entry in entries:
        timestamp = str(entry.get("timestamp", ""))
        provider = str(entry.get("provider", ""))
        model = str(entry.get("model", ""))
        latency = entry.get("latency_ms")
        latency_str = (
            f"{latency:.1f}ms"
            if isinstance(latency, (int, float))
            else "n/a"
        )
        dry = " [dry-run]" if entry.get("dry_run") else ""
        cost = ""
        if isinstance(entry.get("response"), dict):
            usage = entry["response"].get("usage")
            if isinstance(usage, dict):
                total = usage.get("total_tokens")
                if isinstance(total, int):
                    cost = f"  tokens={total}"
        error = entry.get("error")
        suffix = f"  ERROR: {error}" if error else ""
        write_line(
            f"  {timestamp}  [{provider}/{model}]  "
            f"latency={latency_str}{cost}{dry}{suffix}"
        )
    return SUCCESS


def cmd_ai_models(args: argparse.Namespace) -> int:
    """PH-06 slice 6.3: list installed models for a provider.

    Today only ``ollama`` returns a real list (via the slice 6.2
    ``list_models`` helper). Other providers report
    ``configured / not configured`` for parity with ``ai providers``
    but don't surface a model catalogue — none of the upstream APIs
    expose a uniform "list models" endpoint that's worth wiring
    here. Future PH-08 (Provider Routing) may change that.
    """
    provider_name = getattr(args, "provider", "")

    if provider_name == "ollama":
        from .ai.ollama_health import list_models

        models, health = list_models()
        if _flag(args, "json"):
            write_json(
                {
                    "command": "ai models",
                    "provider": provider_name,
                    "health": health.to_dict(),
                    "models": models,
                }
            )
            return SUCCESS if health.reachable else OPERATIONAL_FAILURE

        if not health.reachable:
            write_error(
                f"Ollama daemon unreachable at {health.endpoint}: "
                f"{health.error or 'no connection'}."
            )
            for hint in health.details:
                write_bullet(hint, indent=2)
            return OPERATIONAL_FAILURE

        if not models:
            write_line(f"Ollama at {health.endpoint}: no models installed.")
            write_line("- Run `ollama pull <model>` to install one (e.g. llama3.2).")
            return SUCCESS

        write_line(f"Ollama at {health.endpoint}: {len(models)} model(s).")
        for entry in models:
            name = str(entry.get("name", "(unnamed)"))
            size = entry.get("size")
            family = (entry.get("details") or {}).get("family") if isinstance(
                entry.get("details"), dict
            ) else None
            extras: list[str] = []
            if isinstance(size, (int, float)) and size > 0:
                extras.append(f"size={int(size)}")
            if family:
                extras.append(f"family={family}")
            suffix = f"  ({', '.join(extras)})" if extras else ""
            write_line(f"  - {name}{suffix}")
        return SUCCESS

    # Other providers: route through the new ``list_models(remote=...)``
    # protocol added in Phase D (2026-05-02). Falls through to the
    # legacy canned "(not implemented)" branch if the provider does
    # not expose ``list_models`` — preserved per the additive-only
    # rule. ``--remote`` triggers a live HTTP listing where the
    # provider supports it (Anthropic / OpenAI / Gemini / OpenRouter
    # all do). Failures fall back to the static catalog with a warning.
    root = Path(getattr(args, "path", ".")).resolve()
    registry = _ai_registry(root)
    provider = registry.providers().get(provider_name)
    if provider is None:
        write_error(f"Unknown provider: {provider_name!r}.")
        return USER_INPUT_ERROR

    status = provider.validate_config()

    list_models_method = getattr(provider, "list_models", None)
    if callable(list_models_method):
        remote_flag = bool(_flag(args, "remote"))
        try:
            listing = list_models_method(remote=remote_flag)
        except Exception as exc:  # noqa: BLE001 — never crash on listing errors
            # Defensive fallback: catalog-level errors should already
            # be wrapped, but this guards a misbehaving provider.
            payload = {
                "command": "ai models",
                "provider": provider_name,
                "configured": status.configured,
                "details": list(status.details),
                "implemented": False,
                "models": [],
                "warnings": [f"list_models raised: {exc}"],
            }
            if _flag(args, "json"):
                write_json(payload)
            else:
                write_error(f"Model listing failed for {provider_name}: {exc}")
            return OPERATIONAL_FAILURE

        payload = {
            "command": "ai models",
            "provider": provider_name,
            "configured": status.configured,
            "details": list(status.details),
            "implemented": True,
            "source": listing.source,
            "models": [m.to_dict() for m in listing.models],
            "warnings": list(listing.warnings),
        }
        if _flag(args, "json"):
            write_json(payload)
            return SUCCESS

        # Human render.
        if not listing.models:
            write_line(
                f"{provider_name}: no models in {listing.source} catalog."
            )
        else:
            write_line(
                f"{provider_name} models ({listing.source}, "
                f"{len(listing.models)} entries):"
            )
            for m in listing.models:
                ctx = (
                    f"  ctx={m.context_window:,}" if m.context_window else ""
                )
                cap = (
                    f"  caps=[{', '.join(m.capabilities)}]"
                    if m.capabilities
                    else ""
                )
                write_line(f"  - {m.id}  ({m.display_name}){ctx}{cap}")
        for w in listing.warnings:
            write_line(f"  ! {w}")
        return SUCCESS

    # Legacy canned fallback — preserved per additive-only rule. Only
    # reached if a provider somehow lacks ``list_models`` (no current
    # provider does after Phase D, but this branch keeps the code
    # robust against future provider additions that forget to
    # implement it).
    payload = {
        "command": "ai models",
        "provider": provider_name,
        "configured": status.configured,
        "details": list(status.details),
        "implemented": False,
        "models": [],
        "note": (
            f"Model listing is not implemented for {provider_name!r} yet — "
            "use the provider's documented model id with `ai run --provider`."
        ),
    }
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS
    write_line(payload["note"])
    return SUCCESS


def cmd_verify_dispatch(args: argparse.Namespace) -> int:
    """Phase 20.B (additive 2026-05-03): when ``--replay`` is
    passed, delegate to ``forge resume`` (PH-03 slice 3.8) instead
    of running normal verify. The operator gets a one-flag
    shortcut for "re-run the last forge workflow from its first
    non-succeeded step" without retyping the original
    ``forge run`` invocation."""
    if _flag(args, "replay"):
        return _cmd_verify_replay(args)
    return cmd_verify(args)


def _cmd_verify_replay(args: argparse.Namespace) -> int:
    """Build a forge-resume-shaped Namespace from the verify
    args and delegate. Forge resume handles all output (text /
    JSON / exit code) so we just forward the result."""
    from .forge import cmd_forge_resume

    forge_ns = argparse.Namespace(
        path=args.path,
        provider=getattr(args, "provider", "") or "copy-paste",
        workflow=getattr(args, "workflow", "") or "",
        interactive=False,
        strict=_flag(args, "strict"),
        skip_ledger=False,
        skip_reflection=False,
        json=_flag(args, "json"),
    )
    return cmd_forge_resume(forge_ns)


def cmd_provider(args: argparse.Namespace) -> int:
    """PH-02 slice 2.4 alias: ``mythic-vibe provider`` ⇒ ``ai providers``.

    Thin wrapper so the slash picker can offer ``/provider`` without
    teaching plugin authors and operators a separate dispatch path.
    Behaviour and exit codes are identical to ``cmd_ai_providers``.
    """
    return cmd_ai_providers(args)


def cmd_audit(args: argparse.Namespace) -> int:
    """PH-02 slice 2.5 alias: ``mythic-vibe audit`` ⇒ ``doctor --json``.

    Forces JSON output so an audit run is always machine-readable —
    that's the distinction from plain ``doctor``, which renders a
    human report by default.
    """
    args.json = True
    return cmd_doctor(args)


def cmd_graph_dispatch(args: argparse.Namespace) -> int:
    """PH-05 slices 5.5 / 5.6: dispatcher for `mythic-vibe graph`
    subcommands (query / entity / edges / brief / visualize)."""
    sub = getattr(args, "graph_command", "")
    if sub == "query":
        return cmd_graph_query(args)
    if sub == "entity":
        return cmd_graph_entity(args)
    if sub == "edges":
        return cmd_graph_edges(args)
    if sub == "brief":
        return cmd_graph_brief(args)
    if sub == "visualize":
        return cmd_graph_visualize(args)
    write_error(
        f"Unknown graph subcommand: {sub!r}. "
        "Valid: query | entity | edges | brief | visualize."
    )
    return USER_INPUT_ERROR


def cmd_graph_query(args: argparse.Namespace) -> int:
    """Run the slice 5.3 retriever against the project's graph."""
    from .context.graph import GraphStore
    from .context.retriever import top_k

    root = Path(getattr(args, "path", ".")).resolve()
    tags = list(getattr(args, "tag", []) or [])
    k = int(getattr(args, "top_k", 10) or 10)
    expand = not bool(getattr(args, "no_expand", False))
    with GraphStore.open(root) as store:
        results = top_k(store, tags, k=k, expand_neighbours=expand)
    if _flag(args, "json"):
        write_json(
            {
                "command": "graph query",
                "path": str(root),
                "tags": tags,
                "top_k": k,
                "results": [r.to_dict() for r in results],
            }
        )
        return SUCCESS
    if not results:
        write_line(
            "Graph query: no matches "
            f"(tags={tags!r}, top_k={k})."
        )
        return SUCCESS
    write_line(f"Graph query: {len(results)} match(es).")
    for result in results:
        write_line(
            f"  [{result.entity.kind}] {result.entity.name}  "
            f"(score {result.score:.2f})"
        )
        for reason in result.reasons:
            write_bullet(reason, indent=4)
    return SUCCESS


def cmd_graph_entity(args: argparse.Namespace) -> int:
    """List entities matching kind / name / path filters."""
    from .context.graph import GraphStore

    root = Path(getattr(args, "path", ".")).resolve()
    kind = getattr(args, "kind", "") or None
    name = getattr(args, "name", "") or None
    path_filter = getattr(args, "name_path", "") or None
    with GraphStore.open(root) as store:
        entities = store.find_entities(
            kind=kind,
            name_like=name,
            path_like=path_filter,
        )
    if _flag(args, "json"):
        write_json(
            {
                "command": "graph entity",
                "path": str(root),
                "filters": {"kind": kind, "name": name, "path": path_filter},
                "entities": [e.to_dict() for e in entities],
            }
        )
        return SUCCESS
    if not entities:
        write_line("Graph entity: no matches.")
        return SUCCESS
    write_line(f"Graph entity: {len(entities)} match(es).")
    for entity in entities:
        write_line(
            f"  #{entity.id}  [{entity.kind}] {entity.name}  "
            f"(path={entity.path or '-'})"
        )
    return SUCCESS


def cmd_graph_edges(args: argparse.Namespace) -> int:
    """List edges by filter."""
    from .context.graph import GraphStore

    root = Path(getattr(args, "path", ".")).resolve()
    kind = getattr(args, "kind", "") or None
    src_id = int(getattr(args, "src_id", 0) or 0)
    dst_id = int(getattr(args, "dst_id", 0) or 0)
    with GraphStore.open(root) as store:
        edges = store.find_edges(
            kind=kind,
            src_id=src_id or None,
            dst_id=dst_id or None,
        )
    if _flag(args, "json"):
        write_json(
            {
                "command": "graph edges",
                "path": str(root),
                "filters": {"kind": kind, "src_id": src_id, "dst_id": dst_id},
                "edges": [e.to_dict() for e in edges],
            }
        )
        return SUCCESS
    if not edges:
        write_line("Graph edges: no matches.")
        return SUCCESS
    write_line(f"Graph edges: {len(edges)} match(es).")
    for edge in edges:
        write_line(
            f"  #{edge.id}  {edge.src_id} -[{edge.kind}]-> {edge.dst_id}"
        )
    return SUCCESS


def cmd_graph_brief(args: argparse.Namespace) -> int:
    """Render the slice 5.4 session brief from the project's graph."""
    from .context.graph import GraphStore
    from .context.rehydrator import build_session_brief, render_brief_text

    root = Path(getattr(args, "path", ".")).resolve()
    phase = getattr(args, "phase", "build") or "build"
    with GraphStore.open(root) as store:
        brief = build_session_brief(store, phase)
    if _flag(args, "json"):
        write_json(
            {
                "command": "graph brief",
                "path": str(root),
                "brief": brief.to_dict(),
            }
        )
        return SUCCESS
    write_line(render_brief_text(brief))
    return SUCCESS


def cmd_graph_visualize(args: argparse.Namespace) -> int:
    """Export the graph as Mermaid (default) or DOT."""
    from .context.graph import GraphStore
    from .context.visualize import render_dot, render_mermaid

    root = Path(getattr(args, "path", ".")).resolve()
    fmt = getattr(args, "format", "mermaid")
    node_id = int(getattr(args, "node", 0) or 0)
    with GraphStore.open(root) as store:
        if fmt == "dot":
            rendered = render_dot(store, focus_node=node_id or None)
        else:
            rendered = render_mermaid(store, focus_node=node_id or None)
    write_line(rendered)
    return SUCCESS


def _workspace_root_from_args(args: argparse.Namespace):
    from .workspaces.manager import resolve_workspace_root

    return resolve_workspace_root(getattr(args, "workspace_root", "") or None)


def _workspace_action_payload(action: object) -> dict[str, object]:
    return action.to_dict()  # type: ignore[attr-defined]


def _render_workspace_action(action: object) -> None:
    payload = _workspace_action_payload(action)
    write_line(f"Workspace {payload['action']}")
    write_key_value("Message", payload.get("message", ""))
    if payload.get("repo_url"):
        write_key_value("Repo", payload["repo_url"])
    if payload.get("target_path"):
        write_key_value("Path", payload["target_path"])
    if payload.get("branch"):
        write_key_value("Branch", payload["branch"])
    if payload.get("base_branch"):
        write_key_value("Base", payload["base_branch"])
    write_key_value("Executed", str(payload.get("executed", False)).lower())
    if payload.get("command"):
        write_key_value("Command", " ".join(str(part) for part in payload["command"]))
    if payload.get("exit_code"):
        write_key_value("Exit code", payload["exit_code"])
    metadata = payload.get("metadata")
    if isinstance(metadata, dict) and metadata.get("draft"):
        write_line("")
        write_line(str(metadata["draft"]).rstrip())


def cmd_workspace_dispatch(args: argparse.Namespace) -> int:
    sub = getattr(args, "workspace_command", "")
    if sub == "status":
        return cmd_workspace_status(args)
    if sub == "clone":
        return cmd_workspace_clone(args)
    if sub == "open":
        return cmd_workspace_open(args)
    if sub == "branch":
        return cmd_workspace_branch(args)
    if sub == "track":
        return cmd_workspace_track(args)
    if sub == "pr":
        return cmd_workspace_pr(args)
    if sub == "plan":
        return cmd_workspace_plan(args)
    if sub == "diff":
        return cmd_workspace_diff(args)
    if sub == "commit":
        return cmd_workspace_commit(args)
    if sub == "push":
        return cmd_workspace_push(args)
    write_error(
        f"Unknown workspace subcommand: {sub!r}. "
        "Valid: status | clone | open | branch | track | pr | plan | diff | commit | push."
    )
    return USER_INPUT_ERROR


def cmd_workspace_status(args: argparse.Namespace) -> int:
    from .workspaces.manager import workspace_status

    root = Path(getattr(args, "path", ".")).resolve()
    workspace_root = _workspace_root_from_args(args)
    status = workspace_status(root, workspace_root)
    if _flag(args, "json"):
        write_json({"command": "workspace status", "status": status.to_dict()})
        return SUCCESS
    write_line("Workspace status")
    write_key_value("Workspace root", status.workspace_root)
    write_key_value("Current repo", status.current_repo or "(none)")
    write_key_value("Current branch", status.current_branch or "(none)")
    write_key_value("Remote", status.remote or "(none)")
    write_key_value("Dirty", str(status.dirty).lower())
    if status.tracked:
        write_line("Tracked workspaces:")
        for record in status.tracked:
            write_line(f"  {record.name}: {record.path} ({record.branch or '-'})")
    else:
        write_line("Tracked workspaces: none")
    return SUCCESS


def cmd_workspace_diff(args: argparse.Namespace) -> int:
    from .workspaces.manager import show_diff

    action = show_diff(
        Path(getattr(args, "path", ".")).resolve(),
        workspace_root=_workspace_root_from_args(args),
    )
    if _flag(args, "json"):
        write_json({"command": "workspace diff", "action": action.to_dict()})
        return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR
    _render_workspace_action(action)
    if action.stdout:
        write_line("")
        write_line(action.stdout)
    return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR


def cmd_workspace_commit(args: argparse.Namespace) -> int:
    from .workspaces.manager import commit_changes

    action = commit_changes(
        Path(getattr(args, "path", ".")).resolve(),
        workspace_root=_workspace_root_from_args(args),
        message=str(getattr(args, "message", "") or ""),
        execute=bool(getattr(args, "yes", False)),
    )
    if _flag(args, "json"):
        write_json({"command": "workspace commit", "action": action.to_dict()})
        return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR
    _render_workspace_action(action)
    if action.stdout:
        write_line("")
        write_line(action.stdout)
    return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR


def cmd_workspace_push(args: argparse.Namespace) -> int:
    from .workspaces.manager import push_branch

    action = push_branch(
        Path(getattr(args, "path", ".")).resolve(),
        workspace_root=_workspace_root_from_args(args),
        execute=bool(getattr(args, "yes", False)),
    )
    if _flag(args, "json"):
        write_json({"command": "workspace push", "action": action.to_dict()})
        return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR
    _render_workspace_action(action)
    if action.stdout:
        write_line("")
        write_line(action.stdout)
    if action.stderr:
        write_line(action.stderr)
    return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR


def cmd_workspace_clone(args: argparse.Namespace) -> int:
    from .workspaces.manager import clone_repo

    action = clone_repo(
        str(getattr(args, "repo_url", "")),
        workspace_root=_workspace_root_from_args(args),
        name=str(getattr(args, "name", "") or ""),
        execute=bool(getattr(args, "yes", False)),
    )
    if _flag(args, "json"):
        write_json({"command": "workspace clone", "action": action.to_dict()})
        return SUCCESS if action.exit_code == 0 else OPERATIONAL_FAILURE
    _render_workspace_action(action)
    return SUCCESS if action.exit_code == 0 else OPERATIONAL_FAILURE


def cmd_workspace_open(args: argparse.Namespace) -> int:
    from .workspaces.manager import open_workspace

    action = open_workspace(
        Path(getattr(args, "repo_path", ".")).resolve(),
        workspace_root=_workspace_root_from_args(args),
        name=str(getattr(args, "name", "") or ""),
    )
    if _flag(args, "json"):
        write_json({"command": "workspace open", "action": action.to_dict()})
        return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR
    _render_workspace_action(action)
    return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR


def cmd_workspace_branch(args: argparse.Namespace) -> int:
    from .workspaces.manager import create_branch

    try:
        action = create_branch(
            Path(getattr(args, "path", ".")).resolve(),
            str(getattr(args, "branch", "")),
            workspace_root=_workspace_root_from_args(args),
            execute=bool(getattr(args, "yes", False)),
        )
    except ValueError as exc:
        write_error(str(exc))
        return USER_INPUT_ERROR
    if _flag(args, "json"):
        write_json({"command": "workspace branch", "action": action.to_dict()})
        return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR
    _render_workspace_action(action)
    return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR


def cmd_workspace_track(args: argparse.Namespace) -> int:
    from .workspaces.manager import track_branch

    try:
        action = track_branch(
            Path(getattr(args, "path", ".")).resolve(),
            workspace_root=_workspace_root_from_args(args),
            branch=str(getattr(args, "branch", "") or ""),
        )
    except ValueError as exc:
        write_error(str(exc))
        return USER_INPUT_ERROR
    if _flag(args, "json"):
        write_json({"command": "workspace track", "action": action.to_dict()})
        return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR
    _render_workspace_action(action)
    return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR


def cmd_workspace_pr(args: argparse.Namespace) -> int:
    from .workspaces.manager import prepare_pr_draft

    try:
        action = prepare_pr_draft(
            Path(getattr(args, "path", ".")).resolve(),
            workspace_root=_workspace_root_from_args(args),
            title=str(getattr(args, "title", "") or ""),
            body=str(getattr(args, "body", "") or ""),
            base_branch=str(getattr(args, "base", "main") or "main"),
            write=bool(getattr(args, "write", False)),
        )
    except ValueError as exc:
        write_error(str(exc))
        return USER_INPUT_ERROR
    if _flag(args, "json"):
        write_json({"command": "workspace pr", "action": action.to_dict()})
        return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR
    _render_workspace_action(action)
    return SUCCESS if action.exit_code == 0 else USER_INPUT_ERROR


def cmd_workspace_plan(args: argparse.Namespace) -> int:
    from .workspaces.manager import propose_workspace_plan

    raw_request = getattr(args, "request", "")
    request = " ".join(str(part) for part in raw_request) if isinstance(raw_request, list) else str(raw_request)
    workspace_root = _workspace_root_from_args(args)
    rendered = propose_workspace_plan(request, workspace_root=workspace_root)
    if _flag(args, "json"):
        write_json({"command": "workspace plan", "workspace_root": str(workspace_root), "proposal": rendered})
        return SUCCESS
    write_line(rendered)
    return SUCCESS


def cmd_knowledge_dispatch(args: argparse.Namespace) -> int:
    sub = getattr(args, "knowledge_command", "")
    if sub == "status":
        return cmd_knowledge_status(args)
    if sub == "sources":
        return cmd_knowledge_sources(args)
    if sub == "search":
        return cmd_knowledge_search(args)
    write_error(
        f"Unknown knowledge subcommand: {sub!r}. "
        "Valid: status | sources | search."
    )
    return USER_INPUT_ERROR


def cmd_knowledge_status(args: argparse.Namespace) -> int:
    from .knowledge.reader import knowledge_status, render_status

    root = Path(getattr(args, "path", ".")).resolve()
    statuses = knowledge_status(root)
    if _flag(args, "json"):
        write_json(
            {
                "command": "knowledge status",
                "path": str(root),
                "sources": [status.to_dict() for status in statuses],
            }
        )
        return SUCCESS
    write_line(render_status(statuses))
    return SUCCESS


def cmd_knowledge_sources(args: argparse.Namespace) -> int:
    from .knowledge.reader import load_knowledge_sources, render_sources

    root = Path(getattr(args, "path", ".")).resolve()
    sources = load_knowledge_sources(root)
    if _flag(args, "json"):
        write_json(
            {
                "command": "knowledge sources",
                "path": str(root),
                "sources": [source.to_dict() for source in sources],
            }
        )
        return SUCCESS
    write_line(render_sources(root))
    return SUCCESS


def cmd_knowledge_search(args: argparse.Namespace) -> int:
    from .knowledge.reader import render_search, search_knowledge

    root = Path(getattr(args, "path", ".")).resolve()
    raw_query = getattr(args, "query", "")
    if isinstance(raw_query, list):
        query = " ".join(str(part) for part in raw_query).strip()
    else:
        query = str(raw_query).strip()
    if not query:
        write_error("Knowledge search requires a non-empty query.")
        return USER_INPUT_ERROR
    limit = int(getattr(args, "limit", 5) or 5)
    result = search_knowledge(root, query, limit=limit)
    if _flag(args, "json"):
        payload = result.to_dict()
        payload["command"] = "knowledge search"
        payload["path"] = str(root)
        write_json(payload)
        return SUCCESS
    write_line(render_search(result))
    return SUCCESS


def cmd_memory_dispatch(args: argparse.Namespace) -> int:
    """Dispatcher for `mythic-vibe memory` subactions."""
    sub = getattr(args, "memory_command", "")
    if sub == "list":
        return cmd_memory_list(args)
    if sub == "show":
        return cmd_memory_show(args)
    if sub == "compact":
        return cmd_memory_compact(args)
    if sub == "rehydrate":
        return cmd_memory_rehydrate(args)
    if sub == "last":
        return cmd_memory_last(args)
    if sub == "spine":
        return cmd_memory_spine(args)
    write_error(
        f"Unknown memory subcommand: {sub!r}. "
        "Valid: list | show | compact | rehydrate | last | spine."
    )
    return USER_INPUT_ERROR


def cmd_memory_list(args: argparse.Namespace) -> int:
    """List every conversation record under mythic/ai/conversations/."""
    from .memory.conversation import list_conversations

    root = Path(getattr(args, "path", ".")).resolve()
    records = list_conversations(root)
    if _flag(args, "json"):
        write_json(
            {
                "command": "memory list",
                "path": str(root),
                "conversations": [r.to_dict() for r in records],
            }
        )
        return SUCCESS
    if not records:
        write_line("Memory: no conversations recorded yet.")
        return SUCCESS
    write_line(f"Memory: {len(records)} conversation(s).")
    for record in records:
        write_line(
            f"  {record.conversation_id}  "
            f"turns={record.turn_count}  "
            f"updated={record.updated_at}  "
            f"provider={record.provider or '-'}"
        )
    return SUCCESS


def cmd_memory_show(args: argparse.Namespace) -> int:
    """Print one conversation record by id (text or JSON)."""
    from .memory.conversation import read_conversation, render_record_text

    root = Path(getattr(args, "path", ".")).resolve()
    cid = getattr(args, "id", "")
    record = read_conversation(root, cid)
    if record is None:
        write_error(f"Conversation {cid!r} not found.")
        return USER_INPUT_ERROR
    if _flag(args, "json"):
        write_json({"command": "memory show", "conversation": record.to_dict()})
        return SUCCESS
    write_line(render_record_text(record))
    return SUCCESS


def cmd_memory_compact(args: argparse.Namespace) -> int:
    """PH-15 slice 15.2 wrapper — compact a conversation into a
    summary sidecar. Honours --dry-run."""
    from .memory.compaction import compact_conversation

    root = Path(getattr(args, "path", ".")).resolve()
    cid = getattr(args, "id", "")
    keep_recent = int(getattr(args, "keep_recent", 3) or 3)
    payload = compact_conversation(
        root,
        cid,
        keep_recent=keep_recent,
        dry_run=bool(_flag(args, "dry_run")),
    )
    if _flag(args, "json"):
        write_json({"command": "memory compact", "result": payload.to_dict()})
        return SUCCESS if (payload.written or payload.dry_run) else OPERATIONAL_FAILURE
    if payload.metadata.get("error") == "conversation not found":
        write_error(f"Conversation {cid!r} not found.")
        return USER_INPUT_ERROR
    if payload.dry_run:
        write_line(
            f"Memory compact (dry run): would write "
            f"{payload.markdown_path} + JSON sidecar."
        )
        return SUCCESS
    if not payload.written:
        write_error(
            "Failed to write summary: "
            f"{payload.metadata.get('error', 'unknown error')}"
        )
        return OPERATIONAL_FAILURE
    write_line(
        f"Memory compact: {payload.markdown_path} "
        f"({payload.recent_turns_count} recent / "
        f"{payload.earlier_turns_count} earlier turns)."
    )
    return SUCCESS


def cmd_memory_rehydrate(args: argparse.Namespace) -> int:
    """PH-15 slice 15.4 — combine the graph-backed session brief
    (PH-05 slice 5.4) with the latest conversation summary (slice
    15.2) and the latest handoff. The result is a one-call cheat-
    sheet for session resume."""
    from .context.graph import GraphStore, graph_path_for
    from .context.rehydrator import build_session_brief
    from .memory.compaction import latest_summary_for
    from .memory.conversation import latest_conversation

    root = Path(getattr(args, "path", ".")).resolve()
    phase = getattr(args, "phase", "build") or "build"

    # Session brief (graph-backed if graph exists; empty otherwise).
    brief_payload: dict[str, object] = {}
    if graph_path_for(root).exists():
        with GraphStore.open(root) as store:
            brief = build_session_brief(store, phase)
            brief_payload = brief.to_dict()

    # Latest conversation + summary.
    convo = latest_conversation(root)
    convo_payload: dict[str, object] | None = None
    summary_text = ""
    if convo is not None:
        convo_payload = {
            "conversation_id": convo.conversation_id,
            "provider": convo.provider,
            "model": convo.model,
            "updated_at": convo.updated_at,
            "turn_count": convo.turn_count,
        }
        summary_text = latest_summary_for(root, convo.conversation_id)

    # Latest handoff (file-based, existing infrastructure).
    handoff_payload: dict[str, object] | None = None
    handoff_record = load_latest_handoff(root)
    if handoff_record is not None:
        handoff_payload = {
            "handoff_id": handoff_record.handoff_id,
            "timestamp": handoff_record.timestamp,
            "objective": handoff_record.objective,
            "next_steps": list(handoff_record.next_steps),
        }

    payload = {
        "command": "memory rehydrate",
        "path": str(root),
        "phase": phase,
        "session_brief": brief_payload,
        "latest_conversation": convo_payload,
        "conversation_summary": summary_text,
        "latest_handoff": handoff_payload,
    }
    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line(f"Rehydration brief — phase: {phase}")
    write_line("")
    if brief_payload:
        write_line(
            "- Session brief: graph populated; "
            f"top {len(brief_payload.get('top_k', []))} retrieval hits, "
            f"{len(brief_payload.get('recent_decisions', []))} recent decisions."
        )
    else:
        write_line(
            "- Session brief: graph absent; run `mythic-vibe scan` to populate."
        )
    if convo_payload is not None:
        write_line(
            f"- Latest conversation: {convo_payload['conversation_id']} "
            f"({convo_payload['turn_count']} turns)"
        )
        if summary_text:
            write_line("- Summary file present.")
        else:
            write_line("- No summary yet; run `memory compact` to generate.")
    else:
        write_line("- Latest conversation: none recorded.")
    if handoff_payload is not None:
        write_line(
            f"- Latest handoff: {handoff_payload['handoff_id']} — "
            f"{handoff_payload.get('objective') or '(no objective)'}"
        )
    else:
        write_line("- Latest handoff: none.")
    return SUCCESS


def cmd_memory_last(args: argparse.Namespace) -> int:
    """Render the project-level SQLite memory resume answer."""
    from .memory.spine import build_memory_snapshot, render_last_time

    root = Path(getattr(args, "path", ".")).resolve()
    if _flag(args, "json"):
        snapshot = build_memory_snapshot(root)
        write_json(
            {
                "command": "memory last",
                "path": str(root),
                "memory": snapshot.to_dict(),
                "answer": render_last_time(root),
            }
        )
        return SUCCESS
    write_line(render_last_time(root))
    return SUCCESS


def cmd_memory_spine(args: argparse.Namespace) -> int:
    """Show SQLite memory-spine status and recent entries."""
    from .memory.spine import build_memory_snapshot, init_memory_spine

    root = Path(getattr(args, "path", ".")).resolve()
    limit = int(getattr(args, "limit", 10) or 10)
    db_path = init_memory_spine(root)
    snapshot = build_memory_snapshot(root, limit=limit)
    if _flag(args, "json"):
        write_json(
            {
                "command": "memory spine",
                "path": str(root),
                "memory": snapshot.to_dict(),
            }
        )
        return SUCCESS

    write_line("Memory spine")
    write_key_value("SQLite", db_path)
    write_line("Counts:")
    for kind, count in snapshot.counts.items():
        write_line(f"  {kind}: {count}")
    if not snapshot.entries:
        write_line("Recent entries: none")
        return SUCCESS
    write_line("Recent entries:")
    for entry in snapshot.entries:
        write_line(
            f"  {entry.entry_id} [{entry.kind}] "
            f"{entry.created_at} — {entry.content}"
        )
    return SUCCESS


def cmd_voice_dispatch(args: argparse.Namespace) -> int:
    """PH-07 slices 7.1-7.3: dispatch ``mythic-vibe voice <action>``."""
    sub = getattr(args, "voice_command", "")
    if sub == "transcribe":
        return cmd_voice_transcribe(args)
    if sub == "say":
        return cmd_voice_say(args)
    write_error(
        f"Unknown voice subcommand: {sub!r}. Valid: transcribe | say."
    )
    return USER_INPUT_ERROR


def cmd_voice_transcribe(args: argparse.Namespace) -> int:
    """PH-07 slice 7.1 (+ 7.2 via ``--capture-intent``).

    Stub engine works without any audio dep; whisper engine
    requires ``pip install openai-whisper`` (and ffmpeg on PATH).
    With ``--capture-intent``, the transcription is piped into a
    fresh ``mythic/checkins/<ts>-intent.md`` Mythic Phase Record
    via the slice 2.3 ``cmd_intent_capture`` path.

    PH-07 follow-up: ``--mic [--duration N]`` records from the
    system microphone (via sounddevice) into a temp WAV and feeds
    that into the same transcribe pipeline. The temp file is always
    cleaned up after the call.
    """
    from .voice.transcribe import (
        DEFAULT_MIC_DURATION,
        MissingExtraError,
        TranscriptionRequest,
        record_to_temp_wav,
        transcribe,
    )

    root = Path(getattr(args, "path", ".")).resolve()

    use_mic = bool(_flag(args, "mic"))
    file_arg = str(getattr(args, "file", "") or "")
    if not use_mic and not file_arg:
        write_error("voice transcribe requires either --file PATH or --mic.")
        return USER_INPUT_ERROR
    if use_mic and file_arg:
        write_error("--file and --mic are mutually exclusive.")
        return USER_INPUT_ERROR

    mic_temp_path: str = ""
    if use_mic:
        duration = float(getattr(args, "duration", DEFAULT_MIC_DURATION) or DEFAULT_MIC_DURATION)
        if duration <= 0:
            write_error(f"--duration must be > 0 seconds (got {duration!r}).")
            return USER_INPUT_ERROR
        try:
            mic_temp_path = record_to_temp_wav(duration)
        except MissingExtraError as exc:
            write_error(f"Microphone capture unavailable: {exc}")
            write_bullet(f"Install hint: {exc.install_hint}", indent=2)
            return OPERATIONAL_FAILURE
        except Exception as exc:  # noqa: BLE001 — surface unexpected audio backend failures cleanly
            write_error(f"Microphone capture failed: {exc}")
            return OPERATIONAL_FAILURE
        source_path = mic_temp_path
    else:
        source_path = file_arg

    try:
        request = TranscriptionRequest(
            source_path=source_path,
            engine=str(getattr(args, "engine", "stub") or "stub"),
            language=str(getattr(args, "language", "en") or "en"),
            model=str(getattr(args, "model", "base") or "base"),
        )
        result = transcribe(request)
    finally:
        if mic_temp_path:
            Path(mic_temp_path).unlink(missing_ok=True)

    payload: dict[str, object] = {
        "command": "voice transcribe",
        "path": str(root),
        "request": request.to_dict(),
        "result": result.to_dict(),
    }

    capture_intent = bool(_flag(args, "capture_intent"))
    intent_payload: dict[str, object] | None = None
    if capture_intent:
        task = str(getattr(args, "task", "") or "").strip()
        if not task:
            write_error(
                "--capture-intent requires --task <short task name> so the "
                "phase record has a meaningful header."
            )
            return USER_INPUT_ERROR
        if result.error:
            write_error(
                f"Transcription failed; not writing phase record. {result.error}"
            )
            payload["intent_capture"] = {
                "written": False,
                "error": result.error,
            }
            if _flag(args, "json"):
                write_json(payload)
                return OPERATIONAL_FAILURE
            return OPERATIONAL_FAILURE
        # Build a minimal Namespace shaped like the slice 2.3 capture
        # handler expects, then delegate.
        capture_args = argparse.Namespace(
            path=str(root),
            task=task,
            summary=result.text or "(empty transcription)",
            note=[
                f"transcription engine: {result.engine}",
                f"source file: {result.source_path}",
            ],
            confidence="unspecified",
            risk="",
            next_step="",
            operator="",
            json=False,
            dry_run=False,
        )
        # Capture writes its own JSON to stdout when json=True; we
        # suppress that and re-surface from our outer payload.
        captured_buf = io.StringIO()
        with redirect_stdout(captured_buf):
            inner_code = cmd_intent_capture(capture_args)
        intent_payload = {
            "written": inner_code == SUCCESS,
            "exit_code": inner_code,
            "task": task,
            "summary_chars": len(result.text or ""),
        }
        payload["intent_capture"] = intent_payload

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS if not result.error else OPERATIONAL_FAILURE

    if result.error:
        write_error(f"Transcription failed: {result.error}")
        if "missing_extra" in result.metadata:
            write_bullet(
                f"Install hint: `pip install {result.metadata['missing_extra']}`",
                indent=2,
            )
        return OPERATIONAL_FAILURE

    write_line(
        f"Voice transcribe ({result.engine}/{result.model}, "
        f"language={result.language}, dry_run={result.dry_run}):"
    )
    write_line(result.text or "(empty)")
    if intent_payload is not None:
        if intent_payload.get("written"):
            write_line(
                f"- Wrote intent phase record (task={intent_payload['task']!r})."
            )
        else:
            write_error(
                "Failed to write intent phase record "
                f"(exit_code={intent_payload.get('exit_code')})."
            )
            return OPERATIONAL_FAILURE
    return SUCCESS


def cmd_voice_say(args: argparse.Namespace) -> int:
    """PH-07 slice 7.3 — speak text via the configured TTS engine.

    Default-disabled: respects ``MYTHIC_VOICE_TTS_ENABLED`` unless
    ``--force`` is passed for direct testing.
    """
    from .voice.tts import is_tts_enabled, say

    text = str(getattr(args, "text", "") or "")
    engine = str(getattr(args, "engine", "stub") or "stub")
    force = bool(_flag(args, "force"))
    result = say(text, engine=engine, force=force)

    payload = {
        "command": "voice say",
        "tts_enabled": is_tts_enabled(),
        "force": force,
        "result": result.to_dict(),
    }

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS if not result.error else OPERATIONAL_FAILURE

    if result.error:
        write_error(f"voice say failed: {result.error}")
        if "missing_extra" in result.metadata:
            write_bullet(
                f"Install hint: `pip install {result.metadata['missing_extra']}`",
                indent=2,
            )
        return OPERATIONAL_FAILURE
    if result.spoken:
        write_line(f"voice say: spoken via {result.engine}.")
    else:
        write_line(f"voice say: not spoken ({result.skipped_reason or 'no audio'}).")
    return SUCCESS


def cmd_hardware(args: argparse.Namespace) -> int:
    """PH-06 slice 6.6: detect host hardware and optionally persist
    it to ``docs/hardware_profiles.md`` (plus a JSON sidecar).

    Best-effort throughout — every measurement is guarded so a
    partially broken environment still produces a usable record.
    Missing values land in the profile's ``notes`` list rather than
    raising.
    """
    from .hardware import detect_profile, render_profile_text, write_profile

    root = Path(getattr(args, "path", ".")).resolve()
    profile = detect_profile()
    payload: dict[str, object] = {
        "command": "hardware",
        "path": str(root),
        "profile": profile.to_dict(),
        "written": False,
    }

    if _flag(args, "write"):
        try:
            md_path, json_path = write_profile(root, profile)
        except OSError as exc:
            payload["written"] = False
            payload["error"] = str(exc)
        else:
            payload["written"] = True
            payload["markdown_path"] = str(md_path)
            payload["json_path"] = str(json_path)

    if _flag(args, "json"):
        write_json(payload)
        return SUCCESS

    write_line(render_profile_text(profile).rstrip())
    if _flag(args, "write"):
        if payload.get("written"):
            write_key_value("Markdown", payload["markdown_path"])
            write_key_value("JSON sidecar", payload["json_path"])
        else:
            write_error(
                f"Failed to write profile: {payload.get('error', 'unknown error')}"
            )
            return OPERATIONAL_FAILURE
    return SUCCESS


def cmd_drift(args: argparse.Namespace) -> int:
    """PH-13 slice 13.1: scan the project for drift between docs, code,
    and decisions.

    Three heuristic detectors run today (undocumented handlers,
    undocumented modules, superseded-but-referenced decisions). The
    set will grow as PH-13 progresses. Exit code stays ``SUCCESS``
    even with findings — the operator decides what to act on. Future
    slices may bump exit on ``error``-severity findings; the heuristics
    today only emit ``info`` / ``warning``.

    Phase 20.E (audit remediation 2026-05-03): when the optional
    ``subcommand`` positional == ``"dashboard"``, emit the rollup
    scorecard (markdown by default; JSON via ``--json``).
    """
    from .drift import (
        build_dashboard_payload,
        render_dashboard_markdown,
        render_findings_text,
        scan_for_drift,
        to_payload,
    )

    root = Path(getattr(args, "path", ".")).resolve()
    findings = scan_for_drift(root)
    sub = (getattr(args, "subcommand", "") or "").strip().lower()

    if sub == "dashboard":
        if _flag(args, "json"):
            write_json(build_dashboard_payload(findings))
            return SUCCESS
        write_line(render_dashboard_markdown(findings))
        return SUCCESS

    if _flag(args, "json"):
        write_json(to_payload(findings))
        return SUCCESS
    write_line(render_findings_text(findings))
    return SUCCESS


COMMAND_HANDLERS: dict[str, CommandHandler] = {
    "init": cmd_init,
    "start": cmd_init,
    "imbue": cmd_init,
    "checkin": cmd_checkin,
    "reflect": cmd_reflect,
    "handoff": cmd_handoff_dispatch,
    "resume": cmd_resume,
    "examples": cmd_examples,
    "guide": cmd_guide,
    "next": cmd_next,
    "explain": cmd_explain_dispatch,
    "tutorial": cmd_tutorial,
    "completion": cmd_completion,
    "scan": cmd_scan,
    "import-md": cmd_import_md,
    "codex-pack": cmd_codex_pack,
    "evoke": cmd_codex_pack,
    "packet": cmd_packet_dispatch,
    "workflow": cmd_workflow_dispatch,
    "codex-log": cmd_codex_log,
    "status": cmd_status,
    "sync": cmd_sync,
    "method": cmd_method_dispatch,
    "doctor": cmd_doctor,
    "scry": cmd_doctor,
    "weave": cmd_weave,
    "prune": cmd_prune,
    "heal": cmd_heal,
    "oath": cmd_oath,
    "grimoire": cmd_grimoire,
    "plugin": cmd_plugin_dispatch,
    "security": cmd_security_dispatch,
    "ci": cmd_ci_dispatch,
    "docker": cmd_docker_dispatch,
    "release": cmd_release,
    "rollback": cmd_rollback,
    "policy": cmd_policy_dispatch,
    "simulate": cmd_simulate,
    "protocols": cmd_protocols_dispatch,
    "surface": cmd_surface_dispatch,
    "config": cmd_config_dispatch,
    "state": cmd_state_dispatch,
    "db": cmd_db_dispatch,
    "plunder": cmd_plunder,
    # Phase 20.6 (additive 2026-05-03): provenance verify.
    "provenance": cmd_provenance,
    # Phase 20.A (additive 2026-05-03): persona presets.
    "persona": cmd_persona,
    # Phase 20.H (additive 2026-05-03): architecture review.
    "review": cmd_review,
    # v1.0 / Hermes (2026-05-03): top-level agent introspection.
    "hermes": cmd_hermes,
    "ai": cmd_ai_dispatch,
    "verify": cmd_verify_dispatch,
    "slash": cmd_slash_dispatch,
    "shell": cmd_shell,
    "tui": cmd_tui,
    "test": cmd_test,
    "lint": cmd_lint,
    "typecheck": cmd_typecheck,
    "scaffold": cmd_scaffold,
    "changelog": cmd_changelog,
    "version": cmd_version,
    "intent": cmd_intent_dispatch,
    "constraints": cmd_constraints_dispatch,
    "architecture": cmd_architecture_dispatch,
    "plan": cmd_plan_dispatch,
    "build": cmd_build_dispatch,
    "forge": cmd_forge_dispatch,
    "provider": cmd_provider,
    "audit": cmd_audit,
    "drift": cmd_drift,
    "workspace": cmd_workspace_dispatch,
    "graph": cmd_graph_dispatch,
    "knowledge": cmd_knowledge_dispatch,
    "memory": cmd_memory_dispatch,
    "hardware": cmd_hardware,
    "voice": cmd_voice_dispatch,
}
