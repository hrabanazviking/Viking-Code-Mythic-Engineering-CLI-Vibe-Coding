"""Hardware profile detection (PH-06 slice 6.6).

Snaps a small, portable description of the host machine the CLI is
running on. Used by future PH-08 (Provider Routing) to inform
hardware-aware model selection and by operators who want a quick
"can my box run this model" sanity check before pulling a 7B.

Schema is deliberately tiny:

- ``os`` — platform name + release.
- ``arch`` — machine architecture (``x86_64``, ``arm64``…).
- ``cpu`` — string from ``platform.processor()`` (best-effort; may
  be empty on some Linux distros — falls back to ``platform.machine()``).
- ``logical_cpus`` — ``os.cpu_count()`` (or 0 when unavailable).
- ``physical_cpus`` — populated only when ``psutil`` is importable;
  falls back to 0 otherwise.
- ``ram_total_mb`` / ``ram_available_mb`` — populated only via
  ``psutil``; 0 + ``"unknown (psutil not installed)"`` note when
  the optional dep is missing.
- ``python_version`` / ``platform`` — full ``platform.platform()`` /
  ``platform.python_version()`` strings for traceability.

Intentionally **not** detected here: GPU presence, model name, VRAM,
CUDA / Metal availability. Those require either ``torch`` (heavy
dep with platform-specific wheels) or per-OS shell-outs (``nvidia-smi``,
``system_profiler``, ``wmic``) that don't generalise. PH-08 may
revisit when GPU-aware routing actually becomes a need.

Cross-platform: stdlib only as the hard requirement; ``psutil`` is
an opt-in enrichment the detector tolerates being absent.
"""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HARDWARE_PROFILE_DIR = ("docs",)
DEFAULT_PROFILE_FILENAME = "hardware_profiles.md"
DEFAULT_PROFILE_JSON_FILENAME = "hardware_profile.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class HardwareProfile:
    """Read-only snapshot of host hardware. Defaults are used so the
    detector never raises — missing data lands as 0 / empty string /
    a ``notes`` entry instead."""

    detected_at: str = ""
    os: str = ""
    os_release: str = ""
    arch: str = ""
    cpu: str = ""
    logical_cpus: int = 0
    physical_cpus: int = 0
    ram_total_mb: int = 0
    ram_available_mb: int = 0
    python_version: str = ""
    platform: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected_at": self.detected_at,
            "os": self.os,
            "os_release": self.os_release,
            "arch": self.arch,
            "cpu": self.cpu,
            "logical_cpus": self.logical_cpus,
            "physical_cpus": self.physical_cpus,
            "ram_total_mb": self.ram_total_mb,
            "ram_available_mb": self.ram_available_mb,
            "python_version": self.python_version,
            "platform": self.platform,
            "notes": list(self.notes),
        }


