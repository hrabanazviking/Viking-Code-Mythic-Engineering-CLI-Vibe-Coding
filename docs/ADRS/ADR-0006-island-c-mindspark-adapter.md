# ADR-0006: Island C (MindSpark ThoughtForge) Adapter

## Status

Accepted

## Context

MindSpark ThoughtForge is Volmarr's separate "universal cognitive
enhancement layer" project — sovereign offline RAG + TurboQuant
inference + deterministic cognition scaffolds + fragment salvage,
shipped as the open-source Python package `thoughtforge`. It is
not vendored into this repository; it is installed at runtime via
the optional `mythic-vibe[mindspark]` extra (or directly via
`pip install thoughtforge`).

PH-09 of the master roadmap calls for bringing MindSpark online
as Island C through an ADR-governed adapter with a feature flag.

## Decision

Add a thin adapter at
`mythic_vibe_cli/ai/providers/mindspark.py` that:

1. **Try-imports the canonical Python package name `thoughtforge`.**
   No reference to any in-tree vendored snapshot. The adapter
   resolves whatever module the operator's `sys.path` / pip env
   makes available.

2. **Gates real activation behind two conditions** — both must be
   true:
   - The package import succeeds.
   - The operator sets `MYTHIC_ISLAND_MINDSPARK_ENABLED=1`.
   When either is false, the adapter reports `configured=False`
   and `run()` returns a stub-shaped placeholder rather than
   raising.

3. **Exposes the provider as `"mindspark"`** in the
   :class:`ProviderRegistry`. Operators can route to it via
   `mythic-vibe ai run --provider mindspark ...` once the gate is
   on. The slice 8.3 routing fallback chain handles the
   not-configured case (skip + fall forward).

4. **Routes through a duck-typed contract** — the adapter tries
   `thoughtforge.plan(prompt)` / `cognition.plan` /
   `cognition.scaffold.plan` / `cognition.router.route` /
   `ask(prompt)` in order. The first callable wins. Unknown
   shape → `AttributeError`, contained in `metadata["error"]`.

5. **Adds the optional dep** to `pyproject.toml`:

   ```toml
   [project.optional-dependencies]
   mindspark = ["thoughtforge>=0.1"]
   ```

   Operators install with `pip install mythic-vibe[mindspark]`.

## Provenance

- MindSpark ThoughtForge source lives at
  `github.com/hrabanazviking/MindSpark_ThoughtForge` (Volmarr's
  repo, CC BY 4.0 per its `__init__.py` license declaration).
- The adapter writes new code under `mythic_vibe_cli/`; no
  vendor source is copied.
- The adapter contract is a duck-typed superset that any
  reasonable cognition / planner package can satisfy.

## Consequences

- The CLI gains an opt-in Planner-agent backend.
- ADR-0002's no-direct-vendor-imports rule is honoured — the
  adapter never imports from any in-tree MindSpark mirror.
- A missing `thoughtforge` package is now handled gracefully by
  the registry rather than via an exception path.
- The `mythic-vibe[mindspark]` extra is the canonical install
  story; a direct `pip install thoughtforge` also works.

## Verification

```bash
mythic-vibe ai providers --json
# mindspark entry present with configured: false (default)

pip install mythic-vibe[mindspark]
MYTHIC_ISLAND_MINDSPARK_ENABLED=1 mythic-vibe ai providers --json
# mindspark configured: true (when both flag and dep present)

pytest tests/test_island_mindspark.py
```
