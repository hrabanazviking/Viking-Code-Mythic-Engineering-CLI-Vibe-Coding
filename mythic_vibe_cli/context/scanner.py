from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Iterable

from .file_filters import FileFilterRules
from ..runtime.exec import exec_command


CURRENT_INDEX_SCHEMA_VERSION = 1
LARGE_FILE_THRESHOLD = 1_000_000
TEXT_EXTENSIONS = {
    ".py": "python",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".txt": "text",
    ".toml": "toml",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".ini": "ini",
    ".cfg": "ini",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".sh": "shell",
    ".ps1": "powershell",
    ".bat": "batch",
    ".go": "go",
    ".rs": "rust",
    ".html": "html",
    ".css": "css",
}
IMPORTANT_FILE_NAMES = {
    "README.md",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "Makefile",
    "justfile",
    "Justfile",
    "requirements.txt",
    "Pipfile",
    "tox.ini",
    "pytest.ini",
}
DOC_DIRECTORIES = {"docs"}
TEST_DIRECTORIES = {"tests", "test"}
PACKAGE_TEST_COMMANDS = {
    "pyproject.toml": "pytest -q",
    "pytest.ini": "pytest -q",
    "package.json": "npm test",
    "Cargo.toml": "cargo test",
    "go.mod": "go test ./...",
    "Makefile": "make test",
    "justfile": "just test",
    "Justfile": "just test",
}


@dataclass
class ProjectIndex:
    generated_at: str
    root: str
    git: dict[str, Any] = field(default_factory=dict)
    languages: dict[str, dict[str, int]] = field(default_factory=dict)
    important_files: list[dict[str, Any]] = field(default_factory=list)
    docs: list[dict[str, Any]] = field(default_factory=list)
    tests: list[dict[str, Any]] = field(default_factory=list)
    ignored: list[dict[str, Any]] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommended_context: list[str] = field(default_factory=list)
    schema_version: int = CURRENT_INDEX_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "root": self.root,
            "git": self.git,
            "languages": self.languages,
            "important_files": self.important_files,
            "docs": self.docs,
            "tests": self.tests,
            "ignored": self.ignored,
            "risks": self.risks,
            "recommended_context": self.recommended_context,
        }


