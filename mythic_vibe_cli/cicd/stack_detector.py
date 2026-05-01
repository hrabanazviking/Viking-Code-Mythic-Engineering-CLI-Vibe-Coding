"""Tech-stack detector (PH-12 Slice 12.1).

Pure inspector that reads a project's manifest files and reports
which language ecosystems + tooling are present. The CI / Docker
scaffolders consume the result.

Detection strategy is **manifest-first**: we read well-known
files (pyproject.toml, package.json, Cargo.toml, go.mod, etc)
rather than walking every source file. This is fast, stable
across project sizes, and matches how operators think about
"what stack is this?".

Cross-platform: pure stdlib (``pathlib`` + ``json`` +
``tomllib`` / ``tomli``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DetectedStack:
    """Aggregated detection result. Each language flag is True
    when its primary manifest is present."""

    has_python: bool = False
    has_node: bool = False
    has_rust: bool = False
    has_go: bool = False
    has_java: bool = False
    has_ruby: bool = False

    python_test_runner: str = ""  # "pytest" | "unittest" | ""
    python_linters: tuple[str, ...] = ()  # ("ruff", "mypy", ...)
    python_min_version: str = ""  # e.g. ">=3.10"

    node_package_manager: str = ""  # "npm" | "yarn" | "pnpm" | ""
    node_test_command: str = ""
    node_lint_command: str = ""

    notes: list[str] = field(default_factory=list)

    @property
    def primary_language(self) -> str:
        """First detected language in priority order. Used by
        scaffolders to pick a template when several languages
        are present."""
        if self.has_python:
            return "python"
        if self.has_node:
            return "node"
        if self.has_rust:
            return "rust"
        if self.has_go:
            return "go"
        if self.has_java:
            return "java"
        if self.has_ruby:
            return "ruby"
        return "unknown"

    @property
    def detected_languages(self) -> tuple[str, ...]:
        out: list[str] = []
        if self.has_python:
            out.append("python")
        if self.has_node:
            out.append("node")
        if self.has_rust:
            out.append("rust")
        if self.has_go:
            out.append("go")
        if self.has_java:
            out.append("java")
        if self.has_ruby:
            out.append("ruby")
        return tuple(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_language": self.primary_language,
            "detected_languages": list(self.detected_languages),
            "has_python": self.has_python,
            "has_node": self.has_node,
            "has_rust": self.has_rust,
            "has_go": self.has_go,
            "has_java": self.has_java,
            "has_ruby": self.has_ruby,
            "python_test_runner": self.python_test_runner,
            "python_linters": list(self.python_linters),
            "python_min_version": self.python_min_version,
            "node_package_manager": self.node_package_manager,
            "node_test_command": self.node_test_command,
            "node_lint_command": self.node_lint_command,
            "notes": list(self.notes),
        }


def _load_pyproject(path: Path) -> dict[str, Any] | None:
    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:  # pragma: no cover — 3.10 fallback
            import tomli as tomllib  # type: ignore[no-redef, import-not-found]
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except Exception:  # noqa: BLE001 — defensive; bad TOML never crashes detection
        return None


def _detect_python(root: Path, notes: list[str]) -> tuple[bool, str, tuple[str, ...], str]:
    pyproject = root / "pyproject.toml"
    setup_py = root / "setup.py"
    requirements_files = list(root.glob("requirements*.txt"))

    has_python = pyproject.is_file() or setup_py.is_file() or bool(requirements_files)
    if not has_python:
        return False, "", (), ""

    test_runner = ""
    linters: list[str] = []
    min_version = ""

    if pyproject.is_file():
        payload = _load_pyproject(pyproject)
        if isinstance(payload, dict):
            project = payload.get("project")
            if isinstance(project, dict):
                requires = project.get("requires-python")
                if isinstance(requires, str):
                    min_version = requires.strip()
            tool = payload.get("tool")
            if isinstance(tool, dict):
                if "pytest" in tool or "ini_options" in (tool.get("pytest") or {}):
                    test_runner = "pytest"
                if "ruff" in tool:
                    linters.append("ruff")
                if "mypy" in tool:
                    linters.append("mypy")
                if "black" in tool:
                    linters.append("black")
            optional_deps = (project or {}).get("optional-dependencies", {})
            if isinstance(optional_deps, dict):
                flat = " ".join(
                    str(item) for items in optional_deps.values() for item in items
                ).lower()
                if "pytest" in flat and not test_runner:
                    test_runner = "pytest"
                if "ruff" in flat and "ruff" not in linters:
                    linters.append("ruff")
                if "mypy" in flat and "mypy" not in linters:
                    linters.append("mypy")
        else:
            notes.append("pyproject.toml present but unparseable")

    if not test_runner and (root / "tests").is_dir():
        # Operators may use plain unittest without configuring pytest.
        test_runner = "pytest"  # safe default — pytest runs unittest classes too

    return has_python, test_runner, tuple(linters), min_version


def _detect_node(root: Path, notes: list[str]) -> tuple[bool, str, str, str]:
    package_json = root / "package.json"
    if not package_json.is_file():
        return False, "", "", ""

    package_manager = "npm"
    if (root / "yarn.lock").is_file():
        package_manager = "yarn"
    elif (root / "pnpm-lock.yaml").is_file():
        package_manager = "pnpm"

    test_command = ""
    lint_command = ""
    try:
        with package_json.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:  # noqa: BLE001 — bad JSON never crashes detection
        notes.append("package.json present but unparseable")
        return True, package_manager, "", ""

    scripts = payload.get("scripts") if isinstance(payload, dict) else None
    if isinstance(scripts, dict):
        if isinstance(scripts.get("test"), str) and scripts["test"]:
            test_command = f"{package_manager} test"
        if isinstance(scripts.get("lint"), str) and scripts["lint"]:
            lint_command = f"{package_manager} run lint"

    return True, package_manager, test_command, lint_command


def detect_stack(root: Path) -> DetectedStack:
    """Walk the project root and return a :class:`DetectedStack`."""
    root = Path(root)
    notes: list[str] = []

    has_python, py_runner, py_linters, py_min = _detect_python(root, notes)
    has_node, node_pm, node_test, node_lint = _detect_node(root, notes)
    has_rust = (root / "Cargo.toml").is_file()
    has_go = (root / "go.mod").is_file()
    has_java = (root / "pom.xml").is_file() or (root / "build.gradle").is_file() or (
        root / "build.gradle.kts"
    ).is_file()
    has_ruby = (root / "Gemfile").is_file()

    return DetectedStack(
        has_python=has_python,
        has_node=has_node,
        has_rust=has_rust,
        has_go=has_go,
        has_java=has_java,
        has_ruby=has_ruby,
        python_test_runner=py_runner,
        python_linters=py_linters,
        python_min_version=py_min,
        node_package_manager=node_pm,
        node_test_command=node_test,
        node_lint_command=node_lint,
        notes=notes,
    )


__all__ = [
    "DetectedStack",
    "detect_stack",
]
