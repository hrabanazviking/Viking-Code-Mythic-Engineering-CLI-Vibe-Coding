from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import textwrap
import urllib.error
import urllib.request

CANONICAL_REPO = "https://github.com/hrabanazviking/Mythic-Engineering"
CANONICAL_README_RAW = (
    "https://raw.githubusercontent.com/hrabanazviking/Mythic-Engineering/main/README.md"
)
CANONICAL_TREE_API = "https://api.github.com/repos/hrabanazviking/Mythic-Engineering/git/trees/main?recursive=1"
CANONICAL_RAW_BASE = "https://raw.githubusercontent.com/hrabanazviking/Mythic-Engineering/main/"

DEFAULT_METHOD_NOTES = textwrap.dedent(
    """
    Mythic Engineering Vibe Loop (fallback profile)

    1) Intent
       - Define what to build in one clear sentence.
       - Define the user outcome first.

    2) Constraints
       - List known constraints (time, stack, risk, quality bar).
       - Prefer simpler architecture when uncertain.

    3) Architecture
       - Name the owning modules, data flow, and interfaces.
       - Keep dependencies pointed toward stable boundaries.

    4) Plan
       - Break into smallest valuable milestones.
       - State assumptions before coding.

    5) Build
       - Implement one milestone at a time.
       - Keep the code understandable for future maintainers.

    6) Verify
       - Run checks/tests after each milestone.
       - Confirm result matches intent, not just that code runs.

    7) Reflect
       - Document what changed and why.
       - Capture follow-up improvements and risks.
    """
).strip()


@dataclass
class MethodBundle:
    source: str
    content: str


@dataclass
class MethodManifestEntry:
    path: str
    bytes: int
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "bytes": self.bytes,
            "sha256": self.sha256,
        }


@dataclass
class MethodImportManifest:
    source: str
    ref: str
    manifest_path: Path
    files: list[MethodManifestEntry]
    generated_at: str
    schema_version: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source": self.source,
            "ref": self.ref,
            "generated_at": self.generated_at,
            "markdown_files": len(self.files),
            "files": [entry.to_dict() for entry in self.files],
            "paths": [entry.path for entry in self.files],
        }


@dataclass
class MethodStatus:
    source: str
    profile: str
    version: str
    cache_file: Path
    cached: bool
    sections: list[str]
    freshness: str
    pinned: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "profile": self.profile,
            "version": self.version,
            "cache_file": str(self.cache_file),
            "cached": self.cached,
            "sections": self.sections,
            "freshness": self.freshness,
            "pinned": self.pinned,
        }


class MethodStore:
    def __init__(self, app_home: Path | None = None):
        self.app_home = app_home or Path(os.environ.get("MYTHIC_HOME", Path.home() / ".mythic-vibe"))
        self.app_home.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.app_home / "method_cache.json"

    def sync(self, timeout: int = 10) -> MethodBundle:
        req = urllib.request.Request(CANONICAL_README_RAW, headers={"User-Agent": "mythic-vibe-cli/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8", errors="replace")

        bundle = MethodBundle(source=CANONICAL_REPO, content=content)
        self.cache_file.write_text(json.dumps(bundle.__dict__, indent=2), encoding="utf-8")
        return bundle

    def load(self) -> MethodBundle:
        if self.cache_file.exists():
            data = json.loads(self.cache_file.read_text(encoding="utf-8"))
            return MethodBundle(source=data["source"], content=data["content"])

        try:
            return self.sync()
        except (urllib.error.URLError, TimeoutError):
            return MethodBundle(source="fallback", content=DEFAULT_METHOD_NOTES)

    def load_cached_or_fallback(self) -> tuple[MethodBundle, bool]:
        if self.cache_file.exists():
            data = json.loads(self.cache_file.read_text(encoding="utf-8"))
            return MethodBundle(source=data["source"], content=data["content"]), True
        return MethodBundle(source="fallback", content=DEFAULT_METHOD_NOTES), False

    def status(self) -> MethodStatus:
        bundle, cached = self.load_cached_or_fallback()
        version = hashlib.sha256(bundle.content.encode("utf-8")).hexdigest()[:12]
        profile = "canonical-cache" if cached else "fallback"
        freshness = "cached" if cached else "fallback-no-cache"
        sections = [
            "principles",
            "workflow",
            "AI roles",
            "required docs",
            "refactor method",
            "debugging method",
            "verification method",
            "failure modes",
        ]
        return MethodStatus(
            source=bundle.source,
            profile=profile,
            version=version,
            cache_file=self.cache_file,
            cached=cached,
            sections=sections,
            freshness=freshness,
        )

    def import_all_markdown(self, target_dir: Path, timeout: int = 20) -> MethodImportManifest:
        target_dir.mkdir(parents=True, exist_ok=True)

        req = urllib.request.Request(CANONICAL_TREE_API, headers={"User-Agent": "mythic-vibe-cli/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            tree_payload = json.loads(resp.read().decode("utf-8", errors="replace"))

        items = tree_payload.get("tree", [])
        md_paths = [item["path"] for item in items if item.get("type") == "blob" and item.get("path", "").lower().endswith(".md")]
        ref = str(tree_payload.get("sha") or "main")

        files: list[MethodManifestEntry] = []
        for rel_path in md_paths:
            raw_url = f"{CANONICAL_RAW_BASE}{rel_path}"
            out_path = target_dir / rel_path
            out_path.parent.mkdir(parents=True, exist_ok=True)

            file_req = urllib.request.Request(raw_url, headers={"User-Agent": "mythic-vibe-cli/0.1"})
            with urllib.request.urlopen(file_req, timeout=timeout) as file_resp:
                content = file_resp.read().decode("utf-8", errors="replace")

            out_path.write_text(content, encoding="utf-8")
            encoded = content.encode("utf-8")
            files.append(
                MethodManifestEntry(
                    path=rel_path,
                    bytes=len(encoded),
                    sha256=hashlib.sha256(encoded).hexdigest(),
                )
            )

        manifest = MethodImportManifest(
            source=CANONICAL_REPO,
            ref=ref,
            manifest_path=target_dir / "method_manifest.json",
            files=files,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        manifest.manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
        (target_dir / "_import_index.json").write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
        return manifest
