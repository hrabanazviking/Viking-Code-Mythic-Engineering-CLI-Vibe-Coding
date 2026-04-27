# ADR-0004: Doctor Diagnostics

## Status

Accepted

## Context

The `doctor` and `scry` commands are responsible for surface-level project health scanning, documentation drift detection, and repository boundary checks.

## Decision

- `doctor` should report actionable findings, not vague encouragement.
- Diagnostic checks should be explicit, durable, and JSON-friendly.
- Documentation drift and phase coherence are health signals, not optional trivia.

## Consequences

- The CLI can expose missing artifacts, stale docs, and coherence problems before they become confusing failures.
- The diagnostic layer must stay close to the active runtime contract and evolve with it.
