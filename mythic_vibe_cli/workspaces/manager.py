"""Local Git/GitHub workspace manager.

Phase 7 makes Mythic aware of local working directories without
performing destructive actions. Clone and branch creation are explicit
operations, and the CLI keeps them gated behind ``--yes``. Natural
shell prompts use the proposal helpers only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

from ..runtime.exec import DEFAULT_EXEC_TIMEOUT_SECONDS, ExecResult, exec_command


DEFAULT_WORKSPACE_DIR = (".mythic-vibe", "workspaces")
REGISTRY_FILENAME = "workspaces.json"
PR_DRAFT_DIR = "pr_drafts"
SAFE_BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_workspace_root() -> Path:
    env = os.environ.get("MYTHIC_WORKSPACE_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    home = Path(os.environ.get("HOME") or Path.home())
    return home.joinpath(*DEFAULT_WORKSPACE_DIR).resolve()


def resolve_workspace_root(value: str | Path | None = None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return default_workspace_root()


@dataclass(frozen=True)
class WorkspaceRecord:
    name: str
    path: str
    remote: str = ""
    branch: str = ""
    tracked_branches: tuple[str, ...] = ()
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "remote": self.remote,
            "branch": self.branch,
            "tracked_branches": list(self.tracked_branches),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorkspaceRecord":
        return cls(
            name=str(payload.get("name", "")),
            path=str(payload.get("path", "")),
            remote=str(payload.get("remote", "")),
            branch=str(payload.get("branch", "")),
            tracked_branches=tuple(str(item) for item in payload.get("tracked_branches", []) if str(item)),
            updated_at=str(payload.get("updated_at", "")),
        )


@dataclass(frozen=True)
class WorkspaceAction:
    action: str
    workspace_root: str
    repo_url: str = ""
    target_path: str = ""
    branch: str = ""
    base_branch: str = ""
    executed: bool = False
    command: tuple[str, ...] = ()
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    message: str = ""
    record: WorkspaceRecord | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "workspace_root": self.workspace_root,
            "repo_url": self.repo_url,
            "target_path": self.target_path,
            "branch": self.branch,
            "base_branch": self.base_branch,
            "executed": self.executed,
            "command": list(self.command),
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "message": self.message,
            "record": self.record.to_dict() if self.record else None,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class WorkspaceStatus:
    workspace_root: str
    current_repo: str = ""
    current_branch: str = ""
    dirty: bool = False
    remote: str = ""
    tracked: tuple[WorkspaceRecord, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_root": self.workspace_root,
            "current_repo": self.current_repo,
            "current_branch": self.current_branch,
            "dirty": self.dirty,
            "remote": self.remote,
            "tracked": [record.to_dict() for record in self.tracked],
        }


def registry_path(workspace_root: Path) -> Path:
    return workspace_root / REGISTRY_FILENAME


def load_registry(workspace_root: Path) -> list[WorkspaceRecord]:
    path = registry_path(workspace_root)
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw_items = payload.get("workspaces", []) if isinstance(payload, dict) else []
    records: list[WorkspaceRecord] = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if isinstance(item, dict):
                record = WorkspaceRecord.from_dict(item)
                if record.name and record.path:
                    records.append(record)
    return records


def save_registry(workspace_root: Path, records: list[WorkspaceRecord]) -> Path:
    workspace_root.mkdir(parents=True, exist_ok=True)
    path = registry_path(workspace_root)
    payload = {"updated_at": _utc_now_iso(), "workspaces": [record.to_dict() for record in records]}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def upsert_record(workspace_root: Path, record: WorkspaceRecord) -> WorkspaceRecord:
    records = [item for item in load_registry(workspace_root) if item.name != record.name]
    records.append(record)
    records.sort(key=lambda item: item.name)
    save_registry(workspace_root, records)
    return record


def repo_name_from_url(repo_url: str) -> str:
    text = repo_url.strip().rstrip("/")
    if not text:
        return "workspace"
    if text.startswith("git@"):
        text = text.rsplit(":", 1)[-1]
    else:
        parsed = urlparse(text)
        text = parsed.path if parsed.path else text
    name = Path(text).name
    if name.endswith(".git"):
        name = name[:-4]
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-._")
    return cleaned or "workspace"


def ensure_safe_branch_name(branch: str) -> str:
    cleaned = branch.strip()
    if not cleaned:
        raise ValueError("branch name is required")
    if cleaned.startswith("-") or ".." in cleaned or cleaned.endswith("/") or not SAFE_BRANCH_RE.match(cleaned):
        raise ValueError(f"unsafe branch name: {branch!r}")
    return cleaned


def git_output(cwd: Path, *args: str) -> ExecResult:
    return exec_command(
        "git",
        list(args),
        cwd=cwd,
        timeout=DEFAULT_EXEC_TIMEOUT_SECONDS,
    )


def detect_repo(path: Path) -> tuple[str, str, str, bool]:
    root_result = git_output(path, "rev-parse", "--show-toplevel")
    repo = root_result.stdout.strip() if root_result.code == 0 else ""
    branch_result = git_output(path, "branch", "--show-current")
    branch = branch_result.stdout.strip() if branch_result.code == 0 else ""
    remote_result = git_output(path, "remote", "get-url", "origin")
    remote = remote_result.stdout.strip() if remote_result.code == 0 else ""
    status_result = git_output(path, "status", "--porcelain")
    dirty = bool(status_result.stdout.strip()) if status_result.code == 0 else False
    return repo, branch, remote, dirty


def workspace_status(path: Path, workspace_root: Path) -> WorkspaceStatus:
    repo, branch, remote, dirty = detect_repo(path)
    return WorkspaceStatus(
        workspace_root=str(workspace_root),
        current_repo=repo,
        current_branch=branch,
        dirty=dirty,
        remote=remote,
        tracked=tuple(load_registry(workspace_root)),
    )


def clone_repo(
    repo_url: str,
    *,
    workspace_root: Path,
    name: str = "",
    execute: bool = False,
) -> WorkspaceAction:
    workspace_root.mkdir(parents=True, exist_ok=True)
    repo_name = name.strip() or repo_name_from_url(repo_url)
    target = (workspace_root / repo_name).resolve()
    command = ("git", "clone", repo_url, str(target))
    if not execute:
        return WorkspaceAction(
            action="clone",
            workspace_root=str(workspace_root),
            repo_url=repo_url,
            target_path=str(target),
            command=command,
            message="Dry run: pass --yes to clone this repository.",
        )
    result = exec_command("git", ["clone", repo_url, str(target)], cwd=workspace_root, timeout=DEFAULT_EXEC_TIMEOUT_SECONDS)
    record = None
    if result.code == 0:
        repo, branch, remote, _dirty = detect_repo(target)
        record = upsert_record(
            workspace_root,
            WorkspaceRecord(
                name=repo_name,
                path=repo or str(target),
                remote=remote or repo_url,
                branch=branch,
                updated_at=_utc_now_iso(),
            ),
        )
    return WorkspaceAction(
        action="clone",
        workspace_root=str(workspace_root),
        repo_url=repo_url,
        target_path=str(target),
        executed=True,
        command=command,
        exit_code=result.code,
        stdout=result.stdout,
        stderr=result.stderr,
        message="Clone completed." if result.code == 0 else "Clone failed.",
        record=record,
    )


def open_workspace(path: Path, *, workspace_root: Path, name: str = "") -> WorkspaceAction:
    repo, branch, remote, dirty = detect_repo(path)
    if not repo:
        return WorkspaceAction(
            action="open",
            workspace_root=str(workspace_root),
            target_path=str(path.resolve()),
            exit_code=1,
            message="No Git repository detected at this path.",
        )
    repo_name = name.strip() or Path(repo).name
    record = upsert_record(
        workspace_root,
        WorkspaceRecord(
            name=repo_name,
            path=repo,
            remote=remote,
            branch=branch,
            tracked_branches=(branch,) if branch else (),
            updated_at=_utc_now_iso(),
        ),
    )
    return WorkspaceAction(
        action="open",
        workspace_root=str(workspace_root),
        target_path=repo,
        branch=branch,
        executed=True,
        message="Workspace recorded.",
        record=record,
        metadata={"dirty": dirty},
    )


def create_branch(path: Path, branch: str, *, workspace_root: Path, execute: bool = False) -> WorkspaceAction:
    safe_branch = ensure_safe_branch_name(branch)
    repo, current_branch, remote, dirty = detect_repo(path)
    if not repo:
        return WorkspaceAction(
            action="branch",
            workspace_root=str(workspace_root),
            target_path=str(path.resolve()),
            branch=safe_branch,
            exit_code=1,
            message="No Git repository detected at this path.",
        )
    command = ("git", "switch", "-c", safe_branch)
    if not execute:
        return WorkspaceAction(
            action="branch",
            workspace_root=str(workspace_root),
            target_path=repo,
            branch=safe_branch,
            command=command,
            message="Dry run: pass --yes to create and switch to this branch.",
            metadata={"current_branch": current_branch, "dirty": dirty},
        )
    result = git_output(Path(repo), "switch", "-c", safe_branch)
    tracked = tuple(dict.fromkeys([current_branch, safe_branch] if current_branch else [safe_branch]))
    record = None
    if result.code == 0:
        record = upsert_record(
            workspace_root,
            WorkspaceRecord(
                name=Path(repo).name,
                path=repo,
                remote=remote,
                branch=safe_branch,
                tracked_branches=tracked,
                updated_at=_utc_now_iso(),
            ),
        )
    return WorkspaceAction(
        action="branch",
        workspace_root=str(workspace_root),
        target_path=repo,
        branch=safe_branch,
        executed=True,
        command=command,
        exit_code=result.code,
        stdout=result.stdout,
        stderr=result.stderr,
        message="Branch created." if result.code == 0 else "Branch creation failed.",
        record=record,
        metadata={"dirty": dirty},
    )


def track_branch(path: Path, *, workspace_root: Path, branch: str = "") -> WorkspaceAction:
    repo, current_branch, remote, dirty = detect_repo(path)
    if not repo:
        return WorkspaceAction(
            action="track",
            workspace_root=str(workspace_root),
            target_path=str(path.resolve()),
            exit_code=1,
            message="No Git repository detected at this path.",
        )
    target_branch = ensure_safe_branch_name(branch or current_branch)
    existing = next((record for record in load_registry(workspace_root) if Path(record.path).resolve() == Path(repo).resolve()), None)
    tracked = tuple(dict.fromkeys([*(existing.tracked_branches if existing else ()), target_branch]))
    record = upsert_record(
        workspace_root,
        WorkspaceRecord(
            name=existing.name if existing else Path(repo).name,
            path=repo,
            remote=remote,
            branch=target_branch,
            tracked_branches=tracked,
            updated_at=_utc_now_iso(),
        ),
    )
    return WorkspaceAction(
        action="track",
        workspace_root=str(workspace_root),
        target_path=repo,
        branch=target_branch,
        executed=True,
        message="Branch tracked.",
        record=record,
        metadata={"dirty": dirty},
    )


def prepare_pr_draft(
    path: Path,
    *,
    workspace_root: Path,
    title: str,
    body: str = "",
    base_branch: str = "main",
    write: bool = False,
) -> WorkspaceAction:
    repo, branch, remote, dirty = detect_repo(path)
    if not repo:
        return WorkspaceAction(
            action="pr",
            workspace_root=str(workspace_root),
            target_path=str(path.resolve()),
            exit_code=1,
            message="No Git repository detected at this path.",
        )
    base = ensure_safe_branch_name(base_branch)
    pr_body = body.strip() or "Describe the change, verification, and risk before opening this PR."
    draft = (
        "# Pull Request Draft\n\n"
        f"- Title: {title.strip() or f'Update {Path(repo).name}'}\n"
        f"- Base: {base}\n"
        f"- Head: {branch or '(current branch unknown)'}\n"
        f"- Remote: {remote or '(none)'}\n"
        f"- Dirty working tree: {str(dirty).lower()}\n\n"
        "## Body\n\n"
        f"{pr_body}\n"
    )
    metadata: dict[str, Any] = {"draft": draft}
    target_path = ""
    if write:
        drafts = workspace_root / PR_DRAFT_DIR
        drafts.mkdir(parents=True, exist_ok=True)
        filename = f"{Path(repo).name}-{branch or 'branch'}-pr.md".replace("/", "-")
        target = drafts / filename
        target.write_text(draft, encoding="utf-8")
        target_path = str(target)
    return WorkspaceAction(
        action="pr",
        workspace_root=str(workspace_root),
        target_path=target_path or repo,
        branch=branch,
        base_branch=base,
        executed=write,
        message="PR draft written." if write else "PR draft prepared; pass --write to save it.",
        metadata=metadata,
    )


def propose_workspace_plan(prompt: str, *, workspace_root: Path) -> str:
    text = prompt.strip()
    repo_url = _extract_repo_url(text)
    branch = _extract_branch_name(text)
    lines = ["Workspace proposal"]
    if repo_url:
        target = workspace_root / repo_name_from_url(repo_url)
        lines.append(f"  1. Clone {repo_url} into {target}")
    else:
        lines.append("  1. Identify or open the target repository workspace.")
    if branch:
        lines.append(f"  2. Create and track branch {branch}")
    else:
        lines.append("  2. Choose a branch name for the work.")
    lines.append("  3. Prepare a PR draft after changes and verification.")
    lines.append("")
    lines.append("No changes were made. Use `workspace clone ... --yes` and `workspace branch ... --yes` to execute.")
    return "\n".join(lines)


def _extract_repo_url(text: str) -> str:
    tokens = text.replace(",", " ").split()
    for token in tokens:
        cleaned = token.strip("'\"")
        if cleaned.startswith(("https://", "http://", "git@")) and ("github.com" in cleaned or cleaned.endswith(".git")):
            return cleaned
    for token in tokens:
        cleaned = token.strip("'\"")
        if "/" in cleaned and not cleaned.startswith("/") and "." not in cleaned.split("/", 1)[0]:
            return f"https://github.com/{cleaned.rstrip('.')}"
    return ""


def _extract_branch_name(text: str) -> str:
    lowered = text.lower()
    markers = ("branch for ", "branch named ", "branch ")
    for marker in markers:
        idx = lowered.find(marker)
        if idx >= 0:
            raw = text[idx + len(marker):].strip().split()
            if raw:
                candidate = "-".join(part.strip(" .,!?:;\"'").lower() for part in raw[:4] if part.strip(" .,!?:;\"'"))
                candidate = re.sub(r"[^a-z0-9._/-]+", "-", candidate).strip("-")
                if candidate:
                    return f"mythic/{candidate}" if "/" not in candidate else candidate
    return ""


__all__ = [
    "WorkspaceAction",
    "WorkspaceRecord",
    "WorkspaceStatus",
    "clone_repo",
    "create_branch",
    "default_workspace_root",
    "detect_repo",
    "load_registry",
    "open_workspace",
    "prepare_pr_draft",
    "propose_workspace_plan",
    "registry_path",
    "resolve_workspace_root",
    "save_registry",
    "track_branch",
    "workspace_status",
]
