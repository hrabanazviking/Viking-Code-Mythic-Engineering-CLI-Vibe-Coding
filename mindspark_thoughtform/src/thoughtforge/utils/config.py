"""Runtime configuration loading for ThoughtForge."""

import json
import logging
from pathlib import Path
from typing import Any

import yaml

from thoughtforge.utils.paths import get_configs_dir, get_hardware_profiles_dir

logger = logging.getLogger(__name__)

_config_cache: dict[str, Any] | None = None


def load_config(override_path: Path | None = None) -> dict[str, Any]:
    """Load runtime config from configs/default.yaml, optionally merged with a local override."""
    global _config_cache
    if _config_cache is not None and override_path is None:
        return _config_cache

    default_path = get_configs_dir() / "default.yaml"
    if not default_path.exists():
        logger.warning("Default config not found at %s — using empty config", default_path)
        return {}

    with default_path.open("r", encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f) or {}

    local_path = override_path or (get_configs_dir() / "local_config.yaml")
    if local_path.exists():
        with local_path.open("r", encoding="utf-8") as f:
            local: dict[str, Any] = yaml.safe_load(f) or {}
        config = _deep_merge(config, local)
        logger.debug("Merged local config from %s", local_path)

    if override_path is None:
        _config_cache = config
    return config


def load_hardware_profile(profile_id: str) -> dict[str, Any]:
    """Load a hardware profile JSON by ID (e.g. 'desktop_cpu')."""
    profiles_dir = get_hardware_profiles_dir()
    path = profiles_dir / f"{profile_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Hardware profile not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


def list_hardware_profiles() -> list[str]:
    """Return all available hardware profile IDs."""
    profiles_dir = get_hardware_profiles_dir()
    return [p.stem for p in sorted(profiles_dir.glob("*.json"))]


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base, returning a new dict."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
