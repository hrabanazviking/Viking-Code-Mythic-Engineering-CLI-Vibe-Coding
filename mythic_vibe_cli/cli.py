from __future__ import annotations

import argparse
from pathlib import Path
import sys

from . import __version__
from .codex_bridge import CodexBridge, CodexPacketRequest
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command in {"init", "start"}:
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

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
