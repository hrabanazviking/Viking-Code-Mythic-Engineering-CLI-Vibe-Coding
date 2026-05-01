"""Sandbox execution policy (PH-11 Slice 11.4).

Reads ``mythic/security.toml [sandbox]`` to decide whether
subprocess execution should be sandboxed:

- ``directory_restriction``: refuse to run subprocesses whose
  cwd resolves outside the project root.
- ``network_disabled``: best-effort attempt to spawn the
  subprocess without network access.

Today's :func:`mythic_vibe_cli.runtime.exec_command` already
runs subprocesses with ``shell=False``. This module adds the
two sandbox modes operators opt into via security.toml.

**Cross-platform notes** — network disabling is best-effort:

- **Linux**: prepend ``unshare -n`` when the binary is
  available + the running user has CAP_SYS_ADMIN. We test for
  the binary; we do **not** assume the cap (the wrap will
  simply fail if the kernel rejects it).
- **macOS / Windows**: there is no portable user-mode network
  isolation. The policy reports ``advisory_only=True`` and the
  subprocess runs with normal network access; operators get a
  clear warning in the policy report.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

import platform
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .approval import load_security_config


@dataclass(frozen=True)
class SandboxPolicy:
    """Result of :func:`resolve_sandbox_policy`. Operators can
    inspect this from the CLI to confirm what's enforced."""

    enabled: bool
    directory_restriction: bool
    network_disabled: bool
    network_advisory_only: bool
    project_root: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "directory_restriction": self.directory_restriction,
            "network_disabled": self.network_disabled,
            "network_advisory_only": self.network_advisory_only,
            "project_root": self.project_root,
            "notes": list(self.notes),
        }


def _is_linux_unshare_available() -> bool:
    """``unshare -n`` is the only widely-available user-mode
    network sandbox. Returns True only on Linux with the binary
    on PATH; we don't actually exec it here, so the absence of
    CAP_SYS_ADMIN won't show up until the subprocess actually
    spawns."""
    if platform.system().lower() != "linux":
        return False
    return shutil.which("unshare") is not None


def resolve_sandbox_policy(root: Path) -> SandboxPolicy:
    """Build the active :class:`SandboxPolicy` for a project.

    Reads ``[sandbox]`` from ``mythic/security.toml`` if present.
    Defaults: every flag off → ``enabled=False``. Once any flag
    is set the policy is active for that capability.
    """
    config = load_security_config(root)
    section = config.get("sandbox") if isinstance(config, dict) else None
    notes: list[str] = []

    if not isinstance(section, dict):
        return SandboxPolicy(
            enabled=False,
            directory_restriction=False,
            network_disabled=False,
            network_advisory_only=True,
            project_root=str(Path(root).resolve()),
            notes=["sandbox not configured (no [sandbox] section)"],
        )

    enabled = bool(section.get("enabled", False))
    directory_restriction = bool(section.get("directory_restriction", False))
    network_disabled = bool(section.get("network_disabled", False))

    network_advisory_only = False
    if network_disabled and not _is_linux_unshare_available():
        network_advisory_only = True
        notes.append(
            "network_disabled=true is advisory-only on this platform — "
            "no portable user-mode network sandbox is available "
            "(Linux + `unshare -n` is required for enforcement)"
        )

    if directory_restriction:
        notes.append(
            f"directory_restriction enforced: subprocesses must stay "
            f"under {Path(root).resolve()}"
        )

    return SandboxPolicy(
        enabled=enabled,
        directory_restriction=directory_restriction,
        network_disabled=network_disabled,
        network_advisory_only=network_advisory_only,
        project_root=str(Path(root).resolve()),
        notes=notes,
    )


def is_cwd_inside_root(cwd: str | Path, root: str | Path) -> bool:
    """Return True if ``cwd`` resolves to a path under ``root``.
    Used by :func:`enforce_directory_restriction` and the slice-
    11.7 audit command."""
    try:
        cwd_resolved = Path(cwd).resolve()
        root_resolved = Path(root).resolve()
    except (OSError, RuntimeError):
        return False
    try:
        cwd_resolved.relative_to(root_resolved)
    except ValueError:
        return False
    return True


def enforce_directory_restriction(
    *,
    cwd: str | Path,
    policy: SandboxPolicy,
) -> tuple[bool, str]:
    """Check ``cwd`` against the policy's directory restriction.
    Returns ``(allowed, reason)``. When the policy disables the
    restriction, always allows."""
    if not policy.enabled or not policy.directory_restriction:
        return True, ""
    if is_cwd_inside_root(cwd, policy.project_root):
        return True, ""
    return False, (
        f"sandbox directory_restriction blocked: "
        f"cwd {Path(cwd).resolve()} resolves outside project root "
        f"{policy.project_root}"
    )


def wrap_argv_for_network_disabled(
    argv: list[str] | tuple[str, ...],
    *,
    policy: SandboxPolicy,
) -> list[str]:
    """If the policy enables network_disabled AND ``unshare -n``
    is available, prepend it to the argv. Otherwise return the
    argv unchanged. Operators see ``network_advisory_only`` in
    :class:`SandboxPolicy` when the wrap is a no-op."""
    if not policy.enabled or not policy.network_disabled:
        return list(argv)
    if policy.network_advisory_only:
        return list(argv)
    # Linux + unshare path.
    return ["unshare", "-n", "--"] + list(argv)


__all__ = [
    "SandboxPolicy",
    "enforce_directory_restriction",
    "is_cwd_inside_root",
    "resolve_sandbox_policy",
    "wrap_argv_for_network_disabled",
]
