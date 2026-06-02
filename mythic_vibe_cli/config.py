from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


@dataclass
class AppConfig:
    excerpt_limit: int = 1800
    packet_char_budget: int = 12000
    auto_compact: bool = True
    method_source: str = "https://github.com/hrabanazviking/Mythic-Engineering"
    ai_provider: str = "copy-paste"
    ai_model: str = "manual"


@dataclass
class LoadedConfig:
    config: AppConfig
    sources: list[Path]


class ConfigStore:
    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root.resolve() if project_root else None

    def _candidate_paths(self) -> list[Path]:
        home = Path(os.environ.get("HOME") or Path.home())
        xdg_home = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))

        paths = [
            home / ".mythic-vibe.json",
            xdg_home / "mythic-vibe" / "config.json",
        ]
        if self.project_root:
            paths.append(self.project_root / ".mythic-vibe.json")
        return paths

    def load(self) -> LoadedConfig:
        payload: dict = {}
        sources: list[Path] = []

        for path in self._candidate_paths():
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(data, dict):
                payload = _deep_merge(payload, data)
                sources.append(path)

        codex = payload.get("codex", {}) if isinstance(payload.get("codex", {}), dict) else {}
        method = payload.get("method", {}) if isinstance(payload.get("method", {}), dict) else {}
        ai = payload.get("ai", {}) if isinstance(payload.get("ai", {}), dict) else {}

        config = AppConfig(
            excerpt_limit=_parse_int_env(
                "MYTHIC_EXCERPT_LIMIT",
                codex.get("excerpt_limit", 1800),
                minimum=200,
                maximum=12000,
            ),
            packet_char_budget=_parse_int_env(
                "MYTHIC_PACKET_CHAR_BUDGET",
                codex.get("packet_char_budget", 12000),
                minimum=1000,
                maximum=100000,
            ),
            auto_compact=_parse_bool_env("MYTHIC_AUTO_COMPACT", codex.get("auto_compact", True)),
            method_source=_parse_str_env(
                "MYTHIC_METHOD_SOURCE",
                method.get("source", AppConfig.method_source),
            ),
            ai_provider=_parse_str_env(
                "MYTHIC_AI_PROVIDER",
                ai.get("provider", AppConfig.ai_provider),
            ),
            ai_model=_parse_str_env(
                "MYTHIC_AI_MODEL",
                ai.get("model", AppConfig.ai_model),
            ),
        )

        return LoadedConfig(config=config, sources=sources)

    def save_project_values(self, updates: dict[str, Any]) -> Path:
        """Merge dotted-key updates into ``<project>/.mythic-vibe.json``.

        This is the JSON config path :meth:`load` already reads. The
        legacy ``config set`` command still writes ``mythic/config.toml``
        for compatibility; companion-shell model selection uses this
        method so the saved values actually participate in runtime
        resolution.
        """
        if self.project_root is None:
            raise ValueError("project_root is required to save project config")

        path = self.project_root / ".mythic-vibe.json"
        payload: dict[str, Any] = {}
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                raw = {}
            if isinstance(raw, dict):
                payload = raw

        for key, value in updates.items():
            _set_dotted(payload, key, value)

        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path


def _deep_merge(base: dict, incoming: dict) -> dict:
    out = dict(base)
    for key, value in incoming.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _set_dotted(payload: dict[str, Any], key: str, value: Any) -> None:
    parts = [part for part in key.split(".") if part]
    if not parts:
        return
    target = payload
    for part in parts[:-1]:
        current = target.get(part)
        if not isinstance(current, dict):
            current = {}
            target[part] = current
        target = current
    target[parts[-1]] = value


def _parse_int_env(name: str, fallback: int, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name)
    value = fallback
    if raw is not None:
        try:
            value = int(raw)
        except ValueError:
            value = fallback
    return max(minimum, min(maximum, int(value)))


def _parse_bool_env(name: str, fallback: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return bool(fallback)

    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return bool(fallback)


def _parse_str_env(name: str, fallback: str) -> str:
    raw = os.environ.get(name)
    if raw is not None and raw.strip():
        return raw.strip()
    return str(fallback).strip()
