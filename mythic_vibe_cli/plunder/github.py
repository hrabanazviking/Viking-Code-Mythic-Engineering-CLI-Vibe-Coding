from __future__ import annotations

import base64
from dataclasses import dataclass
import json
from pathlib import Path
import urllib.parse
import urllib.request


@dataclass(frozen=True)
class GitHubRepoInfo:
    repo: str
    ref: str
    sha: str
    license_spdx_id: str
    license_name: str
    html_url: str

    def to_dict(self) -> dict[str, str]:
        return {
            "repo": self.repo,
            "ref": self.ref,
            "sha": self.sha,
            "license_spdx_id": self.license_spdx_id,
            "license_name": self.license_name,
            "html_url": self.html_url,
        }


@dataclass(frozen=True)
class GitHubFile:
    repo: str
    path: str
    ref: str
    sha: str
    text: str
    html_url: str

    def to_dict(self) -> dict[str, str]:
        return {
            "repo": self.repo,
            "path": self.path,
            "ref": self.ref,
            "sha": self.sha,
            "html_url": self.html_url,
        }


class GitHubClient:
    def __init__(self, token: str = ""):
        self.token = token.strip()

    def get_json(self, url: str) -> dict[str, object]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "mythic-vibe-cli",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Unexpected GitHub API response for {url}")
        return payload

    def inspect_repo(self, repo: str, ref: str) -> GitHubRepoInfo:
        repo_payload = self.get_json(f"https://api.github.com/repos/{repo}")
        ref_payload = self.get_json(f"https://api.github.com/repos/{repo}/commits/{urllib.parse.quote(ref)}")
        license_payload = repo_payload.get("license") if isinstance(repo_payload.get("license"), dict) else {}
        return GitHubRepoInfo(
            repo=repo,
            ref=ref,
            sha=str(ref_payload.get("sha") or ref),
            license_spdx_id=str(license_payload.get("spdx_id") or "Unknown"),
            license_name=str(license_payload.get("name") or "Unknown"),
            html_url=str(repo_payload.get("html_url") or f"https://github.com/{repo}"),
        )

    def get_file(self, repo: str, source_path: str, ref: str) -> GitHubFile:
        encoded_path = urllib.parse.quote(source_path.strip("/"))
        url = f"https://api.github.com/repos/{repo}/contents/{encoded_path}?ref={urllib.parse.quote(ref)}"
        payload = self.get_json(url)
        if payload.get("type") != "file":
            raise ValueError(f"Source is not a file: {source_path}")
        if payload.get("encoding") != "base64":
            raise ValueError(f"Unsupported GitHub encoding for {source_path}: {payload.get('encoding')}")
        raw = str(payload.get("content") or "")
        text = base64.b64decode(raw).decode("utf-8")
        return GitHubFile(
            repo=repo,
            path=source_path,
            ref=ref,
            sha=str(payload.get("sha") or ""),
            text=text,
            html_url=str(payload.get("html_url") or f"https://github.com/{repo}/blob/{ref}/{source_path}"),
        )

    def fetch_to_cache(self, root: Path, repo: str, source_path: str, ref: str) -> tuple[GitHubFile, Path]:
        github_file = self.get_file(repo, source_path, ref)
        cache_path = root / "mythic" / "imports" / "cache" / repo.replace("/", "__") / ref / source_path
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(github_file.text, encoding="utf-8")
        return github_file, cache_path
