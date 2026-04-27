from __future__ import annotations

import importlib
from typing import Any

from .api import PLUGIN_HOOKS, PluginHealth, PluginRecord, validate_hooks


def _split_entrypoint(entrypoint: str) -> tuple[str, str]:
    if ":" not in entrypoint:
        raise ValueError("Plugin entrypoint must use module:object syntax.")
    module_name, object_name = entrypoint.split(":", 1)
    module_name = module_name.strip()
    object_name = object_name.strip()
    if not module_name or not object_name:
        raise ValueError("Plugin entrypoint must include both module and object name.")
    return module_name, object_name


def _declared_hooks(plugin_obj: Any) -> list[str]:
    raw_hooks = getattr(plugin_obj, "MYTHIC_HOOKS", None)
    if raw_hooks is None and isinstance(plugin_obj, type):
        raw_hooks = getattr(plugin_obj, "MYTHIC_HOOKS", None)
    if raw_hooks is None:
        raw_hooks = [hook for hook in PLUGIN_HOOKS if hasattr(plugin_obj, hook)]
    return [str(item) for item in raw_hooks if str(item)]


def inspect_plugin(record: PluginRecord, *, import_plugin: bool = True) -> dict[str, object]:
    warnings = ["Sandbox warning: plugins are local Python code. Inspect before enabling or executing hooks."]
    errors: list[str] = []
    declared_hooks = list(record.hooks)
    version = record.version

    if not record.enabled:
        warnings.append("Plugin is disabled.")

    if import_plugin:
        try:
            module_name, object_name = _split_entrypoint(record.entrypoint)
            module = importlib.import_module(module_name)
            plugin_obj = getattr(module, object_name)
            declared_hooks = _declared_hooks(plugin_obj)
            version = str(getattr(plugin_obj, "__version__", getattr(module, "__version__", version)))
        except Exception as exc:  # noqa: BLE001 - inspection should report failures, not raise into callers.
            errors.append(str(exc))

    invalid_hooks = validate_hooks(declared_hooks)
    if invalid_hooks:
        errors.append(f"Unknown hook(s): {', '.join(invalid_hooks)}")

    status = "disabled"
    if record.enabled:
        status = "healthy" if not errors else "error"

    health = PluginHealth(status=status, errors=errors, warnings=warnings)
    return {
        "entrypoint": record.entrypoint,
        "enabled": record.enabled,
        "version": version,
        "hooks": declared_hooks,
        "health": health.to_dict(),
    }
