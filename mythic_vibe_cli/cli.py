from __future__ import annotations

import argparse
import base64
import json
import sqlite3
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request
import os

from . import __version__
from .codex_bridge import CodexBridge, CodexPacketRequest
from .config import ConfigStore
from .mythic_data import MethodStore
from .workflow import MythicRunConfig, MythicWorkflow, PHASES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mythic-vibe",
        description="Mythic Engineering-aligned vibe coding CLI",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Initialize Mythic Engineering docs + workflow scaffolding")
    init_cmd.add_argument("--goal", required=True, help="Plain language product goal")
    init_cmd.add_argument("--path", default=".", help="Project directory (default: current directory)")
    init_cmd.add_argument("--noob", action="store_true", help="Enable beginner-friendly guidance")

    start = sub.add_parser("start", help="Alias of `init`")
    start.add_argument("--goal", required=True, help="Plain language product goal")
    start.add_argument("--path", default=".", help="Project directory (default: current directory)")
    start.add_argument("--noob", action="store_true", help="Enable beginner-friendly guidance")

    checkin = sub.add_parser("checkin", help="Log a Mythic phase update and advance tracking")
    checkin.add_argument("--phase", required=True, choices=PHASES, help="Current Mythic phase")
    checkin.add_argument("--update", required=True, help="Short progress update")
    checkin.add_argument("--path", default=".", help="Project directory (default: current directory)")

    status = sub.add_parser("status", help="Show current Mythic progress summary")
    status.add_argument("--path", default=".", help="Project directory (default: current directory)")

    import_md = sub.add_parser("import-md", help="Import all Markdown files from Mythic Engineering repo")
    import_md.add_argument("--path", default=".", help="Project directory (default: current directory)")
    import_md.add_argument(
        "--target",
        default="docs/mythic_source",
        help="Target folder inside project for imported files (default: docs/mythic_source)",
    )

    codex_pack = sub.add_parser(
        "codex-pack",
        help="Generate a copy/paste-ready prompt packet for ChatGPT Plus/Codex users",
    )
    codex_pack.add_argument("--task", required=True, help="Specific coding task for Codex")
    codex_pack.add_argument("--phase", required=True, choices=PHASES, help="Current Mythic phase")
    codex_pack.add_argument("--audience", default="beginner", help="Audience level: beginner/intermediate/advanced")
    codex_pack.add_argument("--path", default=".", help="Project directory (default: current directory)")
    codex_pack.add_argument("--out", default=None, help="Output file path (default: <project>/mythic/codex_prompt.md)")

    codex_log = sub.add_parser(
        "codex-log",
        help="Record a check-in update after receiving a response from ChatGPT/Codex",
    )
    codex_log.add_argument("--phase", required=True, choices=PHASES, help="Current Mythic phase")
    codex_log.add_argument("--response", required=True, help="One-line summary from Codex response")
    codex_log.add_argument("--path", default=".", help="Project directory (default: current directory)")

    sub.add_parser("sync", help="Sync Mythic Engineering method notes from GitHub")
    sub.add_parser("method", help="Print active Mythic method notes")


    doctor = sub.add_parser("doctor", help="Validate Mythic project structure and status")
    doctor.add_argument("--path", default=".", help="Project directory (default: current directory)")

    # Mythic ritual aliases from design doc.
    imbue = sub.add_parser("imbue", help="Initialize project vision and Mythic scaffolding")
    imbue.add_argument("--goal", required=True, help="Plain language product goal")
    imbue.add_argument("--path", default=".", help="Project directory (default: current directory)")
    imbue.add_argument("--noob", action="store_true", help="Enable beginner-friendly guidance")

    evoke = sub.add_parser("evoke", help="Generate a Codex packet from an architecture-aware prompt")
    evoke.add_argument("--task", required=True, help="Specific coding task for Codex")
    evoke.add_argument("--phase", default="plan", choices=PHASES, help="Current Mythic phase (default: plan)")
    evoke.add_argument("--audience", default="beginner", help="Audience level: beginner/intermediate/advanced")
    evoke.add_argument("--path", default=".", help="Project directory (default: current directory)")
    evoke.add_argument("--out", default=None, help="Output file path (default: <project>/mythic/codex_prompt.md)")

    scry = sub.add_parser("scry", help="Analyze project health and diagnostics")
    scry.add_argument("--path", default=".", help="Project directory (default: current directory)")

    weave = sub.add_parser("weave", help="Record documentation synchronization checkpoint")
    weave.add_argument("--path", default=".", help="Project directory (default: current directory)")

    prune = sub.add_parser("prune", help="Suggest dead-code pruning workflow")
    prune.add_argument("--path", default=".", help="Project directory (default: current directory)")

    heal = sub.add_parser("heal", help="Guide a test-healing workflow")
    heal.add_argument("--path", default=".", help="Project directory (default: current directory)")
    heal.add_argument("--failing-test", default="", help="Optional failing test identifier")

    oath = sub.add_parser("oath", help="Display responsible AI usage oath")
    oath.add_argument("--yes", action="store_true", help="Echo acceptance message after displaying the oath")

    grimoire = sub.add_parser("grimoire", help="Manage plugins")
    grimoire_sub = grimoire.add_subparsers(dest="grimoire_command", required=True)
    grimoire_add = grimoire_sub.add_parser("add", help="Register a plugin entrypoint string")
    grimoire_add.add_argument("plugin", help="Plugin entrypoint, e.g. package.module:Plugin")
    grimoire_add.add_argument("--path", default=".", help="Project directory (default: current directory)")
    grimoire_list = grimoire_sub.add_parser("list", help="List registered plugins")
    grimoire_list.add_argument("--path", default=".", help="Project directory (default: current directory)")

    config = sub.add_parser("config", help="Show or manage configuration values")
    config.add_argument("--path", default=".", help="Project directory used for local overrides")
    config_sub = config.add_subparsers(dest="config_command", required=False)
    config_set = config_sub.add_parser("set", help="Set a dotted configuration value")
    config_set.add_argument("key", help="Dotted key, e.g. core.default_model")
    config_set.add_argument("value", help="String value")
    config_set.add_argument("--path", default=".", help="Project directory (default: current directory)")

    db = sub.add_parser("db", help="Database maintenance tasks")
    db_sub = db.add_subparsers(dest="db_command", required=True)
    db_migrate = db_sub.add_parser("migrate", help="Create/upgrade local weave database")
    db_migrate.add_argument("--path", default=".", help="Project directory (default: current directory)")

    plunder = sub.add_parser(
        "plunder",
        help="Copy a single file from a GitHub repo into the local project (one file per run)",
    )
    plunder.add_argument("--repo", required=True, help="GitHub repo in owner/name form")
    plunder.add_argument("--source", required=True, help="Source file path in the repo")
    plunder.add_argument("--dest", required=True, help="Destination path in this project")
    plunder.add_argument("--ref", default="main", help="Branch/tag/SHA in source repo (default: main)")
    plunder.add_argument(
        "--token-env",
        default="GITHUB_TOKEN",
        help="Environment variable holding a GitHub token (default: GITHUB_TOKEN)",
    )

    return parser


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    root.mkdir(parents=True, exist_ok=True)

    store = MethodStore()
    method = store.load()
    workflow = MythicWorkflow(root)
    created = workflow.init_project(
        MythicRunConfig(goal=args.goal, noob_mode=args.noob),
        method_source=method.source,
    )

    print("Mythic Engineering project scaffolding ready.")
    print(f"Method source: {method.source}")
    if created:
        print("Created files:")
        for path in created:
            print(f"- {path}")
    else:
        print("No new files were created (scaffold already existed).")

    print("Next step: run `mythic-vibe import-md` to copy the full Mythic markdown corpus locally.")
    return 0


