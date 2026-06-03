"""Patch Proposal System.

Phase 8 implements the patch proposal engine. This subsystem handles staging 
proposed edits, generating diffs, and applying or rejecting them with explicit
user consent. No destructive edits happen automatically.
"""

from __future__ import annotations

import json
import difflib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PatchProposal:
    target_file: str
    original_content: str
    proposed_content: str

    def generate_diff(self) -> str:
        """Generates a unified diff for the proposed patch."""
        original_lines = self.original_content.splitlines(keepends=True)
        proposed_lines = self.proposed_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            original_lines,
            proposed_lines,
            fromfile=self.target_file,
            tofile=self.target_file,
            n=3
        )
        return "".join(diff)

    def to_dict(self) -> dict[str, str]:
        return {
            "target_file": self.target_file,
            "original_content": self.original_content,
            "proposed_content": self.proposed_content,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "PatchProposal":
        return cls(
            target_file=data["target_file"],
            original_content=data["original_content"],
            proposed_content=data["proposed_content"],
        )


class PatchManager:
    """Manages the active patch proposal across the session via file persistence."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        if project_root is None:
            self.project_root = Path.cwd()
        else:
            self.project_root = Path(project_root).resolve()
            
        self.state_file = self.project_root / ".mythic" / "active_patch.json"
        self._active_loaded = False
        self._active: PatchProposal | None = None

    def _read_active(self) -> PatchProposal | None:
        if self._active_loaded:
            return self._active
        if not self.state_file.exists():
            self._active_loaded = True
            self._active = None
            return None
        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            self._active = PatchProposal.from_dict(data)
            self._active_loaded = True
            return self._active
        except Exception:
            self._active_loaded = True
            self._active = None
            return None

    def _write_active(self, proposal: PatchProposal | None) -> None:
        self._active = proposal
        self._active_loaded = True
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if proposal is None:
            if self.state_file.exists():
                self.state_file.unlink()
        else:
            self.state_file.write_text(json.dumps(proposal.to_dict(), indent=2), encoding="utf-8")

    def propose(self, target_file: str | Path, proposed_content: str) -> PatchProposal:
        """Stages a patch for review."""
        path = Path(target_file)
        if not path.is_absolute():
            path = self.project_root / path
        path = path.resolve()
        
        try:
            original_content = path.read_text(encoding="utf-8") if path.exists() else ""
        except UnicodeDecodeError:
            original_content = ""  # binary or unreadable file fallback
            
        proposal = PatchProposal(
            target_file=str(path),
            original_content=original_content,
            proposed_content=proposed_content,
        )
        self._write_active(proposal)
        return proposal

    def get_active(self) -> PatchProposal | None:
        """Returns the currently active patch proposal, if any."""
        return self._read_active()

    def apply_active(self) -> bool:
        """Applies the active patch to the file system and clears it."""
        active = self._read_active()
        if not active:
            return False
            
        path = Path(active.target_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(active.proposed_content, encoding="utf-8")
        self._write_active(None)
        return True

    def reject_active(self) -> bool:
        """Rejects the active patch and clears it."""
        if not self._read_active():
            return False
            
        self._write_active(None)
        return True

    def get_diff(self) -> str:
        """Returns the unified diff of the active patch."""
        active = self._read_active()
        if not active:
            return "No active patch proposal."
        return active.generate_diff()

__all__ = ["PatchProposal", "PatchManager"]
