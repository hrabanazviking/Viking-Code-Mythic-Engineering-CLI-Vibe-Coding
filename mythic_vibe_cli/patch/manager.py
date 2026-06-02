"""Patch Proposal System.

Phase 8 implements the patch proposal engine. This subsystem handles staging 
proposed edits, generating diffs, and applying or rejecting them with explicit
user consent. No destructive edits happen automatically.
"""

from __future__ import annotations

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


class PatchManager:
    """Manages the active patch proposal in the current session."""

    def __init__(self) -> None:
        self._active_patch: PatchProposal | None = None

    def propose(self, target_file: str | Path, proposed_content: str) -> PatchProposal:
        """Stages a patch for review."""
        path = Path(target_file).resolve()
        
        try:
            original_content = path.read_text(encoding="utf-8") if path.exists() else ""
        except UnicodeDecodeError:
            original_content = ""  # binary or unreadable file fallback
            
        proposal = PatchProposal(
            target_file=str(path),
            original_content=original_content,
            proposed_content=proposed_content,
        )
        self._active_patch = proposal
        return proposal

    def get_active(self) -> PatchProposal | None:
        """Returns the currently active patch proposal, if any."""
        return self._active_patch

    def apply_active(self) -> bool:
        """Applies the active patch to the file system and clears it."""
        if not self._active_patch:
            return False
            
        path = Path(self._active_patch.target_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._active_patch.proposed_content, encoding="utf-8")
        self._active_patch = None
        return True

    def reject_active(self) -> bool:
        """Rejects the active patch and clears it."""
        if not self._active_patch:
            return False
            
        self._active_patch = None
        return True

    def get_diff(self) -> str:
        """Returns the unified diff of the active patch."""
        if not self._active_patch:
            return "No active patch proposal."
        return self._active_patch.generate_diff()

__all__ = ["PatchProposal", "PatchManager"]
