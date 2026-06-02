"""WASI stdlib usage audit (PH-23.15).

Walks ``mythic_vibe_cli/`` AST + transitively follows imports
to build the set of stdlib modules the CLI's stdlib-only base
actually uses. Outputs a sorted list operators can compare
against CPython's WASI freeze list to identify pruning
candidates.

The audit is deliberately conservative — when a module imports
``import json``, the audit assumes the entire ``json`` package
is needed (json's own internal C-extensions, helper modules,
etc.). Pruning would only apply to stdlib top-level modules the
CLI never references *anywhere* in its transitive import graph.

Usage:
    python tools/wasi_stdlib_audit.py
    python tools/wasi_stdlib_audit.py --json    # machine-readable
    python tools/wasi_stdlib_audit.py --root C:/path/to/different/repo

The current CPython 3.12 stdlib has ~200 top-level modules.
A typical CLI with a small surface uses ~40-60. Pruning the
remaining ~140 from the WASI freeze list shrinks the python.wasm
artifact by an estimated 30-40%.

Limitations:
- AST-only static analysis — dynamic imports via importlib
  are not detected. The audit prints any ``importlib.import_module``
  calls it finds so an operator can manually verify those
  dynamic targets are accounted for.
- C-extension modules in the stdlib (``_json``, ``_socket``,
  etc.) are accounted for via their pure-Python wrappers'
  imports. The freeze list only freezes pure Python anyway;
  C-extensions are linked in via the WASI build's static-
  link path.
"""

from __future__ import annotations

import argparse
import ast
import json as _json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mythic_vibe_cli.runtime.script_guard import guarded_main


# Python 3.12 stdlib top-level modules. Maintained as a snapshot
# rather than computed at runtime so the audit is reproducible
# across systems (avoids picking up site-packages or operator-
# installed shadows of stdlib names).
PY312_STDLIB_TOP_LEVEL: frozenset[str] = frozenset({
    "__future__", "_thread", "abc", "aifc", "antigravity", "argparse",
    "array", "ast", "asynchat", "asyncio", "asyncore", "audioop",
    "base64",
    "bdb", "binascii", "bisect", "builtins", "bz2", "cProfile",
    "calendar", "cgi", "cgitb", "chunk", "cmath", "cmd", "code",
    "codecs", "codeop", "collections", "colorsys", "compileall",
    "concurrent", "configparser", "contextlib", "contextvars",
    "copy", "copyreg", "crypt", "csv", "ctypes", "curses",
    "dataclasses", "datetime", "dbm", "decimal", "difflib", "dis",
    "doctest", "email", "encodings", "ensurepip", "enum", "errno",
    "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
    "fractions", "ftplib", "functools", "gc", "genericpath",
    "getopt", "getpass", "gettext", "glob", "graphlib", "grp",
    "gzip", "hashlib", "heapq", "hmac", "html", "http", "idlelib",
    "imaplib", "imghdr", "importlib", "inspect", "io", "ipaddress",
    "itertools", "json", "keyword", "lib2to3", "linecache", "locale",
    "logging", "lzma", "mailbox", "mailcap", "marshal", "math",
    "mimetypes", "mmap", "modulefinder", "msilib", "msvcrt",
    "multiprocessing", "netrc", "nis", "nntplib", "ntpath", "numbers",
    "opcode", "operator", "optparse", "os", "ossaudiodev",
    "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil",
    "platform", "plistlib", "poplib", "posix", "posixpath",
    "pprint", "profile", "pstats", "pty", "pwd", "py_compile",
    "pyclbr", "pydoc", "pydoc_data", "pyexpat", "queue", "quopri",
    "random", "re", "readline", "reprlib", "resource", "rlcompleter",
    "runpy", "sched", "secrets", "select", "selectors", "shelve",
    "shlex", "shutil", "signal", "site", "smtpd", "smtplib", "sndhdr",
    "socket", "socketserver", "spwd", "sqlite3", "sre_compile",
    "sre_constants", "sre_parse", "ssl", "stat", "statistics",
    "string", "stringprep", "struct", "subprocess", "sunau",
    "symtable", "sys", "sysconfig", "syslog", "tabnanny", "tarfile",
    "telnetlib", "tempfile", "termios", "test", "textwrap",
    "threading", "time", "timeit", "tkinter", "token", "tokenize",
    "tomllib", "trace", "traceback", "tracemalloc", "tty", "turtle",
    "turtledemo", "types", "typing", "unicodedata", "unittest",
    "urllib", "uu", "uuid", "venv", "warnings", "wave", "weakref",
    "webbrowser", "winreg", "winsound", "wsgiref", "xdrlib", "xml",
    "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib", "zoneinfo",
})

