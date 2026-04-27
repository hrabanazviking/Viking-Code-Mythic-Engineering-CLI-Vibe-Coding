from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .scanner import ProjectContextScanner, ProjectIndex


class ProjectIndexer:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.index_path = self.root / "mythic" / "project_index.json"

    def build(
        self,
        *,
        changed_only: bool = False,
        docs_only: bool = False,
        include_patterns: Iterable[str] | None = None,
        exclude_patterns: Iterable[str] | None = None,
        write: bool = True,
    ) -> ProjectIndex:
        index = ProjectContextScanner(self.root).scan(
            changed_only=changed_only,
            docs_only=docs_only,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )
        if write:
            self.write(index)
        return index

    def write(self, index: ProjectIndex) -> Path:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(index.to_dict(), indent=2) + "\n", encoding="utf-8")
        return self.index_path
