# Session Handoff Template

Use this template at the end of substantial work sessions to preserve continuity for the next contributor.

---

## Session metadata

- **Date (UTC):**
- **Branch:**
- **Primary objective:**
- **Session type:** (implementation / refactor / documentation / investigation / triage)

---

## What changed

Summarize concrete modifications in plain language.

- Files modified:
- Commands executed:
- Tests/checks run:
- Artifacts produced:

---

## Why these changes were made

Capture rationale, tradeoffs, and constraints.

- Decision drivers:
- Alternatives considered:
- Risks accepted:

---

## Current repository state

- Working tree status:
- Known unstable areas:
- Open TODOs intentionally deferred:

---

## Validation summary

List checks with pass/fail status and key output.

- [ ] Unit tests
- [ ] Linting/formatting
- [ ] Smoke run of changed commands
- [ ] Documentation synchronization

Notes:

---

## Continuity threads for next session

Record unresolved questions as explicit prompts.

1.
2.
3.

---

## Documentation sync checklist

Before closing:

- [ ] `DEVLOG.md` updated with date and rationale
- [ ] `CHANGELOG.md` updated if user-facing behavior shifted
- [ ] `docs/INDEX.md` updated for new/moved docs
- [ ] Cross-links checked
- [ ] Deprecated claims removed or marked historical

---

## Optional: paste-ready handoff note

```md
### Handoff Summary
Date: <YYYY-MM-DD>
Objective: <one line>
Completed: <bullets>
Deferred: <bullets>
Next recommended step: <one line>
```

This template is intentionally concise so it gets used. Precision is better than volume; continuity is better than silence.
