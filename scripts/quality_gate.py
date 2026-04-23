#!/usr/bin/env python3
"""Repository quality gate checks for test/exception hygiene."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def is_test_file(path: Path) -> bool:
    return path.name.startswith("test_") or "tests" in path.parts


def scan() -> dict:
    py_files = [
        p for p in ROOT.rglob("*.py")
        if ".venv" not in p.parts and "__pycache__" not in p.parts
    ]
    findings = {
        "bare_except": [],
        "sys_exit_in_tests": [],
        "test_returns_value": [],
    }

    for path in py_files:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        test_file = is_test_file(path)

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                findings["bare_except"].append({"file": rel, "line": node.lineno})

            if test_file and isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "sys" and node.func.attr == "exit":
                    findings["sys_exit_in_tests"].append({"file": rel, "line": node.lineno})

            if test_file and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                for child in node.body:
                    if isinstance(child, ast.Return) and child.value is not None:
                        findings["test_returns_value"].append(
                            {"file": rel, "function": node.name, "line": child.lineno}
                        )

    return findings


def main() -> int:
    findings = scan()
    failures = sum(len(v) for v in findings.values())

    if failures == 0:
        print("quality_gate: PASS")
        return 0

    print("quality_gate: FAIL")
    for key, values in findings.items():
        if not values:
            continue
        print(f"- {key}: {len(values)}")
        for item in values[:20]:
            print(f"  {item}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
