# Session Handoff Template

Use this template at the end of substantial work sessions to preserve continuity for the next contributor.

> **Tip.** `mythic-vibe reflect --summary "..." --next-step "..." --note "..."` writes a structured handoff record under `mythic/handoffs/` (Markdown + JSON) that follows the same contract this template encodes. The template is for the cases where you want to draft the handoff in your editor first, or when you're recording session continuity outside a Mythic-scaffolded project. Either path is fine.

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

- [ ] `pytest -q` (unit + integration + property + snapshot tests)
- [ ] `ruff check mythic_vibe_cli tests scripts tools` (linting)
- [ ] `mypy mythic_vibe_cli` (type checking)
- [ ] `python tools/contract_audit.py --strict` (docs↔code drift gate, v1.0)
- [ ] Smoke run of changed commands
- [ ] Documentation synchronization
- [ ] (When changing CHANGELOG) `python scripts/check_changelog.py` (release gate) + `--classify` (Unclassified count = 0)

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
- [ ] `CHANGELOG.md` updated if user-facing behavior shifted (use a conventional-commit prefix so the PH-20.F classifier buckets it cleanly)
- [ ] `docs/INDEX.md` updated for new/moved docs
- [ ] Cross-links checked
- [ ] Deprecated claims removed or marked historical
- [ ] (v1.0+) `docs/security/threat_model.md` updated if a new attack surface was added (per its §8 update procedure)
- [ ] (v1.0+) `docs/compatibility_policy.md` updated if a Stable-tier surface changed

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
