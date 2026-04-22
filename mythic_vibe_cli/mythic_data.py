from __future__ import annotations

import json
import os
from pathlib import Path
import textwrap
import urllib.error
import urllib.request

from dataclasses import dataclass

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

    3) Plan
       - Break into smallest valuable milestones.
       - State assumptions before coding.

    4) Build
       - Implement one milestone at a time.
       - Keep the code understandable for future maintainers.

    5) Verify
       - Run checks/tests after each milestone.
       - Confirm result matches intent, not just that code runs.

    6) Reflect
       - Document what changed and why.
       - Capture follow-up improvements and risks.
    """
).strip()


@dataclass
class MethodBundle:
    source: str
    content: str


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

    def import_all_markdown(self, target_dir: Path, timeout: int = 20) -> list[Path]:
        target_dir.mkdir(parents=True, exist_ok=True)

        req = urllib.request.Request(CANONICAL_TREE_API, headers={"User-Agent": "mythic-vibe-cli/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            tree_payload = json.loads(resp.read().decode("utf-8", errors="replace"))

        items = tree_payload.get("tree", [])
        md_paths = [item["path"] for item in items if item.get("type") == "blob" and item.get("path", "").lower().endswith(".md")]

        written: list[Path] = []
        for rel_path in md_paths:
            raw_url = f"{CANONICAL_RAW_BASE}{rel_path}"
            out_path = target_dir / rel_path
            out_path.parent.mkdir(parents=True, exist_ok=True)

            file_req = urllib.request.Request(raw_url, headers={"User-Agent": "mythic-vibe-cli/0.1"})
            with urllib.request.urlopen(file_req, timeout=timeout) as file_resp:
                content = file_resp.read().decode("utf-8", errors="replace")

            out_path.write_text(content, encoding="utf-8")
            written.append(out_path)

        index = target_dir / "_import_index.json"
        index.write_text(
            json.dumps(
                {
                    "source": CANONICAL_REPO,
                    "markdown_files": len(written),
                    "paths": [str(p.relative_to(target_dir)) for p in written],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return written
