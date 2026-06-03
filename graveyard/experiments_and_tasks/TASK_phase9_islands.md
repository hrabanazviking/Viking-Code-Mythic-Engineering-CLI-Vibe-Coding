# TASK — PH-09 Island Integrations

**Created:** 2026-05-01
**Branch:** `development`
**Operator:** Volmarr
**Resume from:** HEAD `0400960` (follow-up sub-slices closeout)

PH-09 brings the four dormant islands online via ADR-governed
adapters with feature flags, per Law 9 (Boundary Discipline).
Each island is gated behind try-import + a per-island env
feature flag so the CLI never crashes on a missing dep and never
silently activates a heavy backend.

**Master roadmap dependency:** `[PH-01, PH-05, PH-06]` — all closed.

---

## Adapter contract (applies to all islands)

Every island adapter must satisfy:

1. **ADR** in `docs/ADRS/` describing the need, boundary, and
   provenance.
2. **Adapter module** inside `mythic_vibe_cli/` — never imports
   from the dormant in-tree paths (`yggdrasil/`, `mindspark_thoughtform/`,
   etc.) per ADR-0002. Instead try-imports the canonically-named
   Python package; if missing, raises
   :class:`MissingExtraError` with a clean install hint.
3. **Feature flag** env var `MYTHIC_ISLAND_<NAME>_ENABLED` —
   default off. Even when the dep is installed, the adapter is a
   stub-only no-op until the operator opts in.
4. **Tests** proving:
   - Import-failure path raises MissingExtraError cleanly.
   - Feature-flag-off path is a clean no-op.
   - Feature-flag-on + dep-present path exercises the adapter.
5. **Doc updates** — `docs/DORMANT_ISLANDS.md` notes that the
   island has crossed the gate; `docs/ARCHITECTURE.md` mentions
   the adapter.

---

## Slice 9.1 — Island B (Yggdrasil router)

**Goal:** add `mythic_vibe_cli/ai/providers/yggdrasil.py` as an
optional Architect-agent backend that try-imports the
`yggdrasil` package and exposes its router as an :class:`AIProvider`.

**Files:**
- `mythic_vibe_cli/ai/providers/yggdrasil.py` (new) — adapter
  class `YggdrasilProvider(AIProvider)` with try-import.
- `mythic_vibe_cli/ai/registry.py` — register the new provider.
- `docs/ADRS/ADR-0005-island-b-yggdrasil-adapter.md` (new).
- `tests/test_island_yggdrasil.py` (new).

**Feature flag:** `MYTHIC_ISLAND_YGGDRASIL_ENABLED` (default off).

**Ghost-import note:** `core/emotional.py` and `core/dream_system.py`
import `yggdrasil_core` (which doesn't exist; closest is
`yggdrasil.core`). These files live in dormant `core/`, outside
the active runtime boundary. ADR-0005 documents the ghost as a
known-broken artifact inside dormant scope, out-of-contract for
the adapter. We don't touch dormant code.

**Acceptance:**
- `mythic-vibe ai providers --json` lists "yggdrasil" with
  `configured: false` when env flag off OR dep missing.
- Provider raises clean error when called with flag off /
  dep missing.
- All existing tests pass.

**Progress:** [ ] not started

---

## Slice 9.2 — Island C (MindSpark ThoughtForge)

**Goal:** add `mythic_vibe_cli/ai/providers/mindspark.py` —
optional Planner-agent backend that try-imports the `thoughtforge`
package (Volmarr's separate MindSpark repo, available as
`mythic-vibe[mindspark]` extra).

**Files:**
- `mythic_vibe_cli/ai/providers/mindspark.py` (new).
- `mythic_vibe_cli/ai/registry.py` — register.
- `pyproject.toml` — add `mindspark = ["thoughtforge>=1.2"]`
  to `[project.optional-dependencies]`.
- `docs/ADRS/ADR-0006-island-c-mindspark-adapter.md` (new).
- `tests/test_island_mindspark.py` (new).

**Feature flag:** `MYTHIC_ISLAND_MINDSPARK_ENABLED` (default off).

**Acceptance:**
- Adapter raises MissingExtraError with `pip install
  mythic-vibe[mindspark]` hint.
