"""
Identity Protocol (T8 — LDP)
============================

Wraps each NPC's context block with identity markers so the LLM can
maintain clean per-character identity boundaries, and validates that no
NPC's tag appears inside another NPC's block before the prompt is sent.

Based on arXiv:2503.09732 — LDP: Language-Model De-Personification.

Architecture:
  wrap_npc_identity_block(npc_id, content) — surround a block with markers
  validate_identity_isolation(prompt)       — detect + strip nested tags
  _apply_identity_markers(prompt)           — post-hoc pass (rare fallback)

Integration point:
  YggdrasilAIRouter.route_call() calls validate_identity_isolation() on the
  assembled full_prompt before the LLM call.  NPC blocks are wrapped by
  CharacterDataFeed.to_ai_text() via wrap_npc_identity_block().
"""

from __future__ import annotations

import logging
import re
from typing import List, NamedTuple, Optional

logger = logging.getLogger(__name__)

# ── Tag templates ────────────────────────────────────────────────────────────

_START_TMPL = "<|NPC_{npc_id}_Start|>"
_END_TMPL   = "<|NPC_{npc_id}_End|>"

# Matches any identity-protocol start or end tag.
_TAG_PATTERN = re.compile(r"<\|NPC_([A-Za-z0-9_\-]+)_(Start|End)\|>")


# ── Public helpers ────────────────────────────────────────────────────────────

def wrap_npc_identity_block(npc_id: str, content: str) -> str:
    """
    Surround *content* with identity markers for *npc_id*.

    >>> wrap_npc_identity_block("bjorn_karl", "Bjorn is a farmer.")
    '<|NPC_bjorn_karl_Start|>\\nBjorn is a farmer.\\n<|NPC_bjorn_karl_End|>'
    """
    if not npc_id or not content:
        return content
    start = _START_TMPL.format(npc_id=npc_id)
    end   = _END_TMPL.format(npc_id=npc_id)
    return f"{start}\n{content}\n{end}"


class IsolationViolation(NamedTuple):
    outer_npc_id: str
    inner_npc_id: str
    position: int        # char offset of the nested start tag in the prompt


def validate_identity_isolation(
    prompt: str,
    strip_violations: bool = True,
) -> tuple[str, List[IsolationViolation]]:
    """
    Scan *prompt* for NPC identity tags that appear inside another NPC's block.

    Returns ``(cleaned_prompt, violations)``.

    * If *strip_violations* is True (default) the nested inner tags are removed
      from the returned string.
    * Violations are logged at WARNING level so they are visible in session logs
      without raising.
    * Safe to call on prompts that contain no identity tags — returns the
      original string and an empty list.
    """
    if "<|NPC_" not in prompt:
        return prompt, []

    violations: List[IsolationViolation] = []
    # Track which NPC's block we are currently inside (stack-based).
    stack: list[str] = []          # npc_ids of open blocks, innermost last
    positions_to_strip: list[tuple[int, int]] = []   # (start, end) char spans

    for match in _TAG_PATTERN.finditer(prompt):
        npc_id  = match.group(1)
        tag_type = match.group(2)   # "Start" or "End"

        if tag_type == "Start":
            if stack:
                # A Start tag while already inside another block = violation.
                outer = stack[-1]
                v = IsolationViolation(
                    outer_npc_id=outer,
                    inner_npc_id=npc_id,
                    position=match.start(),
                )
                violations.append(v)
                logger.warning(
                    "Identity isolation violation: NPC_%s_Start found inside "
                    "NPC_%s block at offset %d",
                    npc_id, outer, match.start(),
                )
                if strip_violations:
                    positions_to_strip.append((match.start(), match.end()))
                # Do NOT push the violating inner tag onto the stack.  If we
                # did, the inner End tag would pop the outer NPC, orphaning
                # the outer End tag and corrupting all subsequent LLM output.
            else:
                stack.append(npc_id)

        elif tag_type == "End":
            if stack and stack[-1] == npc_id:
                stack.pop()
            elif stack:
                # Mismatched end tag — strip it.
                outer = stack[-1]
                logger.warning(
                    "Identity isolation: NPC_%s_End found while inside "
                    "NPC_%s block (mismatch) at offset %d",
                    npc_id, outer, match.start(),
                )
                if strip_violations:
                    positions_to_strip.append((match.start(), match.end()))
            # If stack is empty and we get an End tag, just ignore it.

    if not positions_to_strip:
        return prompt, violations

    # Strip in reverse order to preserve offsets.
    cleaned = list(prompt)
    for start, end in sorted(positions_to_strip, reverse=True):
        del cleaned[start:end]
    return "".join(cleaned), violations


def _apply_identity_markers(prompt: str, npc_ids: List[str]) -> str:
    """
    Fallback post-hoc pass: if an NPC's block delimiter (``=== {id} ...``) is
    present but NOT yet wrapped with identity markers, wrap it now.

    This is a best-effort scan — it only handles the canonical
    ``=== NAME (role) ===`` header format used by CharacterDataFeed.to_ai_text().
    Prefer calling wrap_npc_identity_block() at block-assembly time.
    """
    if not npc_ids:
        return prompt

    for npc_id in npc_ids:
        start_tag = _START_TMPL.format(npc_id=npc_id)
        if start_tag in prompt:
            continue   # already wrapped

        # Look for the canonical header line that contains the npc_id.
        # Pattern: line starting with "=== " that contains the id (case-insensitive).
        # Use word-boundary (\b) anchors so short ids like "ol" don't match
        # "olaf", "colour", etc. accidentally.
        header_re = re.compile(
            r"(^=== [^\n]*\b" + re.escape(npc_id) + r"\b[^\n]*===\n?)",
            re.IGNORECASE | re.MULTILINE,
        )
        match = header_re.search(prompt)
        if not match:
            continue

        # Find the matching end — next "=== ... ===" header or end of string.
        block_start = match.start()
        next_header = re.search(r"^=== ", prompt[match.end():], re.MULTILINE)
        if next_header:
            block_end = match.end() + next_header.start()
        else:
            block_end = len(prompt)

        block_content = prompt[block_start:block_end].rstrip("\n")
        end_tag   = _END_TMPL.format(npc_id=npc_id)
        wrapped   = f"{start_tag}\n{block_content}\n{end_tag}\n"
        prompt    = prompt[:block_start] + wrapped + prompt[block_end:]

    return prompt
