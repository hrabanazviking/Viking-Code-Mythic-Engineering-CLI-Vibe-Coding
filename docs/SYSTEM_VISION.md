# System Vision

## Purpose

Mythic Vibe CLI exists to help people build software with **intentional structure and durable continuity**. It is designed as an engineering companion that turns ambition into tractable loops, and loops into preserved progress.

The system should feel like a calm, reliable co-navigator:

- structured enough to prevent drift,
- flexible enough to keep creative momentum,
- explicit enough to support handoffs and long-lived maintenance.

---

## North Star

Enable individuals and small teams to move from idea to resilient implementation through a transparent method loop:

`intent -> constraints -> architecture -> plan -> build -> verify -> reflect`

Success means users can repeatedly deliver coherent outcomes with fewer rewrites, clearer decisions, and stronger session-to-session continuity.

---

## Product promises

1. **Architecture-first by default**  
   Encourage builders to model goals, constraints, and system boundaries before coding.

2. **Beginner-friendly, expert-capable**  
   Keep baseline workflows understandable while preserving depth for advanced operators.

3. **Traceable progress**  
   Each meaningful action should produce artifacts that can be reviewed later.

4. **Practical human + AI collaboration**  
   Prompt packets should improve signal quality, not obscure responsibility.

5. **Method fidelity without rigidity**  
   Strong defaults should guide, not imprison, healthy adaptation.

6. **Recoverability over heroic memory**  
   Work should survive interruptions, context loss, and contributor turnover.

---

## Scope

### In scope

- Project initialization + method-aligned scaffolding.
- Workflow commands for planning, check-ins, diagnostics, and status.
- Structured prompt packet generation and response logging.
- Documentation/process reinforcement for continuity.

### Out of scope

- Replacing engineering judgment.
- Fully autonomous implementation without human review.
- Provider lock-in to a single model/service.
- Implicit hidden state that cannot be inspected or repaired.

---

## Design principles

- **Clarity over cleverness** — behavior should be legible.
- **Artifacts over memory** — key decisions belong in files.
- **Small loops, fast feedback** — incremental progress beats fragile leaps.
- **Stable defaults, configurable edges** — protect beginners while enabling experts.
- **Transparency over magic** — explain why the system asks for each step.
- **Continuity over novelty** — prefer workflows that remain useful over time.

---

## User experience expectations

A user should be able to:

1. Initialize or adopt a project quickly.
2. Understand current phase and completion criteria.
3. Generate high-signal AI context without abandoning method structure.
4. Resume work after delay with minimal reconstruction.
5. Diagnose and repair stalled momentum with clear guidance.

A maintainer should be able to:

1. Trace rationale behind significant decisions.
2. Review release-facing changes clearly.
3. Validate boundary compliance in a large monorepo.
4. Onboard a new contributor through docs alone.

---

## Quality bar

High-quality Mythic Vibe CLI behavior is:

- **Coherent** — interactions reinforce one mental model.
- **Recoverable** — state can be inspected and corrected.
- **Documented** — rationale and outcomes are preserved.
- **Composable** — workflow steps chain cleanly.
- **Trustworthy** — diagnostics reflect actual system state.
- **Durable** — artifacts remain useful beyond a single session.

---

## Evolution path

### Near-term priorities

1. Sharper phase guidance and error remediation messaging.
2. Better diagnostics with concrete fix recommendations.
3. Higher-signal context packet composition controls.
4. Stronger contributor onboarding and governance records.
5. Consistent release history discipline via changelog practices.

### Mid-term opportunities

- richer state introspection tooling,
- stronger template systems for planning docs,
- improved integration surfaces for external tooling.

### Long-term opportunities

- multi-agent coordination patterns,
- memory/retrieval extensions with explicit guardrails,
- broader ritual command ecosystem with maintainable contracts.

---

## Anti-goals

The system should not become:

- a black-box agent that hides decisions,
- a process bureaucracy detached from delivery,
- a style-policing layer that ignores outcomes,
- an opaque wrapper around external vendors.

---

## Final vision statement

Mythic Vibe CLI is an engineering compass: a toolchain that helps humans and AI create software with stronger intent, clearer structure, and preserved continuity from first concept through long-term maintenance.
