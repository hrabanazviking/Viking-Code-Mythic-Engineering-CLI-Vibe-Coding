from __future__ import annotations

import argparse
import base64
from collections.abc import Callable
import json
import os
from pathlib import Path
import sqlite3
import urllib.error
import urllib.parse
import urllib.request

from .codex_bridge import CodexBridge, CodexPacketRequest, PACKET_OUTPUT_FORMATS, PACKET_ROLES
from .ai.registry import ProviderRegistry
from .context.indexer import ProjectIndexer
from .config import ConfigStore
from .errors import CliError, format_error
from .exit_codes import OPERATIONAL_FAILURE, SUCCESS, USER_INPUT_ERROR, VERIFICATION_FAILURE
from .mythic_data import MethodStore
from .output import write_bullet, write_error, write_json, write_key_value, write_line, write_verbose
from .core.state import PHASES, VerificationRecord, coerce_project_state, utc_now, validate_state_payload
from .persistence.json_store import JsonStateStore, StateStoreError
from .persistence.migrations import migrate_project_state
from .workflow import MythicRunConfig, MythicWorkflow
from .verify import VerificationArtifact, new_verification_id, write_verification_artifact
from .verify.doc_checker import check_docs
from .verify.git_diff import review_changed_files
from .verify.invariant_checker import check_invariants
from .verify.test_runner import run_default_commands


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

    if subcommand_attr:
        return f"{command} {subcommand_attr}"
    if command:
        return command
    return fallback


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if _flag(args, "dry_run"):
        write_line("Dry run: no project files will be written.")
        write_key_value("Project path", root)
        write_key_value("Goal", args.goal)
        write_line("Would create Mythic docs, tasks, and runtime state if missing.")
        return SUCCESS

    root.mkdir(parents=True, exist_ok=True)

    store = MethodStore()
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

    store = MethodStore()
    try:
        written = store.import_all_markdown(target)
    except Exception as exc:  # noqa: BLE001 - surface remote import issues in CLI.
        write_error(format_error(CliError(f"Import failed: {exc}")))
        return OPERATIONAL_FAILURE

    write_line("Imported Mythic Engineering markdown files.")
    write_key_value("Destination", target)
    write_key_value("Files imported", len(written))
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

    index = indexer.build(
        changed_only=_flag(args, "changed"),
        docs_only=_flag(args, "docs"),
        include_patterns=getattr(args, "include", []) or [],
        exclude_patterns=getattr(args, "exclude", []) or [],
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

    bridge = CodexBridge(root)
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
    bridge = CodexBridge(root)
    records = bridge.list_packets()
    if _flag(args, "json"):
        write_json(
            {
                "command": "packet list",
                "path": str(root),
                "packets": [record.to_dict() for record in records],
            }
        )
        return SUCCESS

    if not records:
        write_line("No packet records found.")
        return SUCCESS

    write_line("Packet records")
    for record in records:
        write_key_value(record.packet_id, f"{record.phase} | {record.role} | {record.created_at}", indent=2)
        write_bullet(record.task, indent=4)
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

    try:
        record = bridge.ingest_packet(source)
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        write_error(str(exc))
        return USER_INPUT_ERROR

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


def cmd_packet_diff(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    bridge = CodexBridge(root)
    left_id = args.left
    right_id = args.right

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
                "diff": diff,
            }
        )
        return SUCCESS

    write_line(diff)
    return SUCCESS


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
    return SUCCESS


def _github_get_file(repo: str, source_path: str, ref: str, token: str) -> str:
    encoded_path = urllib.parse.quote(source_path.strip("/"))
    url = f"https://api.github.com/repos/{repo}/contents/{encoded_path}?ref={urllib.parse.quote(ref)}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "mythic-vibe-cli",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("type") != "file":
        raise ValueError(f"Source is not a file: {source_path}")
    raw = payload.get("content", "")
    if payload.get("encoding") != "base64":
        raise ValueError(f"Unsupported GitHub encoding for {source_path}: {payload.get('encoding')}")
    return base64.b64decode(raw).decode("utf-8")


