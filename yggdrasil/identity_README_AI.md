# identity.py — README_AI

## Purpose

T3-A Identity Protocol (LDP — arXiv:2503.09732).

Wraps each NPC's context block with identity markers so the LLM maintains clean
per-character identity boundaries, and validates that no NPC's tag appears inside
another NPC's block before the prompt is sent.

This prevents identity cross-contamination — the failure mode where the LLM begins
blending two characters' knowledge, speech patterns, or memories when their context
blocks are adjacent.

## Key Components

### `wrap_npc_identity_block(npc_id, content) -> str`
Surrounds `content` with `<|NPC_{npc_id}_Start|>` and `<|NPC_{npc_id}_End|>` tags.
Empty `npc_id` or `content` returns the input unchanged.

### `validate_identity_isolation(prompt, strip_violations) -> (str, List[IsolationViolation])`
Scans the assembled prompt for nested identity tags (a Start tag inside another
character's open block). Logs violations at WARNING level. If `strip_violations=True`
(default), removes the nested tags from the returned string.
Safe to call on prompts without any identity tags.

### `IsolationViolation` (NamedTuple)
`outer_npc_id`, `inner_npc_id`, `position` — describes one detected violation.

### `_apply_identity_markers(prompt, npc_ids) -> str`
Post-hoc fallback: finds `=== {npc_id} ... ===` header lines that are not yet
wrapped and adds identity markers. Prefer calling `wrap_npc_identity_block()` at
block-assembly time instead.

## Integration

Called from `yggdrasil/router.py` `route_call()` after prompt assembly:
```python
full_prompt, violations = validate_identity_isolation(full_prompt, strip_violations=True)
```

`wrap_npc_identity_block()` is available to call from `CharacterDataFeed.to_ai_text()`
when assembling NPC blocks.

## Config knobs (`config.yaml`)
```yaml
identity_protocol:
  enabled: true
  strip_violations: true
```

---
**Last Updated**: 2026-03-14 | v8.0.0
