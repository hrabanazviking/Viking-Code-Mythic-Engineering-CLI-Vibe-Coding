# identity.py — INTERFACE

## `wrap_npc_identity_block(npc_id: str, content: str) -> str`
Wraps `content` with `<|NPC_{npc_id}_Start|>` / `<|NPC_{npc_id}_End|>` tags.
Returns `content` unchanged if either argument is empty.

---

## `IsolationViolation` (NamedTuple)

### Fields
`outer_npc_id: str`, `inner_npc_id: str`, `position: int`

---

## `validate_identity_isolation(prompt: str, strip_violations: bool = True) -> tuple[str, List[IsolationViolation]]`
Scan prompt for nested NPC identity tags.
- Returns `(cleaned_prompt, violations)`.
- If `strip_violations=True`: nested/mismatched tags are removed from output.
- If no tags present: returns `(prompt, [])` immediately.
- Never raises.

---

## `_apply_identity_markers(prompt: str, npc_ids: List[str]) -> str`
Post-hoc fallback: wraps untagged `=== {npc_id} ===` header blocks.
Does not double-wrap already-tagged blocks.

---
**Contract Version**: 1.0 | 2026-03-14
