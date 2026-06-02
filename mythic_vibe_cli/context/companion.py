"""Shell-facing repository context summaries.

This module adapts the existing project scanner into concise responses
for the companion shell. It does not replace ``scan`` or the project
indexer; it gives natural-language shell prompts a read-only context
path that can answer questions like "Find the memory system".
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path
from typing import Any

from .file_filters import FileFilterRules
from .scanner import LARGE_FILE_THRESHOLD, ProjectContextScanner, ProjectIndex, TEXT_EXTENSIONS


STOP_WORDS = frozenset({
    "a",
    "about",
    "and",
    "code",
    "find",
    "for",
    "in",
    "is",
    "me",
    "of",
    "project",
    "repo",
    "repository",
    "show",
    "system",
    "the",
    "this",
    "where",
})


@dataclass(frozen=True)
class RelevantFile:
    path: str
    score: int
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "score": self.score,
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class CompanionContextSummary:
    index: ProjectIndex
    query: str = ""
    relevant_files: tuple[RelevantFile, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index.to_dict(),
            "query": self.query,
            "relevant_files": [item.to_dict() for item in self.relevant_files],
        }


def build_companion_context(root: Path, query: str = "") -> CompanionContextSummary:
    scanner = ProjectContextScanner(root)
    index = scanner.scan()
    relevant = find_relevant_files(root, query) if query.strip() else ()
    return CompanionContextSummary(index=index, query=query, relevant_files=relevant)


def find_relevant_files(root: Path, query: str, suggested_max_results: int = 8) -> tuple[RelevantFile, ...]:
    tokens = _query_tokens(query)
    if not tokens:
        return ()

    resolved_root = root.resolve()
    rules = FileFilterRules.load(resolved_root)
    results: list[RelevantFile] = []

    for path in _candidate_text_files(resolved_root, rules):
        rel = path.relative_to(resolved_root)
        rel_text = rel.as_posix()
        score, reasons = _score_file(path, rel_text, tokens)
        if score <= 0:
            continue
        results.append(RelevantFile(path=rel_text, score=score, reasons=tuple(reasons)))

    results.sort(key=lambda item: (-item.score, item.path))
    return tuple(results[:suggested_max_results])


def render_companion_context(summary: CompanionContextSummary) -> str:
    index = summary.index
    lines = [
        "Repository context",
        f"  Root: {index.root}",
        f"  Branch: {index.git.get('branch', 'unknown')}",
        f"  Dirty: {bool(index.git.get('dirty'))}",
    ]

    languages = sorted(
        index.languages.items(),
        key=lambda item: (-int(item[1].get("files", 0)), item[0]),
    )
    if languages:
        language_text = ", ".join(
            f"{name} ({stats.get('files', 0)} files)"
            for name, stats in languages[:5]
        )
        lines.append(f"  Languages: {language_text}")

    test_commands = sorted({
        str(item.get("command"))
        for item in index.tests
        if item.get("command")
    })
    if test_commands:
        lines.append("  Test commands: " + ", ".join(test_commands))

    if index.recommended_context:
        lines.append("  Recommended context:")
        for path in index.recommended_context[:8]:
            lines.append(f"    - {path}")

    if summary.relevant_files:
        lines.append("  Relevant files:")
        for item in summary.relevant_files:
            reason_text = ", ".join(item.reasons)
            lines.append(f"    - {item.path} ({reason_text})")

    if index.risks:
        lines.append("  Risks:")
        for risk in index.risks[:5]:
            lines.append(f"    - {risk}")

    return "\n".join(lines)


def _query_tokens(query: str) -> tuple[str, ...]:
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"[a-zA-Z0-9_]+", query.lower()):
        if len(raw) < 3 or raw in STOP_WORDS or raw in seen:
            continue
        seen.add(raw)
        tokens.append(raw)
    return tuple(tokens)


def _candidate_text_files(root: Path, rules: FileFilterRules) -> list[Path]:
    paths: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if ".git" in rel.parts:
            continue
        decision = rules.classify(rel)
        if decision.ignored:
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size >= LARGE_FILE_THRESHOLD:
            continue
        paths.append(path)
    return paths


def _score_file(path: Path, rel_text: str, tokens: tuple[str, ...]) -> tuple[int, list[str]]:
    lower_path = rel_text.lower()
    score = 0
    reasons: list[str] = []

    for token in tokens:
        if token in lower_path:
            score += 6
            reasons.append(f"path:{token}")

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        content = ""
    lower_content = content.lower()
    for token in tokens:
        count = lower_content.count(token)
        if count <= 0:
            continue
        score += min(5, count)
        reasons.append(f"content:{token}")

    return score, reasons


__all__ = [
    "CompanionContextSummary",
    "RelevantFile",
    "build_companion_context",
    "find_relevant_files",
    "render_companion_context",
]
