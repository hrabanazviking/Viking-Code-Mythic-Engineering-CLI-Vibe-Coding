from __future__ import annotations

import json
from pathlib import Path

from .api import PLUGIN_HOOKS, PluginRecord, utc_now, validate_hooks


class PluginRegistry:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.path = self.root / "mythic" / "plugins.json"

    def load(self) -> list[PluginRecord]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Plugin registry must be a JSON object: {self.path}")
        raw_plugins = payload.get("plugin_records", payload.get("plugins", []))
        if not isinstance(raw_plugins, list):
            raise ValueError(f"Plugin registry entries must be a list: {self.path}")
        return [PluginRecord.from_raw(item) for item in raw_plugins]

    def save(self, records: list[PluginRecord]) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 2,
            "hooks_version": 1,
            "available_hooks": PLUGIN_HOOKS,
            "sandbox_warning": "Plugins are local Python extension points. Inspect and trust them before enabling.",
            "plugins": [record.entrypoint for record in records],
            "plugin_records": [record.to_dict() for record in records],
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return self.path

    def add(self, entrypoint: str, hooks: list[str] | None = None, version: str = "unknown") -> tuple[PluginRecord, bool]:
        hooks = hooks or []
        invalid = validate_hooks(hooks)
        if invalid:
            raise ValueError(f"Unknown plugin hook(s): {', '.join(invalid)}")
        records = self.load()
        for record in records:
            if record.entrypoint == entrypoint:
                return record, False
        record = PluginRecord(entrypoint=entrypoint, hooks=hooks, version=version)
        records.append(record)
        self.save(records)
        return record, True

    def list(self, *, include_disabled: bool = True) -> list[PluginRecord]:
        records = self.load()
        if include_disabled:
            return records
        return [record for record in records if record.enabled]

    def get(self, entrypoint: str) -> PluginRecord | None:
        for record in self.load():
            if record.entrypoint == entrypoint:
                return record
        return None

    def disable(self, entrypoint: str) -> PluginRecord | None:
        records = self.load()
        for record in records:
            if record.entrypoint == entrypoint:
                record.enabled = False
                record.disabled_at = utc_now()
                self.save(records)
                return record
        return None
