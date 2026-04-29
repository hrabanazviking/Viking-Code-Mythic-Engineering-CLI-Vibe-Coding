from __future__ import annotations

from dataclasses import dataclass, field
import sys
from pathlib import Path
from typing import Any

from ..runtime.exec import exec_command


@dataclass
class CommandResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": list(self.command),
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


@dataclass
class TestRunnerResult:
    commands: list[CommandResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(item.exit_code == 0 for item in self.commands)

    def to_dict(self) -> dict[str, Any]:
        return {
            "commands": [item.to_dict() for item in self.commands],
            "warnings": list(self.warnings),
            "ok": self.ok,
        }


def discover_default_commands(root: Path) -> list[list[str]]:
    tests_dir = root / "tests"
    if not tests_dir.exists():
        return []
    if not any(tests_dir.rglob("test*.py")):
        return []
    return [[sys.executable, "-m", "pytest", "-q"]]


def run_command(command: list[str], *, cwd: Path) -> CommandResult:
    if not command:
        return CommandResult(command=[], exit_code=127, stdout="", stderr="Empty command")
    result = exec_command(command[0], command[1:], cwd=cwd)
    return CommandResult(
        command=command,
        exit_code=result.code,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def run_default_commands(root: Path) -> TestRunnerResult:
    commands = discover_default_commands(root)
    if not commands:
        return TestRunnerResult(warnings=["No test commands discovered for this project."])

    results = [run_command(command, cwd=root) for command in commands]
    return TestRunnerResult(commands=results)
