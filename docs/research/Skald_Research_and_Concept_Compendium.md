# Skald Research and Concept Compendium

## Purpose of this compendium

Capture high-value concept directions that align with the current codebase reality and can guide future implementation choices.

---

## I. Concept: The Forge-and-Weave Model

### Thesis
A productive AI engineering platform should separate:

- **Forge**: deterministic craft layer (tests, constraints, file ops, verification).
- **Weave**: interpretive narrative layer (naming, vision, rationale, continuity stories).

### Why it fits this project
The CLI already has a Forge baseline. A Skald agent and related docs establish the Weave so teams maintain conceptual coherence over long horizons.

### Research questions
1. Which project outcomes improve when teams write explicit vision statements before coding?
2. How does ritualized phase language affect check-in quality and handoff success?
3. Can naming quality be scored for clarity + resonance + maintainability?

---

## II. Concept: Memory as Civic Infrastructure

### Thesis
Project memory should be treated as shared civic infrastructure, not personal notes.

### Practical implication
Use event logs + decision records + status snapshots as first-class artifacts, with machine-readable schemas.

### Candidate schema fragments

```json
{
  "event_id": "uuid",
  "time": "2026-04-23T00:00:00Z",
  "actor": "user|assistant|automation",
  "event_type": "checkin",
  "phase": "build",
  "summary": "Implemented topology analyzer v1"
}
```

```json
{
  "decision_id": "ADR-014",
  "title": "Adopt three-ring architecture",
  "status": "accepted",
  "consequences": ["reduced runtime ambiguity", "requires migration plan"]
}
```

---

## III. Concept: Mythic UX without Mystification

### Thesis
Mythic language can improve memory and motivation, but only if every poetic term maps to an operational behavior.

### Mapping standard
- `scry` -> diagnostics.
- `imbue` -> scaffold initialization.
- `weave` -> documentation synchronization.

Every term should have a plain-language alias and help text so onboarding remains inclusive.

---

## IV. Concept: Sovereign Interop Mesh

### Thesis
Imported systems (WYRD, MindSpark, Norse Saga components) should interoperate through adapters, not source sprawl.

### Research directions
1. Define adapter contracts for data exchange (events, memory records, world state).
2. Evaluate minimal viable protocol for model/tool routing across subprojects.
3. Build “capability cards” that declare trust level, required resources, and safety constraints.

---

## V. Concept: Narrative-Backed Technical Governance

### Thesis
Technical governance gains adoption when written as both policy and story.

### Dual-document pattern
- **Policy doc:** strict requirements and checklists.
- **Skald doc:** why those rules exist, what failure feels like, what success protects.

This pattern reduces mechanical compliance fatigue.

---

## VI. Immediate research backlog (actionable)

1. Build benchmark for prompt packet usefulness:
   - task success,
   - correction count,
   - user perceived clarity.
2. Compare compacted vs full packet outcomes.
3. Measure effect of phase-aware prompts on regression rate.
4. Track whether architectural vision docs reduce mid-project rewrites.
5. Evaluate naming conventions against contributor onboarding speed.

---

## VII. Suggested future documents (Skald series)

- `Skald_Module_Naming_Grimoire.md`
- `Skald_Philosophy_of_Sovereign_AI_Projects.md`
- `Skald_Glossary_Mythic_to_Engineering.md`
- `Skald_Contributor_Onboarding_Story.md`

These should remain grounded in real commands, files, and tests.
