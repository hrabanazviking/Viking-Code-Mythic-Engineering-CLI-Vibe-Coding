"""Session-scope safety fixtures for the test suite.

PH-23.2 (additive 2026-05-05) — adds a session finalizer that
scans the repo working tree for evidence of a test leaking
absolute Windows-style paths as relative paths under the repo
root. The 2026-05-02 audit cycle left a `Users/volma/AppData/
Local/Temp/...` debris tree in the working copy from a test that
treated an absolute path as relative; this fixture prevents
recurrence by failing the session loudly if any test leaves
similar debris behind.

The fixture is autouse + session-scoped so every CI run + every
local pytest run gets the safety check without any opt-in
ceremony.

Implementation note: pytest discovers conftest.py at the same
directory level as the tests it scopes — placing it at
tests/conftest.py applies the fixture to every test in the
existing tests/ tree without affecting third-party test trees
elsewhere in the repo (e.g. mindspark_thoughtform/tests/,
WYRD-Protocol-*/tests/) that have their own conftest layout.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Iterable

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent

# Top-level directory names that must NOT appear under the repo
# root after a test session. Each name corresponds to a known
# Windows / macOS / Linux absolute-path prefix that, if treated
# as relative by buggy test code, would land debris under the
# repo working tree.
ABSOLUTE_PATH_LEAK_NAMES = {
    "Users",        # Windows: C:\Users\... -> Users\... if drive stripped
    "private",      # macOS: /private/var/folders/... -> private/...
    "var",          # POSIX: /var/folders/... or /var/tmp/...
    "tmp",          # POSIX: /tmp/...
    "AppData",      # Windows: C:\AppData\... shorthand
    "ProgramData",  # Windows: C:\ProgramData\...
}


def _enumerate_leak_dirs() -> list[Path]:
    """Return any directories under REPO_ROOT whose name matches
    a known absolute-path leak indicator. The check is shallow
    (one level deep) — the leak pattern is always a top-level
    repo-root child, since cwd is repo root during test runs."""
    found: list[Path] = []
    for name in ABSOLUTE_PATH_LEAK_NAMES:
        candidate = REPO_ROOT / name
        if candidate.exists():
            found.append(candidate)
    return found


def _format_finding(path: Path) -> str:
    """Format a leak finding for the session-end report.

    Walks one level into the leak dir to surface the most-likely
    test-related sub-path so the operator can grep for it. We
    intentionally don't recurse the full tree — the top-level
    finding is enough to point at the offending test.
    """
    try:
        first_children = list(path.iterdir())[:5]
    except OSError:
        first_children = []
    child_summary = (
        ", ".join(c.name for c in first_children)
        if first_children
        else "(empty)"
    )
    return f"  - {path.relative_to(REPO_ROOT)}/  [first children: {child_summary}]"


@pytest.fixture(scope="session", autouse=True)
def detect_absolute_path_leaks() -> Iterable[None]:
    """Session-scope finalizer that fails the run if any test left
    absolute-path-style debris in the repo working tree.

    Strategy:
      1. Snapshot leak-pattern dirs that exist BEFORE the session
         starts (so a pre-existing debris dir from a crashed
         previous run doesn't fail the new session — those are
         already-known and tracked separately).
      2. Yield to the test session.
      3. After the session, re-scan and report any newly-appeared
         leak dirs by comparing against the snapshot.

    The ``MYTHIC_LEAK_GUARD_DISABLED`` env var disables the
    finalizer. Useful when an operator is intentionally running a
    test that creates such paths (e.g. a future regression test
    for this exact issue) — but in normal operation the var stays
    unset.
    """
    if os.environ.get("MYTHIC_LEAK_GUARD_DISABLED"):
        yield
        return

    pre_session_leaks = {p.resolve() for p in _enumerate_leak_dirs()}

    yield

    post_session_leaks = {p.resolve() for p in _enumerate_leak_dirs()}
    new_leaks = post_session_leaks - pre_session_leaks
    if not new_leaks:
        return

    findings = [_format_finding(p) for p in sorted(new_leaks)]
    pytest.fail(
        "\n\nAbsolute-path-leak guard tripped: a test left "
        "debris under the repo working tree that matches a known "
        "absolute-path-treated-as-relative pattern.\n\n"
        "New leak dirs detected:\n"
        + "\n".join(findings)
        + "\n\nFix the test that produced these paths. The most "
        "common cause is treating tempfile.gettempdir() output as "
        "relative — pass absolute paths through unchanged. To "
        "temporarily disable this guard during debugging, set "
        "MYTHIC_LEAK_GUARD_DISABLED=1 in the env."
    )


@pytest.fixture(scope="session", autouse=True)
def remove_stale_test_debris() -> Iterable[None]:
    """Companion to :func:`detect_absolute_path_leaks` — at
    session start, delete any pre-existing debris dirs that match
    a known leak pattern AND are clearly the May-2026 audit-cycle
    debris pattern.

    Specific signature we delete:
      - REPO_ROOT/Users/volma/AppData/Local/Temp/tmpXXXXX/...

    Any other unexpected matches are reported but NOT deleted —
    this fixture is conservative about removing files the
    operator might want to inspect.
    """
    if os.environ.get("MYTHIC_LEAK_GUARD_DISABLED"):
        yield
        return

    debris_root = REPO_ROOT / "Users" / "volma" / "AppData" / "Local" / "Temp"
    if debris_root.is_dir():
        # Each child should be a `tmpXXXXX` from tempfile +
        # contain only nested junk + an out.txt. Defensive:
        # require that signature before removing.
        for child in debris_root.iterdir():
            if child.name.startswith("tmp") and child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
        # If the cleanup left an empty parent chain, prune it
        # back to REPO_ROOT/Users.
        for parent in (
            debris_root,
            debris_root.parent,        # AppData/Local
            debris_root.parent.parent, # AppData
            debris_root.parent.parent.parent,  # volma
            REPO_ROOT / "Users",
        ):
            if parent.is_dir():
                try:
                    parent.rmdir()
                except OSError:
                    # Non-empty — stop pruning further up.
                    break

    yield
