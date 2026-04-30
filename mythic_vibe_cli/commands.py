from __future__ import annotations

import argparse
from collections.abc import Callable
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
    if _flag(args, "dry_run"):
        write_line("Dry run: no project files will be written.")
        write_key_value("Project path", root)
        write_key_value("Goal", args.goal)
        write_line("Would create Mythic docs, tasks, and runtime state if missing.")
        return SUCCESS

    root.mkdir(parents=True, exist_ok=True)

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
    root = Path(getattr(args, "path", ".")).resolve()
    registry = _ai_registry(root)
    provider = registry.providers().get(args.provider)
    if provider is None:
        write_error(f"Unknown provider: {args.provider}")
        return USER_INPUT_ERROR

    status = provider.validate_config()
    if not status.configured and not _flag(args, "dry_run"):
        write_error(f"Provider not configured: {args.provider}. Use --dry-run or set the required API key.")
        return USER_INPUT_ERROR

    packet = _resolve_ai_packet(root, args.packet)
    response = provider.run(packet, dry_run=_flag(args, "dry_run"))
    payload = {
        "command": "ai run",
        "path": str(root),
        "provider": provider.name,
        "dry_run": _flag(args, "dry_run") or response.dry_run,
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
    }
    write_json(payload)
    return SUCCESS


def cmd_ai_ingest_response(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    out_dir = root / "mythic" / "ai"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "latest_response.json"
    payload = {
        "provider": args.provider,
        "model": args.model,
        "packet_id": args.packet_id,
        "response": args.response,
        "applied": False,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if _flag(args, "json"):
        write_json({"command": "ai ingest-response", "path": str(out_path), "payload": payload})
        return SUCCESS
    write_line("AI response ingested as metadata only.")
    write_key_value("Path", out_path)
    write_key_value("Applied", "false")
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


def cmd_scaffold(args: argparse.Namespace) -> int:
    """Add a new artefact to an existing Mythic project.

    Today only ``scaffold adr <title>`` is implemented. The remaining
    artefact types (task / interface / invariant / risk) are routed to
    PH-10 slice 10.4 (artefact-template extension points).
    """
    root = Path(getattr(args, "path", ".")).resolve()
    artefact = getattr(args, "artefact", None)

    if artefact != "adr":
        write_error(
            f"Scaffold artefact {artefact!r} not yet implemented. "
            "Available now: adr. Future types (task/interface/invariant/risk) land in PH-10 slice 10.4."
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

    root = Path(args.path).resolve()
    workflow = MythicWorkflow(root)
    repo_boundary = _flag(args, "repo_boundary")
    report = workflow.doctor_report(
        repo_boundary=repo_boundary,
        project_scaffold=not repo_boundary,
    )
    drift_findings = scan_for_drift(root)
    drift_payload = [f.to_dict() for f in drift_findings]
    if _flag(args, "json"):
        write_json(
            {
                "path": str(root),
                "repo_boundary": repo_boundary,
                "ok": bool(report["ok"]),
                "errors": list(report["errors"]),
                "warnings": list(report["warnings"]),
                "sections": report["sections"],
                "drift": drift_payload,
            }
        )
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
    oath = "I understand that AI may generate incorrect or insecure code. I will review all changes before committing to the Sacred Grove."
    write_line(oath)
    if args.yes:
        write_line("Oath accepted.")
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


def cmd_plugin_dispatch(args: argparse.Namespace) -> int:
    if args.plugin_command == "list":
        return cmd_plugin_list(args)
    if args.plugin_command == "inspect":
        return cmd_plugin_inspect(args)
    if args.plugin_command == "disable":
        return cmd_plugin_disable(args)
    return USER_INPUT_ERROR


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
    return USER_INPUT_ERROR


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


SLASH_LOCALS_WITHOUT_ARGPARSE = {"help", "reload", "quit"}


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
    from .repl import run_shell

    project_root = Path(getattr(args, "path", ".")).resolve()
    return run_shell(project_root=project_root)


def cmd_tui(args: argparse.Namespace) -> int:
    project_root = Path(getattr(args, "path", ".")).resolve()
    theme = getattr(args, "theme", None)
    try:
        from .tui.app import run_tui
    except ImportError as exc:
        write_error(
            "Textual is not installed. Install the optional TUI extra with: "
            "pip install \"mythic-vibe-cli[tui]\"  (or: pip install textual)"
        )
        write_error(f"Underlying import error: {exc}")
        return OPERATIONAL_FAILURE
    return run_tui(project_root, theme=theme)


def cmd_ai_dispatch(args: argparse.Namespace) -> int:
    if args.ai_command == "providers":
        return cmd_ai_providers(args)
    if args.ai_command == "test":
        return cmd_ai_test(args)
    if args.ai_command == "run":
        return cmd_ai_run(args)
    if args.ai_command == "ingest-response":
        return cmd_ai_ingest_response(args)
    write_error(
        f"Unknown ai subcommand: {args.ai_command!r}. Valid: providers | test | run | ingest-response."
    )
    return USER_INPUT_ERROR


def cmd_verify_dispatch(args: argparse.Namespace) -> int:
    return cmd_verify(args)


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
    setattr(args, "json", True)
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


def cmd_drift(args: argparse.Namespace) -> int:
    """PH-13 slice 13.1: scan the project for drift between docs, code,
    and decisions.

    Three heuristic detectors run today (undocumented handlers,
    undocumented modules, superseded-but-referenced decisions). The
    set will grow as PH-13 progresses. Exit code stays ``SUCCESS``
    even with findings — the operator decides what to act on. Future
    slices may bump exit on ``error``-severity findings; the heuristics
    today only emit ``info`` / ``warning``.
    """
    from .drift import render_findings_text, scan_for_drift, to_payload

    root = Path(getattr(args, "path", ".")).resolve()
    findings = scan_for_drift(root)
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
    "config": cmd_config_dispatch,
    "state": cmd_state_dispatch,
    "db": cmd_db_dispatch,
    "plunder": cmd_plunder,
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
    "graph": cmd_graph_dispatch,
}
