# Bug Crush List (Top 100 Targets)

## Data Integrity
1. Duplicate memory IDs during concurrent writes.
2. Missing source attribution in stitched context.
3. Non-deterministic sorting for equal relevance scores.
4. Event timestamps without timezone normalization.
5. Silent truncation of long narrative notes.

## Planning Quality
6. Plans lacking fallback steps.
7. Over-optimistic risk scoring.
8. Missing dependency checks before execution.
9. Unstable ordering of candidate actions.
10. No dead-end detection for blocked goals.

## Runtime Reliability
11. Retry loops without backoff jitter.
12. Partial writes when downstream fails.
13. Logging payload mismatch across modules.
14. Missing heartbeat for long-running tasks.
15. Weak protection against repeated dispatcher failures.

## UX/Narrative Consistency
16. Inconsistent NPC title formatting.
17. Sudden tone changes between adjacent scenes.
18. Incorrect pronoun persistence.
19. Duplicate quest hints in one session.
20. Overly generic region descriptions.

## Continue Expanding
- Add 80 more bug candidates during triage workshops.
- Tag each with severity, owner, and reproduction notes.
