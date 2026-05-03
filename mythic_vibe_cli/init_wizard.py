"""Phase 20.0 — opt-in ``mythic-vibe init --interactive`` wizard.

The default ``mythic-vibe init`` flow is intentionally
non-interactive: operators pass ``--goal`` (and optionally
``--noob``) and the scaffold is written deterministically. That
flow remains unchanged.

The wizard is a strictly opt-in alternate path triggered by
``--interactive``. It asks the operator a small fixed set of
questions and persists the answers to
``mythic/project_settings.json`` alongside the scaffold the
existing init code already writes:

- **Project name** — defaults to the directory's basename.
- **Goal** — required (the existing ``--goal`` field). If the
  operator passed ``--goal`` on the CLI we keep it and skip the
  prompt.
- **Default AI provider** — one of the registered providers
  (``copy-paste`` / ``local`` / ``openai`` / ``anthropic`` /
  ``gemini`` / ``openrouter`` / ``ollama`` / ``yggdrasil`` /
  ``mindspark``). Defaults to ``copy-paste`` (no key required).
- **Operator name** — defaults to ``$USER`` / ``$USERNAME``,
  falling back to ``"unknown"``.
- **Scaffold sample ADR / oath / constraint files?** — y/n.

The wizard is **idempotent**: re-running it overwrites
``mythic/project_settings.json`` only when ``--force`` is set.
Without ``--force`` it refuses to overwrite an existing settings
file (defends against accidentally clobbering operator
customization).

Cross-platform: pure stdlib (``json``, ``os``, ``pathlib``).
Wizard input is stdin-driven via callable injection so tests can
feed deterministic answers.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


# Keep in lockstep with mythic_vibe_cli.ai.registry.ProviderRegistry —
# tested by tests/test_init_wizard.py to prevent silent drift.
SUPPORTED_PROVIDERS: tuple[str, ...] = (
    "copy-paste",
    "local",
    "openai",
    "anthropic",
    "gemini",
    "openrouter",
    "ollama",
    "yggdrasil",
    "mindspark",
)

DEFAULT_PROVIDER = "copy-paste"

SETTINGS_FILENAME = "project_settings.json"
SETTINGS_SCHEMA_VERSION = 1


@dataclass
class WizardAnswers:
    """Result of one wizard run. Always serializable; carries
    enough information for ``cmd_init`` to scaffold the project
    AND for future commands to read defaults from
    ``project_settings.json``."""

    project_name: str
    goal: str
    provider: str
    operator: str
    scaffold_samples: bool
    schema_version: int = SETTINGS_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "goal": self.goal,
            "provider": self.provider,
            "operator": self.operator,
            "scaffold_samples": self.scaffold_samples,
        }


@dataclass
class WizardConfig:
    """Pre-resolved defaults handed to the wizard runner. Kept as
    a dataclass so tests can mutate fields without touching real
    env vars or filesystem state."""

    root: Path
    initial_goal: str | None = None
    default_provider: str = DEFAULT_PROVIDER
    default_operator: str = field(default_factory=lambda: _resolve_operator_default())


def _resolve_operator_default() -> str:
    """Best-effort operator name from environment. Mirrors the
    same fallback chain used in workflow phase capture
    (slice 2.3) so wizard + capture agree on operator identity."""
    for env_key in ("USER", "USERNAME"):
        value = os.environ.get(env_key)
        if value and value.strip():
            return value.strip()
    return "unknown"


def _prompt(
    reader: Callable[[str], str],
    writer: Callable[[str], None],
    label: str,
    *,
    default: str | None = None,
    choices: tuple[str, ...] | None = None,
) -> str:
    """Render a prompt, read the response via ``reader``,
    fall back to ``default`` when the operator hits ENTER on a
    field that has one. EOFError (Ctrl+D / piped stdin exhausted)
    is treated as "accept default" so unattended flows degrade
    cleanly."""
    suffix = ""
    if choices is not None:
        suffix += f" ({'/'.join(choices)})"
    if default is not None:
        suffix += f" [{default}]"
    prompt = f"{label}{suffix}: "

    while True:
        try:
            raw = reader(prompt)
        except EOFError:
            if default is None:
                raise WizardAbortedError(
                    f"interactive input ended with no value for {label!r} "
                    "and no default available"
                ) from None
            return default
        cleaned = raw.strip()
        if not cleaned:
            if default is not None:
                return default
            writer(f"  (a value is required for {label})\n")
            continue
        if choices is not None and cleaned not in choices:
            writer(
                f"  (must be one of {', '.join(choices)} — try again)\n"
            )
            continue
        return cleaned


def _prompt_yes_no(
    reader: Callable[[str], str],
    writer: Callable[[str], None],
    label: str,
    *,
    default: bool,
) -> bool:
    """Yes/no prompt; accepts y/yes/n/no, case-insensitive."""
    default_token = "y" if default else "n"
    while True:
        raw = _prompt(
            reader, writer, label,
            default=default_token,
            choices=("y", "yes", "n", "no"),
        )
        token = raw.lower()
        if token in {"y", "yes"}:
            return True
        if token in {"n", "no"}:
            return False


class WizardAbortedError(RuntimeError):
    """Raised when the wizard cannot proceed (EOF on a required
    field, invalid existing settings, refused overwrite)."""


def run_wizard(
    config: WizardConfig,
    *,
    reader: Callable[[str], str] | None = None,
    writer: Callable[[str], None] | None = None,
) -> WizardAnswers:
    """Run the wizard against the given config and return the
    operator's answers. Pure orchestration — does NOT write any
    files. Caller is responsible for persisting via
    :func:`write_project_settings`.

    ``reader``/``writer`` default to ``input``/``sys.stdout.write``
    but can be injected for tests."""
    import sys

    if reader is None:
        reader = input
    if writer is None:
        writer = sys.stdout.write

    project_name_default = config.root.name or "mythic-project"

    project_name = _prompt(
        reader, writer, "Project name",
        default=project_name_default,
    )

    if config.initial_goal is not None and config.initial_goal.strip():
        goal = config.initial_goal.strip()
        writer(f"  (goal carried in from --goal: {goal!r})\n")
    else:
        goal = _prompt(reader, writer, "Project goal")

    provider = _prompt(
        reader, writer, "Default AI provider",
        default=config.default_provider,
        choices=SUPPORTED_PROVIDERS,
    )

    operator = _prompt(
        reader, writer, "Operator name",
        default=config.default_operator,
    )

    scaffold = _prompt_yes_no(
        reader, writer,
        "Scaffold a sample ADR + oath + constraint file?",
        default=True,
    )

    return WizardAnswers(
        project_name=project_name,
        goal=goal,
        provider=provider,
        operator=operator,
        scaffold_samples=scaffold,
    )


def write_project_settings(
    root: Path,
    answers: WizardAnswers,
    *,
    force: bool = False,
) -> Path:
    """Persist the wizard's answers to
    ``<root>/mythic/project_settings.json``. Refuses to overwrite
    an existing file unless ``force=True`` to defend against
    accidental clobbering of operator customization.

    Returns the path written. Raises :class:`WizardAbortedError`
    when refusing to overwrite.
    """
    from mythic_vibe_cli.runtime.atomic_write import atomic_write_text

    settings_path = root / "mythic" / SETTINGS_FILENAME
    if settings_path.exists() and not force:
        raise WizardAbortedError(
            f"{settings_path} already exists — pass --force to overwrite"
        )

    payload = json.dumps(answers.to_dict(), indent=2, sort_keys=True) + "\n"
    atomic_write_text(settings_path, payload)
    return settings_path


def scaffold_sample_artifacts(
    root: Path,
    answers: WizardAnswers,
) -> list[Path]:
    """Write the three opt-in sample artefacts (ADR / oath /
    constraint) when ``answers.scaffold_samples`` is True.
    Returns the list of paths created (skipping any that already
    exist — never overwrites pre-authored content).
    """
    if not answers.scaffold_samples:
        return []

    from mythic_vibe_cli.runtime.atomic_write import atomic_write_text

    created: list[Path] = []
    targets = (
        (
            root / "docs" / "ADRS" / "ADR-SAMPLE-wizard.md",
            _SAMPLE_ADR.format(
                project=answers.project_name, operator=answers.operator
            ),
        ),
        (
            root / "mythic" / "oaths" / "OATH-SAMPLE.md",
            _SAMPLE_OATH.format(project=answers.project_name),
        ),
        (
            root / "mythic" / "constraints" / "CONSTRAINT-SAMPLE.md",
            _SAMPLE_CONSTRAINT.format(project=answers.project_name),
        ),
    )
    for path, content in targets:
        if path.exists():
            continue
        atomic_write_text(path, content)
        created.append(path)
    return created


_SAMPLE_ADR = """# ADR-SAMPLE — Wizard-generated example ADR

