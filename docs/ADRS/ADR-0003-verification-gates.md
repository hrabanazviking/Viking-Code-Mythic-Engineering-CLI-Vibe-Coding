# ADR-0003: Verification Gates

## Status

Accepted

## Context

The CLI now records durable verification artifacts and blocks reflective check-ins until the latest verification has passed.

## Decision

- Verification must be explicit and recorded.
- A successful verification artifact is required before `reflect` check-ins can complete.
- The verification record is part of the project memory, not a throwaway console result.

## Consequences

- The CLI can refuse to claim completion when reality has not been checked.
- Future changes to verification must keep artifact writing and state linkage intact.
