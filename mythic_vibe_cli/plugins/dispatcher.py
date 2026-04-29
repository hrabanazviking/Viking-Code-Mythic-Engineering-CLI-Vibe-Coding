"""Plugin event dispatcher.

Loads enabled plugins from the project's :class:`PluginRegistry`, resolves
each plugin's ``before_*`` / ``after_*`` hook methods, and subscribes them to
a fresh :class:`EventBusController`. Command code can then call
:meth:`PluginHookDispatcher.emit` at the right moments without knowing
anything about the plugin layer.

A plugin that fails to import is skipped silently — surface plugin health via
``mythic-vibe plugin inspect``; do not fail the command. A plugin handler
that raises is contained by the underlying event bus contract (logged to
stderr, never crashes the bus or the command).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import sys
import traceback
from pathlib import Path
from types import TracebackType
from typing import Callable

from ..runtime.event_bus import EventBusController, create_event_bus
from ..runtime.event_log import append_event, event_log_path_for
from ..runtime.slash_commands import SlashCommandInfo
from .api import PLUGIN_HOOKS, PluginRecord
from .loader import _split_entrypoint
from .registry import PluginRegistry


@dataclass
class _Subscription:
    plugin: PluginRecord
    hook: str
    unsubscribe: Callable[[], None]


@dataclass
class _LoadedPlugin:
    record: PluginRecord
    plugin_obj: object
    hooks: list[str] = field(default_factory=list)


class PluginHookDispatcher:
    """Per-invocation dispatcher binding plugin hooks to an event bus."""

    def __init__(self, root: Path, *, bus: EventBusController | None = None) -> None:
        self.root = Path(root)
        self.bus = bus or create_event_bus()
        self._subscriptions: list[_Subscription] = []
        self._loaded: list[_LoadedPlugin] = []

    def load_and_subscribe(self) -> int:
        """Discover enabled plugins, subscribe their hook methods to the bus.

        Returns the number of plugins successfully loaded. Plugins whose
        entrypoints fail to import are skipped silently.
        """
        registry = PluginRegistry(self.root)
        try:
            records = registry.list(include_disabled=False)
        except (OSError, ValueError):
            return 0

        loaded_count = 0
        for record in records:
            plugin_obj = self._import_plugin(record)
            if plugin_obj is None:
                continue
            hooks = self._subscribe_plugin(record, plugin_obj)
            self._loaded.append(_LoadedPlugin(record=record, plugin_obj=plugin_obj, hooks=hooks))
            loaded_count += 1
        return loaded_count

    def emit(self, hook: str, payload: object) -> None:
        """Emit ``payload`` on the named hook channel and persist a row in the
        per-project event log at ``mythic/events.jsonl``.

        Validates the hook name against ``PLUGIN_HOOKS`` so a typo at the call
        site is caught immediately rather than silently ignored. Log writes are
        best-effort: IO errors do not propagate.
        """
        if hook not in PLUGIN_HOOKS:
            raise ValueError(f"Unknown plugin hook: {hook}")
        self.bus.emit(hook, payload)
        try:
            append_event(event_log_path_for(self.root), hook, payload)
        except Exception:  # noqa: BLE001 - event-log persistence is best-effort
            pass

    def teardown(self) -> None:
        """Unsubscribe every handler this dispatcher registered."""
        for subscription in self._subscriptions:
            try:
                subscription.unsubscribe()
            except Exception:  # noqa: BLE001 - teardown is best-effort
                continue
        self._subscriptions.clear()
        self._loaded.clear()

    def discover_slash_commands(self) -> list[SlashCommandInfo]:
        """Aggregate ``SlashCommandInfo`` entries contributed by enabled plugins.

        A plugin may declare a callable named ``slash_commands`` (class method,
        static method, or instance method — anything ``getattr`` + ``callable``
        accepts). When invoked with no arguments, it returns an iterable of
        :class:`SlashCommandInfo`. Items that fail ``isinstance`` are skipped
        silently. Exceptions raised by the plugin's method are caught, logged
        to stderr (channel name + traceback, matching the event bus contract),
        and the plugin contributes nothing.

        This is a one-shot discovery convention — it is **not** an event hook
        and is intentionally not part of ``PLUGIN_HOOKS``. Callers run this
        after :meth:`load_and_subscribe`.
        """
        discovered: list[SlashCommandInfo] = []
        for loaded in self._loaded:
            method = getattr(loaded.plugin_obj, "slash_commands", None)
            if not callable(method):
                continue
            try:
                items = method()
            except Exception:  # noqa: BLE001 - match bus log-and-continue contract
                print(
                    f"Plugin slash_commands error ({loaded.record.entrypoint}):",
                    file=sys.stderr,
                )
                traceback.print_exc(file=sys.stderr)
                continue
            try:
                for item in items:
                    if isinstance(item, SlashCommandInfo):
                        discovered.append(item)
            except TypeError:
                # Returned object was not iterable; skip silently.
                continue
        return discovered

    @property
    def loaded_plugins(self) -> list[PluginRecord]:
        return [item.record for item in self._loaded]

    @property
    def subscribed_hooks(self) -> list[str]:
        return [subscription.hook for subscription in self._subscriptions]

    def __enter__(self) -> PluginHookDispatcher:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.teardown()

    def _import_plugin(self, record: PluginRecord) -> object | None:
        try:
            module_name, object_name = _split_entrypoint(record.entrypoint)
            module = importlib.import_module(module_name)
            return getattr(module, object_name)
        except Exception:  # noqa: BLE001 - per-plugin failure must not break commands
            return None

    def _subscribe_plugin(self, record: PluginRecord, plugin_obj: object) -> list[str]:
        hooks_subscribed: list[str] = []
        for hook in PLUGIN_HOOKS:
            handler = getattr(plugin_obj, hook, None)
            if not callable(handler):
                continue
            unsubscribe = self.bus.on(hook, handler)
            self._subscriptions.append(
                _Subscription(plugin=record, hook=hook, unsubscribe=unsubscribe)
            )
            hooks_subscribed.append(hook)
        return hooks_subscribed
