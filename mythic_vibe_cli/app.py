"""Mythic Vibe CLI — argparse construction, dispatch, and runtime flags.

This module owns the full command surface. Concretely:

* :func:`build_parser` constructs every argparse subparser and wires
  each subcommand's flags. This is the source of truth for the public
  CLI shape.
* :func:`main` is the program entry point. It parses argv, configures
  output (quiet/verbose/json), records startup timings, dispatches to
  the appropriate handler in :data:`mythic_vibe_cli.commands.COMMAND_HANDLERS`,
  and emits the timing profile when ``MYTHIC_TIMING`` is set.
* :data:`COMMAND_HANDLERS` is re-exported from :mod:`mythic_vibe_cli.commands`
  so the thin :mod:`mythic_vibe_cli.cli` shim can expose it.

What does *not* live here:

* Command implementations — those live in :mod:`mythic_vibe_cli.commands`.
* Runtime primitives (event bus, exec, timings, output guard) — those
  live under :mod:`mythic_vibe_cli.runtime`.
* User-facing terminal rendering — that lives in :mod:`mythic_vibe_cli.output`.

Keep this file focused on *parser shape and dispatch routing*. Any
command-specific logic that grows here should be moved into
``commands.py``.
"""

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
from .runtime.output_guard import json_output_guard
from .runtime.timings import print_timings, record, reset_timings
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
    packet_show.add_argument("--previous-workflow", action="store_true", help="Resolve --workflow from the second-most-recent entry in mythic/workflow_history.json (requires --step)")
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
    packet_diff.add_argument("--left", required=True, help="Left packet reference: PKT-... ID, WF-<id>:<step_id>, LATEST:<step_id>, PREVIOUS:<step_id>, or bare step-NN with --latest-workflow")
    packet_diff.add_argument("--right", required=True, help="Right packet reference: PKT-... ID, WF-<id>:<step_id>, LATEST:<step_id>, PREVIOUS:<step_id>, or bare step-NN with --latest-workflow")
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

    workflow_history = workflow_sub.add_parser(
        "history",
        help="List recorded workflow plan saves from mythic/workflow_history.json",
    )
    workflow_history.add_argument("--path", default=".", help="Project directory (default: current directory)")
    workflow_history.add_argument("--limit", type=int, default=0, help="Show only the first N entries (newest first)")
    add_runtime_options(workflow_history, json_output=True)

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

    heal = sub.add_parser(
        "heal",
        help="Generate an additive Scribe reconciliation packet from drift findings",
    )
    heal.add_argument("--path", default=".", help="Project directory (default: current directory)")
    heal.add_argument("--failing-test", default="", help="Optional failing test identifier (informational; not yet acted on)")
    add_runtime_options(heal, json_output=True, dry_run=True)

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
    # PH-15 sub-slice: optional conversation-id + opt-out flag for the
    # slice-15.1 conversation log auto-record.
    ai_run.add_argument(
        "--conversation-id",
        default="",
        help="Conversation id (CV-XXXXXX) to record under. If empty, a fresh id is generated.",
    )
    ai_run.add_argument(
        "--no-record",
        action="store_true",
        help="Skip recording this call into the conversation log.",
    )
    add_runtime_options(ai_run, json_output=True, dry_run=True)
    ai_ingest = ai_sub.add_parser("ingest-response", help="Record a provider response as metadata only")
    ai_ingest.add_argument("--path", default=".", help="Project directory (default: current directory)")
    ai_ingest.add_argument("--provider", required=True, help="Provider name")
    ai_ingest.add_argument("--model", required=True, help="Provider model name")
    ai_ingest.add_argument("--packet-id", required=True, help="Packet ID the response belongs to")
    ai_ingest.add_argument("--response", required=True, help="Provider response text or summary")
    ai_ingest.add_argument(
        "--conversation-id",
        default="",
        help="Conversation id (CV-XXXXXX) to record under. If empty, a fresh id is generated.",
    )
    ai_ingest.add_argument(
        "--no-record",
        action="store_true",
        help="Skip recording this response into the conversation log.",
    )
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

    slash = sub.add_parser(
        "slash",
        help="Inspect slash command catalog (built-in + plugin-contributed)",
    )
    slash_sub = slash.add_subparsers(dest="slash_command", required=True)
    slash_list = slash_sub.add_parser(
        "list",
        help="List builtin slash commands and any contributed by enabled plugins",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe slash list
              mythic-vibe slash list --json
              mythic-vibe slash list --source builtin
              mythic-vibe slash list --source plugin --json
            """
        ),
    )
    slash_list.add_argument("--path", default=".", help="Project directory (default: current directory)")
    slash_list.add_argument(
        "--source",
        default="",
        choices=["", "builtin", "extension", "prompt", "skill", "plugin"],
        help="Restrict output to one source (default: show all)",
    )
    add_runtime_options(slash_list, json_output=True)

    slash_inspect = slash_sub.add_parser(
        "inspect",
        help="Show provenance + argparse help for one slash command",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe slash inspect status
              mythic-vibe slash inspect /verify
              mythic-vibe slash inspect intent --json
              mythic-vibe slash inspect quit

            Notes:
              Looks up the name in BUILTIN_SLASH_COMMANDS first, then in
              plugin-contributed entries. For builtin entries that map onto
              a top-level argparse subcommand, the parser's --help text is
              rendered. The three interactive-local entries (help / reload
              / quit) have no argparse subcommand and are flagged as such.
            """
        ),
    )
    slash_inspect.add_argument("name", help="Slash command name (with or without leading /)")
    slash_inspect.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(slash_inspect, json_output=True)

    shell = sub.add_parser(
        "shell",
        help="Open an interactive prompt that dispatches to existing CLI commands",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe shell
              mythic-vibe shell --path ./project
              echo "/help" | mythic-vibe shell
            """
        ),
    )
    shell.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(shell)

    tui = sub.add_parser(
        "tui",
        help="Open the Textual-based TUI showing project status (requires the [tui] extra)",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe tui
              mythic-vibe tui --path ./project

            Install the optional TUI extra first if needed:
              pip install "mythic-vibe-cli[tui]"
            """
        ),
    )
    tui.add_argument("--path", default=".", help="Project directory (default: current directory)")
    from .tui.themes import TEXTUAL_BUILTIN_THEMES

    tui.add_argument(
        "--theme",
        choices=TEXTUAL_BUILTIN_THEMES,
        default=None,
        metavar="NAME",
        help="Override the initial Textual theme (default: textual-dark). "
        "Use 't' inside the TUI to cycle through a curated subset.",
    )
    add_runtime_options(tui)

    # --- PH-02 slice 2.2: developer-tool shortcuts ---

    test_cmd = sub.add_parser(
        "test",
        help="Run the project's test suite (pytest by default)",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe test
              mythic-vibe test --command pytest -k slow
              mythic-vibe test --json
            """
        ),
    )
    test_cmd.add_argument("--path", default=".", help="Project directory (default: current directory)")
    test_cmd.add_argument(
        "--command",
        dest="override_command",
        nargs="+",
        help="Override the discovered test invocation (e.g. --command pytest -q tests/)",
    )
    add_runtime_options(test_cmd, json_output=True, dry_run=True)

    lint_cmd = sub.add_parser(
        "lint",
        help="Run ruff check across the project",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe lint
              mythic-vibe lint --command ruff check src/ tests/
              mythic-vibe lint --json
            """
        ),
    )
    lint_cmd.add_argument("--path", default=".", help="Project directory (default: current directory)")
    lint_cmd.add_argument(
        "--command",
        dest="override_command",
        nargs="+",
        help="Override the default `ruff check .` invocation",
    )
    add_runtime_options(lint_cmd, json_output=True, dry_run=True)

    typecheck_cmd = sub.add_parser(
        "typecheck",
        help="Run mypy across the project",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe typecheck
              mythic-vibe typecheck --command mypy mythic_vibe_cli
              mythic-vibe typecheck --json
            """
        ),
    )
    typecheck_cmd.add_argument("--path", default=".", help="Project directory (default: current directory)")
    typecheck_cmd.add_argument(
        "--command",
        dest="override_command",
        nargs="+",
        help="Override the default `mypy .` invocation",
    )
    add_runtime_options(typecheck_cmd, json_output=True, dry_run=True)

    scaffold_cmd = sub.add_parser(
        "scaffold",
        help="Add an artefact to an existing Mythic project (today: adr)",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe scaffold adr --title "Adopt knowledge graph"
              mythic-vibe scaffold adr --title "Use SQLite for state" --dry-run
              mythic-vibe scaffold adr --title "Pin Python 3.11" --json

            Notes:
              Today only `scaffold adr` is implemented. Other artefact types
              (task / interface / invariant / risk) land in PH-10 slice 10.4.
            """
        ),
    )
    scaffold_cmd.add_argument("artefact", choices=["adr"], help="Artefact type (adr)")
    scaffold_cmd.add_argument("--title", required=True, help="Human-readable title for the artefact")
    scaffold_cmd.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(scaffold_cmd, json_output=True, dry_run=True)

    changelog_cmd = sub.add_parser(
        "changelog",
        help="Print or validate the project's CHANGELOG.md [Unreleased] section",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe changelog
              mythic-vibe changelog --check
              mythic-vibe changelog --json
            """
        ),
    )
    changelog_cmd.add_argument("--path", default=".", help="Project directory (default: current directory)")
    changelog_cmd.add_argument(
        "--check",
        action="store_true",
        help="Run scripts/check_changelog.py if present and return its exit code",
    )
    add_runtime_options(changelog_cmd, json_output=True)

    version_cmd = sub.add_parser(
        "version",
        help="Print the CLI version (subcommand form of --version)",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe version
              mythic-vibe version --verbose
              mythic-vibe version --json
            """
        ),
    )
    add_runtime_options(version_cmd, json_output=True)

    # --- PH-03 slice 3.3: forge command (dry-run + ledger inspection) ---

    forge_cmd = sub.add_parser(
        "forge",
        help="Multi-agent forge orchestrator (dry-run + ledger inspection today; provider-backed run lands in slice 3.5)",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe forge plan --dry-run --task "Refactor router"
              mythic-vibe forge plan --dry-run --task "X" --skip-ledger --json
              mythic-vibe forge ledger list
              mythic-vibe forge ledger latest --limit 3
              mythic-vibe forge ledger show --workflow WF-20260429-deadbeef
              mythic-vibe forge ledger show --workflow WF-... --step step-02 --json

            Notes:
              `forge plan --dry-run` is the slice 3.3 deliverable. Provider-
              backed `forge run` waits for slice 3.5; non-dry-run today
              returns UNSAFE_OPERATION_BLOCKED with a helpful message.
            """
        ),
    )
    forge_sub = forge_cmd.add_subparsers(dest="forge_command", required=True)

    forge_plan = forge_sub.add_parser(
        "plan",
        help="Build a workflow plan and per-agent packets (no provider call)",
    )
    forge_plan.add_argument("--task", required=True, help="Plain-language task to forge")
    forge_plan.add_argument("--path", default=".", help="Project directory (default: current directory)")
    forge_plan.add_argument(
        "--skip-ledger",
        action="store_true",
        help="Do not write per-step entries to mythic/forge_ledger.json",
    )
    forge_plan.add_argument(
        "--interactive",
        action="store_true",
        help=(
            "Prompt y/n/?/s between each pair of steps (slice 3.4 approval gates). "
            "y=advance / n=abort and mark remaining steps blocked / "
            "s=skip the next step / ?=show gate detail. "
            "Default off; non-interactive runs proceed straight through."
        ),
    )
    add_runtime_options(forge_plan, json_output=True, dry_run=True)

    forge_run = forge_sub.add_parser(
        "run",
        help="Run the forge end-to-end through a configured provider (PH-03 slice 3.5)",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe forge run --provider copy-paste --task "Refactor router"
              mythic-vibe forge run --provider openai --task "X" --interactive
              mythic-vibe forge run --provider local --task "X" --json --skip-ledger

            Notes:
              - Each agent's packet is routed through the named provider.
                Successful responses become AgentOutput records on the ledger
                (status: pending -> running -> succeeded). Provider errors
                land as `failed` with the exception text in notes.
              - prior_outputs are populated from the ledger as agents
                complete, unblocking the downstream contract gates that
                slice 3.3 dry-run leaves blocked by design.
              - --interactive reuses the slice 3.4 gate machinery: y/n/?/s
                between each step.
              - Exit code: SUCCESS if every step succeeded;
                OPERATIONAL_FAILURE if at least one failed;
                UNSAFE_OPERATION_BLOCKED if the operator aborted.
            """
        ),
    )
    forge_run.add_argument("--task", required=True, help="Plain-language task to forge")
    forge_run.add_argument(
        "--provider",
        required=True,
        help="Provider name (copy-paste / local / openai / anthropic / gemini / openrouter)",
    )
    forge_run.add_argument("--path", default=".", help="Project directory (default: current directory)")
    forge_run.add_argument(
        "--skip-ledger",
        action="store_true",
        help="Do not write per-step entries to mythic/forge_ledger.json",
    )
    forge_run.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt y/n/?/s between each pair of steps (slice 3.4 gates).",
    )
    forge_run.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Abort the run when any Auditor verifier gate fails (slice 3.6). "
            "Default off: a failed verifier transitions the Auditor step to "
            "`failed` but the run continues to the Scribe."
        ),
    )
    forge_run.add_argument(
        "--skip-reflection",
        action="store_true",
        help=(
            "Do not write a reflection artefact at mythic/reflections/<workflow_id>.{md,json} "
            "after the run (slice 3.7)."
        ),
    )
    add_runtime_options(forge_run, json_output=True)

    forge_resume = forge_sub.add_parser(
        "resume",
        help="Resume a partially-completed forge run from the ledger (PH-03 slice 3.8)",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe forge resume --provider copy-paste
              mythic-vibe forge resume --provider stub --workflow WF-20260429-deadbeef
              mythic-vibe forge resume --provider local --interactive --strict

            Notes:
              - With no --workflow, picks up the most recent ledger entry.
              - Skips every step already marked `succeeded`; their
                AgentOutput is fed forward as prior_outputs to the next
                step exactly as `forge run` does.
              - Re-executes the first non-succeeded step and every
                subsequent step. New ledger entries are appended; the
                latest matching entry per (workflow_id, step_id) wins.
              - The reflection is rewritten at the end (the prior
                reflection file is replaced).
              - Returns SUCCESS if every re-executed step succeeded;
                OPERATIONAL_FAILURE if any failed; UNSAFE_OPERATION_BLOCKED
                if the operator aborted; USER_INPUT_ERROR if no resumable
                workflow is found.
            """
        ),
    )
    forge_resume.add_argument(
        "--provider",
        required=True,
        help="Provider name (copy-paste / local / openai / anthropic / gemini / openrouter)",
    )
    forge_resume.add_argument(
        "--workflow",
        default="",
        help="Workflow id to resume. Defaults to the most recent ledger entry.",
    )
    forge_resume.add_argument("--path", default=".", help="Project directory (default: current directory)")
    forge_resume.add_argument(
        "--skip-ledger",
        action="store_true",
        help="Do not write per-step entries to mythic/forge_ledger.json",
    )
    forge_resume.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt y/n/?/s between each pair of re-executed steps (slice 3.4 gates).",
    )
    forge_resume.add_argument(
        "--strict",
        action="store_true",
        help="Abort the resume when any Auditor verifier gate fails (slice 3.6).",
    )
    forge_resume.add_argument(
        "--skip-reflection",
        action="store_true",
        help="Do not rewrite the reflection at mythic/reflections/<workflow_id>.{md,json}.",
    )
    add_runtime_options(forge_resume, json_output=True)

    forge_ledger = forge_sub.add_parser(
        "ledger",
        help="Inspect mythic/forge_ledger.json (per-agent step records)",
    )
    forge_ledger_sub = forge_ledger.add_subparsers(dest="ledger_command", required=True)

    ledger_list = forge_ledger_sub.add_parser("list", help="List every recorded forge ledger entry")
    ledger_list.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(ledger_list, json_output=True)

    ledger_latest = forge_ledger_sub.add_parser("latest", help="Show the most recent N entries")
    ledger_latest.add_argument("--limit", type=int, default=5, help="Window size (default 5)")
    ledger_latest.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(ledger_latest, json_output=True)

    ledger_show = forge_ledger_sub.add_parser("show", help="Show every entry for a given workflow")
    ledger_show.add_argument("--workflow", required=True, help="Workflow id (e.g. WF-20260429-deadbeef)")
    ledger_show.add_argument("--step", default="", help="Optional step filter (e.g. step-02)")
    ledger_show.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(ledger_show, json_output=True)

    forge_reflection = forge_sub.add_parser(
        "reflection",
        help="Inspect mythic/reflections/<workflow_id>.{md,json} (slice 3.7 per-cycle reflections)",
    )
    forge_reflection_sub = forge_reflection.add_subparsers(
        dest="reflection_command", required=True
    )

    reflection_list = forge_reflection_sub.add_parser(
        "list", help="List every recorded forge reflection"
    )
    reflection_list.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(reflection_list, json_output=True)

    reflection_latest = forge_reflection_sub.add_parser(
        "latest", help="Show the most recently written reflection (markdown by default)"
    )
    reflection_latest.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(reflection_latest, json_output=True)

    reflection_show = forge_reflection_sub.add_parser(
        "show", help="Show one reflection by workflow id"
    )
    reflection_show.add_argument("--workflow", required=True, help="Workflow id")
    reflection_show.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(reflection_show, json_output=True)

    # --- PH-02 slice 2.3: workflow-phase capture commands ---
    # Each phase parent has a single `capture` subcommand today; future
    # slices may add `show`, `list`, etc. Subparser dest names use a
    # phase-specific suffix (`intent_command`, `constraints_command`,
    # ...) to avoid the F-023 argparse collision between subparser
    # dests and any future top-level subcommand named `command`.
    for _phase in ("intent", "constraints", "architecture", "plan", "build"):
        _phase_parent = sub.add_parser(
            _phase,
            help=f"Capture a Mythic Phase Record for the {_phase} phase",
            **_example_parser_kwargs(
                f"""
                Examples:
                  mythic-vibe {_phase} capture --task "Refactor router" --summary "Move command handlers into modules"
                  mythic-vibe {_phase} capture --task "Refactor router" --summary "..." --note "Keep alias compatibility" --confidence high --risk low
                  mythic-vibe {_phase} capture --task "Refactor router" --summary "..." --json
                  mythic-vibe {_phase} capture --task "Refactor router" --summary "..." --dry-run
                """
            ),
        )
        _phase_sub = _phase_parent.add_subparsers(dest=f"{_phase}_command", required=True)
        _capture = _phase_sub.add_parser(
            "capture",
            help=f"Write a Mythic Phase Record under mythic/checkins/<ts>-{_phase}.md",
        )
        _capture.add_argument("--task", required=True, help="Short task name (also recorded inside the file)")
        _capture.add_argument("--summary", required=True, help="One-paragraph summary for the {_phase} phase")
        _capture.add_argument("--note", action="append", default=[], help="Additional bullet (repeatable)")
        _capture.add_argument(
            "--confidence",
            choices=["high", "medium", "low", "unspecified"],
            default="unspecified",
            help="Operator confidence in the captured material",
        )
        _capture.add_argument("--risk", default="", help="Short risk note recorded in the phase header")
        _capture.add_argument(
            "--next-step",
            default="",
            help="What the operator intends to do next (rendered into the Next Step section)",
        )
        _capture.add_argument("--operator", default="", help="Operator name override (default: $USER / $USERNAME)")
        _capture.add_argument("--path", default=".", help="Project directory (default: current directory)")
        add_runtime_options(_capture, json_output=True, dry_run=True)

    # --- PH-02 slice 2.4: provider alias ---
    # Top-level alias for `mythic-vibe ai providers` so the slash
    # picker can surface a friendlier `/provider` entry.
    provider_cmd = sub.add_parser(
        "provider",
        help="List configured AI providers (alias of `ai providers`)",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe provider
              mythic-vibe provider --json
              mythic-vibe provider --path ./project
            """
        ),
    )
    provider_cmd.add_argument(
        "--path",
        default=".",
        help="Project directory used for provider logs (default: current directory)",
    )
    add_runtime_options(provider_cmd, json_output=True)

    # --- PH-02 slice 2.5: audit alias ---
    # Top-level alias for `mythic-vibe doctor --json` so audit-style
    # consumers don't have to remember the doctor flag combo.
    audit_cmd = sub.add_parser(
        "audit",
        help="Run a doctor pass and emit JSON (alias of `doctor --json`)",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe audit
              mythic-vibe audit --path ./project
            """
        ),
    )
    audit_cmd.add_argument(
        "--path",
        default=".",
        help="Project directory (default: current directory)",
    )
    add_runtime_options(audit_cmd)

    # --- PH-05 slice 5.5 / 5.6: graph query + visualize ---
    graph_cmd = sub.add_parser(
        "graph",
        help="Read-only queries over the project knowledge graph",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe graph query --tag cli
              mythic-vibe graph entity --kind module --name app
              mythic-vibe graph edges --kind references
              mythic-vibe graph brief --phase build
              mythic-vibe graph visualize --format mermaid
            """
        ),
    )
    graph_sub = graph_cmd.add_subparsers(dest="graph_command", required=True)

    graph_query = graph_sub.add_parser(
        "query",
        help="Run a relevance-ranked retrieval against the graph",
    )
    graph_query.add_argument(
        "--path",
        default=".",
        help="Project directory (default: current directory)",
    )
    graph_query.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Tag to seed retrieval (repeatable)",
    )
    graph_query.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Maximum results to return (default: 10)",
    )
    graph_query.add_argument(
        "--no-expand",
        action="store_true",
        help="Disable 1-hop neighbour expansion",
    )
    add_runtime_options(graph_query, json_output=True)

    graph_entity = graph_sub.add_parser(
        "entity",
        help="Find entities matching a kind / name / path filter",
    )
    graph_entity.add_argument("--path", default=".")
    graph_entity.add_argument("--kind", default="", help="Restrict to entity kind")
    graph_entity.add_argument("--name", default="", help="Substring match on entity name")
    graph_entity.add_argument(
        "--name-path", default="", help="Substring match on entity path"
    )
    add_runtime_options(graph_entity, json_output=True)

    graph_edges = graph_sub.add_parser("edges", help="List edges by filter")
    graph_edges.add_argument("--path", default=".")
    graph_edges.add_argument("--kind", default="", help="Restrict to edge kind")
    graph_edges.add_argument(
        "--src-id", type=int, default=0, help="Restrict to source entity id"
    )
    graph_edges.add_argument(
        "--dst-id", type=int, default=0, help="Restrict to destination entity id"
    )
    add_runtime_options(graph_edges, json_output=True)

    graph_brief = graph_sub.add_parser(
        "brief",
        help="Render the slice 5.4 session brief from the graph",
    )
    graph_brief.add_argument("--path", default=".")
    graph_brief.add_argument(
        "--phase",
        default="build",
        help="Current Mythic phase to scope the brief (default: build)",
    )
    add_runtime_options(graph_brief, json_output=True)

    graph_visualize = graph_sub.add_parser(
        "visualize",
        help="Export the graph as Mermaid (default) or DOT",
    )
    graph_visualize.add_argument("--path", default=".")
    graph_visualize.add_argument(
        "--format",
        choices=("mermaid", "dot"),
        default="mermaid",
        help="Output format (default: mermaid)",
    )
    graph_visualize.add_argument(
        "--node",
        type=int,
        default=0,
        help="Optional entity id — restricts to that node's 1-hop subgraph",
    )
    add_runtime_options(graph_visualize)

    # --- PH-15 slices 15.3 + 15.4: memory show / list / compact / rehydrate ---
    memory_cmd = sub.add_parser(
        "memory",
        help="Conversation memory: show, list, compact, rehydrate",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe memory list
              mythic-vibe memory show --id CV-ABCDEF
              mythic-vibe memory compact --id CV-ABCDEF --keep-recent 3
              mythic-vibe memory rehydrate --phase build
            """
        ),
    )
    memory_sub = memory_cmd.add_subparsers(dest="memory_command", required=True)

    memory_list = memory_sub.add_parser(
        "list", help="List every conversation record (newest first)"
    )
    memory_list.add_argument("--path", default=".")
    add_runtime_options(memory_list, json_output=True)

    memory_show = memory_sub.add_parser(
        "show", help="Print one conversation record by id"
    )
    memory_show.add_argument("--path", default=".")
    memory_show.add_argument("--id", required=True, help="Conversation id (CV-XXXXXX)")
    add_runtime_options(memory_show, json_output=True)

    memory_compact = memory_sub.add_parser(
        "compact",
        help="Compact a conversation into a summary sidecar",
    )
    memory_compact.add_argument("--path", default=".")
    memory_compact.add_argument("--id", required=True, help="Conversation id (CV-XXXXXX)")
    memory_compact.add_argument(
        "--keep-recent",
        type=int,
        default=3,
        help="Number of trailing turns to reproduce verbatim (default: 3)",
    )
    add_runtime_options(memory_compact, json_output=True, dry_run=True)

    memory_rehydrate = memory_sub.add_parser(
        "rehydrate",
        help="Build a session-resume brief from graph + handoff + latest conversation",
    )
    memory_rehydrate.add_argument("--path", default=".")
    memory_rehydrate.add_argument(
        "--phase",
        default="build",
        help="Current Mythic phase to scope the brief (default: build)",
    )
    add_runtime_options(memory_rehydrate, json_output=True)

    # --- PH-13 slice 13.1: drift scan ---
    # Standalone drift-detection scan. Doctor integration (slice 13.2)
    # surfaces the same findings under its own envelope; this top-level
    # subcommand is the focused entry point operators reach for when
    # they want only drift output.
    drift_cmd = sub.add_parser(
        "drift",
        help="Scan the project for drift between docs, code, and decisions",
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe drift
              mythic-vibe drift --path ./project --json
            """
        ),
    )
    drift_cmd.add_argument(
        "--path",
        default=".",
        help="Project directory (default: current directory)",
    )
    add_runtime_options(drift_cmd, json_output=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    reset_timings()
    try:
        parser = build_parser()
        args = parser.parse_args(argv)
        record("argparse")
        configure_output(quiet=getattr(args, "quiet", False), verbose=getattr(args, "verbose", False))
        record("configure_output")

        handler: CommandHandler | None = COMMAND_HANDLERS.get(args.command)
        if handler:
            try:
                with json_output_guard(getattr(args, "json", False)):
                    result = handler(args)
                record(f"handler:{args.command}")
                return result
            finally:
                configure_output()

        parser.error("Unknown command")
        return USER_INPUT_ERROR
    finally:
        print_timings()


if __name__ == "__main__":
    raise SystemExit(main())
