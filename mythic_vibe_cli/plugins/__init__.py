"""Plugin registry, health, and dispatch helpers for Mythic Vibe CLI."""

from .api import PLUGIN_HOOKS, PluginHealth, PluginRecord
from .dispatcher import PluginHookDispatcher
from .loader import inspect_plugin
from .registry import PluginRegistry

__all__ = [
    "PLUGIN_HOOKS",
    "PluginHealth",
    "PluginRecord",
    "PluginRegistry",
    "PluginHookDispatcher",
    "inspect_plugin",
]
