# PH-09 — Phase Finale Close-out (2026-05-01)

**Branch:** `development`
**Final HEAD:** `1fdba08` (this memo will land the next commit)
**Resume from:** `0400960` (follow-up sub-slices closeout)

PH-09 brings the four dormant islands online via ADR-governed
adapters with feature flags. All five slices closed in order;
working tree clean, every commit pushed, no test leaks, all
existing tests still pass.

---

## What landed

| Slice | Island | Commit | Net |
|---|---|---|---|
| TASK file | — | `8f94340` | +208 lines |
| 9.1 | Island B — Yggdrasil router | `362463f` | +516 lines, +15 tests |
| 9.2 | Island C — MindSpark ThoughtForge | `101cebc` | +472 lines, +14 tests |
| 9.3 | Island D — WYRD Protocol | `7612366` | +650 lines, +22 tests |
| 9.4 | Island E — Chatterbox formalisation | `7ad6990` | +312 lines, +10 tests |
| 9.5 | Cross-island isolation tests | `1fdba08` | +318 lines, +16 tests |

**Test delta:** 1085 → 1162 (+77 net).
**Coverage:** 76% (held).
**Lint / type:** clean throughout.
**ADRs added:** ADR-0005, ADR-0006, ADR-0007, ADR-0008.

---

## Adapter contract (now standard across all four islands)

Every island now satisfies:

1. **ADR** in `docs/ADRS/` describing the need, boundary, and
   provenance.
2. **Adapter module** inside `mythic_vibe_cli/` — never imports
   from any in-tree dormant directory per ADR-0002. Each
   adapter try-imports the canonically-named external Python
   package (`yggdrasil`, `thoughtforge`, `wyrd`, `chatterbox`).
3. **Per-island feature flag** env var
   `MYTHIC_ISLAND_<NAME>_ENABLED` — default off. Even when the
   dep resolves, the adapter is a stub-only no-op until the
   operator opts in.
4. **Tests** proving import-failure path is graceful, flag-off
   path is no-op, flag-on + dep-present path exercises the
   adapter.
5. **Doc updates** — `docs/DORMANT_ISLANDS.md` lists all four
   islands in the "crossed the gate" table.

---

## Capability summary

### Island B — Yggdrasil router (`mythic_vibe_cli/ai/providers/yggdrasil.py`)

Optional Architect-agent backend. Try-imports `yggdrasil` and
exposes its router as an :class:`AIProvider`. Two-key gating:
dep importable AND `MYTHIC_ISLAND_YGGDRASIL_ENABLED=1`. Real
path tries `route()` / `router.route()` / `ask()` in order.
ADR-0005. Registered as `"yggdrasil"` in
:class:`ProviderRegistry`. Operators route via
`mythic-vibe ai run --provider yggdrasil`.

### Island C — MindSpark ThoughtForge (`mythic_vibe_cli/ai/providers/mindspark.py`)

Optional Planner-agent backend. Try-imports `thoughtforge`. Two-
key gating with `MYTHIC_ISLAND_MINDSPARK_ENABLED`. Duck-typed
dispatch tries `plan()` / `cognition.plan` /
`cognition.scaffold.plan` / `cognition.router.route` / `ask()`.
Optional dep declared in `pyproject.toml` as
`mindspark = ["thoughtforge>=0.1"]`; install via
`pip install mythic-vibe[mindspark]`. ADR-0006.

### Island D — WYRD Protocol (`mythic_vibe_cli/verify/wyrd_oracle.py`)

Optional Verifier-agent world-model gate. Try-imports `wyrd`,
exposes `gate_wyrd_oracle` compatible with the slice 3.6
forge_verifier registry. Critically: the gate is **not** auto-
registered in `DEFAULT_AUDITOR_GATES` — operators opt in
explicitly via the new `wyrd_gate_if_enabled()` helper:

```python
gates = {**DEFAULT_AUDITOR_GATES, **wyrd_gate_if_enabled()}
run_auditor_gates(plan, agent_input, agent_output, root, gates=gates)
```

This preserves backwards-compat for every existing project. Two-
key gating with `MYTHIC_ISLAND_WYRD_ENABLED`. Verdict coercion
handles bool / dict / truthy-any. ADR-0007. Optional dep:
`wyrd = ["wyrd-protocol>=1.0"]`.

### Island E — Chatterbox TTS (PH-07 + Slice 9.4 formalisation)

Already wired in PH-07; this slice formalises the boundary with
ADR-0008 and adds the per-island flag for parity. Real audio
now requires **both**:

- `MYTHIC_VOICE_TTS_ENABLED=1` (broader voice gate)
- `MYTHIC_ISLAND_CHATTERBOX_ENABLED=1` (per-island gate)

Stub engine behaviour is unchanged. `force=True` bypasses both.

---

## Master-roadmap impact

PH-09 marked closed. All five slices shipped:

- 9.1 Island B (Yggdrasil) ✓
- 9.2 Island C (MindSpark) ✓
- 9.3 Island D (WYRD) ✓
- 9.4 Island E (Chatterbox) ✓
- 9.5 Feature-flag toggle tests ✓

