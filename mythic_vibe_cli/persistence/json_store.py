from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import time
from types import TracebackType
from typing import Any

from mythic_vibe_cli.core.state import ProjectState, coerce_project_state


class StateStoreError(RuntimeError):
    """Raised when project state cannot be read or written safely."""


class FileLock(AbstractContextManager["FileLock"]):
    def __init__(self, lock_path: Path, *, timeout_seconds: float = 5.0):
        self.lock_path = lock_path
        self.timeout_seconds = timeout_seconds
        self._handle: int | None = None

    def __enter__(self) -> FileLock:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                self._handle = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(self._handle, str(os.getpid()).encode("ascii", errors="ignore"))
                return self
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise StateStoreError(f"Timed out waiting for state lock: {self.lock_path}") from None
                time.sleep(0.05)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        if self._handle is not None:
            os.close(self._handle)
            self._handle = None
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass
        return None


class JsonStateStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.mythic_dir = self.root / "mythic"
        self.status_path = self.mythic_dir / "status.json"
        self.backup_dir = self.mythic_dir / "backups"
        self.lock_path = self.status_path.with_suffix(".json.lock")

    def exists(self) -> bool:
        return self.status_path.exists()

    def read_payload(self) -> dict[str, Any] | None:
        if not self.status_path.exists():
            return None
        try:
            payload = json.loads(self.status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise StateStoreError(f"Invalid JSON in {self.status_path}: {exc.msg}") from exc
        except OSError as exc:
            raise StateStoreError(f"Cannot read {self.status_path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise StateStoreError(f"{self.status_path} must contain a JSON object.")
        return payload

    def load_state(self, *, default_goal: str = "unspecified goal") -> ProjectState:
        payload = self.read_payload()
        if payload is None:
            return ProjectState(goal=default_goal)
        return coerce_project_state(payload)

    def backup_status(self) -> Path | None:
        if not self.status_path.exists():
            return None
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        backup = self.backup_dir / f"status.json.{stamp}.bak"
        suffix = 1
        while backup.exists():
            backup = self.backup_dir / f"status.json.{stamp}.{suffix}.bak"
            suffix += 1
        shutil.copy2(self.status_path, backup)
        return backup

    def write_state(self, state: ProjectState) -> Path:
        self.mythic_dir.mkdir(parents=True, exist_ok=True)
        with FileLock(self.lock_path):
            temp_path = self.status_path.with_name(f"{self.status_path.name}.tmp")
            temp_path.write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
            os.replace(temp_path, self.status_path)
        return self.status_path