def cmd_checkin(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    workflow = MythicWorkflow(root)

    try:
        status_file, devlog_file = workflow.check_in(phase=args.phase, update=args.update)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print("Mythic check-in recorded.")
    print(f"- Status: {status_file}")
    print(f"- Devlog: {devlog_file}")
    print("- Summary:")
    print(workflow.status_summary())
    return 0


def cmd_import_md(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    target = root / args.target
    store = MethodStore()
    try:
        written = store.import_all_markdown(target)
    except Exception as exc:  # noqa: BLE001 - surface remote import issues in CLI.
        print(f"Import failed: {exc}", file=sys.stderr)
        return 1

    print("Imported Mythic Engineering markdown files.")
    print(f"- Destination: {target}")
    print(f"- Files imported: {len(written)}")
    print(f"- Index: {target / '_import_index.json'}")
    return 0


def cmd_codex_pack(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    bridge = CodexBridge(root)
    packet = bridge.create_packet(
        request=CodexPacketRequest(task=args.task, phase=args.phase, audience=args.audience),
        out_file=Path(args.out).resolve() if args.out else None,
    )
    print("Codex packet generated.")
    print(f"- File: {packet}")
    print("Paste the 'Prompt To Paste' section into ChatGPT/Codex.")
    return 0


def cmd_codex_log(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    workflow = MythicWorkflow(root)
    try:
        status_file, devlog_file = workflow.check_in(phase=args.phase, update=args.response)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print("Codex response logged into Mythic workflow.")
    print(f"- Status: {status_file}")
    print(f"- Devlog: {devlog_file}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    workflow = MythicWorkflow(root)
    print(workflow.status_summary())
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    loaded = ConfigStore(root).load()

    print("Resolved mythic-vibe configuration")
    print(f"- Project path: {root}")
    if loaded.sources:
        print("- Loaded sources (low -> high precedence):")
        for src in loaded.sources:
            print(f"  - {src}")
    else:
        print("- Loaded sources: none (using defaults + env vars)")

    print("- Effective values:")
    print(f"  - codex.excerpt_limit: {loaded.config.excerpt_limit}")
    print(f"  - codex.packet_char_budget: {loaded.config.packet_char_budget}")
    print(f"  - codex.auto_compact: {str(loaded.config.auto_compact).lower()}")
    return 0


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
    errors, warnings = workflow.doctor()

    print("Mythic project diagnostics")
    print(f"- Path: {root}")

    if errors:
        print("- Errors:")
        for item in errors:
            print(f"  - {item}")
    else:
        print("- Errors: none")

    if warnings:
        print("- Warnings:")
        for item in warnings:
            print(f"  - {item}")
    else:
        print("- Warnings: none")

    return 1 if errors else 0


def cmd_sync() -> int:
    store = MethodStore()
    try:
        bundle = store.sync()
    except Exception as exc:  # noqa: BLE001 - CLI should show actionable message and continue.
        print(f"Sync failed: {exc}", file=sys.stderr)
        return 1

    print("Synced Mythic method notes.")
    print(f"Source: {bundle.source}")
    print(f"Cache: {store.cache_file}")
    return 0


def cmd_method() -> int:
    store = MethodStore()
    bundle = store.load()
    print(f"Method source: {bundle.source}")
    print("=" * 72)
    print(bundle.content)
    return 0


def cmd_oath(args: argparse.Namespace) -> int:
    oath = "I understand that AI may generate incorrect or insecure code. I will review all changes before committing to the Sacred Grove."
    print(oath)
    if args.yes:
        print("Oath accepted.")
    return 0


def cmd_grimoire(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    store_file = root / "mythic" / "plugins.json"
    store_file.parent.mkdir(parents=True, exist_ok=True)
    if store_file.exists():
        import json

        data = json.loads(store_file.read_text(encoding="utf-8"))
    else:
        data = {"plugins": []}

    if args.grimoire_command == "add":
        if args.plugin not in data["plugins"]:
            data["plugins"].append(args.plugin)
            import json

            store_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            print(f"Registered plugin: {args.plugin}")
        else:
            print(f"Plugin already registered: {args.plugin}")
        print(f"Registry: {store_file}")
        return 0

    plugins = data.get("plugins", [])
    if not plugins:
        print("No plugins registered.")
        return 0
    print("Registered plugins:")
    for plugin in plugins:
        print(f"- {plugin}")
    return 0


def cmd_config_set(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    config_file = root / "mythic" / "config.toml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with config_file.open("a", encoding="utf-8") as fh:
        fh.write(f'{args.key} = "{args.value}"\n')
    print(f"Updated config: {config_file}")
    print(f"- {args.key} = {args.value}")
    return 0


def cmd_plunder(args: argparse.Namespace) -> int:
    token = os.getenv(args.token_env, "").strip()
    if not token:
        print(
            f"Missing token. Set {args.token_env} and retry (repo access is required).",
            file=sys.stderr,
        )
        return 2

    try:
        text = _github_get_file(args.repo, args.source, args.ref, token)
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        print(f"GitHub API error ({exc.code}): {message}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Plunder failed: {exc}", file=sys.stderr)
        return 1

    out_path = Path(args.dest).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8")
    print("Plunder complete.")
    print(f"- Repo: {args.repo}@{args.ref}")
    print(f"- Source: {args.source}")
    print(f"- Destination: {out_path}")
    return 0


def cmd_db_migrate(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    db_path = root / "mythic" / "weave.db"
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
    print(f"Database migrated: {db_path}")
    return 0


def cmd_weave(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    workflow = MythicWorkflow(root)
    try:
        status_file, devlog_file = workflow.check_in(phase="reflect", update="Ran mythic weave doc synchronization checkpoint.")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print("Weave synchronization checkpoint recorded.")
    print(f"- Status: {status_file}")
    print(f"- Devlog: {devlog_file}")
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    print("Prune ritual scaffold ready.")
    print(f"- Project: {root}")
    print("Next: run your linter/dead-code tool and remove one safe item at a time.")
    return 0


def cmd_heal(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    print("Heal ritual scaffold ready.")
    print(f"- Project: {root}")
    if args.failing_test:
        print(f"- Target failing test: {args.failing_test}")
    print("Next: reproduce the failure, patch minimally, then rerun tests.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in {"init", "start", "imbue"}:
        return cmd_init(args)
    if args.command == "checkin":
        return cmd_checkin(args)
    if args.command == "import-md":
        return cmd_import_md(args)
    if args.command == "codex-pack":
        return cmd_codex_pack(args)
    if args.command == "codex-log":
        return cmd_codex_log(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "sync":
        return cmd_sync()
    if args.command == "method":
        return cmd_method()
    if args.command == "doctor":
        return cmd_doctor(args)
    if args.command == "evoke":
        return cmd_codex_pack(args)
    if args.command == "scry":
        return cmd_doctor(args)
    if args.command == "weave":
        return cmd_weave(args)
    if args.command == "prune":
        return cmd_prune(args)
    if args.command == "heal":
        return cmd_heal(args)
    if args.command == "oath":
        return cmd_oath(args)
    if args.command == "grimoire":
        return cmd_grimoire(args)
    if args.command == "config":
        if args.config_command == "set":
            return cmd_config_set(args)
        return cmd_config(args)
    if args.command == "db":
        return cmd_db_migrate(args)
    if args.command == "plunder":
        return cmd_plunder(args)

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