def cmd_doctor(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    workflow = MythicWorkflow(root)
    repo_boundary = _flag(args, "repo_boundary")
    report = workflow.doctor_report(
        repo_boundary=repo_boundary,
        project_scaffold=not repo_boundary,
    )
    if _flag(args, "json"):
        write_json(
            {
                "path": str(root),
                "repo_boundary": repo_boundary,
                "ok": bool(report["ok"]),
                "errors": list(report["errors"]),
                "warnings": list(report["warnings"]),
                "sections": report["sections"],
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

    return OPERATIONAL_FAILURE if report["errors"] else SUCCESS


def cmd_sync(_args: argparse.Namespace) -> int:
    if _flag(_args, "dry_run"):
        store = MethodStore()
        write_line("Dry run: no method sync will be performed.")
        write_key_value("Cache", store.cache_file)
        return SUCCESS

    store = MethodStore()
    try:
        bundle = store.sync()
    except Exception as exc:  # noqa: BLE001 - CLI should show actionable message and continue.
        write_error(format_error(CliError(f"Sync failed: {exc}")))
        return OPERATIONAL_FAILURE

    write_line("Synced Mythic method notes.")
    write_key_value("Source", bundle.source)
    write_key_value("Cache", store.cache_file)
    return SUCCESS


def cmd_method(_args: argparse.Namespace) -> int:
    store = MethodStore()
    bundle = store.load()
    write_verbose(f"Loaded method bundle from {bundle.source}")
    write_key_value("Method source", bundle.source)
    write_line("=" * 72)
    write_line(bundle.content)
    return SUCCESS


def cmd_oath(args: argparse.Namespace) -> int:
    oath = "I understand that AI may generate incorrect or insecure code. I will review all changes before committing to the Sacred Grove."
    write_line(oath)
    if args.yes:
        write_line("Oath accepted.")
    return SUCCESS


def cmd_grimoire(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    store_file = root / "mythic" / "plugins.json"
    if _flag(args, "dry_run") and args.grimoire_command == "add":
        payload = {
            "command": "grimoire add",
            "dry_run": True,
            "registry": str(store_file),
            "plugin": args.plugin,
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no plugin registry entry will be written.")
            write_key_value("Registry", store_file)
            write_key_value("Plugin", args.plugin)
        return SUCCESS

    store_file.parent.mkdir(parents=True, exist_ok=True)
    if store_file.exists():
        data = json.loads(store_file.read_text(encoding="utf-8"))
    else:
        data = {"plugins": []}

    if args.grimoire_command == "add":
        if args.plugin not in data["plugins"]:
            data["plugins"].append(args.plugin)
            store_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            message = f"Registered plugin: {args.plugin}"
        else:
            message = f"Plugin already registered: {args.plugin}"
        if _flag(args, "json"):
            write_json(
                {
                    "command": "grimoire add",
                    "dry_run": False,
                    "registry": str(store_file),
                    "plugin": args.plugin,
                    "plugins": data.get("plugins", []),
                }
            )
            return SUCCESS
        write_line(message)
        write_key_value("Registry", store_file)
        return SUCCESS

    plugins = data.get("plugins", [])
    if _flag(args, "json"):
        write_json({"command": "grimoire list", "registry": str(store_file), "plugins": plugins})
        return SUCCESS

    if not plugins:
        write_line("No plugins registered.")
        return SUCCESS
    write_line("Registered plugins:")
    for plugin in plugins:
        write_bullet(plugin)
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


def cmd_plunder(args: argparse.Namespace) -> int:
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

    token = os.getenv(args.token_env, "").strip()
    if not token:
        write_error(
            format_error(
                CliError(
                    f"Missing token. Set {args.token_env} and retry (repo access is required).",
                    exit_code=USER_INPUT_ERROR,
                )
            )
        )
        return USER_INPUT_ERROR

    try:
        text = _github_get_file(args.repo, args.source, args.ref, token)
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        write_error(format_error(CliError(f"GitHub API error ({exc.code}): {message}")))
        return OPERATIONAL_FAILURE
    except Exception as exc:  # noqa: BLE001
        write_error(format_error(CliError(f"Plunder failed: {exc}")))
        return OPERATIONAL_FAILURE

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    if _flag(args, "json"):
        write_json(
            {
                "command": "plunder",
                "dry_run": False,
                "repo": args.repo,
                "source": args.source,
                "ref": args.ref,
                "destination": str(out_path),
            }
        )
        return SUCCESS

    write_line("Plunder complete.")
    write_key_value("Repo", f"{args.repo}@{args.ref}")
    write_key_value("Source", args.source)
    write_key_value("Destination", out_path)
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
    root = Path(args.path).resolve()
    write_line("Heal ritual scaffold ready.")
    write_key_value("Project", root)
    if args.failing_test:
        write_key_value("Target failing test", args.failing_test)
    write_line("Next: reproduce the failure, patch minimally, then rerun tests.")
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


def cmd_ai_dispatch(args: argparse.Namespace) -> int:
    if args.ai_command == "providers":
        return cmd_ai_providers(args)
    if args.ai_command == "test":
        return cmd_ai_test(args)
    if args.ai_command == "run":
        return cmd_ai_run(args)
    if args.ai_command == "ingest-response":
        return cmd_ai_ingest_response(args)
    return USER_INPUT_ERROR


def cmd_verify_dispatch(args: argparse.Namespace) -> int:
    return cmd_verify(args)


COMMAND_HANDLERS: dict[str, CommandHandler] = {
    "init": cmd_init,
    "start": cmd_init,
    "imbue": cmd_init,
    "checkin": cmd_checkin,
    "scan": cmd_scan,
    "import-md": cmd_import_md,
    "codex-pack": cmd_codex_pack,
    "evoke": cmd_codex_pack,
    "packet": cmd_packet_dispatch,
    "codex-log": cmd_codex_log,
    "status": cmd_status,
    "sync": cmd_sync,
    "method": cmd_method,
    "doctor": cmd_doctor,
    "scry": cmd_doctor,
    "weave": cmd_weave,
    "prune": cmd_prune,
    "heal": cmd_heal,
    "oath": cmd_oath,
    "grimoire": cmd_grimoire,
    "config": cmd_config_dispatch,
    "state": cmd_state_dispatch,
    "db": cmd_db_dispatch,
    "plunder": cmd_plunder,
    "ai": cmd_ai_dispatch,
    "verify": cmd_verify_dispatch,
}
