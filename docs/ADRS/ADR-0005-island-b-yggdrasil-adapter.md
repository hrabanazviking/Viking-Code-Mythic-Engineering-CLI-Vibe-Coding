# ADR-0005: Island B (Yggdrasil) Adapter

## Status

Accepted

## Context

Yggdrasil is a Norse-mythology-inspired cognitive routing
architecture (Volmarr's separate research project — Asgard /
Vanaheim / Alfheim / Midgard / Jotunheim / Svartalfheim /
Niflheim / Muspelheim / Helheim realms, plus the Huginn / Muninn
ravens). A snapshot of its source lives in this repository under
`yggdrasil/`, but is **dormant** per `docs/DORMANT_ISLANDS.md` and
`ADR-0001` — it has unresolved imports and is not part of the
active CLI runtime.

PH-09 of the master roadmap calls for bringing the islands online
through ADR-governed adapters with feature flags. Yggdrasil is
Island B.

## Decision

Add a thin adapter at
`mythic_vibe_cli/ai/providers/yggdrasil.py` that:

1. **Try-imports the canonical Python package name `yggdrasil`** —
   never imports the in-tree quarantined `yggdrasil/` directory by
   path. This keeps the boundary in `ADR-0002` intact: the
   adapter resolves whatever module the operator's `sys.path` /
   pip env makes available; the in-tree dormant snapshot is never
   coupled to active runtime by reference.

2. **Gates real activation behind two conditions** — both must be
   true:
   - The package import succeeds.
   - The operator sets `MYTHIC_ISLAND_YGGDRASIL_ENABLED=1`.
   When either is false, the adapter reports `configured=False`
   and `run()` returns a stub-shaped placeholder rather than
   raising.

3. **Exposes the provider as ``"yggdrasil"`** in the
   :class:`ProviderRegistry`. Operators can route to it via
   `mythic-vibe ai run --provider yggdrasil ...` once the gate is
   on. The slice 8.3 routing fallback chain handles the
   not-configured case automatically (skips and falls forward
   onto the next provider).

4. **Routes through a narrow contract** — the adapter calls one
   of `yggdrasil.route(prompt)` / `yggdrasil.router.route(prompt)`
   / `yggdrasil.ask(prompt)`, in that order, and accepts whatever
   string it returns. Future slices may widen the contract once
   the upstream API stabilises.

## Ghost-import disposition

`core/emotional.py` and `core/dream_system.py` (in dormant
`core/`, **not** in active `mythic_vibe_cli/`) import
`yggdrasil_core` — a name that does not exist anywhere in the
repository (closest is `yggdrasil.core`). This is a known-broken
artifact in dormant code, **out of scope for this adapter**. The
adapter does not import `core/` and does not depend on the ghost
name being resolvable. We do not modify dormant code as part of
this slice; the broken import remains as a research-time tag and
will be addressed (if at all) by a future cleanup or by deleting
the dormant cluster wholesale.

## Provenance

- Yggdrasil snapshot in `yggdrasil/` is Volmarr's own design
  (no third-party copyrights identified in the snapshot).
- The adapter writes new code under `mythic_vibe_cli/`; no
  vendor source is copied across the boundary.
- The adapter contract (`route` / `router.route` / `ask`) is
  intentionally a duck-typed superset that any reasonable
  Norse-themed routing package can satisfy.

## Consequences

- The CLI gains an opt-in Architect-agent backend.
- ADR-0002's no-direct-vendor-imports rule is honoured — the
  adapter never imports from `yggdrasil/` (the in-tree path); it
  only resolves whatever the Python import system maps.
- A missing `yggdrasil` package is now handled gracefully by the
  registry rather than via an exception path.

## Verification

```bash
mythic-vibe ai providers --json
# yggdrasil entry present with configured: false (default)

MYTHIC_ISLAND_YGGDRASIL_ENABLED=1 mythic-vibe ai providers --json
# yggdrasil still configured: false unless yggdrasil package importable

pytest tests/test_island_yggdrasil.py
```
