"""Robustness sweeps & failure simulation (PH-18).

Four diagnostic capabilities:

- :mod:`boundary_audit` — finds direct subprocess calls that
  bypass :mod:`mythic_vibe_cli.runtime.exec`, bare-except
  clauses, and other Round-1 boundary smells.
- :mod:`path_audit` — finds hardcoded ``mythic/`` path strings
  outside the canonical resolver and direct file writes that
  bypass :mod:`mythic_vibe_cli.runtime.file_mutation_queue`.
- :mod:`api_audit` — finds cross-subpackage imports that reach
  into private modules instead of the subpackage's public
  ``__init__.py`` surface.
- :mod:`simulate` — injects canonical synthetic failures and
  confirms the CLI degrades gracefully.

All four audits are **read-only** — they surface findings,
never mutate source code. Remediation happens incrementally as
the team triages each finding through the
``mythic-vibe simulate`` + audit reports.
"""

from __future__ import annotations
