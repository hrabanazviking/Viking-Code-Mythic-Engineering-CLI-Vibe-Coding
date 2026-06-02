"""GitHub workspace management for the companion shell.

Reforge Phase 7 keeps local workspace operations separate from the
project scanner and plunder/GitHub API code. The manager is designed
around explicit proposals first; mutating Git operations require an
operator confirmation flag in the CLI layer.
"""

from __future__ import annotations

__all__: list[str] = []
