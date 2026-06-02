from __future__ import annotations

from dataclasses import dataclass, field
import sys
from pathlib import Path
from typing import Any

from ..runtime.exec import DEFAULT_EXEC_TIMEOUT_SECONDS, exec_command


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

    def summarize_failures(self, max_lines: int = 50) -> str:
        """Returns a concise summary of test failures to feed to an LLM."""
        if self.ok:
            return "All tests passed successfully."
            
        lines = []
        for cmd_res in self.commands:
            if cmd_res.exit_code != 0:
                lines.append(f"Command '{' '.join(cmd_res.command)}' failed with exit code {cmd_res.exit_code}:")
                # Combine stdout and stderr
                combined = (cmd_res.stdout + "\n" + cmd_res.stderr).strip()
                combined_lines = combined.splitlines()
                if len(combined_lines) > max_lines:
                    lines.append("... (output truncated) ...")
                    lines.extend(combined_lines[-max_lines:])
                else:
                    lines.extend(combined_lines)
                lines.append("-" * 40)
                
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(self.warnings)
            
        return "\n".join(lines)


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
    # Phase 19.0 / BS-3 (additive 2026-05-02): default subprocess
    # timeout — caps how long a hung pytest / ruff / mypy invocation
    # can block the verify pipeline. 5 minutes is generous for any
    # legitimate test suite; longer-running suites can call
    # exec_command directly with a higher timeout.
    result = exec_command(
        command[0], command[1:], cwd=cwd,
        timeout=DEFAULT_EXEC_TIMEOUT_SECONDS,
    )
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
