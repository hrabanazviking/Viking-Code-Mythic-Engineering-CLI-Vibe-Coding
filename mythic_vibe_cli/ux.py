from __future__ import annotations

from dataclasses import dataclass

from .core.state import PHASES


@dataclass(frozen=True)
class PhaseHelp:
    name: str
    purpose: str
    next_action: str
    verification: str


PHASE_GUIDE: dict[str, PhaseHelp] = {
    "intent": PhaseHelp(
        "intent",
        "Name the goal, user, and reason the work should exist.",
        'Run `mythic-vibe checkin --phase intent --update "Goal and user clarified"`.',
        "Check that SYSTEM_VISION.md and tasks/current_GOALS.md tell the same story.",
    ),
    "constraints": PhaseHelp(
        "constraints",
        "Surface boundaries, risks, licenses, safety limits, and non-goals.",
        'Run `mythic-vibe doctor --path .` and record any boundary decisions.',
        "Verify docs/DOMAIN_MAP.md and docs/COMMAND_CONTRACTS.md stay aligned with code.",
    ),
    "architecture": PhaseHelp(
        "architecture",
        "Define ownership, module boundaries, and dependency direction.",
        "Update docs/ARCHITECTURE.md or docs/DOMAIN_MAP.md before broad code changes.",
        "Run `mythic-vibe doctor --repo-boundary --path .` for boundary-sensitive work.",
    ),
    "plan": PhaseHelp(
        "plan",
        "Break the work into small, verifiable steps.",
        "Create a packet or handoff that names the next concrete implementation task.",
        "Check that each planned step has an obvious verification command.",
    ),
    "build": PhaseHelp(
        "build",
        "Write the smallest useful implementation that fits the existing design.",
        "Run focused tests as soon as the first behavior exists.",
        "Use `pytest -q` before moving into verify.",
    ),
    "verify": PhaseHelp(
        "verify",
        "Prove the change behaves as claimed.",
        "Run `mythic-vibe verify --commands --docs --invariants --record`.",
        "Confirm the latest verification artifact reports `pass`.",
    ),
    "reflect": PhaseHelp(
        "reflect",
        "Preserve what changed, why it changed, and what should happen next.",
        'Run `mythic-vibe reflect --summary "What changed"`.',
        "Run `mythic-vibe resume --path .` and confirm the next action is obvious.",
    ),
}


ARTIFACT_GUIDE: dict[str, dict[str, str]] = {
    "status": {
        "path": "mythic/status.json",
        "purpose": "Current project state, phase history, and latest verification pointer.",
        "verify": "Run `mythic-vibe status --json` or `mythic-vibe state validate --path .`.",
    },
    "packet": {
        "path": "mythic/packets/",
        "purpose": "Reusable prompt packets with role, context, and safety sections.",
        "verify": "Run `mythic-vibe packet list --json`.",
    },
    "handoff": {
        "path": "docs/SESSION_HANDOFF.md",
        "purpose": "Latest future-self handoff and next recommended action.",
        "verify": "Run `mythic-vibe resume --json`.",
    },
    "verification": {
        "path": "mythic/verifications/latest.json",
        "purpose": "Latest recorded proof that checks passed or failed.",
        "verify": "Run `mythic-vibe verify --commands --docs --invariants --record`.",
    },
    "plunder": {
        "path": "mythic/imports/plunder_manifest.json",
        "purpose": "Traceability records for imported source files.",
        "verify": "Run `mythic-vibe plunder record --dry-run` with a valid plan.",
    },
    "plugins": {
        "path": "mythic/plugins.json",
        "purpose": "Versioned registry of plugin entrypoints, hooks, and enabled state.",
        "verify": "Run `mythic-vibe plugin list --json`.",
    },
}


EXAMPLES = [
    {
        "name": "Start a project",
        "command": 'mythic-vibe init --goal "Build a calm CLI" --noob',
        "next": "Run `mythic-vibe status`.",
    },
    {
        "name": "Scan local context",
        "command": "mythic-vibe scan --path . --json",
        "next": "Use the generated mythic/project_index.json in a packet.",
    },
    {
        "name": "Create a packet",
        "command": 'mythic-vibe packet create --task "Implement the next feature" --phase build --role "Forge Worker"',
        "next": "Review the packet and send it to your chosen assistant.",
    },
    {
        "name": "Verify work",
        "command": "mythic-vibe verify --commands --docs --invariants --record",
        "next": "Reflect only after verification passes.",
    },
    {
        "name": "Close the session",
        "command": 'mythic-vibe reflect --summary "Feature implemented and verified"',
        "next": "Use `mythic-vibe resume` in the next session.",
    },
]


def phase_names() -> list[str]:
    return list(PHASES)


def artifact_names() -> list[str]:
    return sorted(ARTIFACT_GUIDE)


def next_phase_from_completed(completed: list[str]) -> str:
    for phase in PHASES:
        if phase not in completed:
            return phase
    return "reflect"


def bash_completion() -> str:
    commands = " ".join(
        [
            "init",
            "status",
            "next",
            "examples",
            "guide",
            "tutorial",
            "explain",
            "scan",
            "packet",
            "verify",
            "reflect",
            "handoff",
            "resume",
            "doctor",
            "plugin",
            "plunder",
            "config",
            "db",
            "ai",
        ]
    )
    return (
        "_mythic_vibe_complete() {\n"
        "  COMPREPLY=($(compgen -W \""
        + commands
        + "\" -- \"${COMP_WORDS[COMP_CWORD]}\"))\n"
        "}\n"
        "complete -F _mythic_vibe_complete mythic-vibe mythic\n"
    )


def zsh_completion() -> str:
    commands = " ".join(f"{command}:mythic-vibe command" for command in bash_completion().split('"')[1].split())
    return f"#compdef mythic-vibe mythic\n_arguments '1:command:(({commands}))'\n"


def powershell_completion() -> str:
    commands = bash_completion().split('"')[1].split()
    quoted = ", ".join(f"'{command}'" for command in commands)
    return (
        "Register-ArgumentCompleter -CommandName mythic-vibe,mythic -ScriptBlock {\n"
        "  param($wordToComplete)\n"
        f"  @({quoted}) | Where-Object {{ $_ -like \"$wordToComplete*\" }} | ForEach-Object {{\n"
        "    [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)\n"
        "  }\n"
        "}\n"
    )
