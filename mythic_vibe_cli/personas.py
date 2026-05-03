"""Phase 20.A — operator persona presets (opt-in).

Three named bundles of defaults that match common operator
modes. Personas are **data**, not behavior — applying a persona
writes ``mythic/persona.json`` carrying the default values for
the named mode. Existing commands optionally read from that
file as one input to their own configuration resolution
(env var > CLI flag > persona > built-in default).

The three presets:

- **`solo`** — single-developer mode. Suggest-mode approval,
  beginner-friendly verbosity, light audit cadence.
- **`team-lead`** — coordinating-developer mode. Partial-mode
  approval, intermediate verbosity, mid audit cadence,
  tighter changelog enforcement.
- **`auditor`** — review-focused mode. Suggest-mode approval
  (forces operator to review every action), advanced
  verbosity, strictest audit cadence, every plugin flagged
  for explicit review.

Default behavior is preserved: if no persona is applied, every
command reads its built-in defaults exactly as before. The
persona file is read **only when present** — operators who
never run ``mythic-vibe persona apply`` see no change.

Cross-platform: pure stdlib (``json``, ``pathlib``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


PRESET_NAMES: tuple[str, ...] = ("solo", "team-lead", "auditor")
PresetName = Literal["solo", "team-lead", "auditor"]

PERSONA_FILENAME = "persona.json"
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PersonaPreset:
    """One named bundle of defaults. Fields map to existing
    operator-facing surfaces; reading them is opt-in per
    command."""

    name: PresetName
    description: str
    approval_mode: Literal["suggest", "auto", "partial"]
    audience: Literal["beginner", "intermediate", "advanced"]
    audit_cadence_days: int
    require_plugin_review: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "name": self.name,
            "description": self.description,
            "approval_mode": self.approval_mode,
            "audience": self.audience,
            "audit_cadence_days": self.audit_cadence_days,
            "require_plugin_review": self.require_plugin_review,
        }


PRESETS: dict[str, PersonaPreset] = {
    "solo": PersonaPreset(
        name="solo",
        description="Single-developer mode — calmest defaults; suggest approvals; beginner verbosity.",
        approval_mode="suggest",
        audience="beginner",
        audit_cadence_days=30,
        require_plugin_review=False,
    ),
    "team-lead": PersonaPreset(
        name="team-lead",
        description="Coordinating-developer mode — partial approvals; intermediate verbosity; tighter cadence.",
        approval_mode="partial",
        audience="intermediate",
        audit_cadence_days=14,
        require_plugin_review=True,
    ),
    "auditor": PersonaPreset(
        name="auditor",
        description="Review-focused mode — suggest approvals; advanced verbosity; strictest audit cadence; every plugin flagged for explicit review.",
        approval_mode="suggest",
        audience="advanced",
        audit_cadence_days=7,
        require_plugin_review=True,
    ),
}


@dataclass(frozen=True)
class AppliedPersona:
    """Wraps a preset with the path it was written to. Useful
    for operator-facing output and tests."""

    preset: PersonaPreset
    path: Path

    def to_dict(self) -> dict[str, object]:
        return {
            "preset": self.preset.to_dict(),
            "path": str(self.path),
        }


def get_preset(name: str) -> PersonaPreset:
    """Look up a preset by canonical name. Raises ValueError on
    unknown name with the full vocabulary in the message so the
    caller can surface a useful error."""
    cleaned = name.strip().lower()
    if cleaned not in PRESETS:
        raise ValueError(
            f"Unknown persona preset: {name!r}. "
            f"Valid: {', '.join(PRESET_NAMES)}"
        )
    return PRESETS[cleaned]


def persona_path(root: Path) -> Path:
    """Canonical location for the per-project persona file."""
    return root / "mythic" / PERSONA_FILENAME


def apply_preset(
    root: Path,
    name: str,
    *,
    force: bool = False,
) -> AppliedPersona:
    """Write the named preset to ``mythic/persona.json``.
    Refuses to overwrite an existing file unless ``force=True``
    — defends against accidentally clobbering operator
    customisation."""
    from .runtime.atomic_write import atomic_write_text

    preset = get_preset(name)
    target = persona_path(root)
    if target.exists() and not force:
        raise FileExistsError(
            f"{target} already exists — pass --force to overwrite"
        )
    payload = json.dumps(preset.to_dict(), indent=2, sort_keys=True) + "\n"
    atomic_write_text(target, payload)
    return AppliedPersona(preset=preset, path=target)


@dataclass
class PersonaState:
    """Read-side projection of the active persona file. ``preset``
    is None when no file exists OR the file is malformed; in
    both cases callers should fall through to their own
    defaults."""

    preset: PersonaPreset | None
    path: Path
    error: str | None = field(default=None)

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "active": self.preset is not None,
            "preset": self.preset.to_dict() if self.preset else None,
            "error": self.error,
        }


def load_active_persona(root: Path) -> PersonaState:
    """Read ``mythic/persona.json`` and return a
    :class:`PersonaState`. Never raises — malformed files
    surface in ``error`` and ``preset`` stays None so callers
    can fall through cleanly."""
    target = persona_path(root)
    if not target.is_file():
        return PersonaState(preset=None, path=target)
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return PersonaState(
            preset=None, path=target, error=str(exc)
        )
    if not isinstance(payload, dict):
        return PersonaState(
            preset=None,
            path=target,
            error="persona file must be a JSON object",
        )
    name = str(payload.get("name") or "").strip()
    if name not in PRESETS:
        return PersonaState(
            preset=None,
            path=target,
            error=f"unknown preset name in file: {name!r}",
        )
    return PersonaState(preset=PRESETS[name], path=target)


__all__ = [
    "PERSONA_FILENAME",
    "PRESET_NAMES",
    "PRESETS",
    "SCHEMA_VERSION",
    "AppliedPersona",
    "PersonaPreset",
    "PersonaState",
    "PresetName",
    "apply_preset",
    "get_preset",
    "load_active_persona",
    "persona_path",
]
