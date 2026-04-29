from __future__ import annotations

import argparse
from textwrap import dedent

from . import __version__
from .ai.registry import ProviderRegistry
from .commands import COMMAND_HANDLERS, CommandHandler
from .codex_bridge import PACKET_OUTPUT_FORMATS, PACKET_ROLES
from .core.state import PHASES
from .exit_codes import USER_INPUT_ERROR
from .output import configure_output
from .plugins.api import PLUGIN_HOOKS
from .ux import artifact_names, phase_names
from .workflow_engine import DEFAULT_ROLE_SEQUENCE


def _epilog(text: str) -> str:
    return dedent(text).strip()


def _example_parser_kwargs(epilog: str) -> dict[str, object]:
    return {
        "formatter_class": argparse.RawDescriptionHelpFormatter,
        "epilog": _epilog(epilog),
    }


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

    init_cmd = sub.add_parser(
        "init",
        help="Initialize Mythic Engineering docs + workflow scaffolding",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe init --goal "Build a calm CLI" --noob
              mythic-vibe init --goal "Refactor checkout flow" --path ./app --dry-run
            """
        ),
    )
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

    examples = sub.add_parser("examples", help="Show copy-paste command examples")
    add_runtime_options(examples, json_output=True)

    guide = sub.add_parser("guide", help="Show the compact Mythic Vibe operator guide")
    add_runtime_options(guide, json_output=True)

    next_cmd = sub.add_parser(
        "next",
        help="Show the next recommended phase and command",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe next --path .
              mythic-vibe next --path . --json

            Notes:
              Failed verification comes first, then latest handoff guidance, then phase guidance.
            """
        ),
    )
    next_cmd.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(next_cmd, json_output=True)

    explain = sub.add_parser("explain", help="Explain phases and artifacts")
    add_runtime_options(explain, json_output=True)
    explain_sub = explain.add_subparsers(dest="explain_command", required=True)
    explain_phase = explain_sub.add_parser("phase", help="Explain one Mythic phase")
    explain_phase.add_argument("phase", choices=phase_names(), help="Phase to explain")
    add_runtime_options(explain_phase, json_output=True)
    explain_artifact = explain_sub.add_parser("artifact", help="Explain one generated artifact")
    explain_artifact.add_argument("artifact", choices=artifact_names(), help="Artifact to explain")
    add_runtime_options(explain_artifact, json_output=True)

    tutorial = sub.add_parser("tutorial", help="Show a first full workflow tutorial")
    add_runtime_options(tutorial, json_output=True)

    completion = sub.add_parser("completion", help="Print shell completion script")
    completion.add_argument("--shell", required=True, choices=["bash", "zsh", "powershell"], help="Shell to generate completions for")
    add_runtime_options(completion, json_output=True)

    reflect = sub.add_parser(
        "reflect",
        help="Create a reflection handoff for the current session",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe reflect --summary "Added packet diff tests"
              mythic-vibe reflect --summary "Verified release gates" --next-step "Check GitHub CI"
              mythic-vibe reflect --summary "Docs updated" --dry-run
            """
        ),
    )
    reflect.add_argument("--path", default=".", help="Project directory (default: current directory)")
    reflect.add_argument("--summary", required=True, help="Short summary of the current work session")
    reflect.add_argument("--next-step", default="", help="Optional next action to emphasize")
    reflect.add_argument("--note", default="", help="Optional note to preserve in the handoff")
    add_runtime_options(reflect, json_output=True, dry_run=True)

    scan = sub.add_parser("scan", help="Build a local project index for AI context")
    scan.add_argument("--path", default=".", help="Project directory (default: current directory)")
    scan.add_argument("--changed", action="store_true", help="Restrict the scan to changed files")
    scan.add_argument("--docs", action="store_true", help="Restrict the scan to documentation files")
    scan.add_argument(
        "--include",
        action="append",
        default=[],
        help="Glob pattern to force-include paths in the scan",
    )
    scan.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Glob pattern to exclude paths from the scan",
    )
    add_runtime_options(scan, json_output=True, dry_run=True)

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
    codex_pack.add_argument("--role", default="Forge Worker", choices=PACKET_ROLES, help="Packet role")
    codex_pack.add_argument("--format", default="markdown", choices=PACKET_OUTPUT_FORMATS, help="Packet output format")
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
    method = sub.add_parser("method", help="Inspect and sync the active Mythic Engineering method profile")
    add_runtime_options(method, json_output=True, dry_run=True)
    method_sub = method.add_subparsers(dest="method_command", required=False)
    method_status = method_sub.add_parser("status", help="Show active method source, profile, and version")
    method_status.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(method_status, json_output=True)
    method_show = method_sub.add_parser("show", help="Print active Mythic method notes")
    method_show.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(method_show, json_output=True)
    method_sync = method_sub.add_parser("sync", help="Sync Mythic Engineering method notes into the local cache")
    method_sync.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(method_sync, json_output=True, dry_run=True)
    method_diff = method_sub.add_parser("diff", help="Compare an imported method corpus against its manifest")
    method_diff.add_argument("--path", default=".", help="Project directory (default: current directory)")
    method_diff.add_argument(
        "--target",
        default="docs/mythic_source",
        help="Imported method corpus folder inside project (default: docs/mythic_source)",
    )
    add_runtime_options(method_diff, json_output=True)
    method_pin = method_sub.add_parser("pin", help="Pin a clean imported method corpus for reproducibility")
    method_pin.add_argument("--path", default=".", help="Project directory (default: current directory)")
    method_pin.add_argument(
        "--target",
        default="docs/mythic_source",
        help="Imported method corpus folder inside project (default: docs/mythic_source)",
    )
    method_pin.add_argument("--note", default="", help="Optional note to store with the method pin")
    add_runtime_options(method_pin, json_output=True, dry_run=True)

    doctor = sub.add_parser(
        "doctor",
        help="Validate Mythic project structure and status",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe doctor --path .
              mythic-vibe doctor --path . --repo-boundary
              mythic-vibe doctor --path . --json
            """
        ),
    )
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
    evoke.add_argument("--role", default="Forge Worker", choices=PACKET_ROLES, help="Packet role")
    evoke.add_argument("--format", default="markdown", choices=PACKET_OUTPUT_FORMATS, help="Packet output format")
    evoke.add_argument("--path", default=".", help="Project directory (default: current directory)")
    evoke.add_argument("--out", default=None, help="Output file path (default: <project>/mythic/codex_prompt.md)")
    add_runtime_options(evoke, json_output=True, dry_run=True)

    packet = sub.add_parser("packet", help="Create, show, or list reusable packet artifacts")
    add_runtime_options(packet, json_output=True, dry_run=True)
    packet_sub = packet.add_subparsers(dest="packet_command", required=True)
    packet_create = packet_sub.add_parser(
        "create",
        help="Create a reusable packet artifact",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe packet create --task "Implement login audit" --phase build
              mythic-vibe packet create --task "Review plugin hooks" --phase verify --role Auditor
              mythic-vibe packet create --task "Map data flow" --phase architecture --format json
            """
        ),
    )
    packet_create.add_argument("--task", required=True, help="Specific coding task for the packet")
    packet_create.add_argument("--phase", required=True, choices=PHASES, help="Current Mythic phase")
    packet_create.add_argument("--audience", default="beginner", help="Audience level: beginner/intermediate/advanced")
    packet_create.add_argument("--role", default="Forge Worker", choices=PACKET_ROLES, help="Packet role")
    packet_create.add_argument("--format", default="markdown", choices=PACKET_OUTPUT_FORMATS, help="Packet output format")
    packet_create.add_argument("--path", default=".", help="Project directory (default: current directory)")
    packet_create.add_argument("--out", default=None, help="Optional output file path")
    add_runtime_options(packet_create, json_output=True, dry_run=True)
    packet_show = packet_sub.add_parser("show", help="Show a stored packet by packet ID or workflow+step")
    packet_show.add_argument("--path", default=".", help="Project directory (default: current directory)")
    packet_show.add_argument("--packet-id", default="", help="Packet ID to show (default: latest)")
    packet_show.add_argument("--workflow", default="", help="Workflow ID stamped on the packet (requires --step)")
    packet_show.add_argument("--step", default="", help="Workflow step ID stamped on the packet (requires --workflow or --latest-workflow)")
    packet_show.add_argument("--latest-workflow", action="store_true", help="Resolve --workflow from mythic/workflow_plan.json (requires --step)")
    add_runtime_options(packet_show, json_output=True)
    packet_list = packet_sub.add_parser("list", help="List stored packet records")
    packet_list.add_argument("--path", default=".", help="Project directory (default: current directory)")
    packet_list.add_argument("--workflow", default="", help="Filter to packets stamped with this workflow ID")
    packet_list.add_argument("--step", default="", help="Filter to packets stamped with this workflow step ID (requires --workflow or --latest-workflow)")
    packet_list.add_argument("--latest-workflow", action="store_true", help="Resolve --workflow from mythic/workflow_plan.json")
    add_runtime_options(packet_list, json_output=True)
    packet_ingest = packet_sub.add_parser("ingest", help="Ingest a packet artifact into the local packet store")
    packet_ingest.add_argument("--path", default=".", help="Project directory (default: current directory)")
    packet_ingest.add_argument("--source", required=True, help="Path to a packet markdown or metadata artifact")
    add_runtime_options(packet_ingest, json_output=True, dry_run=True)
    packet_diff = packet_sub.add_parser("diff", help="Diff two stored packet artifacts")
    packet_diff.add_argument("--path", default=".", help="Project directory (default: current directory)")
    packet_diff.add_argument("--left", required=True, help="Left packet reference: PKT-... ID, WF-<id>:<step_id>, or bare step-NN with --latest-workflow")
    packet_diff.add_argument("--right", required=True, help="Right packet reference: PKT-... ID, WF-<id>:<step_id>, or bare step-NN with --latest-workflow")
    packet_diff.add_argument("--latest-workflow", action="store_true", help="Allow bare step-NN refs to resolve against mythic/workflow_plan.json")
    add_runtime_options(packet_diff, json_output=True)

    workflow = sub.add_parser(
        "workflow",
        help="Plan role-based Mythic workflow orchestration",
    )
    add_runtime_options(workflow, json_output=True, dry_run=True)
    workflow_sub = workflow.add_subparsers(dest="workflow_command", required=True)
    workflow_plan = workflow_sub.add_parser(
        "plan",
        help="Write a deterministic role orchestration plan",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe workflow plan --task "Implement the next feature"
              mythic-vibe workflow plan --task "Implement the next feature" --packets
              mythic-vibe workflow plan --task "Review architecture drift" --role Skald --role Architect --role Auditor
              mythic-vibe workflow plan --task "Preview only" --dry-run --json
              mythic-vibe workflow run --dry-run --json

            Notes:
              Defaults to Skald -> Architect -> Cartographer -> Forge Worker -> Auditor -> Scribe.
            """
        ),
    )
    workflow_plan.add_argument("--task", required=True, help="Task or outcome to orchestrate")
    workflow_plan.add_argument("--path", default=".", help="Project directory (default: current directory)")
    workflow_plan.add_argument("--out", default="", help="Optional output file path (default: mythic/workflow_plan.json)")
    workflow_plan.add_argument("--audience", default="advanced", help="Packet audience level when exporting packet requests")
    workflow_plan.add_argument("--format", default="markdown", choices=PACKET_OUTPUT_FORMATS, help="Packet output format for exported/generated packet requests")
    workflow_plan.add_argument("--packets", action="store_true", help="Create one packet artifact per workflow step")
    workflow_plan.add_argument(
        "--role",
        action="append",
        default=[],
        choices=list(DEFAULT_ROLE_SEQUENCE) + ["Debugger", "Refactorer"],
        help="Role to include in order; repeat to customize the sequence",
    )
    add_runtime_options(workflow_plan, json_output=True, dry_run=True)
    workflow_run = workflow_sub.add_parser(
        "run",
        help="Preview ordered workflow execution without invoking providers",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe workflow run --dry-run
              mythic-vibe workflow run --dry-run --packets-only
              mythic-vibe workflow packets --json
              mythic-vibe workflow run --dry-run --task "Preview a new task" --role Skald --role Auditor
              mythic-vibe workflow run --dry-run --plan mythic/workflow_plan.json --json

            Notes:
              Real provider execution is intentionally blocked until orchestration safety gates are added.
            """
        ),
    )
    workflow_run.add_argument("--path", default=".", help="Project directory (default: current directory)")
    workflow_run.add_argument("--plan", default="", help="Plan file to preview (default: mythic/workflow_plan.json)")
    workflow_run.add_argument("--task", default="", help="Optional task to build an in-memory preview plan")
    workflow_run.add_argument("--audience", default="advanced", help="Expected packet audience when validating workflow packets")
    workflow_run.add_argument("--format", default="markdown", choices=PACKET_OUTPUT_FORMATS, help="Expected packet format when validating workflow packets")
    workflow_run.add_argument("--packets-only", action="store_true", help="Validate required packets without executing providers")
    workflow_run.add_argument(
        "--role",
        action="append",
        default=[],
        choices=list(DEFAULT_ROLE_SEQUENCE) + ["Debugger", "Refactorer"],
        help="Role to include in order when --task is supplied; repeat to customize the sequence",
    )
    add_runtime_options(workflow_run, json_output=True, dry_run=True)
    workflow_packets = workflow_sub.add_parser(
        "packets",
        help="List packet readiness for a workflow plan",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe workflow packets
              mythic-vibe workflow packets --missing-only
              mythic-vibe workflow packets --task "Preview a new task" --role Skald --role Auditor --json

            Notes:
              This command inspects stored packet metadata and does not execute providers.
            """
        ),
    )
    workflow_packets.add_argument("--path", default=".", help="Project directory (default: current directory)")
    workflow_packets.add_argument("--plan", default="", help="Plan file to inspect (default: mythic/workflow_plan.json)")
    workflow_packets.add_argument("--task", default="", help="Optional task to build an in-memory packet-readiness view")
    workflow_packets.add_argument("--audience", default="advanced", help="Expected packet audience")
    workflow_packets.add_argument("--format", default="markdown", choices=PACKET_OUTPUT_FORMATS, help="Expected packet output format")
    workflow_packets.add_argument("--missing-only", action="store_true", help="Only show missing workflow packets")
    workflow_packets.add_argument(
        "--role",
        action="append",
        default=[],
        choices=list(DEFAULT_ROLE_SEQUENCE) + ["Debugger", "Refactorer"],
        help="Role to include in order when --task is supplied; repeat to customize the sequence",
    )
    add_runtime_options(workflow_packets, json_output=True)

    handoff = sub.add_parser("handoff", help="Create, inspect, or list session handoff records")
    add_runtime_options(handoff, json_output=True, dry_run=True)
    handoff_sub = handoff.add_subparsers(dest="handoff_command", required=True)
    handoff_create = handoff_sub.add_parser("create", help="Create a session handoff record")
    handoff_create.add_argument("--path", default=".", help="Project directory (default: current directory)")
    handoff_create.add_argument("--summary", default="", help="Optional summary of the current work session")
    handoff_create.add_argument("--next-step", default="", help="Optional next action to emphasize")
    handoff_create.add_argument("--note", default="", help="Optional note to preserve in the handoff")
    add_runtime_options(handoff_create, json_output=True, dry_run=True)
    handoff_show = handoff_sub.add_parser("show", help="Show a stored handoff record")
    handoff_show.add_argument("--path", default=".", help="Project directory (default: current directory)")
    handoff_show.add_argument("--handoff-id", default="", help="Handoff ID to show (default: latest)")
    add_runtime_options(handoff_show, json_output=True)
    handoff_latest = handoff_sub.add_parser("latest", help="Show the latest handoff record")
    handoff_latest.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(handoff_latest, json_output=True)

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

    resume = sub.add_parser(
        "resume",
        help="Summarize the latest handoff and suggest the next step",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe resume --path .
              mythic-vibe resume --path . --json

            Notes:
              Use this at the start of a session to recover the latest handoff.
            """
        ),
    )
    resume.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(resume, json_output=True)

    oath = sub.add_parser("oath", help="Display responsible AI usage oath")
    oath.add_argument("--yes", action="store_true", help="Echo acceptance message after displaying the oath")
    add_runtime_options(oath)

    grimoire = sub.add_parser("grimoire", help="Manage plugins")
    add_runtime_options(grimoire)
    grimoire_sub = grimoire.add_subparsers(dest="grimoire_command", required=True)
    grimoire_add = grimoire_sub.add_parser("add", help="Register a plugin entrypoint string")
    grimoire_add.add_argument("plugin", help="Plugin entrypoint, e.g. package.module:Plugin")
    grimoire_add.add_argument("--path", default=".", help="Project directory (default: current directory)")
    grimoire_add.add_argument("--hook", action="append", default=[], choices=PLUGIN_HOOKS, help="Hook implemented by this plugin")
    grimoire_add.add_argument("--version", default="unknown", help="Plugin version label")
    add_runtime_options(grimoire_add, json_output=True, dry_run=True)
    grimoire_list = grimoire_sub.add_parser("list", help="List registered plugins")
    grimoire_list.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(grimoire_list, json_output=True)

    plugin = sub.add_parser("plugin", help="Inspect and control registered plugins")
    add_runtime_options(plugin, json_output=True)
    plugin_sub = plugin.add_subparsers(dest="plugin_command", required=True)
    plugin_list = plugin_sub.add_parser("list", help="List plugin health without importing plugin code")
    plugin_list.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plugin_list.add_argument("--all", action="store_true", help="Include disabled plugins")
    add_runtime_options(plugin_list, json_output=True)
    plugin_inspect = plugin_sub.add_parser("inspect", help="Inspect one plugin entrypoint and hook declarations")
    plugin_inspect.add_argument("plugin", help="Plugin entrypoint, e.g. package.module:Plugin")
    plugin_inspect.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plugin_inspect.add_argument("--metadata-only", action="store_true", help="Inspect registry metadata without importing plugin code")
    add_runtime_options(plugin_inspect, json_output=True)
    plugin_disable = plugin_sub.add_parser("disable", help="Disable one registered plugin")
    plugin_disable.add_argument("plugin", help="Plugin entrypoint, e.g. package.module:Plugin")
    plugin_disable.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(plugin_disable, json_output=True, dry_run=True)

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
        help="Inspect, plan, fetch, apply, and record lawful single-file reuse",
    )
    plunder.add_argument("--repo", default="", help="Legacy mode: GitHub repo in owner/name form")
    plunder.add_argument("--source", default="", help="Legacy mode: source file path in the repo")
    plunder.add_argument("--dest", default="", help="Legacy mode: destination path in this project")
    plunder.add_argument("--ref", default="main", help="Branch/tag/SHA in source repo (default: main)")
    plunder.add_argument(
        "--token-env",
        default="GITHUB_TOKEN",
        help="Environment variable holding a GitHub token (default: GITHUB_TOKEN)",
    )
    plunder.add_argument("--force", action="store_true", help="Allow overwrite in legacy mode")
    add_runtime_options(plunder, json_output=True, dry_run=True)
    plunder_sub = plunder.add_subparsers(dest="plunder_command", required=False)
    plunder_inspect = plunder_sub.add_parser("inspect", help="Inspect source repo license posture")
    plunder_inspect.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plunder_inspect.add_argument("--repo", required=True, help="GitHub repo in owner/name form")
    plunder_inspect.add_argument("--ref", default="main", help="Branch/tag/SHA in source repo (default: main)")
    plunder_inspect.add_argument("--token-env", default="GITHUB_TOKEN", help="Environment variable holding a GitHub token")
    add_runtime_options(plunder_inspect, json_output=True, dry_run=True)
    plunder_plan = plunder_sub.add_parser("plan", help="Create a license-aware plunder plan")
    plunder_plan.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plunder_plan.add_argument("--repo", required=True, help="GitHub repo in owner/name form")
    plunder_plan.add_argument("--source", required=True, help="Source file path in the repo")
    plunder_plan.add_argument("--dest", required=True, help="Destination path in this project")
    plunder_plan.add_argument("--ref", default="main", help="Branch/tag/SHA in source repo (default: main)")
    plunder_plan.add_argument("--modifications", default="Unmodified import planned.", help="Planned modification notes")
    plunder_plan.add_argument("--token-env", default="GITHUB_TOKEN", help="Environment variable holding a GitHub token")
    add_runtime_options(plunder_plan, json_output=True, dry_run=True)
    plunder_fetch = plunder_sub.add_parser("fetch", help="Fetch a source file into the plunder cache")
    plunder_fetch.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plunder_fetch.add_argument("--repo", required=True, help="GitHub repo in owner/name form")
    plunder_fetch.add_argument("--source", required=True, help="Source file path in the repo")
    plunder_fetch.add_argument("--ref", default="main", help="Branch/tag/SHA in source repo (default: main)")
    plunder_fetch.add_argument("--token-env", default="GITHUB_TOKEN", help="Environment variable holding a GitHub token")
    add_runtime_options(plunder_fetch, json_output=True, dry_run=True)
    plunder_apply = plunder_sub.add_parser("apply", help="Apply a fetched source file from the current plunder plan")
    plunder_apply.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plunder_apply.add_argument("--plan", default="", help="Optional plan path (default: mythic/imports/plunder_plan.json)")
    plunder_apply.add_argument("--modifications", default="", help="Modification notes to record")
    plunder_apply.add_argument("--notice", action="store_true", help="Append a NOTICE entry")
    plunder_apply.add_argument("--force", action="store_true", help="Allow overwrite or force an incompatible license")
    add_runtime_options(plunder_apply, json_output=True, dry_run=True)
    plunder_record = plunder_sub.add_parser("record", help="Record provenance from the current plunder plan")
    plunder_record.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plunder_record.add_argument("--plan", default="", help="Optional plan path (default: mythic/imports/plunder_plan.json)")
    plunder_record.add_argument("--modifications", default="", help="Modification notes to record")
    plunder_record.add_argument("--notice", action="store_true", help="Append a NOTICE entry")
    add_runtime_options(plunder_record, json_output=True, dry_run=True)

    ai = sub.add_parser("ai", help="Manage optional AI provider integrations")
    add_runtime_options(ai, json_output=True, dry_run=True)
    ai_sub = ai.add_subparsers(dest="ai_command", required=True)
    ai_providers = ai_sub.add_parser("providers", help="List available AI providers and config status")
    ai_providers.add_argument("--path", default=".", help="Project directory used for provider logs (default: current directory)")
    add_runtime_options(ai_providers, json_output=True)
    ai_test = ai_sub.add_parser("test", help="Dry-run a provider against a packet payload")
    ai_test.add_argument("--path", default=".", help="Project directory used to resolve packet IDs and logs")
    ai_test.add_argument("--provider", required=True, choices=sorted(ProviderRegistry().providers().keys()))
    ai_test.add_argument("--packet", required=True, help="Packet text or identifier to estimate/run")
    add_runtime_options(ai_test, json_output=True)
    ai_run = ai_sub.add_parser("run", help="Run a provider in explicit provider mode")
    ai_run.add_argument("--path", default=".", help="Project directory used to resolve packet IDs and logs")
    ai_run.add_argument("--provider", required=True, choices=sorted(ProviderRegistry().providers().keys()))
    ai_run.add_argument("--packet", required=True, help="Packet text or identifier to send")
    add_runtime_options(ai_run, json_output=True, dry_run=True)
    ai_ingest = ai_sub.add_parser("ingest-response", help="Record a provider response as metadata only")
    ai_ingest.add_argument("--path", default=".", help="Project directory (default: current directory)")
    ai_ingest.add_argument("--provider", required=True, help="Provider name")
    ai_ingest.add_argument("--model", required=True, help="Provider model name")
    ai_ingest.add_argument("--packet-id", required=True, help="Packet ID the response belongs to")
    ai_ingest.add_argument("--response", required=True, help="Provider response text or summary")
    add_runtime_options(ai_ingest, json_output=True)

    verify = sub.add_parser(
        "verify",
        help="Run verification gates and write a durable verification record",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe verify --commands --record
              mythic-vibe verify --commands --docs --invariants --record
              mythic-vibe verify --changed-files --docs --json
            """
        ),
    )
    verify.add_argument("--path", default=".", help="Project directory (default: current directory)")
    verify.add_argument("--commands", action="store_true", help="Run discovered test commands")
    verify.add_argument("--changed-files", action="store_true", help="Review changed files and diffs")
    verify.add_argument("--docs", action="store_true", help="Check active documentation files")
    verify.add_argument("--invariants", action="store_true", help="Check project invariants and boundaries")
    verify.add_argument("--record", action="store_true", help="Promote the verification artifact to latest and update state")
    add_runtime_options(verify, json_output=True)

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
