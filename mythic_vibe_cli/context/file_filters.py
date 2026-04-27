from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable


DEFAULT_IGNORE_PATTERNS = [
    ".git/",
    "__pycache__/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".venv/",
    "venv/",
    "node_modules/",
    "dist/",
    "build/",
    "target/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.webp",
    "*.mp4",
    "*.mov",
    "*.mkv",
    "*.wav",
    "*.mp3",
    "*.ogg",
    "*.flac",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.gguf",
    "ai/",
    "core/",
    "systems/",
    "sessions/",
    "yggdrasil/",
    "imports/",
    "mindspark_thoughtform/",
    "ollama/",
    "whisper/",
    "chatterbox/",
    "WYRD-Protocol-*/",
]


@dataclass
class FilterDecision:
    ignored: bool
    reason: str | None = None
    matched_pattern: str | None = None


@dataclass
class FileFilterRules:
    root: Path
    include_patterns: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    mythicignore_patterns: list[str] = field(default_factory=list)
    default_patterns: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE_PATTERNS))

    @classmethod
    def load(
        cls,
        root: Path,
        *,
        include_patterns: Iterable[str] | None = None,
        exclude_patterns: Iterable[str] | None = None,
    ) -> FileFilterRules:
        root = root.resolve()
        mythicignore = root / ".mythicignore"
        patterns: list[str] = []
        if mythicignore.exists():
            for line in mythicignore.read_text(encoding="utf-8", errors="replace").splitlines():
                entry = line.strip()
                if not entry or entry.startswith("#"):
                    continue
                patterns.append(entry)
        return cls(
            root=root,
            include_patterns=list(include_patterns or []),
            exclude_patterns=list(exclude_patterns or []),
            mythicignore_patterns=patterns,
        )

    def classify(self, rel_path: Path | str) -> FilterDecision:
        posix = _to_posix(rel_path)

        if self.include_patterns and self._matches_any(posix, self.include_patterns):
            return FilterDecision(ignored=False, reason=None)

        pattern = self._last_match(posix, self.default_patterns + self.mythicignore_patterns + self.exclude_patterns)
        if pattern is not None:
            if pattern.startswith("!"):
                return FilterDecision(ignored=False, reason=None, matched_pattern=pattern)
            return FilterDecision(
                ignored=True,
                reason=f"ignored by pattern: {pattern}",
                matched_pattern=pattern,
            )

        if self.include_patterns:
            return FilterDecision(
                ignored=True,
                reason="did not match any include pattern",
                matched_pattern=None,
            )

        return FilterDecision(ignored=False, reason=None)

    def _matches_any(self, posix_path: str, patterns: Iterable[str]) -> bool:
        return any(self._pattern_matches(posix_path, pattern) for pattern in patterns)

    def _last_match(self, posix_path: str, patterns: Iterable[str]) -> str | None:
        matched: str | None = None
        for raw_pattern in patterns:
            pattern = raw_pattern.strip()
            if not pattern or pattern.startswith("#"):
                continue
            inverted = pattern.startswith("!")
            candidate = pattern[1:] if inverted else pattern
            if self._pattern_matches(posix_path, candidate):
                matched = pattern
                if inverted:
                    matched = pattern
                else:
                    matched = pattern
        return matched

    def _pattern_matches(self, posix_path: str, pattern: str) -> bool:
        if not pattern:
            return False
        if pattern.endswith("/"):
            prefix = pattern.rstrip("/")
            return posix_path == prefix or posix_path.startswith(prefix + "/")
        if "/" in pattern:
            return fnmatch(posix_path, pattern)
        name = Path(posix_path).name
        return fnmatch(name, pattern) or fnmatch(posix_path, pattern)


def _to_posix(rel_path: Path | str) -> str:
    if isinstance(rel_path, Path):
        return rel_path.as_posix()
    return Path(rel_path).as_posix()
