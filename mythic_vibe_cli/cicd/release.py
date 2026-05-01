"""Release helper (PH-12 Slice 12.3).

Semver-aware release command. Pure helpers here — orchestrated
by the ``cmd_release`` handler in commands.py.

Capabilities:

- Read current version from ``pyproject.toml`` (``[project]
  version`` field).
- Compute the next major / minor / patch bump.
- Write the bumped version back into ``pyproject.toml``.
- Render a CHANGELOG entry stub.
- Create a git tag (via ``git tag`` subprocess; never pushes).

**Defense in depth:** the helper never pushes the tag to a
remote and never invokes ``git push`` of any kind. Operators
own the publish step. Per the global Claude Code "risky
actions" rule, force-push / push-to-shared-branch operations
are kept out of the release helper entirely.

Cross-platform: pure stdlib + ``subprocess`` (the same
``runtime.exec_command`` shell-false contract).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


BumpKind = Literal["major", "minor", "patch"]
SEMVER_RE = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?P<suffix>.*)?$")


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    suffix: str = ""

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}{self.suffix}"

    def bump(self, kind: BumpKind) -> "Version":
        if kind == "major":
            return Version(self.major + 1, 0, 0)
        if kind == "minor":
            return Version(self.major, self.minor + 1, 0)
        if kind == "patch":
            return Version(self.major, self.minor, self.patch + 1)
        raise ValueError(f"unknown bump kind: {kind}")

    @classmethod
    def parse(cls, raw: str) -> "Version":
        cleaned = (raw or "").strip()
        match = SEMVER_RE.match(cleaned)
        if not match:
            raise ValueError(f"not a valid semver: {raw!r}")
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            suffix=match.group("suffix") or "",
        )


def read_pyproject_version(root: Path) -> Version | None:
    """Read the version from ``pyproject.toml``. Returns None on
    missing / unparseable / version-less manifests."""
    path = Path(root) / "pyproject.toml"
    if not path.is_file():
        return None
    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:  # pragma: no cover
            import tomli as tomllib  # type: ignore[no-redef, import-not-found]
        with path.open("rb") as fh:
            payload = tomllib.load(fh)
    except Exception:  # noqa: BLE001
        return None
    project = payload.get("project") if isinstance(payload, dict) else None
    if not isinstance(project, dict):
        return None
    raw = project.get("version")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return Version.parse(raw)
    except ValueError:
        return None


def write_pyproject_version(root: Path, new_version: Version) -> bool:
    """In-place version bump in ``pyproject.toml``. Uses a
    targeted regex over the line-shape ``version = "..."`` inside
    the ``[project]`` table — avoids needing a full TOML
    round-tripper. Returns True on a successful write."""
    path = Path(root) / "pyproject.toml"
    if not path.is_file():
        return False
    try:
        original = path.read_text(encoding="utf-8")
    except OSError:
        return False

    pattern = re.compile(
        r'(?P<lead>\nversion\s*=\s*")[^"\n]+(?P<trail>")', re.MULTILINE
    )
    replaced, count = pattern.subn(
        lambda m: f'{m.group("lead")}{new_version}{m.group("trail")}',
        original,
        count=1,
    )
    if count != 1:
        return False
    try:
        path.write_text(replaced, encoding="utf-8")
    except OSError:
        return False
    return True


def render_changelog_entry(
    *,
    new_version: Version,
    summary: str = "",
    bullets: list[str] | None = None,
) -> str:
    """Render a CHANGELOG entry stub for the new version. Operators
    edit the result before committing; the helper just provides
    the structural skeleton."""
    body_bullets = "\n".join(f"- {item}" for item in (bullets or []))
    body_bullets = body_bullets or "- TODO: list user-visible changes."
    summary_line = (
        summary.strip() if summary.strip() else "TODO: one-sentence summary."
    )
    return (
        f"## v{new_version}\n\n"
        f"_{summary_line}_\n\n"
        f"{body_bullets}\n"
    )


@dataclass
class GitTagResult:
    tag: str
    created: bool
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tag": self.tag,
            "created": self.created,
            "error": self.error,
        }


def create_git_tag(root: Path, tag: str, *, message: str = "") -> GitTagResult:
    """Run ``git tag <tag> [-m <msg>]`` in ``root``. Returns a
    typed :class:`GitTagResult`; never raises into callers. The
    helper does **not** push the tag — operators own the publish
    step (defense in depth)."""
    argv = ["git", "tag", tag]
    if message:
        argv += ["-a", "-m", message]
    try:
        proc = subprocess.run(
            argv,
            cwd=str(root),
            shell=False,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return GitTagResult(tag=tag, created=False, error="git binary not found on PATH")
    except OSError as exc:
        return GitTagResult(tag=tag, created=False, error=f"OSError: {exc}")
    if proc.returncode != 0:
        return GitTagResult(
            tag=tag,
            created=False,
            error=(proc.stderr or proc.stdout or "git tag failed").strip(),
        )
    return GitTagResult(tag=tag, created=True)


@dataclass
class ReleaseResult:
    """Outcome of a :func:`prepare_release` call."""

    bump_kind: BumpKind
    current_version: Version | None
    new_version: Version | None
    pyproject_updated: bool = False
    changelog_entry: str = ""
    tag: GitTagResult | None = None
    dry_run: bool = True
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bump_kind": self.bump_kind,
            "current_version": str(self.current_version) if self.current_version else "",
            "new_version": str(self.new_version) if self.new_version else "",
            "pyproject_updated": self.pyproject_updated,
            "changelog_entry": self.changelog_entry,
            "tag": self.tag.to_dict() if self.tag else None,
            "dry_run": self.dry_run,
            "notes": list(self.notes),
        }


def prepare_release(
    root: Path,
    *,
    bump: BumpKind,
    apply: bool = False,
    create_tag: bool = False,
    summary: str = "",
    bullets: list[str] | None = None,
) -> ReleaseResult:
    """Compute the next version + render the changelog stub.
    When ``apply=True``, also write pyproject.toml. When
    ``create_tag=True`` (in addition to ``apply``), also create
    the git tag locally. **Never pushes.**"""
    current = read_pyproject_version(Path(root))
    if current is None:
        return ReleaseResult(
            bump_kind=bump,
            current_version=None,
            new_version=None,
            dry_run=not apply,
            notes=["pyproject.toml missing or has no [project] version"],
        )

    new_version = current.bump(bump)
    changelog = render_changelog_entry(
        new_version=new_version, summary=summary, bullets=bullets
    )
    notes: list[str] = []
    pyproject_updated = False
    tag_result: GitTagResult | None = None

    if apply:
        pyproject_updated = write_pyproject_version(Path(root), new_version)
        if not pyproject_updated:
            notes.append(
                "pyproject.toml version line could not be updated "
                "(non-standard format?)"
            )
        if create_tag and pyproject_updated:
            tag_name = f"v{new_version}"
            tag_result = create_git_tag(Path(root), tag_name, message=tag_name)
            if not tag_result.created:
                notes.append(
                    f"git tag could not be created: {tag_result.error}"
                )

    return ReleaseResult(
        bump_kind=bump,
        current_version=current,
        new_version=new_version,
        pyproject_updated=pyproject_updated,
        changelog_entry=changelog,
        tag=tag_result,
        dry_run=not apply,
        notes=notes,
    )


__all__ = [
    "BumpKind",
    "GitTagResult",
    "ReleaseResult",
    "Version",
    "create_git_tag",
    "prepare_release",
    "read_pyproject_version",
    "render_changelog_entry",
    "write_pyproject_version",
]
