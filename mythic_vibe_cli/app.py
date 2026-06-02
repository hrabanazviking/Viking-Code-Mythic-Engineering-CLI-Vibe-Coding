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
import sys
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


def build_parser(admin_mode: bool = False) -> argparse.ArgumentParser:
    def _help(text: str) -> str:
        return text if admin_mode else argparse.SUPPRESS

    parser = argparse.ArgumentParser(
        prog="mythic-vibe",
        description="Mythic Engineering-aligned vibe coding CLI",
        epilog=(
            "Reforge default: run `mythic` with no arguments to open the "
            "interactive coding companion shell. Advanced command-catalog "
            "mode remains available directly, or through `mythic admin <command>`."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser(
        "init",
        help=_help("Initialize Mythic Engineering docs + workflow scaffolding"),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe init --goal "Build a calm CLI" --noob
              mythic-vibe init --goal "Refactor checkout flow" --path ./app --dry-run
            """
        ),
    )
    # Phase 20.0 (audit remediation 2026-05-02): --goal is no longer
    # marked required at the argparse layer because the new
    # --interactive wizard prompts for it. Default behaviour is
    # preserved by an explicit post-parse check in cmd_init that
    # rejects "neither --goal nor --interactive supplied".
    init_cmd.add_argument("--goal", help="Plain language product goal")
    init_cmd.add_argument("--path", default=".", help="Project directory (default: current directory)")
    init_cmd.add_argument("--noob", action="store_true", help="Enable beginner-friendly guidance")
    init_cmd.add_argument(
        "--interactive",
        action="store_true",
        help="Opt into a Q&A wizard that asks for project name, goal, default AI provider, operator, and sample-scaffold preference.",
    )
    init_cmd.add_argument(
        "--force",
        action="store_true",
        help="With --interactive: overwrite mythic/project_settings.json if it already exists.",
    )
    add_runtime_options(init_cmd, dry_run=True)

    start = sub.add_parser("start", help=_help("Alias of `init`"))
    start.add_argument("--goal", help="Plain language product goal")
    start.add_argument("--path", default=".", help="Project directory (default: current directory)")
    start.add_argument("--noob", action="store_true", help="Enable beginner-friendly guidance")
    start.add_argument(
        "--interactive",
        action="store_true",
        help="Opt into a Q&A wizard (same as `init --interactive`).",
    )
    start.add_argument(
        "--force",
        action="store_true",
        help="With --interactive: overwrite mythic/project_settings.json if it already exists.",
    )
    add_runtime_options(start, dry_run=True)

    checkin = sub.add_parser("checkin", help=_help("Log a Mythic phase update and advance tracking"))
    checkin.add_argument("--phase", required=True, choices=PHASES, help="Current Mythic phase")
    checkin.add_argument("--update", required=True, help="Short progress update")
    checkin.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(checkin, dry_run=True)

    status = sub.add_parser("status", help=_help("Show current Mythic progress summary"))
    status.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(status, json_output=True)

    examples = sub.add_parser("examples", help=_help("Show copy-paste command examples"))
    add_runtime_options(examples, json_output=True)

    guide = sub.add_parser("guide", help=_help("Show the compact Mythic Vibe operator guide"))
    add_runtime_options(guide, json_output=True)

    next_cmd = sub.add_parser(
        "next",
        help=_help("Show the next recommended phase and command"),
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

    explain = sub.add_parser("explain", help=_help("Explain phases and artifacts"))
    add_runtime_options(explain, json_output=True)
    explain_sub = explain.add_subparsers(dest="explain_command", required=True)
    explain_phase = explain_sub.add_parser("phase", help=_help("Explain one Mythic phase"))
    explain_phase.add_argument("phase", choices=phase_names(), help="Phase to explain")
    add_runtime_options(explain_phase, json_output=True)
    explain_artifact = explain_sub.add_parser("artifact", help=_help("Explain one generated artifact"))
    explain_artifact.add_argument("artifact", choices=artifact_names(), help="Artifact to explain")
    add_runtime_options(explain_artifact, json_output=True)

    tutorial = sub.add_parser("tutorial", help=_help("Show a first full workflow tutorial"))
    add_runtime_options(tutorial, json_output=True)

    completion = sub.add_parser("completion", help=_help("Print shell completion script"))
    completion.add_argument("--shell", required=True, choices=["bash", "zsh", "powershell"], help="Shell to generate completions for")
    add_runtime_options(completion, json_output=True)

    reflect = sub.add_parser(
        "reflect",
        help=_help("Create a reflection handoff for the current session"),
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

    scan = sub.add_parser("scan", help=_help("Build a local project index for AI context"))
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

    import_md = sub.add_parser("import-md", help=_help("Import all Markdown files from Mythic Engineering repo"))
    import_md.add_argument("--path", default=".", help="Project directory (default: current directory)")
    import_md.add_argument(
        "--target",
        default="docs/mythic_source",
        help="Target folder inside project for imported files (default: docs/mythic_source)",
    )
    add_runtime_options(import_md, dry_run=True)

    codex_pack = sub.add_parser(
        "codex-pack",
        help=_help("Generate a copy/paste-ready prompt packet for ChatGPT Plus/Codex users"),
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
        help=_help("Record a check-in update after receiving a response from ChatGPT/Codex"),
    )
    codex_log.add_argument("--phase", required=True, choices=PHASES, help="Current Mythic phase")
    codex_log.add_argument("--response", required=True, help="One-line summary from Codex response")
    codex_log.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(codex_log, dry_run=True)

    sync = sub.add_parser("sync", help=_help("Sync Mythic Engineering method notes from GitHub"))
    add_runtime_options(sync, dry_run=True)
    method = sub.add_parser("method", help=_help("Inspect and sync the active Mythic Engineering method profile"))
    add_runtime_options(method, json_output=True, dry_run=True)
    method_sub = method.add_subparsers(dest="method_command", required=False)
    method_status = method_sub.add_parser("status", help=_help("Show active method source, profile, and version"))
    method_status.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(method_status, json_output=True)
    method_show = method_sub.add_parser("show", help=_help("Print active Mythic method notes"))
    method_show.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(method_show, json_output=True)
    method_sync = method_sub.add_parser("sync", help=_help("Sync Mythic Engineering method notes into the local cache"))
    method_sync.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(method_sync, json_output=True, dry_run=True)
    method_diff = method_sub.add_parser("diff", help=_help("Compare an imported method corpus against its manifest"))
    method_diff.add_argument("--path", default=".", help="Project directory (default: current directory)")
    method_diff.add_argument(
        "--target",
        default="docs/mythic_source",
        help="Imported method corpus folder inside project (default: docs/mythic_source)",
    )
    add_runtime_options(method_diff, json_output=True)
    method_pin = method_sub.add_parser("pin", help=_help("Pin a clean imported method corpus for reproducibility"))
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
        help=_help("Validate Mythic project structure and status"),
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
    # Phase 20.2 (audit remediation 2026-05-02): tightly-scoped
    # auto-remediation. Two safe fixes (missing mythic/ subdirs;
    # missing CHANGELOG [Unreleased] section). Hard-rule: never
    # touches user-authored content.
    doctor.add_argument(
        "--fix",
        action="store_true",
        help="Auto-remediate safe scaffolding gaps (missing mythic/ subdirs, missing CHANGELOG [Unreleased]).",
    )
    doctor.add_argument(
        "--fix-dry-run",
        action="store_true",
        help="Preview what --fix would do without writing anything.",
    )
    add_runtime_options(doctor, json_output=True)

    # Mythic ritual aliases from design doc.
    imbue = sub.add_parser("imbue", help=_help("Initialize project vision and Mythic scaffolding"))
    imbue.add_argument("--goal", required=True, help="Plain language product goal")
    imbue.add_argument("--path", default=".", help="Project directory (default: current directory)")
    imbue.add_argument("--noob", action="store_true", help="Enable beginner-friendly guidance")
    add_runtime_options(imbue, dry_run=True)

    evoke = sub.add_parser("evoke", help=_help("Generate a Codex packet from an architecture-aware prompt"))
    evoke.add_argument("--task", required=True, help="Specific coding task for Codex")
    evoke.add_argument("--phase", default="plan", choices=PHASES, help="Current Mythic phase (default: plan)")
    evoke.add_argument("--audience", default="beginner", help="Audience level: beginner/intermediate/advanced")
    evoke.add_argument("--role", default="Forge Worker", choices=PACKET_ROLES, help="Packet role")
    evoke.add_argument("--format", default="markdown", choices=PACKET_OUTPUT_FORMATS, help="Packet output format")
    evoke.add_argument("--path", default=".", help="Project directory (default: current directory)")
    evoke.add_argument("--out", default=None, help="Output file path (default: <project>/mythic/codex_prompt.md)")
    add_runtime_options(evoke, json_output=True, dry_run=True)

    packet = sub.add_parser("packet", help=_help("Create, show, or list reusable packet artifacts"))
    add_runtime_options(packet, json_output=True, dry_run=True)
    packet_sub = packet.add_subparsers(dest="packet_command", required=True)
    packet_create = packet_sub.add_parser(
        "create",
        help=_help("Create a reusable packet artifact"),
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
    packet_show = packet_sub.add_parser("show", help=_help("Show a stored packet by packet ID or workflow+step"))
    packet_show.add_argument("--path", default=".", help="Project directory (default: current directory)")
    packet_show.add_argument("--packet-id", default="", help="Packet ID to show (default: latest)")
    packet_show.add_argument("--workflow", default="", help="Workflow ID stamped on the packet (requires --step)")
    packet_show.add_argument("--step", default="", help="Workflow step ID stamped on the packet (requires --workflow or --latest-workflow)")
    packet_show.add_argument("--latest-workflow", action="store_true", help="Resolve --workflow from mythic/workflow_plan.json (requires --step)")
    packet_show.add_argument("--previous-workflow", action="store_true", help="Resolve --workflow from the second-most-recent entry in mythic/workflow_history.json (requires --step)")
    add_runtime_options(packet_show, json_output=True)
    packet_list = packet_sub.add_parser("list", help=_help("List stored packet records"))
    packet_list.add_argument("--path", default=".", help="Project directory (default: current directory)")
    packet_list.add_argument("--workflow", default="", help="Filter to packets stamped with this workflow ID")
    packet_list.add_argument("--step", default="", help="Filter to packets stamped with this workflow step ID (requires --workflow or --latest-workflow)")
    packet_list.add_argument("--latest-workflow", action="store_true", help="Resolve --workflow from mythic/workflow_plan.json")
    add_runtime_options(packet_list, json_output=True)
    packet_ingest = packet_sub.add_parser("ingest", help=_help("Ingest a packet artifact into the local packet store"))
    packet_ingest.add_argument("--path", default=".", help="Project directory (default: current directory)")
    packet_ingest.add_argument("--source", required=True, help="Path to a packet markdown or metadata artifact")
    add_runtime_options(packet_ingest, json_output=True, dry_run=True)
    packet_diff = packet_sub.add_parser("diff", help=_help("Diff two stored packet artifacts"))
    packet_diff.add_argument("--path", default=".", help="Project directory (default: current directory)")
    packet_diff.add_argument("--left", required=True, help="Left packet reference: PKT-... ID, WF-<id>:<step_id>, LATEST:<step_id>, PREVIOUS:<step_id>, or bare step-NN with --latest-workflow")
    packet_diff.add_argument("--right", required=True, help="Right packet reference: PKT-... ID, WF-<id>:<step_id>, LATEST:<step_id>, PREVIOUS:<step_id>, or bare step-NN with --latest-workflow")
    packet_diff.add_argument("--latest-workflow", action="store_true", help="Allow bare step-NN refs to resolve against mythic/workflow_plan.json")
    add_runtime_options(packet_diff, json_output=True)
    # Phase 20.1 (audit remediation 2026-05-02): packet lint —
    # heuristic packet-quality linter. See packet_lint.py.
    packet_lint = packet_sub.add_parser(
        "lint",
        help=_help("Lint a packet for missing required sections, vague intent, weak verification anchors, etc."),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe packet lint --packet-id PKT-000003
              mythic-vibe packet lint                       # lints latest stored packet
              mythic-vibe packet lint --file ./draft.md     # lints an ad-hoc file
              mythic-vibe packet lint --json                # machine-readable findings
            """
        ),
    )
    packet_lint.add_argument("--path", default=".", help="Project directory (default: current directory)")
    packet_lint.add_argument("--packet-id", default="", help="Packet ID to lint (default: latest stored packet)")
    packet_lint.add_argument("--file", default="", help="Lint an ad-hoc packet file outside the store; bypasses --packet-id resolution")
    add_runtime_options(packet_lint, json_output=True)

    workflow = sub.add_parser(
        "workflow",
        help=_help("Plan role-based Mythic workflow orchestration"),
    )
    add_runtime_options(workflow, json_output=True, dry_run=True)
    workflow_sub = workflow.add_subparsers(dest="workflow_command", required=True)
    workflow_plan = workflow_sub.add_parser(
        "plan",
        help=_help("Write a deterministic role orchestration plan"),
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
        help=_help("Preview ordered workflow execution without invoking providers"),
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
        help=_help("List packet readiness for a workflow plan"),
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
        help=_help("List recorded workflow plan saves from mythic/workflow_history.json"),
    )
    workflow_history.add_argument("--path", default=".", help="Project directory (default: current directory)")
    workflow_history.add_argument("--limit", type=int, default=0, help="Show only the first N entries (newest first)")
    add_runtime_options(workflow_history, json_output=True)

    # Phase 20.C (audit remediation 2026-05-03): workflow lineage
    # viewer. Reads forge_ledger entries; emits Mermaid markdown
    # or structured JSON.
    workflow_lineage = workflow_sub.add_parser(
        "lineage",
        help=_help("Render a workflow's per-step graph from the forge ledger."),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe workflow lineage
              mythic-vibe workflow lineage --workflow WF-000123
              mythic-vibe workflow lineage --json
            """
        ),
    )
    workflow_lineage.add_argument("--path", default=".", help="Project directory (default: current directory)")
    workflow_lineage.add_argument("--workflow", default="", help="Workflow id to render (default: most recent in ledger).")
    add_runtime_options(workflow_lineage, json_output=True)

    handoff = sub.add_parser("handoff", help=_help("Create, inspect, or list session handoff records"))
    add_runtime_options(handoff, json_output=True, dry_run=True)
    handoff_sub = handoff.add_subparsers(dest="handoff_command", required=True)
    handoff_create = handoff_sub.add_parser("create", help=_help("Create a session handoff record"))
    handoff_create.add_argument("--path", default=".", help="Project directory (default: current directory)")
    handoff_create.add_argument("--summary", default="", help="Optional summary of the current work session")
    handoff_create.add_argument("--next-step", default="", help="Optional next action to emphasize")
    handoff_create.add_argument("--note", default="", help="Optional note to preserve in the handoff")
    add_runtime_options(handoff_create, json_output=True, dry_run=True)
    handoff_show = handoff_sub.add_parser("show", help=_help("Show a stored handoff record"))
    handoff_show.add_argument("--path", default=".", help="Project directory (default: current directory)")
    handoff_show.add_argument("--handoff-id", default="", help="Handoff ID to show (default: latest)")
    add_runtime_options(handoff_show, json_output=True)
    handoff_latest = handoff_sub.add_parser("latest", help=_help("Show the latest handoff record"))
    handoff_latest.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(handoff_latest, json_output=True)

    scry = sub.add_parser("scry", help=_help("Analyze project health and diagnostics"))
    scry.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(scry, json_output=True)

    weave = sub.add_parser("weave", help=_help("Record documentation synchronization checkpoint"))
    weave.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(weave, dry_run=True)

    prune = sub.add_parser("prune", help=_help("Suggest dead-code pruning workflow"))
    prune.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(prune)

    heal = sub.add_parser(
        "heal",
        help=_help("Generate an additive Scribe reconciliation packet from drift findings"),
    )
    heal.add_argument("--path", default=".", help="Project directory (default: current directory)")
    heal.add_argument("--failing-test", default="", help="Optional failing test identifier (informational; not yet acted on)")
    add_runtime_options(heal, json_output=True, dry_run=True)

    resume = sub.add_parser(
        "resume",
        help=_help("Summarize the latest handoff and suggest the next step"),
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

    oath = sub.add_parser("oath", help=_help("Display responsible AI usage oath"))
    oath.add_argument("--yes", action="store_true", help="Echo acceptance message after displaying the oath")
    oath.add_argument(
        "--path", default=".", help="Project directory (default: current directory)"
    )
    oath.add_argument(
        "--override",
        default="",
        help=(
            "PH-14 override reason. Required when blocking constraints exist "
            "in mythic/oaths.md / constraints.md / docs/ADRS/."
        ),
    )
    add_runtime_options(oath)

    # PH-14 Slice 14.4: `mythic-vibe policy report`.
    policy = sub.add_parser(
        "policy",
        help=_help("Policy engine surface (PH-14) — list constraints + override history"),
    )
    policy_sub = policy.add_subparsers(dest="policy_command", required=True)
    policy_report = policy_sub.add_parser(
        "report",
        help=_help("List current constraints and override history"),
    )
    policy_report.add_argument(
        "--path", default=".", help="Project directory (default: current directory)"
    )
    add_runtime_options(policy_report, json_output=True)

    # PH-18 Slice 18.4: `mythic-vibe simulate`.
    simulate = sub.add_parser(
        "simulate",
        help=_help("Resilience simulation (PH-18) — inject canonical failures, confirm graceful degradation"),
    )
    add_runtime_options(simulate, json_output=True)

    # PH-16: `mythic-vibe protocols ...` (MCP / ACP / OpenTelemetry).
    protocols = sub.add_parser(
        "protocols",
        help=_help("Standards-based protocol surfaces (MCP / ACP / OpenTelemetry)"),
    )
    protocols_sub = protocols.add_subparsers(
        dest="protocols_command", required=True
    )
    proto_mcp_server = protocols_sub.add_parser(
        "mcp-server",
        help=_help("Bind the Model Context Protocol server to stdio"),
    )
    add_runtime_options(proto_mcp_server, json_output=False)
    proto_acp_bridge = protocols_sub.add_parser(
        "acp-bridge",
        help=_help("Bind the Agent Communication Protocol bridge to stdio"),
    )
    add_runtime_options(proto_acp_bridge, json_output=False)
    proto_otel = protocols_sub.add_parser(
        "otel-status",
        help=_help("Report OpenTelemetry tracing status (env flag + SDK availability)"),
    )
    add_runtime_options(proto_otel, json_output=True)

    # PH-17 Multi-Surface Access.
    surface = sub.add_parser(
        "surface",
        help=_help("Multi-surface access (PH-17) — web terminal / SSH check / chat bridge"),
    )
    surface_sub = surface.add_subparsers(dest="surface_command", required=True)

    surface_web = surface_sub.add_parser(
        "web",
        help=_help("Launch the token-protected web terminal (slice 17.1)"),
    )
    surface_web.add_argument(
        "--bind",
        default="127.0.0.1",
        help="Bind address (default: 127.0.0.1 — loopback only)",
    )
    surface_web.add_argument(
        "--port", type=int, default=8765, help="TCP port (default: 8765)"
    )
    surface_web.add_argument(
        "--token",
        default="",
        help="Auth token (32-byte URL-safe). Auto-generated when omitted.",
    )
    add_runtime_options(surface_web, json_output=True)

    surface_ssh = surface_sub.add_parser(
        "ssh-doctor",
        help=_help("SSH-readiness diagnostic (slice 17.3)"),
    )
    add_runtime_options(surface_ssh, json_output=True)

    surface_chat = surface_sub.add_parser(
        "chat",
        help=(
            "Chat bridge — scaffolding entry by default; --run starts "
            "the long-poll loop (PH-17 slice 17.4 + Phase E remediation)"
        ),
    )
    surface_chat.add_argument(
        "--backend",
        default="",
        choices=("matrix", "telegram"),
        help="Chat backend (matrix is the default first-class choice)",
    )
    # Phase E.3 2026-05-02 (audit remediation, finding #2): --run +
    # --config + --max-iterations. The legacy scaffolding-and-exit
    # behaviour is preserved when --run is absent (additive).
    surface_chat.add_argument(
        "--run",
        action="store_true",
        help=(
            "Start the long-poll loop. Requires "
            "MYTHIC_CHAT_BRIDGE_ENABLED=1 (master gate, default off). "
            "Reads credentials from MYTHIC_CHAT_<BACKEND>_* env vars + "
            "optional --config file. Refuses to start without an "
            "explicit allowlist (see docs/CHAT_BRIDGE_DEPLOYMENT.md)."
        ),
    )
    surface_chat.add_argument(
        "--config",
        default="",
        help=(
            "Path to a JSON config file with `matrix` / `telegram` "
            "sections. File values override env-var defaults. "
            "Without --config, env vars are the sole source."
        ),
    )
    surface_chat.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help=(
            "Test guard: stop the loop after N sync calls. Production "
            "operators leave this unset; the loop runs until SIGINT / "
            "SIGTERM."
        ),
    )
    add_runtime_options(surface_chat, json_output=True)

    # v1.0 / Hermes (2026-05-03): agent control-plane HTTP server.
    surface_hermes = surface_sub.add_parser(
        "hermes",
        help=(
            "Launch the Hermes agent control-plane HTTP server "
            "(token-protected JSON API)"
        ),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe surface hermes
              mythic-vibe surface hermes --bind 127.0.0.1 --port 8770 --token "$TOKEN"
              mythic-vibe surface hermes --json    # prints token + URL, then exits before serving (rehearsal mode is below)
            """
        ),
    )
    surface_hermes.add_argument(
        "--path", default=".", help="Project directory (default: current directory)"
    )
    surface_hermes.add_argument(
        "--bind", default="127.0.0.1",
        help="Bind address (default: 127.0.0.1 — loopback only)",
    )
    surface_hermes.add_argument(
        "--port", type=int, default=8770,
        help="TCP port (default: 8770; distinct from web terminal's 8765)",
    )
    surface_hermes.add_argument(
        "--token", default="",
        help="Auth token (32-byte URL-safe). Auto-generated when omitted.",
    )
    add_runtime_options(surface_hermes, json_output=True)

    # v1.0 / Hermes (2026-05-03): top-level introspection command.
    hermes_cmd = sub.add_parser(
        "hermes",
        help=_help("Inspect Hermes agent tools / invoke tools directly from the CLI."),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe hermes tools
              mythic-vibe hermes tools --json
              mythic-vibe hermes inspect --tool packet_create
              mythic-vibe hermes invoke --tool status
              mythic-vibe hermes invoke --tool checkin --args '{"phase":"build","update":"..."}'
            """
        ),
    )
    hermes_sub = hermes_cmd.add_subparsers(dest="hermes_command", required=True)
    hermes_tools = hermes_sub.add_parser("tools", help=_help("List registered tools."))
    hermes_tools.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(hermes_tools, json_output=True)
    hermes_inspect = hermes_sub.add_parser("inspect", help=_help("Show one tool's full spec."))
    hermes_inspect.add_argument("--path", default=".", help="Project directory (default: current directory)")
    hermes_inspect.add_argument("--tool", required=True, help="Tool name to inspect.")
    add_runtime_options(hermes_inspect, json_output=True)
    hermes_invoke = hermes_sub.add_parser("invoke", help=_help("Invoke a tool directly from the CLI (without HTTP)."))
    hermes_invoke.add_argument("--path", default=".", help="Project directory (default: current directory)")
    hermes_invoke.add_argument("--tool", required=True, help="Tool name to invoke.")
    hermes_invoke.add_argument("--args", default="", help="JSON-object string of arguments (default: empty).")
    add_runtime_options(hermes_invoke, json_output=True)

    grimoire = sub.add_parser("grimoire", help=_help("Manage plugins"))
    add_runtime_options(grimoire)
    grimoire_sub = grimoire.add_subparsers(dest="grimoire_command", required=True)
    grimoire_add = grimoire_sub.add_parser("add", help=_help("Register a plugin entrypoint string"))
    grimoire_add.add_argument("plugin", help="Plugin entrypoint, e.g. package.module:Plugin")
    grimoire_add.add_argument("--path", default=".", help="Project directory (default: current directory)")
    grimoire_add.add_argument("--hook", action="append", default=[], choices=PLUGIN_HOOKS, help="Hook implemented by this plugin")
    grimoire_add.add_argument("--version", default="unknown", help="Plugin version label")
    add_runtime_options(grimoire_add, json_output=True, dry_run=True)
    grimoire_list = grimoire_sub.add_parser("list", help=_help("List registered plugins"))
    grimoire_list.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(grimoire_list, json_output=True)

    plugin = sub.add_parser("plugin", help=_help("Inspect and control registered plugins"))
    add_runtime_options(plugin, json_output=True)
    plugin_sub = plugin.add_subparsers(dest="plugin_command", required=True)
    plugin_list = plugin_sub.add_parser("list", help=_help("List plugin health without importing plugin code"))
    plugin_list.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plugin_list.add_argument("--all", action="store_true", help="Include disabled plugins")
    add_runtime_options(plugin_list, json_output=True)
    plugin_inspect = plugin_sub.add_parser("inspect", help=_help("Inspect one plugin entrypoint and hook declarations"))
    plugin_inspect.add_argument("plugin", help="Plugin entrypoint, e.g. package.module:Plugin")
    plugin_inspect.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plugin_inspect.add_argument("--metadata-only", action="store_true", help="Inspect registry metadata without importing plugin code")
    add_runtime_options(plugin_inspect, json_output=True)
    plugin_disable = plugin_sub.add_parser("disable", help=_help("Disable one registered plugin"))
    plugin_disable.add_argument("plugin", help="Plugin entrypoint, e.g. package.module:Plugin")
    plugin_disable.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(plugin_disable, json_output=True, dry_run=True)

    # PH-10 Slice 10.1: discover + install via setuptools entry-points.
    plugin_discover = plugin_sub.add_parser(
        "discover",
        help=_help("List installed entry-points in the mythic_vibe.plugins group"),
    )
    plugin_discover.add_argument(
        "--path", default=".", help="Project directory (default: current directory)"
    )
    add_runtime_options(plugin_discover, json_output=True)

    plugin_install = plugin_sub.add_parser(
        "install",
        help=_help("Register a discovered entry-point in the project's plugin registry"),
    )
    plugin_install.add_argument(
        "name",
        help=(
            "Entry-point name (friendly) or canonical module:attr string. "
            "Must already be installed via pip; run `plugin discover` to list."
        ),
    )
    plugin_install.add_argument(
        "--path", default=".", help="Project directory (default: current directory)"
    )
    add_runtime_options(plugin_install, json_output=True, dry_run=True)
    # Phase 20.3 (audit remediation 2026-05-02): plugin doctor —
    # capability + circuit-breaker audit. Read-only.
    plugin_doctor = plugin_sub.add_parser(
        "doctor",
        help=_help("Audit plugin capability declarations + circuit-breaker state."),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe plugin doctor
              mythic-vibe plugin doctor --json
            """
        ),
    )
    plugin_doctor.add_argument(
        "--path", default=".", help="Project directory (default: current directory)"
    )
    add_runtime_options(plugin_doctor, json_output=True)

    # PH-12 Slice 12.1: `mythic-vibe ci scaffold`.
    ci = sub.add_parser(
        "ci",
        help=_help("CI/CD scaffolding (PH-12) — workflow generation tuned to the detected stack"),
    )
    ci_sub = ci.add_subparsers(dest="ci_command", required=True)
    ci_scaffold = ci_sub.add_parser(
        "scaffold",
        help=_help("Generate .github/workflows/ci.yml tuned to the detected stack"),
    )
    ci_scaffold.add_argument(
        "--path", default=".", help="Project directory (default: current directory)"
    )
    ci_scaffold.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing .github/workflows/ci.yml",
    )
    add_runtime_options(ci_scaffold, json_output=True, dry_run=True)

    # PH-12 Slice 12.2: `mythic-vibe docker scaffold`.
    docker = sub.add_parser(
        "docker",
        help=_help("Docker scaffolding (PH-12) — Dockerfile + .dockerignore + docker-compose.yml"),
    )
    docker_sub = docker.add_subparsers(dest="docker_command", required=True)
    docker_scaffold = docker_sub.add_parser(
        "scaffold",
        help=_help("Generate Dockerfile, .dockerignore, and docker-compose.yml tuned to the stack"),
    )
    docker_scaffold.add_argument(
        "--path", default=".", help="Project directory (default: current directory)"
    )
    docker_scaffold.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing Dockerfile / .dockerignore / docker-compose.yml",
    )
    add_runtime_options(docker_scaffold, json_output=True, dry_run=True)

    # PH-12 Slice 12.3: `mythic-vibe release`.
    release = sub.add_parser(
        "release",
        help=_help("Semver-aware release helper (PH-12). Bumps version, drafts CHANGELOG, optionally tags. Never pushes."),
    )
    release.add_argument(
        "--path", default=".", help="Project directory (default: current directory)"
    )
    release.add_argument(
        "--bump",
        default="patch",
        choices=("major", "minor", "patch"),
        help="Which semver level to bump (default: patch)",
    )
    release.add_argument(
        "--apply",
        action="store_true",
        help="Write the version bump to pyproject.toml. Default is dry-run.",
    )
    release.add_argument(
        "--tag",
        action="store_true",
        help="Also create a local git tag (requires --apply). Never pushes.",
    )
    release.add_argument(
        "--summary",
        default="",
        help="One-line summary for the CHANGELOG stub.",
    )
    add_runtime_options(release, json_output=True)

    # PH-12 Slice 12.4: `mythic-vibe rollback`.
    rollback = sub.add_parser(
        "rollback",
        help=_help("Summarise commits + files between a baseline ref and HEAD (read-only)"),
    )
    rollback.add_argument(
        "--path", default=".", help="Project directory (default: current directory)"
    )
    rollback.add_argument(
        "--since",
        required=True,
        help="Baseline git ref (e.g. v1.2.3 or a sha) to compare against HEAD",
    )
    add_runtime_options(rollback, json_output=True)

    # PH-11 Slice 11.7: `mythic-vibe security audit`.
    security = sub.add_parser(
        "security",
        help=_help("Security audit + sandbox / approval / privacy policy reporting (PH-11)"),
    )
    security_sub = security.add_subparsers(dest="security_command", required=True)
    security_audit = security_sub.add_parser(
        "audit",
        help=_help("Run secret scan + dangerous-pattern scan; report active policy state"),
    )
    security_audit.add_argument(
        "--path", default=".", help="Project directory (default: current directory)"
    )
    security_audit.add_argument(
        "--approval",
        default=None,
        choices=("suggest", "auto", "partial"),
        help="Override approval mode for this run",
    )
    add_runtime_options(security_audit, json_output=True)

    config = sub.add_parser("config", help=_help("Show or manage configuration values"))
    config.add_argument("--path", default=".", help="Project directory used for local overrides")
    add_runtime_options(config, json_output=True)
    config_sub = config.add_subparsers(dest="config_command", required=False)
    config_set = config_sub.add_parser("set", help=_help("Set a dotted configuration value"))
    config_set.add_argument("key", help="Dotted key, e.g. core.default_model")
    config_set.add_argument("value", help="String value")
    config_set.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(config_set, json_output=True, dry_run=True)

    state = sub.add_parser("state", help=_help("Inspect and validate Mythic project state"))
    state_sub = state.add_subparsers(dest="state_command", required=True)
    state_show = state_sub.add_parser("show", help=_help("Show schema-versioned Mythic project state"))
    state_show.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(state_show, json_output=True)
    state_validate = state_sub.add_parser("validate", help=_help("Validate mythic/status.json against the state contract"))
    state_validate.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(state_validate, json_output=True)

    db = sub.add_parser("db", help=_help("Database maintenance tasks"))
    add_runtime_options(db)
    db_sub = db.add_subparsers(dest="db_command", required=True)
    db_migrate = db_sub.add_parser("migrate", help=_help("Create/upgrade local weave database"))
    db_migrate.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(db_migrate, json_output=True, dry_run=True)

    plunder = sub.add_parser(
        "plunder",
        help=_help("Inspect, plan, fetch, apply, and record lawful single-file reuse"),
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
    plunder_inspect = plunder_sub.add_parser("inspect", help=_help("Inspect source repo license posture"))
    plunder_inspect.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plunder_inspect.add_argument("--repo", required=True, help="GitHub repo in owner/name form")
    plunder_inspect.add_argument("--ref", default="main", help="Branch/tag/SHA in source repo (default: main)")
    plunder_inspect.add_argument("--token-env", default="GITHUB_TOKEN", help="Environment variable holding a GitHub token")
    add_runtime_options(plunder_inspect, json_output=True, dry_run=True)
    plunder_plan = plunder_sub.add_parser("plan", help=_help("Create a license-aware plunder plan"))
    plunder_plan.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plunder_plan.add_argument("--repo", required=True, help="GitHub repo in owner/name form")
    plunder_plan.add_argument("--source", required=True, help="Source file path in the repo")
    plunder_plan.add_argument("--dest", required=True, help="Destination path in this project")
    plunder_plan.add_argument("--ref", default="main", help="Branch/tag/SHA in source repo (default: main)")
    plunder_plan.add_argument("--modifications", default="Unmodified import planned.", help="Planned modification notes")
    plunder_plan.add_argument("--token-env", default="GITHUB_TOKEN", help="Environment variable holding a GitHub token")
    add_runtime_options(plunder_plan, json_output=True, dry_run=True)
    plunder_fetch = plunder_sub.add_parser("fetch", help=_help("Fetch a source file into the plunder cache"))
    plunder_fetch.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plunder_fetch.add_argument("--repo", required=True, help="GitHub repo in owner/name form")
    plunder_fetch.add_argument("--source", required=True, help="Source file path in the repo")
    plunder_fetch.add_argument("--ref", default="main", help="Branch/tag/SHA in source repo (default: main)")
    plunder_fetch.add_argument("--token-env", default="GITHUB_TOKEN", help="Environment variable holding a GitHub token")
    add_runtime_options(plunder_fetch, json_output=True, dry_run=True)
    plunder_apply = plunder_sub.add_parser("apply", help=_help("Apply a fetched source file from the current plunder plan"))
    plunder_apply.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plunder_apply.add_argument("--plan", default="", help="Optional plan path (default: mythic/imports/plunder_plan.json)")
    plunder_apply.add_argument("--modifications", default="", help="Modification notes to record")
    plunder_apply.add_argument("--notice", action="store_true", help="Append a NOTICE entry")
    plunder_apply.add_argument("--force", action="store_true", help="Allow overwrite or force an incompatible license")
    add_runtime_options(plunder_apply, json_output=True, dry_run=True)
    plunder_record = plunder_sub.add_parser("record", help=_help("Record provenance from the current plunder plan"))
    plunder_record.add_argument("--path", default=".", help="Project directory (default: current directory)")
    plunder_record.add_argument("--plan", default="", help="Optional plan path (default: mythic/imports/plunder_plan.json)")
    plunder_record.add_argument("--modifications", default="", help="Modification notes to record")
    plunder_record.add_argument("--notice", action="store_true", help="Append a NOTICE entry")
    add_runtime_options(plunder_record, json_output=True, dry_run=True)

    # Phase 20.6 (audit remediation 2026-05-03): top-level
    # provenance command. Currently one subcommand: verify.
    # Future v1.x slices may add sign / attest once Sigstore
    # lands (PH-21.5).
    provenance_cmd = sub.add_parser(
        "provenance",
        help=_help("Verify checksums of plunder-imported files against recorded provenance."),
    )
    provenance_sub = provenance_cmd.add_subparsers(
        dest="provenance_command", required=True
    )
    provenance_verify = provenance_sub.add_parser(
        "verify",
        help=_help("Verify each manifest entry's local file SHA against the recorded source SHA."),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe provenance verify
              mythic-vibe provenance verify --json
            """
        ),
    )
    provenance_verify.add_argument(
        "--path", default=".", help="Project directory (default: current directory)"
    )
    add_runtime_options(provenance_verify, json_output=True)
    # Phase 20.G (audit remediation 2026-05-03): per-line
    # modification attestation. Pairs with verify (binary equality)
    # by saying WHICH lines drifted when the SHAs differ.
    provenance_attest = provenance_sub.add_parser(
        "attest",
        help=_help("Compute per-line attestation between a local file and an explicit upstream original."),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe provenance attest --destination src/a.py --original cache/a.py
              mythic-vibe provenance attest --destination src/a.py --original cache/a.py --json
            """
        ),
    )
    provenance_attest.add_argument(
        "--path", default=".", help="Project directory (default: current directory)"
    )
    provenance_attest.add_argument(
        "--destination", required=True, help="Project-relative path of the local file to attest."
    )
    provenance_attest.add_argument(
        "--original", required=True, help="Path to the upstream original (project-relative or absolute)."
    )
    add_runtime_options(provenance_attest, json_output=True)

    # Phase 20.A (audit remediation 2026-05-03): persona
    # presets — opt-in bundles of defaults. Default behavior
    # across the rest of the CLI is preserved when no persona
    # is applied.
    persona_cmd = sub.add_parser(
        "persona",
        help=_help("Apply or inspect operator persona presets (solo / team-lead / auditor)."),
    )
    persona_sub = persona_cmd.add_subparsers(
        dest="persona_command", required=True
    )
    persona_apply = persona_sub.add_parser(
        "apply",
        help=_help("Write a preset to mythic/persona.json."),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe persona apply --preset solo
              mythic-vibe persona apply --preset auditor --force
            """
        ),
    )
    persona_apply.add_argument("--path", default=".", help="Project directory (default: current directory)")
    persona_apply.add_argument(
        "--preset",
        required=True,
        choices=["solo", "team-lead", "auditor"],
        help="Persona preset to apply.",
    )
    persona_apply.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing mythic/persona.json.",
    )
    add_runtime_options(persona_apply, json_output=True)
    persona_show = persona_sub.add_parser(
        "show",
        help=_help("Show the active persona (or 'none' when no preset is applied)."),
    )
    persona_show.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(persona_show, json_output=True)

    # Phase 20.H (audit remediation 2026-05-03): top-level review
    # commands. Currently one subcommand: architecture.
    review_cmd = sub.add_parser(
        "review",
        help=_help("Generate governance review checklists (quarterly architecture review)."),
    )
    review_sub = review_cmd.add_subparsers(
        dest="review_command", required=True
    )
    review_arch = review_sub.add_parser(
        "architecture",
        help=_help("Emit the quarterly architecture review checklist (read-only)."),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe review architecture
              mythic-vibe review architecture --json
            """
        ),
    )
    review_arch.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(review_arch, json_output=True)

    ai = sub.add_parser("ai", help=_help("Manage optional AI provider integrations"))
    add_runtime_options(ai, json_output=True, dry_run=True)
    ai_sub = ai.add_subparsers(dest="ai_command", required=True)
    ai_providers = ai_sub.add_parser("providers", help=_help("List available AI providers and config status"))
    ai_providers.add_argument("--path", default=".", help="Project directory used for provider logs (default: current directory)")
    add_runtime_options(ai_providers, json_output=True)
    ai_test = ai_sub.add_parser("test", help=_help("Dry-run a provider against a packet payload"))
    ai_test.add_argument("--path", default=".", help="Project directory used to resolve packet IDs and logs")
    ai_test.add_argument("--provider", required=True, choices=sorted(ProviderRegistry().providers().keys()))
    ai_test.add_argument("--packet", required=True, help="Packet text or identifier to estimate/run")
    add_runtime_options(ai_test, json_output=True)
    ai_run = ai_sub.add_parser("run", help=_help("Run a provider in explicit provider mode"))
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
    ai_run.add_argument(
        "--no-fallback",
        action="store_true",
        help=(
            "Disable the routing fallback chain — call the chosen provider "
            "directly. Default behaviour falls forward onto copy-paste when "
            "the primary fails or is misconfigured."
        ),
    )
    add_runtime_options(ai_run, json_output=True, dry_run=True)

    # PH-06 Slice 6.4: streaming output.
    ai_stream = ai_sub.add_parser(
        "stream",
        help=_help("Stream a provider response token by token (PH-06 Slice 6.4). Ctrl-C cancels cleanly."),
    )
    ai_stream.add_argument(
        "--path",
        default=".",
        help="Project directory used to resolve packet IDs and logs",
    )
    ai_stream.add_argument(
        "--provider",
        required=True,
        choices=sorted(ProviderRegistry().providers().keys()),
    )
    ai_stream.add_argument(
        "--packet", required=True, help="Packet text or identifier to stream"
    )
    add_runtime_options(ai_stream, json_output=True, dry_run=True)
    ai_route = ai_sub.add_parser(
        "route",
        help=_help("Explain how a (role, task_type) would route through the provider table"),
    )
    ai_route.add_argument(
        "--path",
        default=".",
        help="Project directory (used to load mythic/ai/routing.json overlay)",
    )
    ai_route.add_argument(
        "--role",
        default="Forge Worker",
        help="Mythic role to route (default: Forge Worker)",
    )
    ai_route.add_argument(
        "--task",
        default="*",
        help="Task type to route (default: *)",
    )
    ai_route.add_argument(
        "--explain",
        action="store_true",
        help="Verbose trace — show every rule the router considered",
    )
    ai_route.add_argument(
        "--no-hardware",
        action="store_true",
        help="Skip hardware detection; treat all hardware predicates as pass",
    )
    add_runtime_options(ai_route, json_output=True)
    ai_telemetry = ai_sub.add_parser(
        "telemetry",
        help=_help("Read recent provider calls from mythic/ai/provider_calls.jsonl"),
    )
    ai_telemetry.add_argument(
        "--path",
        default=".",
        help="Project directory (default: current directory)",
    )
    ai_telemetry.add_argument(
        "--provider",
        default="",
        help="Filter to a single provider name (default: all)",
    )
    ai_telemetry.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum entries to return, newest first (default: 20)",
    )
    add_runtime_options(ai_telemetry, json_output=True)
    ai_models = ai_sub.add_parser(
        "models",
        help=(
            "List models for a provider. Static catalog by default; "
            "--remote hits the provider's models endpoint live "
            "(Anthropic / OpenAI / Gemini / OpenRouter)."
        ),
    )
    ai_models.add_argument(
        "--path",
        default=".",
        help="Project directory used for provider logs (default: current directory)",
    )
    ai_models.add_argument(
        "--provider",
        required=True,
        choices=sorted(ProviderRegistry().providers().keys()),
    )
    # Phase D 2026-05-02 (audit remediation, finding #5): remote
    # listing flag. When set, the dispatcher calls
    # ``provider.list_models(remote=True)`` which hits the documented
    # listing endpoint. Falls back to the static catalog with a
    # warning if the API key is missing or the remote call fails.
    ai_models.add_argument(
        "--remote",
        action="store_true",
        help=(
            "Hit the provider's models endpoint live instead of "
            "returning the static catalog. Falls back to static + "
            "warning on API key / HTTP error."
        ),
    )
    add_runtime_options(ai_models, json_output=True)
    # Phase 20.4 (audit remediation 2026-05-03): ai recommend —
    # pure-policy DSL scoring static-catalog models against
    # operator-supplied criteria. Zero provider calls.
    ai_recommend = ai_sub.add_parser(
        "recommend",
        help=_help("Score and rank models from the static catalog against task constraints."),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe ai recommend --task "Build a calm CLI" --top 3
              mythic-vibe ai recommend --max-context 100000 --vision --json
              mythic-vibe ai recommend --cost-class cheap --family openai
            """
        ),
    )
    ai_recommend.add_argument(
        "--task", default="", help="Task description (free text; used for keyword heuristics)."
    )
    ai_recommend.add_argument(
        "--max-context",
        type=int,
        default=0,
        help="Minimum acceptable context window in tokens (0 = any).",
    )
    ai_recommend.add_argument(
        "--vision",
        action="store_true",
        help="Require vision capability (multimodal image input).",
    )
    ai_recommend.add_argument(
        "--cost-class",
        default=None,
        choices=["cheap", "standard", "premium"],
        help="Filter by cost class (heuristic from model id).",
    )
    ai_recommend.add_argument(
        "--family",
        default=None,
        help='Restrict to one family (e.g. "anthropic"). Default: all supported families.',
    )
    ai_recommend.add_argument(
        "--top",
        type=int,
        default=3,
        help="How many top picks to return (default: 3; 0 = all candidates).",
    )
    add_runtime_options(ai_recommend, json_output=True)
    ai_ingest = ai_sub.add_parser("ingest-response", help=_help("Record a provider response as metadata only"))
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
        help=_help("Run verification gates and write a durable verification record"),
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
    # Phase 20.B (audit remediation 2026-05-03): replay shortcut.
    # When --replay is passed, verify delegates to forge resume
    # (PH-03 slice 3.8) — re-runs the last forge workflow from
    # its first non-succeeded step. Useful when an Auditor gate
    # failure was the last verify outcome and the operator
    # wants to re-execute the same workflow without re-typing
    # the original `forge run` command.
    verify.add_argument(
        "--replay",
        action="store_true",
        help="Delegate to `forge resume` for the most recent (or specified) workflow.",
    )
    verify.add_argument(
        "--provider",
        default="",
        help="(--replay only) Provider to use when re-executing the workflow. Defaults to copy-paste.",
    )
    verify.add_argument(
        "--workflow",
        default="",
        help="(--replay only) Workflow id to resume; default is the most recent one.",
    )
    verify.add_argument(
        "--strict",
        action="store_true",
        help="(--replay only) Abort on Auditor gate failure (forwarded to forge resume).",
    )
    add_runtime_options(verify, json_output=True)

    slash = sub.add_parser(
        "slash",
        help=_help("Inspect slash command catalog (built-in + plugin-contributed)"),
    )
    slash_sub = slash.add_subparsers(dest="slash_command", required=True)
    slash_list = slash_sub.add_parser(
        "list",
        help=_help("List builtin slash commands and any contributed by enabled plugins"),
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
        help=_help("Show provenance + argparse help for one slash command"),
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
        help=_help("Open an interactive prompt that dispatches to existing CLI commands"),
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
        help=_help("Open the Textual-based TUI showing project status (requires the [tui] extra)"),
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
    # Phase 20.I (audit remediation 2026-05-03): opt-in panels.
    # Comma-separated list. Recognised values: heatmap, risk.
    # Default empty preserves the existing TUI shape.
    tui.add_argument(
        "--panels",
        default="",
        metavar="LIST",
        help="Opt-in TUI panels (comma-separated). Recognised: heatmap, risk. Default: none.",
    )
    add_runtime_options(tui)

    # --- PH-02 slice 2.2: developer-tool shortcuts ---

    test_cmd = sub.add_parser(
        "test",
        help=_help("Run the project's test suite (pytest by default)"),
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
        help=_help("Run ruff check across the project"),
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
        help=_help("Run mypy across the project"),
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
        help=_help("Add an artefact to an existing Mythic project (adr / task / interface / invariant / risk)"),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe scaffold adr --title "Adopt knowledge graph"
              mythic-vibe scaffold adr --title "Use SQLite for state" --dry-run
              mythic-vibe scaffold adr --title "Pin Python 3.11" --json
              mythic-vibe scaffold task --title "Wire chat-bridge poll loop"
              mythic-vibe scaffold interface --title "Plugin runtime contract"
              mythic-vibe scaffold invariant --title "Forge ledger is append-only"
              mythic-vibe scaffold risk --title "Provider-key leak in handoff"

            Artefacts and where they land:
              adr        -> docs/ADRS/ADR-NNNN-<slug>.md
              task       -> mythic/tasks/TASK-NNNN-<slug>.md
              interface  -> docs/interfaces/INT-NNNN-<slug>.md
              invariant  -> docs/invariants/INV-NNNN-<slug>.md
              risk       -> docs/risks/RISK-NNNN-<slug>.md

            Notes:
              The four extended types (task / interface / invariant / risk)
              were added additively on 2026-05-02 (closing the long-standing
              "land in PH-10 slice 10.4" forward reference). The adr path
              is unchanged from its original implementation.
            """
        ),
    )
    scaffold_cmd.add_argument(
        "artefact",
        # Additive 2026-05-02: choices widened from ["adr"] to include the
        # four new artefact types. The argparse-level allowlist is the only
        # mechanically-additive way to make the new types reachable through
        # the CLI; ``cmd_scaffold``'s legacy USER_INPUT_ERROR branch is
        # preserved unchanged for direct-call callers passing an unknown
        # artefact (e.g. existing tests).
        choices=["adr", "task", "interface", "invariant", "risk"],
        help="Artefact type (adr / task / interface / invariant / risk)",
    )
    scaffold_cmd.add_argument("--title", required=True, help="Human-readable title for the artefact")
    scaffold_cmd.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(scaffold_cmd, json_output=True, dry_run=True)

    changelog_cmd = sub.add_parser(
        "changelog",
        help=_help("Print or validate the project's CHANGELOG.md [Unreleased] section"),
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
        help=_help("Print the CLI version (subcommand form of --version)"),
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
        help=_help("Multi-agent forge orchestrator (dry-run + ledger inspection today; provider-backed run lands in slice 3.5)"),
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
        help=_help("Build a workflow plan and per-agent packets (no provider call)"),
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
        help=_help("Run the forge end-to-end through a configured provider (PH-03 slice 3.5)"),
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
        help=_help("Resume a partially-completed forge run from the ledger (PH-03 slice 3.8)"),
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
        help=_help("Inspect mythic/forge_ledger.json (per-agent step records)"),
    )
    forge_ledger_sub = forge_ledger.add_subparsers(dest="ledger_command", required=True)

    ledger_list = forge_ledger_sub.add_parser("list", help=_help("List every recorded forge ledger entry"))
    ledger_list.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(ledger_list, json_output=True)

    ledger_latest = forge_ledger_sub.add_parser("latest", help=_help("Show the most recent N entries"))
    ledger_latest.add_argument("--limit", type=int, default=5, help="Window size (default 5)")
    ledger_latest.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(ledger_latest, json_output=True)

    ledger_show = forge_ledger_sub.add_parser("show", help=_help("Show every entry for a given workflow"))
    ledger_show.add_argument("--workflow", required=True, help="Workflow id (e.g. WF-20260429-deadbeef)")
    ledger_show.add_argument("--step", default="", help="Optional step filter (e.g. step-02)")
    ledger_show.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(ledger_show, json_output=True)

    forge_reflection = forge_sub.add_parser(
        "reflection",
        help=_help("Inspect mythic/reflections/<workflow_id>.{md,json} (slice 3.7 per-cycle reflections)"),
    )
    forge_reflection_sub = forge_reflection.add_subparsers(
        dest="reflection_command", required=True
    )

    reflection_list = forge_reflection_sub.add_parser(
        "list", help=_help("List every recorded forge reflection")
    )
    reflection_list.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(reflection_list, json_output=True)

    reflection_latest = forge_reflection_sub.add_parser(
        "latest", help=_help("Show the most recently written reflection (markdown by default)")
    )
    reflection_latest.add_argument("--path", default=".", help="Project directory (default: current directory)")
    add_runtime_options(reflection_latest, json_output=True)

    reflection_show = forge_reflection_sub.add_parser(
        "show", help=_help("Show one reflection by workflow id")
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
            help=_help(f"Capture a Mythic Phase Record for the {_phase} phase"),
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
        help=_help("List configured AI providers (alias of `ai providers`)"),
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
        help=_help("Run a doctor pass and emit JSON (alias of `doctor --json`)"),
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

    # --- Reforge Phase 7: GitHub workspace system ----------------------
    workspace_cmd = sub.add_parser(
        "workspace",
        help=_help("Manage local Git/GitHub workspaces"),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe workspace status
              mythic-vibe workspace clone https://github.com/owner/repo --yes
              mythic-vibe workspace open ./repo
              mythic-vibe workspace branch feature/memory --yes
              mythic-vibe workspace pr --title "Fix memory"
            """
        ),
    )
    workspace_sub = workspace_cmd.add_subparsers(dest="workspace_command", required=True)

    workspace_status = workspace_sub.add_parser("status", help=_help("Detect current repo and tracked workspaces"))
    workspace_status.add_argument("--path", default=".")
    workspace_status.add_argument("--workspace-root", default="")
    add_runtime_options(workspace_status, json_output=True)

    workspace_clone = workspace_sub.add_parser("clone", help=_help("Clone a repo into the workspace root"))
    workspace_clone.add_argument("repo_url")
    workspace_clone.add_argument("--name", default="")
    workspace_clone.add_argument("--workspace-root", default="")
    workspace_clone.add_argument("--yes", action="store_true", help="Actually run git clone")
    add_runtime_options(workspace_clone, json_output=True)

    workspace_open = workspace_sub.add_parser("open", help=_help("Record an existing local Git repo as a workspace"))
    workspace_open.add_argument("repo_path")
    workspace_open.add_argument("--name", default="")
    workspace_open.add_argument("--workspace-root", default="")
    add_runtime_options(workspace_open, json_output=True)

    workspace_branch = workspace_sub.add_parser("branch", help=_help("Create and track a branch in the current repo"))
    workspace_branch.add_argument("branch")
    workspace_branch.add_argument("--path", default=".")
    workspace_branch.add_argument("--workspace-root", default="")
    workspace_branch.add_argument("--yes", action="store_true", help="Actually create and switch to the branch")
    add_runtime_options(workspace_branch, json_output=True)

    workspace_track = workspace_sub.add_parser("track", help=_help("Track the current or named branch"))
    workspace_track.add_argument("--path", default=".")
    workspace_track.add_argument("--branch", default="")
    workspace_track.add_argument("--workspace-root", default="")
    add_runtime_options(workspace_track, json_output=True)

    workspace_pr = workspace_sub.add_parser("pr", help=_help("Prepare a pull request draft"))
    workspace_pr.add_argument("--path", default=".")
    workspace_pr.add_argument("--title", default="")
    workspace_pr.add_argument("--body", default="")
    workspace_pr.add_argument("--base", default="main")
    workspace_pr.add_argument("--workspace-root", default="")
    workspace_pr.add_argument("--write", action="store_true", help="Write the draft under the workspace root")
    add_runtime_options(workspace_pr, json_output=True)

    workspace_plan = workspace_sub.add_parser("plan", help=_help("Propose workspace actions from a natural request"))
    workspace_plan.add_argument("request", nargs="+")
    workspace_plan.add_argument("--workspace-root", default="")
    add_runtime_options(workspace_plan, json_output=True)

    # --- PH-05 slice 5.5 / 5.6: graph query + visualize ---
    graph_cmd = sub.add_parser(
        "graph",
        help=_help("Read-only queries over the project knowledge graph"),
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
        help=_help("Run a relevance-ranked retrieval against the graph"),
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
        help=_help("Find entities matching a kind / name / path filter"),
    )
    graph_entity.add_argument("--path", default=".")
    graph_entity.add_argument("--kind", default="", help="Restrict to entity kind")
    graph_entity.add_argument("--name", default="", help="Substring match on entity name")
    graph_entity.add_argument(
        "--name-path", default="", help="Substring match on entity path"
    )
    add_runtime_options(graph_entity, json_output=True)

    graph_edges = graph_sub.add_parser("edges", help=_help("List edges by filter"))
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
        help=_help("Render the slice 5.4 session brief from the graph"),
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
        help=_help("Export the graph as Mermaid (default) or DOT"),
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

    # --- Reforge Phase 6: private knowledge reader ---------------------
    knowledge_cmd = sub.add_parser(
        "knowledge",
        help=_help("Read-only private knowledge sources: status, sources, search"),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe knowledge status
              mythic-vibe knowledge sources
              mythic-vibe knowledge search "Hermes memory"
            """
        ),
    )
    knowledge_sub = knowledge_cmd.add_subparsers(dest="knowledge_command", required=True)

    knowledge_status = knowledge_sub.add_parser(
        "status",
        help=_help("Show configured private knowledge-source health"),
    )
    knowledge_status.add_argument("--path", default=".")
    add_runtime_options(knowledge_status, json_output=True)

    knowledge_sources = knowledge_sub.add_parser(
        "sources",
        help=_help("List configured private knowledge sources"),
    )
    knowledge_sources.add_argument("--path", default=".")
    add_runtime_options(knowledge_sources, json_output=True)

    knowledge_search = knowledge_sub.add_parser(
        "search",
        help=_help("Search configured private knowledge sources read-only"),
    )
    knowledge_search.add_argument("query", nargs="+", help="Search query")
    knowledge_search.add_argument("--path", default=".")
    knowledge_search.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum results to return (default: 5)",
    )
    add_runtime_options(knowledge_search, json_output=True)

    # --- PH-15 + Reforge Phase 5: memory show / list / compact / rehydrate / last / spine ---
    memory_cmd = sub.add_parser(
        "memory",
        help=_help("Conversation memory and SQLite project spine"),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe memory list
              mythic-vibe memory show --id CV-ABCDEF
              mythic-vibe memory compact --id CV-ABCDEF --keep-recent 3
              mythic-vibe memory rehydrate --phase build
              mythic-vibe memory last
              mythic-vibe memory spine --json
            """
        ),
    )
    memory_sub = memory_cmd.add_subparsers(dest="memory_command", required=True)

    memory_list = memory_sub.add_parser(
        "list", help=_help("List every conversation record (newest first)")
    )
    memory_list.add_argument("--path", default=".")
    add_runtime_options(memory_list, json_output=True)

    memory_show = memory_sub.add_parser(
        "show", help=_help("Print one conversation record by id")
    )
    memory_show.add_argument("--path", default=".")
    memory_show.add_argument("--id", required=True, help="Conversation id (CV-XXXXXX)")
    add_runtime_options(memory_show, json_output=True)

    memory_compact = memory_sub.add_parser(
        "compact",
        help=_help("Compact a conversation into a summary sidecar"),
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
        help=_help("Build a session-resume brief from graph + handoff + latest conversation"),
    )
    memory_rehydrate.add_argument("--path", default=".")
    memory_rehydrate.add_argument(
        "--phase",
        default="build",
        help="Current Mythic phase to scope the brief (default: build)",
    )
    add_runtime_options(memory_rehydrate, json_output=True)

    memory_last = memory_sub.add_parser(
        "last",
        help=_help("Answer what the project was doing last time from SQLite memory"),
    )
    memory_last.add_argument("--path", default=".")
    add_runtime_options(memory_last, json_output=True)

    memory_spine = memory_sub.add_parser(
        "spine",
        help=_help("Show SQLite memory-spine status and recent entries"),
    )
    memory_spine.add_argument("--path", default=".")
    memory_spine.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Recent entry count to include (default: 10)",
    )
    add_runtime_options(memory_spine, json_output=True)

    # --- PH-07 slices 7.1-7.3: voice & multimodal ---
    voice_cmd = sub.add_parser(
        "voice",
        help=_help("Voice transcription + TTS (opt-in; stub engines work without extras)"),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe voice transcribe --file fixture.txt
              mythic-vibe voice transcribe --file fixture.wav --engine whisper
              mythic-vibe voice transcribe --file fixture.txt --capture-intent --task "Refactor router"
              mythic-vibe voice say "hello operator"
            """
        ),
    )
    voice_sub = voice_cmd.add_subparsers(dest="voice_command", required=True)

    voice_transcribe = voice_sub.add_parser(
        "transcribe",
        help=_help("Transcribe an audio / text fixture; --capture-intent writes a Mythic Phase Record"),
    )
    voice_transcribe.add_argument(
        "--path",
        default=".",
        help="Project directory (used for --capture-intent writes)",
    )
    voice_transcribe.add_argument(
        "--file",
        default="",
        help="Path to the source file (audio / text fixture). Required unless --mic is set.",
    )
    voice_transcribe.add_argument(
        "--mic",
        action="store_true",
        help=(
            "Record from the system microphone instead of reading --file. "
            "Requires `pip install sounddevice numpy`."
        ),
    )
    voice_transcribe.add_argument(
        "--duration",
        type=float,
        default=5.0,
        help="Mic capture duration in seconds (default: 5.0). Only used with --mic.",
    )
    voice_transcribe.add_argument(
        "--engine",
        default="stub",
        choices=("stub", "whisper"),
        help="Transcription engine (default: stub; whisper requires `pip install openai-whisper`)",
    )
    voice_transcribe.add_argument(
        "--language", default="en", help="Spoken language hint (default: en)"
    )
    voice_transcribe.add_argument(
        "--model",
        default="base",
        help="Engine model name (default: base; ignored by stub engine)",
    )
    voice_transcribe.add_argument(
        "--capture-intent",
        action="store_true",
        help="Pipe the transcription into a fresh intent Mythic Phase Record",
    )
    voice_transcribe.add_argument(
        "--task",
        default="",
        help="Required when --capture-intent is set: short task name for the phase record",
    )
    add_runtime_options(voice_transcribe, json_output=True)

    voice_say = voice_sub.add_parser(
        "say",
        help=_help("Speak text via the configured TTS engine (default: stub; logs to stderr)"),
    )
    voice_say.add_argument(
        "--path",
        default=".",
        help="Project directory (default: current directory)",
    )
    voice_say.add_argument("text", help="Text to speak")
    voice_say.add_argument(
        "--engine",
        default="stub",
        choices=("stub", "chatterbox"),
        help="TTS engine (default: stub; chatterbox requires `pip install chatterbox`)",
    )
    voice_say.add_argument(
        "--force",
        action="store_true",
        help="Speak even when MYTHIC_VOICE_TTS_ENABLED is not set",
    )
    add_runtime_options(voice_say, json_output=True)

    # --- PH-06 slice 6.6: hardware profile ---
    hardware_cmd = sub.add_parser(
        "hardware",
        help=_help("Detect and (optionally) record the host hardware profile"),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe hardware
              mythic-vibe hardware --json
              mythic-vibe hardware --write --path ./project
            """
        ),
    )
    hardware_cmd.add_argument(
        "--path",
        default=".",
        help="Project directory used as the docs/ root for --write (default: current directory)",
    )
    hardware_cmd.add_argument(
        "--write",
        action="store_true",
        help="Persist the profile to docs/hardware_profiles.md plus a JSON sidecar",
    )
    add_runtime_options(hardware_cmd, json_output=True)

    # --- PH-13 slice 13.1: drift scan ---
    # Standalone drift-detection scan. Doctor integration (slice 13.2)
    # surfaces the same findings under its own envelope; this top-level
    # subcommand is the focused entry point operators reach for when
    # they want only drift output.
    drift_cmd = sub.add_parser(
        "drift",
        help=_help("Scan the project for drift between docs, code, and decisions"),
        **_example_parser_kwargs(
            """
            Examples:
              mythic-vibe drift
              mythic-vibe drift --path ./project --json
              mythic-vibe drift dashboard            # Phase 20.E rollup
              mythic-vibe drift dashboard --json
            """
        ),
    )
    # Phase 20.E (audit remediation 2026-05-03): optional
    # positional sub-verb. Default "" preserves the original
    # flat ``drift`` behavior. ``drift dashboard`` runs the
    # rollup view.
    drift_cmd.add_argument(
        "subcommand",
        nargs="?",
        default="",
        choices=["", "dashboard"],
        help="Optional sub-verb (currently: dashboard).",
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
        raw_argv = list(sys.argv[1:] if argv is None else argv)
        if not raw_argv:
            from .interactive_shell import run_interactive_shell

            return run_interactive_shell()

        if raw_argv[0] == "admin":
            raw_argv = raw_argv[1:]
            if not raw_argv or raw_argv[0] in {"-h", "--help"}:
                parser = build_parser(admin_mode=True)
                parser.print_help()
                return 0
            parser = build_parser(admin_mode=True)
        else:
            parser = build_parser(admin_mode=False)

        args = parser.parse_args(raw_argv)
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
