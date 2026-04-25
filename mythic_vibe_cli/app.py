from __future__ import annotations

import argparse

from . import __version__
from .commands import COMMAND_HANDLERS, CommandHandler
from .core.state import PHASES
from .exit_codes import USER_INPUT_ERROR
from .output import configure_output


def add_runtime_options(
    parser: argparse.ArgumentParser,
    *,
    json_output: bool = False,
    dry_run: bool = False,
) -> None:
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("--quiet", action="store_true", help="Suppress non-error text output")
    verbosity.add_argument("--verbose", action="store_true", help="Show extra operational detail when available")
    if json_output:
        parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    if dry_run:
        parser.add_argument("--dry-run", action="store_true", help="Preview the operation without writing files")


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
    add_runtime_options(init_cmd, dry_run=True)

    start = sub.add_parser("start", help="Alias of `init`")
    start.add_argument("--goal", required=True, help="Plain language product goal")
    start.add_argument("--path", default=".", help="Project directory (default: current directory)")
    start.add_argument("--noob", action="store_true", help="Enable beginner-friendly guidance")
    add_runtime_options(start, dry_run=True)

    checkin = sub.add_parser("checkin", help="Log a Mythic phase update and advance tracking")
    checkin.add_argument("--phase", required=True, choices=PHASES, help="Current Mythic phase")
    checkin.add_argument("--update", required=True, help="Short progress update")
    checkin.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(checkin, dry_run=True)

    status = sub.add_parser("status", help="Show current Mythic progress summary")
    status.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(status, json_output=True)

    import_md = sub.add_parser("import-md", help="Import all Markdown files from Mythic Engineering repo")
    import_md.add_argument("--path", default=".", help="Project directory (default: current directory)")
    import_md.add_argument(
        "--target",
        default="docs/mythic_source",
        help="Target folder inside project for imported files (default: docs/mythic_source)",
    )
    add_runtime_options(import_md, dry_run=True)

    codex_pack = sub.add_parser(
        "codex-pack",
        help="Generate a copy/paste-ready prompt packet for ChatGPT Plus/Codex users",
    )
    codex_pack.add_argument("--task", required=True, help="Specific coding task for Codex")
    codex_pack.add_argument("--phase", required=True, choices=PHASES, help="Current Mythic phase")
    codex_pack.add_argument("--audience", default="beginner", help="Audience level: beginner/intermediate/advanced")
    codex_pack.add_argument("--path", default=".", help="Project directory (default: current directory)")
    codex_pack.add_argument("--out", default=None, help="Output file path (default: <project>/mythic/codex_prompt.md)")
    add_runtime_options(codex_pack, json_output=True, dry_run=True)

    codex_log = sub.add_parser(
        "codex-log",
        help="Record a check-in update after receiving a response from ChatGPT/Codex",
    )
    codex_log.add_argument("--phase", required=True, choices=PHASES, help="Current Mythic phase")
    codex_log.add_argument("--response", required=True, help="One-line summary from Codex response")
    codex_log.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(codex_log, dry_run=True)

    sync = sub.add_parser("sync", help="Sync Mythic Engineering method notes from GitHub")
    add_runtime_options(sync, dry_run=True)
    method = sub.add_parser("method", help="Print active Mythic method notes")
    add_runtime_options(method)

    doctor = sub.add_parser("doctor", help="Validate Mythic project structure and status")
    doctor.add_argument("--path", default=".", help="Project directory (default: current directory)")
    doctor.add_argument(
        "--repo-boundary",
        action="store_true",
        help="Validate active runtime boundary docs and forbidden dormant-island imports",
    )
    add_runtime_options(doctor, json_output=True)

    # Mythic ritual aliases from design doc.
    imbue = sub.add_parser("imbue", help="Initialize project vision and Mythic scaffolding")
    imbue.add_argument("--goal", required=True, help="Plain language product goal")
    imbue.add_argument("--path", default=".", help="Project directory (default: current directory)")
    imbue.add_argument("--noob", action="store_true", help="Enable beginner-friendly guidance")
    add_runtime_options(imbue, dry_run=True)

    evoke = sub.add_parser("evoke", help="Generate a Codex packet from an architecture-aware prompt")
    evoke.add_argument("--task", required=True, help="Specific coding task for Codex")
    evoke.add_argument("--phase", default="plan", choices=PHASES, help="Current Mythic phase (default: plan)")
    evoke.add_argument("--audience", default="beginner", help="Audience level: beginner/intermediate/advanced")
    evoke.add_argument("--path", default=".", help="Project directory (default: current directory)")
    evoke.add_argument("--out", default=None, help="Output file path (default: <project>/mythic/codex_prompt.md)")
    add_runtime_options(evoke, json_output=True, dry_run=True)

    scry = sub.add_parser("scry", help="Analyze project health and diagnostics")
    scry.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(scry, json_output=True)

    weave = sub.add_parser("weave", help="Record documentation synchronization checkpoint")
    weave.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(weave, dry_run=True)

    prune = sub.add_parser("prune", help="Suggest dead-code pruning workflow")
    prune.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(prune)

    heal = sub.add_parser("heal", help="Guide a test-healing workflow")
    heal.add_argument("--path", default=".", help="Project directory (default: current directory)")
    heal.add_argument("--failing-test", default="", help="Optional failing test identifier")
    add_runtime_options(heal)

    oath = sub.add_parser("oath", help="Display responsible AI usage oath")
    oath.add_argument("--yes", action="store_true", help="Echo acceptance message after displaying the oath")
    add_runtime_options(oath)

    grimoire = sub.add_parser("grimoire", help="Manage plugins")
    add_runtime_options(grimoire)
    grimoire_sub = grimoire.add_subparsers(dest="grimoire_command", required=True)
    grimoire_add = grimoire_sub.add_parser("add", help="Register a plugin entrypoint string")
    grimoire_add.add_argument("plugin", help="Plugin entrypoint, e.g. package.module:Plugin")
    grimoire_add.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(grimoire_add, json_output=True, dry_run=True)
    grimoire_list = grimoire_sub.add_parser("list", help="List registered plugins")
    grimoire_list.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(grimoire_list, json_output=True)

    config = sub.add_parser("config", help="Show or manage configuration values")
    config.add_argument("--path", default=".", help="Project directory used for local overrides")
    add_runtime_options(config, json_output=True)
    config_sub = config.add_subparsers(dest="config_command", required=False)
    config_set = config_sub.add_parser("set", help="Set a dotted configuration value")
    config_set.add_argument("key", help="Dotted key, e.g. core.default_model")
    config_set.add_argument("value", help="String value")
    config_set.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(config_set, json_output=True, dry_run=True)

    state = sub.add_parser("state", help="Inspect and validate Mythic project state")
    state_sub = state.add_subparsers(dest="state_command", required=True)
    state_show = state_sub.add_parser("show", help="Show schema-versioned Mythic project state")
    state_show.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(state_show, json_output=True)
    state_validate = state_sub.add_parser("validate", help="Validate mythic/status.json against the state contract")
    state_validate.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(state_validate, json_output=True)

    db = sub.add_parser("db", help="Database maintenance tasks")
    add_runtime_options(db)
    db_sub = db.add_subparsers(dest="db_command", required=True)
    db_migrate = db_sub.add_parser("migrate", help="Create/upgrade local weave database")
    db_migrate.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(db_migrate, json_output=True, dry_run=True)

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
    add_runtime_options(plunder, json_output=True, dry_run=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_output(quiet=getattr(args, "quiet", False), verbose=getattr(args, "verbose", False))

    handler: CommandHandler | None = COMMAND_HANDLERS.get(args.command)
    if handler:
        try:
            return handler(args)
        finally:
            configure_output()

    parser.error("Unknown command")
    return USER_INPUT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
