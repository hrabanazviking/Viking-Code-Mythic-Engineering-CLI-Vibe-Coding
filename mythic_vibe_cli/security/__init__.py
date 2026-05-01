"""Security, sandbox & permissions layer (PH-11).

This package collects the seven slice-11 capabilities:

- :mod:`approval` — operator approval modes (suggest /
  auto-approve / partial).
- :mod:`redaction` — payload redaction + forbidden-path policy.
- :mod:`secret_scanner` — pre-packet scan for hardcoded
  credentials.
- :mod:`exec_policy` — config gating for sandboxed subprocess
  execution.
- :mod:`dangerous_patterns` — eval / exec / shell injection /
  unparameterised-SQL detection.
- :mod:`privacy` — privacy-mode payload filtering.

All capabilities are **opt-in by default** — projects that
don't enable security.toml see no behavioural change.
"""

from __future__ import annotations
