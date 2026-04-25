from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mythic_vibe_cli.core.state import CURRENT_STATE_SCHEMA_VERSION, ProjectState, coerce_project_state
from mythic_vibe_cli.persistence.json_store import JsonStateStore, StateStoreError


@dataclass
class MigrationResult:
    status_path: Path
    backup_path: Path | None
    created: bool = False
    migrated: bool = False
    already_current: bool = False
    recovered_corrupt: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "status_path": str(self.status_path),
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "created": self.created,
            "migrated": self.migrated,
            "already_current": self.already_current,
            "recovered_corrupt": self.recovered_corrupt,
        }


def migrate_project_state(root: Path, *, default_goal: str = "unspecified goal") -> MigrationResult:
    store = JsonStateStore(root)

    if not store.exists():
        state = ProjectState(goal=default_goal)
        store.write_state(state)
        return MigrationResult(status_path=store.status_path, backup_path=None, created=True)

    try:
        payload = store.read_payload()
    except StateStoreError:
        backup = store.backup_status()
        store.write_state(ProjectState(goal=default_goal))
        return MigrationResult(
            status_path=store.status_path,
            backup_path=backup,
            migrated=True,
            recovered_corrupt=True,
        )

    if payload is None:
        state = ProjectState(goal=default_goal)
        store.write_state(state)
        return MigrationResult(status_path=store.status_path, backup_path=None, created=True)

    if payload.get("schema_version") == CURRENT_STATE_SCHEMA_VERSION:
        return MigrationResult(status_path=store.status_path, backup_path=None, already_current=True)

    backup = store.backup_status()
    state = coerce_project_state(payload)
    store.write_state(state)
    return MigrationResult(status_path=store.status_path, backup_path=backup, migrated=True)
