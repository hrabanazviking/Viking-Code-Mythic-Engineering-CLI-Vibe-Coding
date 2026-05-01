# ADR-0009: Internal API Surfaces

## Status

Accepted

## Context

PH-18 Slice 18.3 requires that "each subpackage exposes a typed
module-level API; cross-subpackage calls go through public APIs
only." With the runtime now spanning ~119 source files across
twelve subpackages (`ai/`, `cicd/`, `context/`, `core/`,
`forge*` modules, `memory/`, `persistence/`, `plugins/`,
`policy/`, `robustness/`, `runtime/`, `security/`, `verify/`,
`voice/`), informal cross-imports into private modules accumulate
quickly without a documented rule.

## Decision

1. **Public surface** — every subpackage with a non-trivial
   `__init__.py` (>5 non-blank, non-comment lines) is treated
   as having a documented public API. Cross-subpackage callers
   import from `mythic_vibe_cli.<subpackage>` and rely on what
   that subpackage's `__init__.py` re-exports.

2. **Private modules** — anything inside a subpackage that
   isn't re-exported from `__init__.py` is private. Modules
   in *other* subpackages should not import from those private
   modules.

3. **Within-subpackage imports** — relative imports (`from .x
   import y`) and explicit `from mythic_vibe_cli.<sub>.x import y`
   from a sibling module *inside the same subpackage* are
   always allowed. The boundary applies only to **cross-
   subpackage** access.

4. **Top-level files** (`app.py`, `commands.py`, `errors.py`,
   `exit_codes.py`, etc.) are not subpackages — they are
   permitted to reach into any subpackage's private modules
   when explicit import-time wiring requires it. This
   pragmatic carve-out reflects the fact that `commands.py` is
   the central dispatch layer and would need a parallel re-
   export tax otherwise.

5. **Subpackages with empty / placeholder `__init__.py`** are
   not gated. The threshold (>5 non-blank, non-comment lines)
   is intentional — a fresh subpackage starts with a docstring
   and a `from __future__ import annotations`; once it accumulates
   a real public surface, the audit starts enforcing the
   contract.

6. **Verification** — `mythic_vibe_cli.robustness.api_audit`
   walks the runtime tree via `ast` and surfaces every
   cross-subpackage import that targets a private module.
   Reporting only — the audit never mutates source. Operators
   triage findings incrementally; legitimate cross-imports add
   the symbol to the target subpackage's `__init__.py` and the
   finding goes away.

## Provenance

- Rule shape mirrors how Python stdlib distinguishes public
  attributes (re-exported via `__all__` or imported into the
  package's `__init__.py`) from private internals.
- The audit's "non-trivial init" heuristic is informed by
  the existing repo state — half the subpackages already
  re-export their public API today; the other half do not.
- No third-party tooling is required (mypy strict-mode would
  catch some of these but not all; the AST walker complements
  type checking).

## Consequences

- New cross-subpackage usages must add the symbol to the
  target subpackage's `__init__.py` first.
- The current corpus has existing findings that are tracked
  but not blocked — remediation happens incrementally as each
  import becomes the sharpest edge of a refactor.
- The `__init__.py` in newly-created subpackages stays
  intentional: the moment they cross the >5-line threshold,
  the contract activates.

## Verification

```bash
mythic-vibe simulate api-audit --json
# (slice 18.4 surfaces this; today the audit is callable from
# Python: from mythic_vibe_cli.robustness.api_audit import
# audit_api_surfaces; audit_api_surfaces(Path('.'))
pytest tests/test_robustness_api_audit.py
```
