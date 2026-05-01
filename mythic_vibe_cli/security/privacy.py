"""Privacy mode (PH-11 Slice 11.6).

When privacy mode is on, no provider call includes any code
outside an explicit allow-list. This is the strongest setting
on the security stack: operators decide *exactly* which paths
the AI can see, and everything else is filtered before any
provider sees the payload.

Configured per-project via ``mythic/security.toml``:

.. code-block:: toml

    [privacy]
    enabled = true
    allow_paths = [
        "src/",
        "tests/",
        "docs/",
    ]

When ``enabled = true`` and ``allow_paths`` is empty, the policy
is "deny everything" — provider payloads with file references
land empty (the operator must explicitly allow paths to share).

Cross-platform: pure stdlib.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .approval import load_security_config


@dataclass(frozen=True)
class PrivacyPolicy:
    """Resolved privacy policy for a project."""

    enabled: bool
    allow_paths: tuple[str, ...] = ()
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "allow_paths": list(self.allow_paths),
            "notes": list(self.notes),
        }


def resolve_privacy_policy(root: Path) -> PrivacyPolicy:
    """Read ``[privacy]`` from ``mythic/security.toml``. Missing
    section / file → policy disabled (default behaviour preserved)."""
    config = load_security_config(root)
    section = config.get("privacy") if isinstance(config, dict) else None

    if not isinstance(section, dict):
        return PrivacyPolicy(
            enabled=False,
            notes=["privacy mode not configured (no [privacy] section)"],
        )

    enabled = bool(section.get("enabled", False))
    allow_paths_raw = section.get("allow_paths", []) or []
    allow_paths = tuple(
        str(item).strip()
        for item in allow_paths_raw
        if isinstance(item, str) and str(item).strip()
    )

    notes: list[str] = []
    if enabled and not allow_paths:
        notes.append(
            "privacy.enabled=true with empty allow_paths — provider "
            "payloads with file references will be filtered to empty"
        )
    if enabled and allow_paths:
        notes.append(
            f"privacy mode active — only {len(allow_paths)} path globs "
            "will be allowed in provider payloads"
        )

    return PrivacyPolicy(
        enabled=enabled,
        allow_paths=allow_paths,
        notes=notes,
    )


def is_path_allowed(path: str | Path, policy: PrivacyPolicy) -> bool:
    """Return True if ``path`` is under the allow-list. When the
    policy is disabled, always allows. When enabled with empty
    allow-list, never allows."""
    if not policy.enabled:
        return True
    if not policy.allow_paths:
        return False

    candidate = str(path).replace("\\", "/").lstrip("./")
    for glob in policy.allow_paths:
        # Allow globs to match either the start of the path
        # (prefix match — useful for "src/" style allow rules) or
        # via fnmatch (useful for "*.py" style allow rules).
        normalised_glob = glob.replace("\\", "/").lstrip("./")
        if normalised_glob.endswith("/"):
            if candidate.startswith(normalised_glob) or candidate == normalised_glob.rstrip("/"):
                return True
        elif fnmatch.fnmatch(candidate, normalised_glob):
            return True
        elif candidate.startswith(normalised_glob + "/"):
            return True
        elif candidate == normalised_glob:
            return True
    return False


def filter_paths(
    paths: Iterable[str | Path], policy: PrivacyPolicy
) -> tuple[list[str], list[str]]:
    """Split ``paths`` into ``(allowed, denied)``. Returned paths
    are stringified."""
    allowed: list[str] = []
    denied: list[str] = []
    for path in paths:
        s = str(path)
        if is_path_allowed(s, policy):
            allowed.append(s)
        else:
            denied.append(s)
    return allowed, denied


def filter_payload(payload: Any, policy: PrivacyPolicy) -> Any:
    """Recursively filter dict / list payloads against the
    privacy policy. Strings whose content is a path-shape (have
    a slash, no spaces, length < 256) are tested via
    :func:`is_path_allowed`. When disallowed, they're replaced
    with the placeholder ``"[PRIVACY:FILTERED]"``.

    Non-path strings pass through unchanged. Privacy mode is
    intentionally narrow — it doesn't try to redact arbitrary
    content; that's the slice 11.2 redaction engine's job.
    """
    if not policy.enabled:
        return payload

    if isinstance(payload, str):
        return _maybe_filter_string(payload, policy)
    if isinstance(payload, dict):
        return {k: filter_payload(v, policy) for k, v in payload.items()}
    if isinstance(payload, list):
        return [filter_payload(v, policy) for v in payload]
    if isinstance(payload, tuple):
        return tuple(filter_payload(v, policy) for v in payload)
    return payload


_PRIVACY_PLACEHOLDER = "[PRIVACY:FILTERED]"


def _maybe_filter_string(value: str, policy: PrivacyPolicy) -> str:
    """Heuristic: a string is path-shape if it contains '/' or '\\',
    has no whitespace, and is reasonably short. Other strings pass
    through unchanged."""
    if not value or len(value) > 256 or any(c.isspace() for c in value):
        return value
    if "/" not in value and "\\" not in value:
        return value
    if is_path_allowed(value, policy):
        return value
    return _PRIVACY_PLACEHOLDER


__all__ = [
    "PrivacyPolicy",
    "filter_paths",
    "filter_payload",
    "is_path_allowed",
    "resolve_privacy_policy",
]