def detect_profile() -> HardwareProfile:
    """Build a :class:`HardwareProfile` for the current machine.

    Best-effort: every step is guarded so a partially broken
    environment still produces a usable record. Missing values are
    documented in ``notes`` so the operator (or a later automated
    consumer) can tell "0 logical_cpus" apart from "we couldn't
    measure".
    """
    notes: list[str] = []

    cpu_label = platform.processor() or ""
    if not cpu_label:
        # Some Linux distros leave processor() empty; the machine
        # arch is the next-best fallback.
        cpu_label = platform.machine() or ""
        if cpu_label:
            notes.append("cpu label fell back to platform.machine()")
    arch = platform.machine() or ""

    logical_cpus = os.cpu_count() or 0
    if not logical_cpus:
        notes.append("os.cpu_count() returned None")

    physical_cpus = 0
    ram_total_mb = 0
    ram_available_mb = 0
    try:
        import psutil  # type: ignore[import-not-found]

        try:
            physical_cpus = int(psutil.cpu_count(logical=False) or 0)
        except Exception:  # noqa: BLE001 — psutil internals shouldn't crash detection
            notes.append("psutil.cpu_count(logical=False) failed")
        try:
            mem = psutil.virtual_memory()
            ram_total_mb = int(getattr(mem, "total", 0) // (1024 * 1024))
            ram_available_mb = int(getattr(mem, "available", 0) // (1024 * 1024))
        except Exception:  # noqa: BLE001 — same reasoning
            notes.append("psutil.virtual_memory() failed")
    except ImportError:
        notes.append("ram measurements unavailable (psutil not installed)")

    return HardwareProfile(
        detected_at=_utc_now_iso(),
        os=platform.system() or "",
        os_release=platform.release() or "",
        arch=arch,
        cpu=cpu_label,
        logical_cpus=logical_cpus,
        physical_cpus=physical_cpus,
        ram_total_mb=ram_total_mb,
        ram_available_mb=ram_available_mb,
        python_version=platform.python_version() or "",
        platform=platform.platform() or "",
        notes=notes,
    )


def render_profile_text(profile: HardwareProfile) -> str:
    """Human-readable summary used by the CLI text path."""
    lines = [
        "Hardware profile",
        f"  OS:           {profile.os} {profile.os_release}".rstrip(),
        f"  Arch:         {profile.arch or '(unknown)'}",
        f"  CPU:          {profile.cpu or '(unknown)'}",
        f"  Logical CPUs: {profile.logical_cpus or 'unknown'}",
        f"  Physical CPUs:{profile.physical_cpus or 'unknown'}",
        "  RAM total:    "
        + (f"{profile.ram_total_mb} MB" if profile.ram_total_mb else "unknown"),
        "  RAM avail:    "
        + (
            f"{profile.ram_available_mb} MB"
            if profile.ram_available_mb
            else "unknown"
        ),
        f"  Python:       {profile.python_version}",
        f"  Platform:     {profile.platform}",
    ]
    if profile.notes:
        lines.append("  Notes:")
        for note in profile.notes:
            lines.append(f"    - {note}")
    return "\n".join(lines) + "\n"


def render_profile_markdown(profile: HardwareProfile) -> str:
    """Markdown rendering used by ``--write`` to persist the profile
    to ``docs/hardware_profiles.md``. The file is intentionally a
    single most-recent snapshot — re-running ``--write`` overwrites
    so the doc always reflects current hardware. Historical
    snapshots can land in git history if desired."""
    lines = [
        "# Hardware profile",
        "",
        f"_Detected at {profile.detected_at}._",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| OS | `{profile.os} {profile.os_release}`".rstrip() + " |",
        f"| Arch | `{profile.arch or 'unknown'}` |",
        f"| CPU | `{profile.cpu or 'unknown'}` |",
        f"| Logical CPUs | {profile.logical_cpus or 'unknown'} |",
        f"| Physical CPUs | {profile.physical_cpus or 'unknown'} |",
        "| RAM total | "
        + (
            f"{profile.ram_total_mb} MB |"
            if profile.ram_total_mb
            else "unknown |"
        ),
        "| RAM available | "
        + (
            f"{profile.ram_available_mb} MB |"
            if profile.ram_available_mb
            else "unknown |"
        ),
        f"| Python | `{profile.python_version}` |",
        f"| Platform | `{profile.platform}` |",
    ]
    if profile.notes:
        lines.append("")
        lines.append("## Notes")
        lines.append("")
        for note in profile.notes:
            lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def write_profile(
    root: Path,
    profile: HardwareProfile,
    *,
    md_filename: str = DEFAULT_PROFILE_FILENAME,
    json_filename: str = DEFAULT_PROFILE_JSON_FILENAME,
) -> tuple[Path, Path]:
    """Persist ``profile`` to ``<root>/docs/<md_filename>`` plus a
    JSON sidecar. Creates the docs directory if missing. Returns
    the ``(md_path, json_path)`` tuple. Raises only on filesystem
    errors — the caller decides how to surface them."""
    docs_dir = root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    md_path = docs_dir / md_filename
    json_path = docs_dir / json_filename
    md_path.write_text(render_profile_markdown(profile), encoding="utf-8")
    json_path.write_text(
        json.dumps(profile.to_dict(), indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return md_path, json_path


__all__ = [
    "DEFAULT_PROFILE_FILENAME",
    "DEFAULT_PROFILE_JSON_FILENAME",
    "HARDWARE_PROFILE_DIR",
    "HardwareProfile",
    "detect_profile",
    "render_profile_markdown",
    "render_profile_text",
    "write_profile",
]
