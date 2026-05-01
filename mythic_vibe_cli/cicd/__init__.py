"""CI/CD & deployment integration (PH-12).

Four capabilities, all scaffold-style code generators:

- :mod:`stack_detector` — pure detector that inspects manifest
  files (pyproject.toml, package.json, Cargo.toml, go.mod, etc)
  and returns a typed :class:`DetectedStack`.
- :mod:`ci_scaffold` — generates a ``.github/workflows/ci.yml``
  tuned to the detected stack.
- :mod:`docker_scaffold` — generates a ``Dockerfile``,
  ``.dockerignore``, and ``docker-compose.yml``.
- :mod:`release` — semver-aware release helper (version bump +
  tag + changelog stub).
- :mod:`rollback` — read-only summariser for "what would I need
  to revert?" between a baseline ref and HEAD.

All commands honour ``--force`` (overwrite) and ``--dry-run``
(preview only).
"""

from __future__ import annotations