- When dep present + flag on, calls into a thoughtforge
  Planner-equivalent surface (best-effort wrapper; if MindSpark's
  public API doesn't expose a clean Planner today, expose only
  what's stable and document the gap).

**Progress:** [ ] not started

---

## Slice 9.3 — Island D (WYRD Protocol)

**Goal:** add `mythic_vibe_cli/verify/wyrd_oracle.py` — optional
Verifier-agent gate that try-imports `wyrd` and exposes
`passive_oracle` as an extra Auditor gate runner.

**Files:**
- `mythic_vibe_cli/verify/wyrd_oracle.py` (new).
- `mythic_vibe_cli/forge_verifier.py` — register optional
  `gate_wyrd_oracle` in `DEFAULT_AUDITOR_GATES` only when env flag
  is on.
- `pyproject.toml` — add `wyrd = ["wyrd-protocol>=1.0"]` to
  optional-deps.
- `docs/ADRS/ADR-0007-island-d-wyrd-adapter.md` (new).
- `tests/test_island_wyrd.py` (new).

**Feature flag:** `MYTHIC_ISLAND_WYRD_ENABLED` (default off).

**Acceptance:**
- Without WYRD installed and flag off, verifier behaviour is
  unchanged (all existing tests pass).
- With flag on + dep missing, gate runner records "missing extra"
  on the AgentOutput rather than raising.

**Progress:** [ ] not started

---

## Slice 9.4 — Island E (Chatterbox TTS) formalisation

**Goal:** PH-07 already wired Chatterbox via try-import in
`voice/tts.py`. This slice formalises the boundary with an ADR
and parity feature flag so all four islands share the same
shape.

**Files:**
- `docs/ADRS/ADR-0008-island-e-chatterbox-adapter.md` (new).
- `mythic_vibe_cli/voice/tts.py` — honour
  `MYTHIC_ISLAND_CHATTERBOX_ENABLED` in addition to the existing
  `MYTHIC_VOICE_TTS_ENABLED` (the new flag is opt-in for the
  island; the existing flag is the broader TTS gate). Both must
  be on for chatterbox to actually emit audio.
- `tests/test_island_chatterbox.py` (new) — parity with the other
  island toggle tests.

**Feature flag:** `MYTHIC_ISLAND_CHATTERBOX_ENABLED` (default off,
in addition to existing `MYTHIC_VOICE_TTS_ENABLED`).

**Acceptance:**
- Existing PH-07 chatterbox tests still pass (existing
  `MYTHIC_VOICE_TTS_ENABLED` semantics unchanged).
- New island flag gates the chatterbox engine specifically; stub
  engine remains unaffected.

**Progress:** [ ] not started

---

## Slice 9.5 — Feature-flag toggle tests

**Goal:** lock the cross-island isolation invariants — each
island's flag operates independently, and a missing dep on any
single island never breaks the core.

**Files:**
- `tests/test_island_isolation.py` (new) — parameterised tests
  covering all 4 × 4 toggle combinations (on/off × dep-present/
  dep-missing) for each island.

**Acceptance:**
- All 4 islands togglable independently.
- Missing dep on any single island → that island reports not
  configured; all other islands and core CLI behaviour unchanged.
- ALL existing tests still pass with all flags off (default
  behaviour is unchanged from before PH-09).

**Progress:** [ ] not started

---

## Phase finale

After all 5 slices ship:

- `PHASE9_FINALE_CLOSEOUT.md` — summary memo.
- Update `project_mythic_engineering_cli_status.md`,
  `MEMORY.md`.
- Push.
- Mark PH-09 closed in tracker; PH-09 unblocks no other phase
  directly (PH-10/PH-11 already had their deps closed) — pure
  capability addition.

---

## Operational notes

- ME laws apply: stdlib-first, optional deps via try-import +
  MissingExtraError, default-off feature gates, cross-platform.
- 100% open-source — every island package is open-source today
  (Yggdrasil + WYRD + MindSpark are Volmarr's projects;
  Chatterbox is third-party MIT).
- Adapter pattern from ADR-0002: `mythic_vibe_cli/` code never
  imports from the dormant in-tree paths. Adapters only
  try-import the externally-available Python package names.
- After each slice: update memory + status file immediately.
