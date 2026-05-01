"""Redaction engine (PH-11 Slice 11.2).

Extends the existing
:func:`mythic_vibe_cli.ai.providers.base.redact_text` into a
configurable :class:`RedactionEngine`:

- **Pattern-based text redaction** — same regex set the AI
  provider layer already uses, exposed here so plugins, the
  forge cycle, and slice 11.3's secret scanner share one source
  of truth.
- **Forbidden paths** — files like ``.env``, ``*.pem``, ``*.key``,
  ``*.token`` are flagged as forbidden by default. Helpers like
  :func:`is_path_forbidden` let callers skip these files when
  building packets / scan indexes / context payloads.
- **Configurable** — operators extend the default sets via
  ``mythic/security.toml [redaction] extra_patterns`` and
  ``[redaction] forbidden_paths``.

Cross-platform: pure stdlib (``re`` + ``fnmatch``).
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Pattern

from ..ai.providers.base import SECRET_PATTERNS


REDACTION_PLACEHOLDER = "[REDACTED]"

# Default-deny path globs. Filenames matching any of these are
# treated as confidential — the slice-11.3 secret scanner refuses
# to read them, slice-11.6 privacy mode excludes them from
# provider payloads.
DEFAULT_FORBIDDEN_PATHS: tuple[str, ...] = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.token",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_ecdsa",
    "id_ed25519",
    "credentials.json",
    "service_account.json",
)

# Default secret-pattern set. Reuses the existing AI provider
# patterns so the engine and the AI layer agree on what counts
# as a secret. Operators add more via security.toml.
DEFAULT_REDACTION_PATTERNS: tuple[Pattern[str], ...] = tuple(SECRET_PATTERNS)


@dataclass
class RedactionEngine:
    """Stateful holder for the active redaction configuration.
    Most callers use the module-level :func:`redact_text` and
    :func:`is_path_forbidden` shortcuts; the engine class is for
    consumers who want to override the patterns / paths per
    project (e.g. slice-11.7's ``security audit`` subcommand).
    """

    patterns: tuple[Pattern[str], ...] = field(
        default_factory=lambda: DEFAULT_REDACTION_PATTERNS
    )
    forbidden_paths: tuple[str, ...] = field(
        default_factory=lambda: DEFAULT_FORBIDDEN_PATHS
    )
    placeholder: str = REDACTION_PLACEHOLDER

    def redact_text(self, text: str) -> str:
        """Apply every pattern in :attr:`patterns` to ``text``.
        Returns the redacted result; the original is unchanged."""
        if not text:
            return text
        redacted = text
        for pattern in self.patterns:
            redacted = pattern.sub(self.placeholder, redacted)
        return redacted

    def redact_payload(self, value: Any) -> Any:
        """Recursively redact strings inside dict / list / scalar
        payloads. Non-string scalars pass through unchanged."""
        if isinstance(value, str):
            return self.redact_text(value)
        if isinstance(value, dict):
            return {k: self.redact_payload(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.redact_payload(v) for v in value]
        if isinstance(value, tuple):
            return tuple(self.redact_payload(v) for v in value)
        return value

    def is_path_forbidden(self, path: str | Path) -> bool:
        """Return True if ``path``'s basename matches any
        forbidden glob. Operates on the basename only — a file at
        ``./project/.env`` matches the same as ``.env``."""
        name = Path(str(path)).name
        if not name:
            return False
        for glob in self.forbidden_paths:
            if fnmatch.fnmatch(name, glob):
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern_count": len(self.patterns),
            "forbidden_paths": list(self.forbidden_paths),
            "placeholder": self.placeholder,
        }


def _compile_extra_patterns(raw: Iterable[Any]) -> list[Pattern[str]]:
    """Compile a raw list of pattern strings from config into
    :class:`re.Pattern` objects. Invalid regexes are skipped
    silently — security config must never crash the CLI."""
    out: list[Pattern[str]] = []
    for item in raw:
        if not isinstance(item, str) or not item:
            continue
        try:
            out.append(re.compile(item))
        except re.error:
            continue
    return out


def engine_from_config(config: dict[str, Any] | None) -> RedactionEngine:
    """Build a :class:`RedactionEngine` from a parsed
    ``mythic/security.toml`` dict. Missing ``[redaction]`` block
    → defaults only. Use with :func:`approval.load_security_config`:

    .. code-block:: python

        from mythic_vibe_cli.security.approval import load_security_config
        from mythic_vibe_cli.security.redaction import engine_from_config

        engine = engine_from_config(load_security_config(root))
    """
    if not isinstance(config, dict):
        return RedactionEngine()
    section = config.get("redaction")
    if not isinstance(section, dict):
        return RedactionEngine()

    extra_patterns: tuple[Pattern[str], ...] = tuple(
        _compile_extra_patterns(section.get("extra_patterns", []) or [])
    )
    extra_forbidden: tuple[str, ...] = tuple(
        str(item)
        for item in (section.get("forbidden_paths", []) or [])
        if isinstance(item, str) and item
    )
    placeholder = str(
        section.get("placeholder", REDACTION_PLACEHOLDER) or REDACTION_PLACEHOLDER
    )

    return RedactionEngine(
        patterns=DEFAULT_REDACTION_PATTERNS + extra_patterns,
        forbidden_paths=DEFAULT_FORBIDDEN_PATHS + extra_forbidden,
        placeholder=placeholder,
    )


# Module-level shortcuts using the default engine — keeps
# pre-PH-11 callers working without churn.

_DEFAULT_ENGINE = RedactionEngine()


def redact_text(text: str) -> str:
    return _DEFAULT_ENGINE.redact_text(text)


def redact_payload(value: Any) -> Any:
    return _DEFAULT_ENGINE.redact_payload(value)


def is_path_forbidden(path: str | Path) -> bool:
    return _DEFAULT_ENGINE.is_path_forbidden(path)


__all__ = [
    "DEFAULT_FORBIDDEN_PATHS",
    "DEFAULT_REDACTION_PATTERNS",
    "REDACTION_PLACEHOLDER",
    "RedactionEngine",
    "engine_from_config",
    "is_path_forbidden",
    "redact_payload",
    "redact_text",
]
