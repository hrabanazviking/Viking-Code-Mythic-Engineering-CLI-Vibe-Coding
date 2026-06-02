from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mythic_vibe_cli.runtime.script_guard import guarded_main


PATH_PATTERN = re.compile(r"[A-Za-z]:[\\/][^\s'\"<>|]+")
DEFAULT_SUFFIXES = (".py", ".md", ".yaml", ".yml", ".json", ".txt", ".toml")
EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}


@dataclass(frozen=True)
class FixResult:
    path: Path
    replacements: int = 0
    changed: bool = False
    error: str = ""


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _iter_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in suffixes:
            out.append(path)
    return sorted(out)


def _replacement_for(raw_path: str, root: Path) -> str:
    cleaned = raw_path.strip("'\"")
    candidate = Path(cleaned)
    if _is_under(candidate, root):
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    return ""


def fix_file(path: Path, root: Path, *, dry_run: bool, backup: bool) -> FixResult:
    try:
        original = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return FixResult(path=path, error=f"read failed: {exc}")

    replacements = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal replacements
        replacement = _replacement_for(match.group(0), root)
        if replacement != match.group(0):
            replacements += 1
        return replacement

    updated = PATH_PATTERN.sub(replace, original)
    if updated == original:
        return FixResult(path=path)

    if dry_run:
        return FixResult(path=path, replacements=replacements, changed=True)

    try:
        if backup:
            backup_path = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, backup_path)
        path.write_text(updated, encoding="utf-8")
    except OSError as exc:
        return FixResult(path=path, replacements=replacements, error=f"write failed: {exc}")

    return FixResult(path=path, replacements=replacements, changed=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replace Windows absolute paths in text files with repo-relative paths.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=PROJECT_ROOT,
        help="Repository root to scan (default: this checkout).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files.",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Write .bak files before modifying content.",
    )
    parser.add_argument(
        "--suffix",
        action="append",
        default=[],
        help="File suffix to scan. Repeatable. Default: common text/code suffixes.",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print(f"ERROR: root directory not found: {root}", file=sys.stderr)
        return 2

    suffixes = tuple(args.suffix) if args.suffix else DEFAULT_SUFFIXES
    results = [
        fix_file(path, root, dry_run=args.dry_run, backup=args.backup)
        for path in _iter_files(root, suffixes)
    ]

    changed = [item for item in results if item.changed]
    errors = [item for item in results if item.error]

    for item in changed:
        rel = item.path.relative_to(root).as_posix()
        action = "would update" if args.dry_run else "updated"
        print(f"{action}: {rel} ({item.replacements} replacement(s))")

    for item in errors:
        rel = item.path.relative_to(root).as_posix() if _is_under(item.path, root) else str(item.path)
        print(f"ERROR: {rel}: {item.error}", file=sys.stderr)

    print(
        f"Scanned {len(results)} file(s); "
        f"{len(changed)} changed; {len(errors)} error(s)."
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(
        guarded_main(
            lambda: main(),
            script_name=Path(__file__).name,
            json_mode=False,
        )
    )
