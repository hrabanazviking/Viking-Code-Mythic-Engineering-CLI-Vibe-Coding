"""Textual TUI for Mythic Vibe CLI.

Optional dependency on ``textual``. Import the public surface lazily so the
rest of the CLI does not pay the import cost or fail when textual is not
installed.
"""

from .app import build_status_data

__all__ = ["build_status_data"]
