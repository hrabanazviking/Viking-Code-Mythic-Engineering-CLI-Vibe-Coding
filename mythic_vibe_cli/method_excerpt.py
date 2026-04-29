from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

DEFAULT_METHOD_CORPUS_DIR = "docs/mythic_source"
DEFAULT_EXCERPT_CHAR_LIMIT = 600

PHASE_METHOD_SECTIONS: dict[str, tuple[str, ...]] = {
    "intent": ("principles", "workflow"),
    "architecture": ("principles", "ai roles", "required docs"),
    "plan": ("workflow",),
    "build": ("workflow", "refactor method"),
    "verify": ("verification method", "failure modes"),
    "reflect": ("required docs",),
}

ROLE_METHOD_SECTIONS: dict[str, tuple[str, ...]] = {
    "Skald": ("principles", "workflow"),
    "Architect": ("principles", "ai roles", "required docs"),
    "Cartographer": ("workflow", "ai roles"),
    "Forge Worker": ("workflow", "refactor method"),
    "Auditor": ("verification method", "failure modes"),
    "Scribe": ("required docs", "principles"),
    "Debugger": ("debugging method", "failure modes"),
    "Refactorer": ("refactor method",),
}

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$", re.MULTILINE)
_SKIP_FILES = {"method_manifest.json", "_import_index.json", "method_pin.json"}


@dataclass
class MethodExcerpt:
    section: str
    heading: str
    source_path: str
    text: str
    truncated: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "section": self.section,
            "heading": self.heading,
            "source_path": self.source_path,
            "text": self.text,
            "truncated": self.truncated,
        }


def sections_for(role: str | None, phase: str | None) -> tuple[str, ...]:
    if role and role in ROLE_METHOD_SECTIONS:
        return ROLE_METHOD_SECTIONS[role]
    if phase and phase in PHASE_METHOD_SECTIONS:
        return PHASE_METHOD_SECTIONS[phase]
    return ()


def select_method_excerpts(
    corpus_dir: Path | None,
    sections: tuple[str, ...] | list[str],
    *,
    char_limit: int = DEFAULT_EXCERPT_CHAR_LIMIT,
) -> list[MethodExcerpt]:
    if corpus_dir is None or not corpus_dir.exists() or not corpus_dir.is_dir():
        return []
    keywords = tuple(
        keyword.strip().lower()
        for keyword in sections
        if isinstance(keyword, str) and keyword.strip()
    )
    if not keywords:
        return []

    results: dict[str, MethodExcerpt] = {}
    for path in sorted(corpus_dir.rglob("*.md")):
        if not path.is_file() or path.name in _SKIP_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue

        matches = list(_HEADING_RE.finditer(text))
        if not matches:
            continue

        for index, match in enumerate(matches):
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            heading_lower = heading_text.lower()

            for keyword in keywords:
                if keyword in results:
                    continue
                if keyword not in heading_lower:
                    continue
                start = match.end()
                end = len(text)
                for next_match in matches[index + 1 :]:
                    next_level = len(next_match.group(1))
                    if next_level <= level:
                        end = next_match.start()
                        break
                body = text[start:end].strip()
                truncated = len(body) > char_limit
                if truncated:
                    body = body[:char_limit].rstrip() + "…"
                rel_path = path.relative_to(corpus_dir).as_posix()
                results[keyword] = MethodExcerpt(
                    section=keyword,
                    heading=heading_text,
                    source_path=rel_path,
                    text=body,
                    truncated=truncated,
                )
                break

    return [results[key] for key in keywords if key in results]
