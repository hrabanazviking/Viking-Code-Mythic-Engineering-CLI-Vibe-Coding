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
