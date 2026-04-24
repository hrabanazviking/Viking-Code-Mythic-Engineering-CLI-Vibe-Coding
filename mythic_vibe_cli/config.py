from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path


@dataclass
class AppConfig:
    excerpt_limit: int = 1800
    packet_char_budget: int = 12000
    auto_compact: bool = True


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
        )

        return LoadedConfig(config=config, sources=sources)


def _deep_merge(base: dict, incoming: dict) -> dict:
    out = dict(base)
    for key, value in incoming.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


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
