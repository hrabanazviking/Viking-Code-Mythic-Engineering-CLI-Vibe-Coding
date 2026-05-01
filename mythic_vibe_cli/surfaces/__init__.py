"""Multi-surface access (PH-17).

Four surfaces beyond the local terminal:

- :mod:`web_terminal` — token-protected stdlib HTTP server
  serving an xterm.js front-end and JSON command dispatch.
- :mod:`narrow_layout` — TUI single-column fallback for
  terminals < 80 cols.
- :mod:`ssh_doctor` — SSH-readiness diagnostic.
- :mod:`chat_bridge` — Matrix + Telegram adapters for
  remote command dispatch.

All surfaces are opt-in (default off). Operators invoke them
via ``mythic-vibe surface <name>``.
"""

from __future__ import annotations
