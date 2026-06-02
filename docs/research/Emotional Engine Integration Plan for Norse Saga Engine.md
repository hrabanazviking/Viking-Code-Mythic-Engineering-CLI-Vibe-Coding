# Emotional Engine Integration Plan for Norse Saga Engine (vNext)

## Executive Summary

This plan upgrades the existing emotional engine roadmap into a **delivery-grade integration blueprint** with:

- **Current-state alignment** to what already exists in this repository.
- **Gap-driven priorities** (what is still missing vs. already shipped).
- **Deterministic mechanics** with explicit tuning surfaces.
- **Safety and fairness constraints** to avoid stereotyping.
- **Instrumentation, testing, and rollout controls** for stable deployment.

The system remains modular, lore-compatible, and hidden from the player while shaping narrative texture, NPC behavior biasing, and long-horizon character arcs.

---

## 1) Current-State Snapshot (Already Implemented)

The engine already includes substantial emotional infrastructure:

- `systems/emotional_engine.py` with:
  - `EmotionalProfile`
  - `EmotionalEngine`
  - `EmotionalBehavior`
  - `StressAccumulator`
  - keyword extraction (`EMOTION_KEYWORDS` / `extract_stimuli`)
  - intensity labeling for prompt formatting.
- `core/engine.py` integration points:
  - emotional engine registry/cache
  - stimulus extraction and per-turn updates
  - emotional context passed into prompt composition.
- `ai/prompt_builder.py` emotional context rendering.
- `systems/stress_system.py` integration surface.
- `config.yaml` emotional-engine tuning block.
- API debug exposure of emotional-engine snapshots (`api/game_api.py`).

### Why this matters

The previous version of this plan assumed greenfield work. This vNext plan focuses on **hardening and deepening** rather than re-adding what already exists.

---

## 2) Target Outcomes (What “1000x Better” Means)

### O1 — Higher Narrative Coherence
Emotions should influence dialogue, action pacing, and memory salience without breaking immersion.

### O2 — Deterministic + Tunable Simulation
Same input state should produce reproducible outputs under fixed seed/config, with all knobs documented.

### O3 — Non-Stereotyped Modeling
Population tendencies may exist as minor priors, but **individual profile dominates** every decision path.

### O4 — Operational Readiness
Metrics, debug commands, and regression tests ensure emotional logic can be safely evolved.

---

## 3) Core Design Principles

1. **Player-invisible mechanics:** expose effects, not numbers, in normal play.
2. **Individual over demographic priors:** cap gender-axis influence and always combine with individual offset.
3. **No hardcoded lore drift:** keep culturally grounded terms and behavior mappings in data where possible.
4. **Fail-soft behavior:** emotional system must never crash turn resolution.
5. **Composability:** emotional updates should augment, not replace, fear/chaos/chronotype/wyrd systems.

---

## 4) Gap Matrix (Implemented vs. Needs Work)

| Area | Status | Gap | Priority |
|---|---|---|---|
| Profile model (`emotion_profile`) | Mostly implemented | Tighten schema validation + migration defaults | High |
| Stimulus extraction | Implemented (keywords) | Add context windowing, negation handling, speaker attribution | High |
| Turn-loop integration | Implemented | Add deterministic ordering + idempotent decay pass | High |
| Prompt emotional context | Implemented | Add compact + verbose modes by token budget | Medium |
| Stress coupling | Present | Add threshold effects + ritual recovery hooks | High |
| Behavior mapping | Partially present | Add deterministic weighted sampler with personality modifiers | Medium |
| Memory coupling | Partial | Feed high-intensity events into long-term memory salience | High |
| Testing | Partial | Expand deterministic unit + scenario regression tests | Critical |
| Telemetry/debug | Partial | Add `/emotions`, `/stress`, `/emotiontrace` command surfaces | Medium |
| Docs/tuning guide | Fragmented | Consolidate parameter glossary and recipes | Medium |

---

## 5) Implementation Plan (Phased)

## Phase A — Stabilization & Safety (Immediate)

### A1. Profile Normalization Contract
- Enforce strict clamp rules:
  - `tf_axis: [0.0, 1.0]`
  - `gender_axis: [-1.0, 1.0]`
  - `individual_offset: [-0.25, 0.25]`
  - `baseline_intensity: [0.4, 1.8]`
  - `expression_threshold: [0.1, 0.95]`
  - `rumination_bias: [0.0, 1.0]`
  - `decay_rate: [0.01, 0.5]`
- Add profile migration utility for legacy characters missing `emotion_profile`.

### A2. Bias-Limit Guardrails
- Hard cap demographic modifier contribution to a small range (e.g., ±5%).
- Require individual modifiers (`individual_offset`, channel weights, baseline intensity) to outweigh demographic priors.
- Add inline documentation clarifying these are statistical priors, not identity rules.

### A3. Fault-Tolerant Emotional Step
- Wrap emotional update stage in fail-soft boundaries with logger warnings.
- On exception: skip emotional update for that actor, continue turn processing.

---

## Phase B — Signal Quality Upgrade

### B1. Stimulus Extraction v2
Upgrade keyword extraction to include:
- Negation handling (`not afraid`, `never angry`).
- Intensifiers/dampeners (`very`, `slightly`, `barely`, `utterly`).
- Speaker and target cues (who is feeling what).
- Recency weighting across player input + latest narrative + recent memory summary.

### B2. Channel-Specific Decay Dynamics
- Keep current base decay, then modulate by:
  - rumination,
  - unresolved fate thread relevance,
  - stress saturation state.
- Ensure decay never increases net emotion when no stimulus exists.

### B3. Ambient Fear Coupling
- Define explicit coupling function between global fear factor and per-character fear channel.
- Add one-way safety cap to prevent runaway escalation loops.