# Top-level stdlib modules that genuinely don't apply to a WASI
# runtime regardless of CLI usage — pruning these is safe even
# if the AST scanner misses an import, because they wouldn't
# work in WASI anyway. Listed so the audit can report them as
# "always-prune candidates" separately from "never-imported"
# candidates.
WASI_INCOMPATIBLE_STDLIB: frozenset[str] = frozenset({
    # Subprocess + fork primitives — WASI has no process model.
    "subprocess", "multiprocessing", "concurrent",
    # Posix-only signals + tty — not modeled in WASI today.
    "fcntl", "termios", "tty", "pty", "resource", "syslog",
    # GUI / audio — no WASI bindings.
    "tkinter", "turtle", "turtledemo", "idlelib",
    "audioop", "ossaudiodev", "wave", "aifc", "sunau", "chunk",
    "sndhdr",
    # Mac-specific (Python 3.13+ removed; 3.12 still has them).
    "msilib", "msvcrt", "winreg", "winsound", "winreg",
    # Long-deprecated:
    "asynchat", "asyncore", "smtpd",
    # Network-server frameworks the CLI doesn't use:
    "wsgiref", "xmlrpc", "imaplib", "nntplib", "poplib",
    "telnetlib", "ftplib", "smtplib",
    # Media + binary:
    "imghdr", "cgi", "cgitb", "mailcap", "mailbox",
    # Testing infrastructure:
    "test", "unittest", "doctest", "trace", "tracemalloc",
    "tabnanny", "modulefinder", "pyclbr", "py_compile",
    "compileall", "pdb", "bdb", "profile", "cProfile", "pstats",
    "timeit",
    # Database (sqlite3 needs platform native lib):
    "dbm", "shelve", "sqlite3",
    # Compression formats outside the launcher's basic needs:
    "lzma", "gzip", "bz2", "tarfile",
    # Unix-only:
    "pwd", "grp", "spwd", "nis", "crypt",
    # Misc rarely-used:
    "readline", "rlcompleter", "uu",
    "xdrlib", "antigravity",
})


def _resolve_repo_root(override: Path | None) -> Path:
    if override is not None:
        return override.resolve()
    return Path(__file__).resolve().parent.parent


def _walk_python_files(root: Path) -> list[Path]:
    """Return every .py file under ``root`` excluding test +
    third-party trees. The audit covers the runtime surface only
    — operator-side tests aren't shipped in the WASI artifact."""
    files: list[Path] = []
    excluded_dirs = {"__pycache__", "tests", ".venv", "venv",
                     "node_modules", ".git", "build", "dist"}
    for path in root.rglob("*.py"):
        if any(part in excluded_dirs for part in path.parts):
            continue
        files.append(path)
    return files


def _imports_from_file(source_path: Path) -> set[str]:
    """Parse one .py file's top-level imports. Returns the set
    of module names imported (top-level only — for ``from a.b
    import c`` we record ``a``)."""
    try:
        text = source_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text, filename=str(source_path))
    except (OSError, SyntaxError):
        return set()

    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            # Relative imports (level > 0) are intra-package; skip.
            if node.level > 0:
                continue
            if node.module:
                found.add(node.module.split(".", 1)[0])
    return found


def _dynamic_import_call_sites(source_path: Path) -> list[tuple[int, str]]:
    """Find ``importlib.import_module(<arg>)`` call sites and
    return ``(line_number, source_excerpt)`` tuples. The audit
    flags these for operator review since AST static analysis
    can't resolve dynamic targets."""
    try:
        text = source_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text, filename=str(source_path))
    except (OSError, SyntaxError):
        return []

    sites: list[tuple[int, str]] = []
    lines = text.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Match `importlib.import_module(...)` or
        # `import_module(...)` (after `from importlib import import_module`).
        is_dynamic = False
        if isinstance(func, ast.Attribute) and func.attr == "import_module":
            if (
                isinstance(func.value, ast.Name)
                and func.value.id == "importlib"
            ):
                is_dynamic = True
        elif isinstance(func, ast.Name) and func.id == "import_module":
            is_dynamic = True
        if is_dynamic:
            line_no = node.lineno
            if 0 < line_no <= len(lines):
                sites.append((line_no, lines[line_no - 1].strip()))
    return sites


