# PHILOSOPHY

## Why this project exists
This repository treats software as both **craft** and **myth-making**: a practical engine built with clear interfaces, testable behavior, and disciplined iteration, while preserving a narrative identity that keeps builders aligned over long arcs of work.

We optimize for:
- **Clarity over cleverness** in architecture and implementation.
- **Durability over novelty** in design decisions.
- **Composability over monoliths** in systems and docs.
- **Truth-seeking over hand-waving** in claims, metrics, and evaluation.

## Core principles

### 1) Build with intention
Every module should have a purpose that can be explained in plain language. If a component cannot justify its existence, it should be simplified, merged, or removed.

### 2) Prefer explicit contracts
Interfaces, schemas, and boundaries should be concrete and visible. Hidden coupling is technical debt with interest.

### 3) Keep knowledge close to code
Architecture rationale, operating assumptions, and decision records should live in version control near the implementation they describe.

### 4) Design for change
Requirements evolve. Favor patterns that permit extension without rewriting fundamentals.

### 5) Verify reality
When behavior matters, test it. When performance matters, measure it. When safety matters, constrain it.

### 6) Respect the operator
Tooling should be understandable, debuggable, and humane. Error messages should help. Defaults should be safe.

### 7) Narrative is a systems tool
Naming and mythology are not decoration; they are mnemonic scaffolding. A shared language reduces coordination cost and strengthens long-term coherence.

## Engineering stance
- Small, reviewable changes beat heroic rewrites.
- Reproducibility beats folklore.
- Boring infrastructure is a feature.
- Security and permissions are first-class design concerns.
- Documentation is part of the product.

## Collaboration values
- Assume good intent; insist on rigor.
- Critique artifacts, not people.
- Leave every area clearer than you found it.
- Record decisions so future contributors inherit context, not confusion.

## Definition of progress
Progress is not just adding lines of code. Progress means:
1. Better reliability.
2. Better understanding.
3. Better leverage for the next contributor.

If we can ship useful capabilities while making the system simpler to reason about, we are moving in the right direction.
