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

from .codex_bridge import CodexBridge, CodexPacketRequest
from .config import ConfigStore
from .errors import CliError, format_error
from .exit_codes import OPERATIONAL_FAILURE, SUCCESS, USER_INPUT_ERROR
from .mythic_data import MethodStore
from .output import write_bullet, write_error, write_json, write_key_value, write_line, write_verbose
from .workflow import PHASES, MythicRunConfig, MythicWorkflow


CommandHandler = Callable[[argparse.Namespace], int]


def _flag(args: argparse.Namespace, name: str) -> bool:
    return bool(getattr(args, name, False))


def _status_payload(root: Path) -> dict[str, object]:
    status_path = root / "mythic" / "status.json"
    if not status_path.exists():
        return {
            "status_found": False,
            "path": str(status_path),
            "message": 'No Mythic status found. Run `mythic-vibe init --goal "..."` first.',
        }

    try:
        state = json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "status_found": True,
            "valid": False,
            "path": str(status_path),
            "error": f"Invalid JSON: {exc.msg}",
        }

    if not isinstance(state, dict):
        return {
            "status_found": True,
            "valid": False,
            "path": str(status_path),
            "error": "status.json must contain a JSON object.",
        }

    completed = [phase for phase in state.get("completed_phases", []) if phase in PHASES]
    progress = int((len(completed) / len(PHASES)) * 100)
    return {
        "status_found": True,
        "valid": True,
        "path": str(status_path),
        "goal": state.get("goal", "n/a"),
        "current_phase": state.get("current_phase", "intent"),
        "completed_phases": completed,
        "progress_percent": progress,
        "last_update": state.get("last_update", "n/a"),
    }


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


def cmd_codex_pack(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    out_path = Path(args.out).resolve() if args.out else root / "mythic" / "codex_prompt.md"
    if _flag(args, "dry_run"):
        payload = {
            "command": args.command,
            "dry_run": True,
            "path": str(root),
            "output_file": str(out_path),
            "phase": args.phase,
            "task": args.task,
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no Codex packet will be written.")
            write_key_value("File", out_path)
            write_key_value("Phase", args.phase)
            write_key_value("Task", args.task)
        return SUCCESS

    bridge = CodexBridge(root)
    packet = bridge.create_packet(
        request=CodexPacketRequest(task=args.task, phase=args.phase, audience=args.audience),
        out_file=out_path,
    )
    if _flag(args, "json"):
        write_json(
            {
                "command": args.command,
                "dry_run": False,
                "path": str(root),
                "output_file": str(packet),
                "phase": args.phase,
                "task": args.task,
            }
        )
        return SUCCESS

    write_line("Codex packet generated.")
    write_key_value("File", packet)
    write_line("Paste the 'Prompt To Paste' section into ChatGPT/Codex.")
    return SUCCESS


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
    errors, warnings = workflow.doctor(
        repo_boundary=repo_boundary,
        project_scaffold=not repo_boundary,
    )
    if _flag(args, "json"):
        write_json(
            {
                "path": str(root),
                "repo_boundary": repo_boundary,
                "ok": not errors,
                "errors": errors,
                "warnings": warnings,
            }
        )
        return OPERATIONAL_FAILURE if errors else SUCCESS

    write_line("Mythic project diagnostics")
    write_key_value("Path", root)
    if repo_boundary:
        write_line("- Repo boundary checks: enabled")

    if errors:
        write_line("- Errors:")
        for item in errors:
            write_bullet(item, indent=2)
    else:
        write_line("- Errors: none")

    if warnings:
        write_line("- Warnings:")
        for item in warnings:
            write_bullet(item, indent=2)
    else:
        write_line("- Warnings: none")

    return OPERATIONAL_FAILURE if errors else SUCCESS


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
        }
        if _flag(args, "json"):
            write_json(payload)
        else:
            write_line("Dry run: no database migration will be performed.")
            write_key_value("Database", db_path)
        return SUCCESS

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
        write_json({"command": "db migrate", "dry_run": False, "database": str(db_path)})
        return SUCCESS

    write_key_value("Database migrated", db_path)
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


COMMAND_HANDLERS: dict[str, CommandHandler] = {
    "init": cmd_init,
    "start": cmd_init,
    "imbue": cmd_init,
    "checkin": cmd_checkin,
    "import-md": cmd_import_md,
    "codex-pack": cmd_codex_pack,
    "evoke": cmd_codex_pack,
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
    "db": cmd_db_dispatch,
    "plunder": cmd_plunder,
}
