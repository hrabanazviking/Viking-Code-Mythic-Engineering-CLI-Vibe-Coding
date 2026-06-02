"""Canonical filesystem paths for Mythic Vibe runtime state.

The CLI has two kinds of storage:

- project-local state under the operator's project root;
- user-global config/cache/state/log roots controlled by platform defaults
  and explicit environment overrides.

Callers should construct runtime paths here instead of repeating path
fragments in feature modules. User-provided relative paths can be routed
through :func:`resolve_within` to reject traversal before touching disk.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PureWindowsPath
import sys


APP_SLUG = "mythic-vibe"
APP_DISPLAY_NAME = "MythicVibeCLI"

PROJECT_STATE_DIRNAME = "mythic"
PRIVATE_STATE_DIRNAME = ".mythic"
CONFIG_JSON_FILENAME = ".mythic-vibe.json"
CONFIG_FILENAMES = (
    "config.yaml",
    "config.yml",
    CONFIG_JSON_FILENAME,
    ".mythic-vibe.yaml",
    ".mythic-vibe.yml",
)


class PathOwnershipError(ValueError):
    """Raised when an untrusted path would escape its allowed root."""


def _home() -> Path:
    raw = os.environ.get("HOME", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home()


def _env_path(name: str) -> Path | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def config_root() -> Path:
    override = _env_path("MYTHIC_CONFIG_HOME")
    if override is not None:
        return override
    if sys.platform == "win32":
        return _env_path("APPDATA") or (_home() / "AppData" / "Roaming" / APP_DISPLAY_NAME)
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support" / APP_DISPLAY_NAME
    xdg = _env_path("XDG_CONFIG_HOME")
    return (xdg or (_home() / ".config")) / APP_SLUG


def state_root() -> Path:
    override = _env_path("MYTHIC_STATE_HOME")
    if override is not None:
        return override
    if sys.platform == "win32":
        return _env_path("LOCALAPPDATA") or (_home() / "AppData" / "Local" / APP_DISPLAY_NAME)
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support" / APP_DISPLAY_NAME
    xdg = _env_path("XDG_STATE_HOME")
    return (xdg or (_home() / ".local" / "state")) / APP_SLUG


def cache_root() -> Path:
    override = _env_path("MYTHIC_CACHE_HOME")
    if override is not None:
        return override
    if sys.platform == "win32":
        return (_env_path("LOCALAPPDATA") or (_home() / "AppData" / "Local" / APP_DISPLAY_NAME)) / "Cache"
    if sys.platform == "darwin":
        return _home() / "Library" / "Caches" / APP_DISPLAY_NAME
    xdg = _env_path("XDG_CACHE_HOME")
    return (xdg or (_home() / ".cache")) / APP_SLUG


def log_root() -> Path:
    override = _env_path("MYTHIC_LOG_HOME")
    if override is not None:
        return override
    if sys.platform == "win32":
        return state_root() / "logs"
    if sys.platform == "darwin":
        return _home() / "Library" / "Logs" / APP_DISPLAY_NAME
    return state_root() / "logs"


def workspace_root() -> Path:
    override = _env_path("MYTHIC_WORKSPACE_ROOT")
    if override is not None:
        return override.resolve()
    return (state_root() / "workspaces").resolve()


def crash_reports_root() -> Path:
    return state_root() / "crashes"


def script_crash_reports_root() -> Path:
    return state_root() / "script-crashes"


def config_candidates(project_root: Path | str | os.PathLike[str] | None = None) -> tuple[Path, ...]:
    root = config_root()
    candidates = [
        _home() / ".mythic-vibe.json",
        _home() / ".mythic-vibe.yaml",
        _home() / ".mythic-vibe.yml",
        root / "config.json",
        root / "config.yaml",
        root / "config.yml",
    ]
    if project_root is not None:
        project = Path(project_root).expanduser().resolve()
        candidates.extend(project / name for name in CONFIG_FILENAMES)
    return tuple(candidates)


def resolve_within(root: Path, user_path: str | os.PathLike[str]) -> Path:
    """Resolve an untrusted relative path under ``root``.

    Absolute paths, empty paths, Windows drive paths, and ``..`` traversal
    are rejected before the returned path can be used for a read or write.
    """
    text = os.fspath(user_path).strip()
    if not text:
        raise PathOwnershipError("path must not be empty")
    if Path(text).is_absolute() or PureWindowsPath(text).is_absolute():
        raise PathOwnershipError(f"path must be relative: {text}")
    normalized = text.replace("\\", "/")
    parts = [part for part in normalized.split("/") if part not in {"", "."}]
    if not parts:
        raise PathOwnershipError("path must contain a file or directory name")
    if any(part == ".." for part in parts):
        raise PathOwnershipError(f"path escapes project root: {text}")
    base = Path(root).resolve()
    candidate = base.joinpath(*parts).resolve(strict=False)
    if candidate != base and base not in candidate.parents:
        raise PathOwnershipError(f"path escapes project root: {text}")
    return candidate


@dataclass(frozen=True)
class RuntimePaths:
    """Canonical path resolver for one project root."""

    project_root: Path

    @classmethod
    def for_project(cls, root: Path | str | os.PathLike[str]) -> "RuntimePaths":
        return cls(Path(root).expanduser().resolve())

    @property
    def project_state_dir(self) -> Path:
        return self.project_root / PROJECT_STATE_DIRNAME

    @property
    def private_state_dir(self) -> Path:
        return self.project_root / PRIVATE_STATE_DIRNAME

    @property
    def status_file(self) -> Path:
        return self.project_state_dir / "status.json"

    @property
    def state_lock_file(self) -> Path:
        return self.status_file.with_suffix(".json.lock")

    @property
    def state_backup_dir(self) -> Path:
        return self.project_state_dir / "backups"

    @property
    def project_config_file(self) -> Path:
        return self.project_root / CONFIG_JSON_FILENAME

    @property
    def config_candidates(self) -> tuple[Path, ...]:
        return config_candidates(self.project_root)

    @property
    def ai_dir(self) -> Path:
        return self.project_state_dir / "ai"

    @property
    def provider_calls_log(self) -> Path:
        return self.ai_dir / "provider_calls.jsonl"

    @property
    def routing_file(self) -> Path:
        return self.ai_dir / "routing.json"

    @property
    def events_log(self) -> Path:
        return self.project_state_dir / "events.jsonl"

    @property
    def memory_db(self) -> Path:
        return self.private_state_dir / "memory.sqlite"

    @property
    def current_packet_markdown(self) -> Path:
        return self.project_state_dir / "codex_prompt.md"

    @property
    def packets_dir(self) -> Path:
        return self.project_state_dir / "packets"

    @property
    def workflow_plan_file(self) -> Path:
        return self.project_state_dir / "workflow_plan.json"

    def project_path(self, *parts: str | os.PathLike[str]) -> Path:
        return self.project_root.joinpath(*(os.fspath(part) for part in parts))

    def user_path(self, user_path: str | os.PathLike[str]) -> Path:
        return resolve_within(self.project_root, user_path)


def paths_for(root: Path | str | os.PathLike[str]) -> RuntimePaths:
    return RuntimePaths.for_project(root)


__all__ = [
    "APP_DISPLAY_NAME",
    "APP_SLUG",
    "CONFIG_FILENAMES",
    "CONFIG_JSON_FILENAME",
    "PRIVATE_STATE_DIRNAME",
    "PROJECT_STATE_DIRNAME",
    "PathOwnershipError",
    "RuntimePaths",
    "cache_root",
    "config_candidates",
    "config_root",
    "crash_reports_root",
    "log_root",
    "paths_for",
    "resolve_within",
    "script_crash_reports_root",
    "state_root",
    "workspace_root",
]