**Phases now fully closed:** PH-01, PH-02, PH-03, PH-04, PH-05,
PH-06 (5/6), PH-07, PH-08, **PH-09**, PH-13, PH-15. (11 of 20.)

PH-09 unblocks no other phase directly — it's a pure capability
addition. Remaining phases: PH-10 (Plugin Ecosystem), PH-11
(Security/Sandbox), PH-12 (CI/CD), PH-14 (Policy Engine), PH-16
(MCP/ACP/OpenTelemetry), PH-17 (Multi-Surface Access), PH-18
(Robustness Sweeps), PH-19 (Distribution), PH-20 (v1.0.0
Sovereign OS Launch).

**Recommended next move:** PH-10 (Plugin Ecosystem & Community
Infrastructure) — high priority, deps satisfied (PH-01 + PH-02
both closed). PH-11 (Security/Sandbox) is the strategic
alternative if Volmarr wants to anchor security before extending
the plugin surface.

---

## Operational notes

- All five slices shipped under the ME laws: stdlib-first,
  optional deps via try-import + clean install hints, default-off
  feature gates, cross-platform.
- 100% open-source — every island package is open-source today
  (Yggdrasil + WYRD + MindSpark are Volmarr's projects;
  Chatterbox is third-party MIT).
- Adapter pattern from ADR-0002 honoured throughout: no
  `mythic_vibe_cli/` code imports from the dormant in-tree
  paths. Every adapter resolves the canonical external Python
  package name.
- Memory updated incrementally after each slice (per the durable
  rule about not batching).
- New `pyproject.toml` extras: `mindspark`, `wyrd`, `yggdrasil`
  (plus the existing `chatterbox` integration through the
  `voice` flow).

---

## Update Notice — 2026-05-02 Phase F.2 (additive, audit remediation)

The 2026-05-02 pseudo-code audit (`AUDIT_PSEUDOCODE_DEEP_2026-05-02.md`,
finding #8) caught the `yggdrasil` and `mindspark` adapters using
**speculative `getattr` probe loops** for entry-point names that
may not exist in the upstream packages. The probes (`route`,
`router.route`, `ask` for Yggdrasil; `plan`, `cognition.plan`,
`cognition.scaffold.plan`, `cognition.router.route`, `ask` for
MindSpark) were guesses rather than documented contracts.

**Fix shipped in Phase F.2 (additive, both adapters):**

1. **MindSpark — documented primary path:**
   - Verified against `MindSpark_ThoughtForge` HEAD on 2026-05-02:
     `thoughtforge.cognition.ThoughtForgeCore` is exported from
     `cognition/__init__.py`; `.think(prompt)` returns a
     `FinalResponseRecord` with `.text`.
   - `_invoke_thoughtforge` tries this canonical path first via
     the new `_resolve_thoughtforge_core_class(module)` helper.
   - Helper checks `module.cognition.ThoughtForgeCore` first;
     when `module.__name__ == "thoughtforge"` (real package), it
     falls back to a direct `from thoughtforge.cognition import
     core` import (since `import thoughtforge` alone does not
     eagerly import sub-packages).
   - The fallback is **gated on `module.__name__`** so test
     fakes (`_Empty()`, `MagicMock()`) don't accidentally pull in
     the real package.
   - `_invoke_thoughtforge` returns `(text, label)` where label
     is `thoughtforge.cognition.ThoughtForgeCore.think` for the
     primary path or `legacy:thoughtforge.<attr_path>` for
     legacy-probe matches. `run()` propagates the label into
     `response.metadata["entry_point"]`.

2. **Yggdrasil — wyrdforge import path + entry-point labelling:**
   - Verified against `WYRD-Protocol` HEAD on 2026-05-02: the
     canonical published package is `wyrdforge` (per
     `pyproject.toml`), not `yggdrasil`. The legacy `yggdrasil`
     name was an aspirational alias never published.
   - New `_try_import_wyrdforge()` companion to existing
     `_try_import_yggdrasil()`. `__post_init__` tries `wyrdforge`
     first, falls back to `yggdrasil`. Either resolves; whichever
     is on `sys.path` wins.
   - `validate_config` reports the resolved module name via
     `module.__name__` rather than hardcoding "yggdrasil".
   - `_invoke_yggdrasil` returns `(text, label)` where label is
     `<module>.<attr_path>` (e.g. `wyrdforge.route`). Candidate
     list (`route`, `router.route`, `ask`) preserved per the
     additive-only rule.
   - `AttributeError` raised when no candidate resolves now
     points operators at `wyrdforge` as the canonical install
     target.
   - `run()` propagates the label into
     `response.metadata["entry_point"]`.

**Tests:** `tests/test_island_yggdrasil.py` gained 8 new tests
across 3 classes (import priority, entry-point labelling, `run()`
metadata propagation). `tests/test_island_mindspark.py` gained 4
new tests covering the documented primary path, legacy fallback
labelling, and the resolver's "don't fall back for non-thoughtforge
modules" safety. Two pre-existing tests had their assertion text
adjusted (yggdrasil's "not installed" wording; mindspark's
"unknown shape" test gained a Phase-F.2 explanatory comment).

Test count: 1863 → 1875 (+12). Coverage still ≥ 82%. Lint + mypy
clean.

— *Sólrún Hvítmynd & Runa, additive correction*
