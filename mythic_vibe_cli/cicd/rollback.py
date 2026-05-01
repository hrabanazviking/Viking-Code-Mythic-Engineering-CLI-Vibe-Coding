"""Rollback helper (PH-12 Slice 12.4).

**Read-only** summariser. Given a baseline ref (e.g. a release
tag), reports the commits + files that landed between the ref
and HEAD so operators know what would be in scope if a release
misbehaves.

The helper **never** reverts anything, never invokes
``git revert`` or ``git reset``. It just runs ``git log`` /
``git diff --name-only`` and renders the result. Operators run
the actual revert manually.

Cross-platform: pure stdlib + ``subprocess``.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CommitSummary:
    sha: str
    short_sha: str
    author: str
    subject: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sha": self.sha,
            "short_sha": self.short_sha,
            "author": self.author,
            "subject": self.subject,
        }


@dataclass
class RollbackReport:
    """Aggregated view of "what would I revert?"."""

    since_ref: str
    head: str
    commits: list[CommitSummary] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    error: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.error

    def to_dict(self) -> dict[str, Any]:
        return {
            "since_ref": self.since_ref,
            "head": self.head,
            "commits": [c.to_dict() for c in self.commits],
            "files": list(self.files),
            "commit_count": len(self.commits),
            "file_count": len(self.files),
            "error": self.error,
            "notes": list(self.notes),
            "ok": self.ok,
        }


def _run_git(args: list[str], *, cwd: Path) -> tuple[bool, str, str]:
    """Wrapper for git subprocess. Returns ``(ok, stdout, stderr)``.
    Never raises; missing git → ``ok=False`` with stderr describing
    the issue."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            shell=False,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "", "git binary not found on PATH"
    except OSError as exc:
        return False, "", f"OSError: {exc}"
    if proc.returncode != 0:
        return False, proc.stdout, (proc.stderr or "git command failed").strip()
    return True, proc.stdout, ""


def _resolve_head(root: Path) -> str:
    ok, stdout, _stderr = _run_git(["rev-parse", "HEAD"], cwd=root)
    return stdout.strip() if ok else ""


def _parse_commit_lines(stdout: str) -> list[CommitSummary]:
    """Parse the output of ``git log --format=...``. The chosen
    format is ``%H|%h|%an|%s`` so we can split safely on
    whichever character isn't likely to appear in a subject. We
    use ``\\x1f`` (Unit Separator) as the delimiter to avoid
    collisions with ``|`` in messages."""
    summaries: list[CommitSummary] = []
    for line in stdout.splitlines():
        line = line.rstrip("\r")
        if not line:
            continue
        parts = line.split("\x1f", 3)
        if len(parts) != 4:
            continue
        sha, short_sha, author, subject = parts
        summaries.append(
            CommitSummary(
                sha=sha.strip(),
                short_sha=short_sha.strip(),
                author=author.strip(),
                subject=subject.strip(),
            )
        )
    return summaries


def summarise_rollback(
    root: Path,
    *,
    since_ref: str,
) -> RollbackReport:
    """Walk ``git log <since_ref>..HEAD`` + ``git diff --name-only
    <since_ref>..HEAD`` and return a :class:`RollbackReport`.

    Errors (missing git, unknown ref) populate ``report.error``;
    the helper never raises into callers.
    """
    cleaned = (since_ref or "").strip()
    if not cleaned:
        return RollbackReport(
            since_ref="",
            head="",
            error="--since requires a non-empty git ref (e.g. v1.2.3)",
        )

    head = _resolve_head(Path(root))
    if not head:
        return RollbackReport(
            since_ref=cleaned,
            head="",
            error="HEAD could not be resolved (not a git repository?)",
        )

    log_ok, log_out, log_err = _run_git(
        [
            "log",
            f"{cleaned}..HEAD",
            "--format=%H\x1f%h\x1f%an\x1f%s",
        ],
        cwd=Path(root),
    )
    if not log_ok:
        return RollbackReport(
            since_ref=cleaned,
            head=head,
            error=log_err or "git log failed",
        )

    diff_ok, diff_out, diff_err = _run_git(
        ["diff", "--name-only", f"{cleaned}..HEAD"],
        cwd=Path(root),
    )
    if not diff_ok:
        # Log already succeeded; surface the diff failure as a
        # note rather than a hard error so commit info still ships.
        report = RollbackReport(
            since_ref=cleaned,
            head=head,
            commits=_parse_commit_lines(log_out),
            notes=[f"git diff failed: {diff_err}"],
        )
        return report

    commits = _parse_commit_lines(log_out)
    files = [line.strip() for line in diff_out.splitlines() if line.strip()]

    notes: list[str] = []
    if not commits:
        notes.append(
            f"No commits between {cleaned} and HEAD — nothing to roll back."
        )

    return RollbackReport(
        since_ref=cleaned,
        head=head,
        commits=commits,
        files=files,
        notes=notes,
    )


__all__ = [
    "CommitSummary",
    "RollbackReport",
    "summarise_rollback",
]
