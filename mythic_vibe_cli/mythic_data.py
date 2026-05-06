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
DEFAULT_METHOD_BRANCH = "main"

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
class MethodSource:
    source: str
    readme_raw: str
    tree_api: str
    raw_base: str
    ref: str = DEFAULT_METHOD_BRANCH

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source,
            "readme_raw": self.readme_raw,
            "tree_api": self.tree_api,
            "raw_base": self.raw_base,
            "ref": self.ref,
        }


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
class MethodDiff:
    manifest_path: Path
    missing: list[str]
    changed: list[str]
    untracked: list[str]

    @property
    def clean(self) -> bool:
        return not self.missing and not self.changed and not self.untracked

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_path": str(self.manifest_path),
            "clean": self.clean,
            "missing": self.missing,
            "changed": self.changed,
            "untracked": self.untracked,
        }


@dataclass
class MethodPin:
    pin_path: Path
    source: str
    ref: str
    manifest_sha256: str
    markdown_files: int
    paths: list[str]
    pinned_at: str
    note: str = ""
    schema_version: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "source": self.source,
            "ref": self.ref,
            "manifest_sha256": self.manifest_sha256,
            "markdown_files": self.markdown_files,
            "paths": self.paths,
            "pinned_at": self.pinned_at,
            "note": self.note,
            "pin_path": str(self.pin_path),
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
    configured_source: str = CANONICAL_REPO

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
            "configured_source": self.configured_source,
        }


class MethodStore:
    def __init__(self, app_home: Path | None = None, method_source: str = CANONICAL_REPO):
        self.app_home = app_home or Path(os.environ.get("MYTHIC_HOME", Path.home() / ".mythic-vibe"))
        self.app_home.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.app_home / "method_cache.json"
        self.method_source = resolve_method_source(method_source)

    def sync(self, timeout: int = 10) -> MethodBundle:
        from .runtime.url_guard import assert_safe_url
        assert_safe_url(self.method_source.readme_raw)
        req = urllib.request.Request(self.method_source.readme_raw, headers={"User-Agent": "mythic-vibe-cli/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — scheme validated
            content = resp.read().decode("utf-8", errors="replace")

        bundle = MethodBundle(source=self.method_source.source, content=content)
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
            configured_source=self.method_source.source,
        )

    def import_all_markdown(self, target_dir: Path, timeout: int = 20) -> MethodImportManifest:
        from .runtime.url_guard import assert_safe_url
        target_dir.mkdir(parents=True, exist_ok=True)

        assert_safe_url(self.method_source.tree_api)
        req = urllib.request.Request(self.method_source.tree_api, headers={"User-Agent": "mythic-vibe-cli/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — scheme validated
            tree_payload = json.loads(resp.read().decode("utf-8", errors="replace"))

        items = tree_payload.get("tree", [])
        md_paths = [item["path"] for item in items if item.get("type") == "blob" and item.get("path", "").lower().endswith(".md")]
        ref = str(tree_payload.get("sha") or "main")

        files: list[MethodManifestEntry] = []
        for rel_path in md_paths:
            raw_url = f"{self.method_source.raw_base}{rel_path}"
            assert_safe_url(raw_url)
            out_path = target_dir / rel_path
            out_path.parent.mkdir(parents=True, exist_ok=True)

            file_req = urllib.request.Request(raw_url, headers={"User-Agent": "mythic-vibe-cli/0.1"})
            with urllib.request.urlopen(file_req, timeout=timeout) as file_resp:  # noqa: S310 — scheme validated
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
            source=self.method_source.source,
            ref=ref,
            manifest_path=target_dir / "method_manifest.json",
            files=files,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        manifest.manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
        (target_dir / "_import_index.json").write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
        return manifest

    def diff_import_manifest(self, target_dir: Path) -> MethodDiff:
        manifest_path = target_dir / "method_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(manifest_path)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = manifest.get("files", [])
        expected: dict[str, MethodManifestEntry] = {}
        for entry in entries:
            path = str(entry.get("path", ""))
            if not path:
                continue
            expected[path] = MethodManifestEntry(
                path=path,
                bytes=int(entry.get("bytes", 0)),
                sha256=str(entry.get("sha256", "")),
            )

        missing: list[str] = []
        changed: list[str] = []
        for rel_path, entry in expected.items():
            file_path = target_dir / rel_path
            if not file_path.exists():
                missing.append(rel_path)
                continue
            content = file_path.read_bytes()
            if len(content) != entry.bytes or hashlib.sha256(content).hexdigest() != entry.sha256:
                changed.append(rel_path)

        actual_md = {
            str(path.relative_to(target_dir)).replace("\\", "/")
            for path in target_dir.rglob("*.md")
            if path.is_file()
        }
        untracked = sorted(actual_md.difference(expected))
        return MethodDiff(
            manifest_path=manifest_path,
            missing=sorted(missing),
            changed=sorted(changed),
            untracked=untracked,
        )

    def pin_import_manifest(self, target_dir: Path, note: str = "") -> MethodPin:
        diff = self.diff_import_manifest(target_dir)
        if not diff.clean:
            raise ValueError("Cannot pin method corpus while it differs from method_manifest.json.")

        manifest_bytes = diff.manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        pin = MethodPin(
            pin_path=target_dir / "method_pin.json",
            source=str(manifest.get("source", "")),
            ref=str(manifest.get("ref", "")),
            manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
            markdown_files=int(manifest.get("markdown_files", 0)),
            paths=[str(path) for path in manifest.get("paths", [])],
            pinned_at=datetime.now(timezone.utc).isoformat(),
            note=note,
        )
        pin.pin_path.write_text(json.dumps(pin.to_dict(), indent=2), encoding="utf-8")
        return pin


def resolve_method_source(source: str) -> MethodSource:
    normalized = (source or CANONICAL_REPO).strip().rstrip("/")
    if normalized == CANONICAL_REPO:
        return MethodSource(
            source=CANONICAL_REPO,
            readme_raw=CANONICAL_README_RAW,
            tree_api=CANONICAL_TREE_API,
            raw_base=CANONICAL_RAW_BASE,
        )

    marker = "github.com/"
    if marker not in normalized:
        raise ValueError("method source must be a GitHub repository URL like https://github.com/owner/repo")

    repo = normalized.split(marker, 1)[1].strip("/")
    parts = [part for part in repo.split("/") if part]
    if len(parts) < 2:
        raise ValueError("method source must include GitHub owner and repository")
    owner, name = parts[0], parts[1]
    source_url = f"https://github.com/{owner}/{name}"
    return MethodSource(
        source=source_url,
        readme_raw=f"https://raw.githubusercontent.com/{owner}/{name}/{DEFAULT_METHOD_BRANCH}/README.md",
        tree_api=f"https://api.github.com/repos/{owner}/{name}/git/trees/{DEFAULT_METHOD_BRANCH}?recursive=1",
        raw_base=f"https://raw.githubusercontent.com/{owner}/{name}/{DEFAULT_METHOD_BRANCH}/",
    )