class ProjectContextScanner:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def scan(
        self,
        *,
        changed_only: bool = False,
        docs_only: bool = False,
        include_patterns: Iterable[str] | None = None,
        exclude_patterns: Iterable[str] | None = None,
    ) -> ProjectIndex:
        rules = FileFilterRules.load(
            self.root,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )
        candidate_paths = self._discover_paths()
        changed_paths = self._changed_paths()

        included: list[Path] = []
        ignored: list[dict[str, Any]] = []

        for path in candidate_paths:
            rel = path.relative_to(self.root)
            decision = rules.classify(rel)
            if decision.ignored:
                ignored.append(
                    {
                        "path": rel.as_posix(),
                        "reason": decision.reason or "ignored by filter rules",
                    }
                )
                continue
            if changed_only and rel.as_posix() not in changed_paths:
                continue
            if docs_only and not self._is_doc_path(rel):
                continue
            included.append(path)

        git = self._git_metadata(changed_paths)
        languages, docs, tests, important_files, risks = self._summarize(included)
        risks.extend(self._derive_risks(included, docs, tests, important_files, git))
        recommended_context = self._recommended_context(important_files, docs, tests)

        return ProjectIndex(
            generated_at=_utc_now(),
            root=str(self.root),
            git=git,
            languages=languages,
            important_files=important_files,
            docs=docs,
            tests=tests,
            ignored=ignored,
            risks=risks,
            recommended_context=recommended_context,
        )

    def _discover_paths(self) -> list[Path]:
        if self._git_available():
            output = _run_git(self.root, ["ls-files", "-co", "--exclude-standard", "-z"])
            if output is not None:
                return [self.root / entry for entry in output.split("\0") if entry]

        paths: list[Path] = []
        for current_root, dirnames, filenames in os.walk(self.root):
            current = Path(current_root)
            dirnames[:] = [name for name in dirnames if name != ".git"]
            for filename in filenames:
                paths.append(current / filename)
        return paths

    def _changed_paths(self) -> set[str]:
        if not self._git_available():
            return set()
        output = _run_git(self.root, ["status", "--porcelain=v1"])
        if output is None:
            return set()
        changed: set[str] = set()
        for line in output.splitlines():
            if len(line) < 4:
                continue
            status = line[:2]
            path = line[3:]
            if "->" in path:
                path = path.split("->", 1)[1].strip()
            if status == "??":
                changed.add(path)
            else:
                changed.add(path)
        return changed

    def _git_metadata(self, changed_paths: set[str]) -> dict[str, Any]:
        branch = _run_git(self.root, ["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
        dirty = bool(changed_paths)
        return {
            "branch": branch,
            "dirty": dirty,
            "changed_files": sorted(changed_paths),
        }

    def _summarize(
        self,
        included: list[Path],
    ) -> tuple[
        dict[str, dict[str, int]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[str],
    ]:
        languages: dict[str, dict[str, int]] = {}
        docs: list[dict[str, Any]] = []
        tests: list[dict[str, Any]] = []
        important_files: list[dict[str, Any]] = []
        risks: list[str] = []

        for path in included:
            rel = path.relative_to(self.root)
            size = self._file_size(path)
            binary = self._is_binary(path)
            language = self._language_for(rel)
            rel_posix = rel.as_posix()

            if not binary and language:
                stats = languages.setdefault(language, {"files": 0, "bytes": 0})
                stats["files"] += 1
                stats["bytes"] += size

            if self._is_doc_path(rel):
                docs.append(
                    {
                        "path": rel_posix,
                        "size": size,
                        "language": language or "text",
                    }
                )
            if self._is_test_path(rel):
                tests.append(
                    {
                        "path": rel_posix,
                        "size": size,
                        "command": self._test_command_for(path),
                    }
                )
            if rel.name in IMPORTANT_FILE_NAMES or rel.as_posix().startswith("mythic_vibe_cli/"):
                important_files.append(
                    {
                        "path": rel_posix,
                        "reason": self._important_reason(rel),
                        "size": size,
                    }
                )
            if binary:
                risks.append(f"Binary file excluded from prompt context: {rel_posix}")
            elif size >= LARGE_FILE_THRESHOLD:
                risks.append(f"Large file should stay out of prompt context: {rel_posix} ({size} bytes)")

        important_files = self._dedupe_entries(important_files)
        docs = self._dedupe_entries(docs)
        tests = self._dedupe_entries(tests)
        return languages, docs, tests, important_files, risks

    def _derive_risks(
        self,
        included: list[Path],
        docs: list[dict[str, Any]],
        tests: list[dict[str, Any]],
        important_files: list[dict[str, Any]],
        git: dict[str, Any],
    ) -> list[str]:
        risks: list[str] = []
        if not docs:
            risks.append("No documentation files were found in the included context.")
        if not tests:
            risks.append("No test files were found in the included context.")
        if not important_files:
            risks.append("No obvious entrypoint or package files were found in the included context.")
        if git.get("dirty") and included:
            risks.append("Repository is dirty; use the changed-file list to focus prompt context.")

        changed_files = set(git.get("changed_files", []))
        active_changes = [path for path in changed_files if path.startswith("mythic_vibe_cli/")]
        doc_changes = [path for path in changed_files if path.endswith(".md") or path.startswith("docs/")]
        if active_changes and not doc_changes:
            risks.append("Active runtime files changed without matching docs updates; check for drift.")
        return risks

    def _recommended_context(
        self,
        important_files: list[dict[str, Any]],
        docs: list[dict[str, Any]],
        tests: list[dict[str, Any]],
    ) -> list[str]:
        recommended: list[str] = []
        for group in (important_files, docs, tests):
            for item in group:
                path = item.get("path")
                if isinstance(path, str) and path not in recommended:
                    recommended.append(path)
                if len(recommended) >= 12:
                    return recommended
        return recommended

    def _important_reason(self, rel_path: Path) -> str:
        if rel_path.name in IMPORTANT_FILE_NAMES:
            return "package or project metadata"
        if rel_path.as_posix().startswith("mythic_vibe_cli/"):
            return "active runtime code"
        if rel_path.as_posix().startswith("docs/"):
            return "core documentation"
        return "important file"

    def _test_command_for(self, path: Path) -> str | None:
        for ancestor in [path.parent, *path.parents]:
            candidate = ancestor / "pyproject.toml"
            if candidate.exists():
                return "pytest -q"
        root_files = [item.name for item in self.root.iterdir() if item.is_file()]
        for name in root_files:
            if name in PACKAGE_TEST_COMMANDS:
                return PACKAGE_TEST_COMMANDS[name]
        if path.name.startswith("test_") or path.name.endswith("_test.py"):
            return "pytest -q"
        return None

    def _is_doc_path(self, rel_path: Path) -> bool:
        if rel_path.name == "README.md":
            return True
        if rel_path.suffix.lower() in {".md", ".rst"}:
            return True
        return any(part in DOC_DIRECTORIES for part in rel_path.parts)

    def _is_test_path(self, rel_path: Path) -> bool:
        if rel_path.parts and rel_path.parts[0] in TEST_DIRECTORIES:
            return True
        return rel_path.name.startswith("test_") or rel_path.name.endswith("_test.py")

    def _language_for(self, rel_path: Path) -> str | None:
        return TEXT_EXTENSIONS.get(rel_path.suffix.lower())

    def _file_size(self, path: Path) -> int:
        try:
            return path.stat().st_size
        except OSError:
            return 0

    def _is_binary(self, path: Path) -> bool:
        try:
            with path.open("rb") as handle:
                chunk = handle.read(8192)
        except OSError:
            return False
        if b"\0" in chunk:
            return True
        try:
            chunk.decode("utf-8")
        except UnicodeDecodeError:
            return True
        return False

    def _dedupe_entries(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for item in entries:
            path = item.get("path")
            if not isinstance(path, str) or path in seen:
                continue
            seen.add(path)
            deduped.append(item)
        return deduped

    def _git_available(self) -> bool:
        return (self.root / ".git").exists() or _run_git(self.root, ["rev-parse", "--is-inside-work-tree"], quiet=True) is not None


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_git(root: Path, args: list[str], *, quiet: bool = False) -> str | None:
    result = exec_command("git", ["-C", str(root), *args], cwd=root)
    if result.code != 0:
        return None
    text = result.stdout.rstrip("\n")
    if quiet:
        return text
    return text or None