**Status:** Proposed
**Author:** {operator}
**Project:** {project}

## Context

This is a sample Architecture Decision Record generated by the
``mythic-vibe init --interactive`` wizard. Replace this body
with the real architectural choice you want to record. Delete
this file when you no longer need the example.

## Decision

State the decision in a single declarative sentence here.

## Consequences

Bullet the load-bearing consequences (positive and negative).

## Links

- `docs/ARCHITECTURE.md`
- `docs/DOMAIN_MAP.md`
"""

_SAMPLE_OATH = """# OATH-SAMPLE — Wizard-generated example oath

This is a sample operator oath for project **{project}**.

> "I will document every load-bearing decision before merging it,
> and I will not bypass verification gates without recording why."

Replace the oath text with the operator commitment that actually
governs your team's contributions. Delete this file if you don't
use oaths.
"""

_SAMPLE_CONSTRAINT = """# CONSTRAINT-SAMPLE — Wizard-generated example constraint

**Project:** {project}

This is a sample machine-checkable constraint. The Mythic Vibe
policy engine (PH-14) reads constraint files matching
``mythic/constraints/*.md`` and applies them to relevant
commands.

Example constraint body:

```yaml
constraint_id: SAMPLE-001
applies_to: ["forge", "verify"]
rule: "every forge run must be followed by `verify --record`"
severity: warning
```

Delete this file when you no longer need the example.
"""
