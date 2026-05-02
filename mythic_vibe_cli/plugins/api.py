from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


PLUGIN_HOOKS = [
    "before_scan",
    "after_scan",
    "before_packet",
    "after_packet",
    "before_verify",
    "after_verify",
    "before_reflect",
    "after_reflect",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class PluginHealth:
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


@dataclass
class PluginRecord:
    entrypoint: str
    enabled: bool = True
    hooks: list[str] = field(default_factory=list)
    version: str = "unknown"
    added_at: str = field(default_factory=utc_now)
    disabled_at: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entrypoint": self.entrypoint,
            "enabled": self.enabled,
            "hooks": list(self.hooks),
            "version": self.version,
            "added_at": self.added_at,
            "disabled_at": self.disabled_at,
            "notes": list(self.notes),
        }

    @classmethod
    def from_raw(cls, raw: object) -> PluginRecord:
        if isinstance(raw, str):
            return cls(entrypoint=raw)
        if not isinstance(raw, dict):
            raise ValueError("Plugin registry entries must be strings or objects.")
        entrypoint = str(raw.get("entrypoint") or raw.get("plugin") or "").strip()
        if not entrypoint:
            raise ValueError("Plugin entrypoint is required.")
        hooks = [str(item) for item in raw.get("hooks", []) if str(item)]
        return cls(
            entrypoint=entrypoint,
            enabled=bool(raw.get("enabled", True)),
            hooks=hooks,
            version=str(raw.get("version") or "unknown"),
            added_at=str(raw.get("added_at") or utc_now()),
            disabled_at=str(raw.get("disabled_at")) if raw.get("disabled_at") else None,
            notes=[str(item) for item in raw.get("notes", []) if str(item)],
        )


def validate_hooks(hooks: list[str]) -> list[str]:
    allowed = set(PLUGIN_HOOKS)
    return [hook for hook in hooks if hook not in allowed]


# Additive 2026-05-02 (Phase C of audit remediation): in-process
# slash-command run protocol for plugins. Plugins may declare a
# ``run_slash(name, args) -> SlashRunResult`` callable; the
# ``PluginHookDispatcher.dispatch_slash`` helper iterates loaded
# plugins and returns the first ``handled=True`` result. The TUI
# slash picker uses this for plugin-contributed entries that did
# not supply an explicit ``argv`` at registration time, closing
# the audit's "(plugin dispatch not yet implemented)" gap without
# replacing the existing argv-based subprocess path.

@dataclass(frozen=True)
class SlashRunResult:
    """Result of an in-process plugin slash invocation.

    A plugin's ``run_slash(name, args)`` returns an instance of this
    class. ``handled=True`` tells the dispatcher this plugin owned
    the slash and dispatch should stop; ``handled=False`` signals
    "not mine — try the next plugin / fall through to fallback".
    """

    handled: bool
    output: str = ""
    exit_code: int = 0
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "handled": self.handled,
            "output": self.output,
            "exit_code": self.exit_code,
            "error": self.error,
        }
