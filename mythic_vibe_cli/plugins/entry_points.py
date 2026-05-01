"""Entry-point discovery (PH-10 Slice 10.1).

Standard Python entry-points mechanism: plugins published to
PyPI (or installed locally) declare themselves under the group
``mythic_vibe.plugins`` in their ``pyproject.toml``:

    [project.entry-points."mythic_vibe.plugins"]
    my_plugin = "my_package.module:plugin_object"

After ``pip install``, the plugin is discoverable via
:func:`discover_entry_points` without manual registry editing.
The ``mythic-vibe plugin discover`` CLI surfaces this; ``mythic-vibe
plugin install <name>`` registers a discovered entry-point in the
project's plugin registry.

Cross-platform: pure stdlib (``importlib.metadata``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ENTRY_POINT_GROUP = "mythic_vibe.plugins"


@dataclass(frozen=True)
class EntryPointRecord:
    """Typed wrapper around a discovered entry-point. The
    ``module`` and ``attr`` fields are derived from the entry-point
    value (e.g. ``"my_pkg.module:plugin_obj"`` →
    ``module="my_pkg.module"``, ``attr="plugin_obj"``)."""

    name: str
    value: str
    module: str
    attr: str
    distribution: str = ""
    version: str = ""

    @property
    def entrypoint_string(self) -> str:
        """The canonical ``module:attr`` string the plugin registry
        and loader consume."""
        return f"{self.module}:{self.attr}" if self.attr else self.module

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "module": self.module,
            "attr": self.attr,
            "distribution": self.distribution,
            "version": self.version,
            "entrypoint_string": self.entrypoint_string,
        }


def _split_value(value: str) -> tuple[str, str]:
    """Parse an entry-point value into ``(module, attr)``. Accepts
    both ``"pkg.mod:attr"`` and bare ``"pkg.mod"``."""
    if ":" in value:
        module, attr = value.split(":", 1)
        return module.strip(), attr.strip()
    return value.strip(), ""


def discover_entry_points(
    *,
    group: str = ENTRY_POINT_GROUP,
    metadata_module: Any = None,
) -> list[EntryPointRecord]:
    """Enumerate every installed entry-point under ``group``.

    Returns an empty list (never raises) when the importlib API
    is unavailable or the group has no entries — the most common
    state on a fresh install.

    ``metadata_module`` is exposed for tests; production callers
    pass ``None`` to use stdlib ``importlib.metadata``.
    """
    if metadata_module is None:
        try:
            import importlib.metadata as metadata_module  # type: ignore[assignment]
        except ImportError:  # pragma: no cover — stdlib in 3.10+
            return []

    entry_points_fn = getattr(metadata_module, "entry_points", None)
    if entry_points_fn is None:  # pragma: no cover — stdlib invariant
        return []

    try:
        # Python 3.10+: entry_points(group=...) returns a tuple.
        eps = entry_points_fn(group=group)
    except TypeError:
        # Older signature returns a dict-like grouped by group name.
        all_eps = entry_points_fn()
        eps = all_eps.get(group, []) if hasattr(all_eps, "get") else []
    except Exception:  # noqa: BLE001 — never crash discovery on bad metadata
        return []

    records: list[EntryPointRecord] = []
    for ep in eps:
        name = str(getattr(ep, "name", "") or "")
        value = str(getattr(ep, "value", "") or "")
        if not name or not value:
            continue
        module, attr = _split_value(value)
        dist = getattr(ep, "dist", None)
        distribution = ""
        version = ""
        if dist is not None:
            distribution = str(getattr(dist, "name", "") or "")
            version = str(getattr(dist, "version", "") or "")
        records.append(
            EntryPointRecord(
                name=name,
                value=value,
                module=module,
                attr=attr,
                distribution=distribution,
                version=version,
            )
        )
    return records


def find_entry_point(
    name_or_entrypoint: str,
    *,
    group: str = ENTRY_POINT_GROUP,
    metadata_module: Any = None,
) -> EntryPointRecord | None:
    """Look up a single entry-point by name OR by canonical
    ``module:attr`` string. Returns the record if found, else None.

    Used by ``cmd_plugin_install`` so operators can specify either
    the friendly name (``my_plugin``) or the full module path
    (``my_pkg.module:plugin_obj``)."""
    cleaned = name_or_entrypoint.strip()
    if not cleaned:
        return None
    records = discover_entry_points(group=group, metadata_module=metadata_module)
    # Prefer exact name match.
    for record in records:
        if record.name == cleaned:
            return record
    # Fall back to entrypoint-string match.
    for record in records:
        if record.entrypoint_string == cleaned:
            return record
    return None


__all__ = [
    "ENTRY_POINT_GROUP",
    "EntryPointRecord",
    "discover_entry_points",
    "find_entry_point",
]