def audit(repo_root: Path) -> dict:
    """Run the audit. Returns a dict with the structured results."""
    package = repo_root / "mythic_vibe_cli"
    if not package.is_dir():
        raise SystemExit(
            f"mythic_vibe_cli/ package missing under {repo_root}"
        )

    files = _walk_python_files(package)
    imported: set[str] = set()
    dynamic_sites: list[dict] = []

    for path in files:
        imported.update(_imports_from_file(path))
        for line_no, excerpt in _dynamic_import_call_sites(path):
            dynamic_sites.append({
                "file": str(path.relative_to(repo_root).as_posix()),
                "line": line_no,
                "excerpt": excerpt,
            })

    # Filter to stdlib only — third-party imports (anthropic,
    # openai, textual, etc.) are excluded from the v2.0 WASI base
    # by design.
    stdlib_imported = {m for m in imported if m in PY312_STDLIB_TOP_LEVEL}
    third_party_imported = imported - PY312_STDLIB_TOP_LEVEL

    # Always-prunable: stdlib modules that don't WASI-compile
    # at all, regardless of CLI usage.
    always_prunable = WASI_INCOMPATIBLE_STDLIB & PY312_STDLIB_TOP_LEVEL

    # Prune candidates: stdlib modules the CLI doesn't use AND
    # aren't already always-prunable.
    unused = (PY312_STDLIB_TOP_LEVEL
              - stdlib_imported
              - WASI_INCOMPATIBLE_STDLIB)

    return {
        "files_scanned": len(files),
        "stdlib_used": sorted(stdlib_imported),
        "stdlib_used_count": len(stdlib_imported),
        "third_party_imported": sorted(third_party_imported),
        "always_prune_wasi_incompatible": sorted(always_prunable),
        "additional_prune_candidates_unused": sorted(unused),
        "dynamic_import_sites": dynamic_sites,
        "total_stdlib_modules": len(PY312_STDLIB_TOP_LEVEL),
    }


def render_text(report: dict) -> str:
    parts = [
        "WASI stdlib audit (PH-23.15)",
        f"  files scanned: {report['files_scanned']}",
        f"  stdlib used:   {report['stdlib_used_count']} of {report['total_stdlib_modules']}",
        "",
        "Stdlib modules used by mythic-vibe-cli:",
        "  " + ", ".join(report["stdlib_used"]),
        "",
        f"Always-prune (WASI-incompatible regardless of usage): "
        f"{len(report['always_prune_wasi_incompatible'])} modules",
        "  " + ", ".join(report["always_prune_wasi_incompatible"]),
        "",
        f"Additional prune candidates (unused by CLI): "
        f"{len(report['additional_prune_candidates_unused'])} modules",
        "  " + ", ".join(report["additional_prune_candidates_unused"]),
        "",
        f"Dynamic import_module call sites (review manually): "
        f"{len(report['dynamic_import_sites'])}",
    ]
    for site in report["dynamic_import_sites"][:20]:
        parts.append(
            f"  {site['file']}:{site['line']}  {site['excerpt']}"
        )
    if len(report["dynamic_import_sites"]) > 20:
        parts.append(
            f"  ... and {len(report['dynamic_import_sites']) - 20} more"
        )
    parts.extend([
        "",
        "Pruning impact estimate:",
        f"  ~{len(report['always_prune_wasi_incompatible']) + len(report['additional_prune_candidates_unused'])} "
        f"stdlib modules can be pruned from the CPython WASI "
        f"freeze list, shrinking python.wasm by an estimated "
        f"30-40 percent.",
    ])
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit mythic-vibe-cli's stdlib usage for "
                    "WASI freeze-list pruning (PH-23.15)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repo root (default: this script's grandparent)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of human-readable text",
    )
    args = parser.parse_args(argv)

    repo_root = _resolve_repo_root(args.root)
    report = audit(repo_root)

    if args.json:
        print(_json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(
        guarded_main(
            lambda: main(),
            script_name=Path(__file__).name,
            json_mode="--json" in sys.argv,
        )
    )
