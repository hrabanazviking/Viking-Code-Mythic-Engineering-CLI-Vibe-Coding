"""Phase 20.3 — plugin capability declarations (default-deny).

A plugin's ``capabilities`` field declares the *intended* runtime
permissions the plugin requires. The Mythic Vibe CLI does NOT
enforce these at the OS level (Python lacks portable in-process
sandboxing — see ``docs/security/threat_model.md`` §7.1), but
the declarations serve three roles:

1. **Operator-visible audit trail.** ``mythic-vibe plugin doctor``
   surfaces declared vs. expected capabilities so operators can
   spot a plugin asking for more than it should need.
2. **Future-enforcement hook.** When a real subprocess sandbox
   lands (PH-21+ stretch), the declarations become the policy
   input.
3. **Discipline signal.** Plugin authors who declare narrowly
   communicate intent to reviewers and to themselves.

**Default-deny:** a plugin with no ``capabilities`` field — or
an explicitly empty list — is treated as **read-own-context
only**. Capability-requiring features (network, subprocess,
file-write outside the plugin's own context) ARE NOT silently
granted.

The valid capability vocabulary is fixed by
:data:`KNOWN_CAPABILITIES`. Unknown capability strings surface
as warnings in ``plugin doctor`` so typos are caught early.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass


# Fixed vocabulary. Adding a new capability requires:
#   - update this tuple
#   - update plugin_manifest.schema.json enum
#   - update docs/plugins.md operator section
#   - changelog Added entry
KNOWN_CAPABILITIES: tuple[str, ...] = (
    "read",          # read project files inside the operator's repo
    "network",       # outbound HTTP / TCP / etc.
    "subprocess",    # spawn child processes
    "file-write",    # write files outside the plugin's own context dir
)

DEFAULT_CAPABILITIES: tuple[str, ...] = ()  # i.e. read-own-context only


@dataclass(frozen=True)
class CapabilityAudit:
    """Result of validating a single plugin's declared
    capabilities. ``unknown`` lists tokens that are not in
    :data:`KNOWN_CAPABILITIES` — typically typos."""

    declared: tuple[str, ...]
    unknown: tuple[str, ...]
    is_default_deny: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "declared": list(self.declared),
            "unknown": list(self.unknown),
            "is_default_deny": self.is_default_deny,
        }


def parse_capabilities(raw: object) -> tuple[str, ...]:
    """Coerce whatever's in the manifest's ``capabilities`` slot
    into a stable tuple of strings. Non-iterables become empty;
    individual non-string entries are stringified. Order is
    preserved (operator intent often encodes priority)."""
    if raw is None:
        return ()
    if isinstance(raw, str):
        # A single bare string is allowed as shorthand.
        token = raw.strip()
        return (token,) if token else ()
    if not isinstance(raw, (list, tuple)):
        return ()
    parsed: list[str] = []
    for item in raw:
        token = str(item).strip()
        if token:
            parsed.append(token)
    return tuple(parsed)


def audit_capabilities(declared: tuple[str, ...]) -> CapabilityAudit:
    """Validate ``declared`` against :data:`KNOWN_CAPABILITIES`.
    Returns a :class:`CapabilityAudit` carrying the raw list,
    any unknown tokens, and whether the plugin is operating in
    default-deny mode (empty / missing capabilities)."""
    known = set(KNOWN_CAPABILITIES)
    unknown = tuple(
        token for token in declared if token not in known
    )
    return CapabilityAudit(
        declared=tuple(declared),
        unknown=unknown,
        is_default_deny=len(declared) == 0,
    )


__all__ = [
    "DEFAULT_CAPABILITIES",
    "KNOWN_CAPABILITIES",
    "CapabilityAudit",
    "audit_capabilities",
    "parse_capabilities",
]