---

## Phase C — Prompting + Narrative Behavior

### C1. Prompt Layer Enhancements
Add two emotional prompt representations:
- **Compact mode**: token-efficient summary.
- **Expressive mode**: richer descriptors for pivotal scenes.

### C2. Behavioral Bias Output
- Expose a structured “emotional pressure vector” to prompt builder.
- Allow engine to suggest but not force action verbs (`hesitates`, `snaps`, `withdraws`, `seeks oath-bond`).

### C3. Cultural-Lore Phrase Bank
- Move emotional descriptors to a data file with saga-appropriate diction.
- Keep all narration consistent with Norse tone and avoid modern therapy jargon in output voice.

---

## Phase D — Stress, Rituals, and Recovery Arcs

### D1. Stress Threshold Events
Introduce deterministic thresholds (example):
- 30: unease penalties / terse narration cues
- 55: impaired focus cues / social friction
- 75: panic-risk or emotional outburst checks
- 90: crisis-state ritual or withdrawal behavior

### D2. Ritual Integration Hooks
Define canonical ritual effects:
- Fire vigil: lowers fear rumination.
- Oath-speaking: increases attachment stability.
- Solitary night-watch: converts anger to focused resolve.
- Communal feast: raises joy floor, reduces shame spikes.

### D3. Recovery Memory Imprinting
- Persist “healing events” in memory with salience tags.
- Future prompts should reflect whether character has adaptive coping history.

---

## Phase E — Verification, Tuning, and Rollout

### E1. Determinism Test Suite
- Unit tests for impact calculation invariants.
- Property tests for clamp/normalization safety.
- Seeded simulation tests to verify reproducible trajectories.

### E2. Scenario Regression Harness
Build scripted saga scenarios:
- betrayal scene
- battle terror scene
- reconciliation scene
- prolonged hardship scene

Track expected emotion trajectories and narrative markers.

### E3. Runtime Debug Commands
- `/emotions`: current channels + labels.
- `/stress`: stress value + threshold stage.
- `/emotiontrace N`: recent per-turn deltas.

### E4. Rollout Strategy
- Feature flag gates:
  - `emotion_engine.enabled`
  - `emotion_engine.extraction_v2`
  - `emotion_engine.behavior_bias`
- Deploy in shadow mode first (log-only), then enable influence gradually.

---

## 6) Deterministic Math Contract (Reference)

For each actor and channel per turn:

1. `stimulus_strength` from extraction pipeline.
2. `channel_raw = stimulus_strength * channel_weight[channel]`
3. `tf_mod = lerp(0.85, 1.15, tf_axis)`
4. `gender_mod = capped_gender_mod(gender_axis, individual_offset)`
5. `chrono_mod = chronotype_alignment(time_of_day, chronotype)`
6. `impact = channel_raw * tf_mod * gender_mod * chrono_mod * baseline_intensity`
7. `state[channel] = clamp01(state[channel] * (1 - effective_decay) + impact)`
8. If below expression threshold, route part to stress accumulator.

**Invariants:**
- All channels remain in `[0, 1]`.
- No negative stress contributions.
- Update order deterministic across actors.

---

## 7) Data & Config Additions

### Character-level (`emotion_profile`)
Retain current fields and add optional:
- `suppression_tendency`
- `recovery_elasticity`
- `trigger_tags` (e.g., `betrayal`, `isolation`, `oathbreaking`)

### Config-level (`config.yaml`)
Add/confirm knobs:
- extraction mode + weights
- decay scaling
- stress thresholds
- ritual effect strengths
- max demographic modifier contribution
- debug verbosity

---

## 8) Integration Surfaces by File

- `systems/emotional_engine.py`
  - extraction v2, deterministic sampler, clamp/invariant enforcement.
- `core/engine.py`
  - turn-stage orchestration, failure isolation, feature flags.
- `ai/prompt_builder.py`
  - compact/expressive emotional context formatting.
- `systems/stress_system.py`
  - threshold events and ritual recovery effects.
- `session/session_manager.py`
  - persist any additional emotional trace fields.
- `api/game_api.py`
  - expose controlled debug snapshots for tooling.

---

## 9) Acceptance Criteria

1. **Believability:** NPC reactions vary with emotional state in at least 4 scripted scenarios.
2. **Stability:** no turn-loop crashes caused by emotional subsystem under fuzzed input.
3. **Determinism:** seeded runs reproduce channel trajectories exactly.
4. **Fairness:** demographic priors never dominate individual profile effects.
5. **Performance:** emotional processing adds minimal overhead per turn.

---

## 10) Risks and Mitigations

- **Risk:** runaway fear/stress feedback loops.  
  **Mitigation:** hard caps + dampening + crisis cool-down states.

- **Risk:** overfitting to keyword extraction artifacts.  
  **Mitigation:** extraction v2 context windows + optional LLM classifier fallback.

- **Risk:** prompt bloat.  
  **Mitigation:** compact mode under token pressure.

- **Risk:** stereotype drift in narration.  
  **Mitigation:** explicit fairness constraints + review tests for descriptor language.

---

## 11) Immediate Next Sprint (Concrete Tasks)

1. Implement profile normalization + clamp tests.
2. Add extraction v2 (negation + intensifiers) behind feature flag.
3. Add stress threshold event hooks and ritual recovery table.
4. Add `/emotions` and `/stress` debug commands.
5. Create 4 deterministic scenario regressions and baseline outputs.

---

## 12) Closing

The Norse Saga Engine already has a strong emotional foundation. This upgraded plan shifts from “build from scratch” to **precision engineering**: improving signal quality, narrative utility, fairness safeguards, and operational reliability.

If executed in this order, the emotional layer will become a high-trust core system that deepens saga realism without exposing mechanics to the player.
