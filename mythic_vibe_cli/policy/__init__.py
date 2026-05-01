"""Policy Engine & Constraint Verification (PH-14).

Loads operator-declared constraints from oaths, ADRs, and an
explicit constraints file, gates writing commands behind those
constraints, and logs overrides for audit.

Four modules:

- :mod:`constraint_store` — read constraints from disk into a
  typed model.
- :mod:`policy_gate` — evaluate a constraint set against a
  proposed command, return a typed PolicyDecision.
- :mod:`override_log` — append-only audit trail for
  ``--override``-flagged commands.

The CLI surface lives in :mod:`mythic_vibe_cli.commands` —
``cmd_policy_report`` (slice 14.4) + the ``cmd_oath`` wiring
(slice 14.2 demo).

All capabilities are **opt-in**: projects without a
``mythic/constraints.md``, ``mythic/oaths.md``, or any ADR see
zero behavioural change from before PH-14.
"""

from __future__ import annotations
