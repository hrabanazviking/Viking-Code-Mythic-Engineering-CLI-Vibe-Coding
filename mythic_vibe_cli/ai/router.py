"""Provider routing table (PH-08 slice 8.1).

Declarative ``(role, task_type, hardware) -> (provider, model)``
resolver. The router itself is **pure** — given a table, a role,
a task type, and an optional hardware profile, it returns a
:class:`RouteDecision` describing the chosen provider, the rule
that matched, and an ordered fallback chain. Slice 8.3 owns the
runtime that actually invokes the chosen provider; slice 8.4
owns the CLI surface.

Defaults vs overrides:

- :meth:`RoutingTable.from_default` returns the built-in rules
  covering the six Mythic roles plus a generic catch-all.
- :meth:`RoutingTable.load` overlays
  ``<root>/mythic/ai/routing.json`` on top of the defaults — the
  file is a list of rule dicts in the same shape as
  :meth:`RoutingRule.to_dict`. Operators can drop the file in to
  steer routing without editing source.

Predicate semantics:

- ``role`` and ``task_type`` accept either an exact string or
  ``"*"`` (wildcard).
- ``min_ram_mb`` / ``min_logical_cpus`` are checked against the
  supplied :class:`HardwareProfile`. When no hardware is given,
  the predicates pass (a router that doesn't know the host can't
  block on hardware shape).
- ``prefer_local`` is a soft signal — when True the rule still
  applies even if its provider isn't local, but the rule's
  ``priority`` is bumped if the registry resolves the provider
  to an Ollama / local backend.

Rule selection:

- Walk rules in order; first match wins.
- A rule "matches" when every predicate passes.
- :meth:`RoutingTable.from_default` orders rules from most
  specific (per-role + role-fit hardware floor) down to the
  catch-all.

Cross-platform: stdlib only (``json``, ``pathlib``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..hardware import HardwareProfile
from ..runtime.paths import paths_for


ROUTING_FILE_DIR = ("mythic", "ai")
ROUTING_FILENAME = "routing.json"


# ---- Data layer --------------------------------------------------------


@dataclass(frozen=True)
class RoutingRule:
    """One row of the routing table.

    ``role`` and ``task_type`` accept ``"*"`` for "any". Hardware
    floors are optional — 0 means "no requirement". ``fallbacks``
    is an ordered tuple of provider names the runtime tries when
    the primary fails.
    """

    role: str = "*"
    task_type: str = "*"
    min_ram_mb: int = 0
    min_logical_cpus: int = 0
    prefer_local: bool = False
    provider: str = "copy-paste"
    model: str = ""
    fallbacks: tuple[str, ...] = ()
    description: str = ""

    def matches(
        self,
        *,
        role: str,
        task_type: str,
        hardware: HardwareProfile | None,
    ) -> bool:
        if self.role != "*" and self.role != role:
            return False
        if self.task_type != "*" and self.task_type != task_type:
            return False
        if hardware is not None:
            if self.min_ram_mb and hardware.ram_total_mb:
                if hardware.ram_total_mb < self.min_ram_mb:
                    return False
            if self.min_logical_cpus and hardware.logical_cpus:
                if hardware.logical_cpus < self.min_logical_cpus:
                    return False
        return True

    def reason(
        self,
        *,
        role: str,
        task_type: str,
        hardware: HardwareProfile | None,
    ) -> str:
        """One-line explanation of why this rule did/didn't match.
        Used by the slice 8.4 ``--explain`` output."""
        parts: list[str] = []
        parts.append(f"role={self.role!r}")
        parts.append(f"task_type={self.task_type!r}")
        if self.min_ram_mb:
            parts.append(f"min_ram_mb={self.min_ram_mb}")
        if self.min_logical_cpus:
            parts.append(f"min_cpus={self.min_logical_cpus}")
        if self.prefer_local:
            parts.append("prefer_local")
        verdict = (
            "match"
            if self.matches(role=role, task_type=task_type, hardware=hardware)
            else "skip"
        )
        return f"{verdict}: " + ", ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "task_type": self.task_type,
            "min_ram_mb": self.min_ram_mb,
            "min_logical_cpus": self.min_logical_cpus,
            "prefer_local": self.prefer_local,
            "provider": self.provider,
            "model": self.model,
            "fallbacks": list(self.fallbacks),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RoutingRule":
        fallbacks = payload.get("fallbacks") or ()
        if not isinstance(fallbacks, (list, tuple)):
            fallbacks = ()
        return cls(
            role=str(payload.get("role", "*")),
            task_type=str(payload.get("task_type", "*")),
            min_ram_mb=int(payload.get("min_ram_mb", 0) or 0),
            min_logical_cpus=int(payload.get("min_logical_cpus", 0) or 0),
            prefer_local=bool(payload.get("prefer_local", False)),
            provider=str(payload.get("provider", "copy-paste")),
            model=str(payload.get("model", "")),
            fallbacks=tuple(str(name) for name in fallbacks),
            description=str(payload.get("description", "")),
        )


@dataclass(frozen=True)
class RouteDecision:
    """Result of :func:`route`. The runtime in slice 8.3 consumes
    ``provider`` first; ``fallbacks`` is the ordered chain to walk
    on failure. ``reasons`` lists every rule the router considered
    so ``ai route --explain`` can render a debuggable trace."""

    provider: str
    model: str
    rule_matched: RoutingRule | None
    fallbacks: tuple[str, ...]
    reasons: tuple[str, ...] = field(default_factory=tuple)
    role: str = ""
    task_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "rule_matched": (
                self.rule_matched.to_dict()
                if self.rule_matched is not None
                else None
            ),
            "fallbacks": list(self.fallbacks),
            "reasons": list(self.reasons),
            "role": self.role,
            "task_type": self.task_type,
        }


# ---- Defaults ----------------------------------------------------------


DEFAULT_RULES: tuple[RoutingRule, ...] = (
    # Forge worker — code generation on a beefy box prefers Anthropic
    # Sonnet for quality; falls back to OpenAI then copy-paste.
    RoutingRule(
        role="Forge Worker",
        task_type="*",
        min_ram_mb=16_000,
        provider="anthropic",
        model="claude-sonnet-4",
        fallbacks=("openai", "copy-paste"),
        description="Forge Worker on >=16 GB RAM hosts: Anthropic Sonnet",
    ),
    # Forge worker on smaller hosts — defer to local Ollama if any.
    RoutingRule(
        role="Forge Worker",
        task_type="*",
        prefer_local=True,
        provider="ollama",
        model="llama3.2",
        fallbacks=("copy-paste",),
        description="Forge Worker on small hosts: local Ollama",
    ),
    # Architect / Auditor — quality-sensitive; lean on Claude.
    RoutingRule(
        role="Architect",
        task_type="*",
        provider="anthropic",
        model="claude-sonnet-4",
        fallbacks=("openai", "copy-paste"),
        description="Architect: Anthropic Sonnet",
    ),
    RoutingRule(
        role="Auditor",
        task_type="*",
        provider="anthropic",
        model="claude-sonnet-4",
        fallbacks=("openai", "copy-paste"),
        description="Auditor: Anthropic Sonnet",
    ),
    # Cartographer / Skald / Scribe — narrative work; OpenAI default.
    RoutingRule(
        role="Cartographer",
        task_type="*",
        provider="openai",
        model="gpt-4o-mini",
        fallbacks=("anthropic", "copy-paste"),
        description="Cartographer: OpenAI gpt-4o-mini",
    ),
    RoutingRule(
        role="Skald",
        task_type="*",
        provider="openai",
        model="gpt-4o-mini",
        fallbacks=("anthropic", "copy-paste"),
        description="Skald: OpenAI gpt-4o-mini",
    ),
    RoutingRule(
        role="Scribe",
        task_type="*",
        provider="openai",
        model="gpt-4o-mini",
        fallbacks=("anthropic", "copy-paste"),
        description="Scribe: OpenAI gpt-4o-mini",
    ),
    # Catch-all — always-available copy-paste mode.
    RoutingRule(
        role="*",
        task_type="*",
        provider="copy-paste",
        model="manual",
        fallbacks=(),
        description="Catch-all fallback: copy-paste",
    ),
)


@dataclass
class RoutingTable:
    """Ordered list of :class:`RoutingRule`. First match wins."""

    rules: list[RoutingRule] = field(default_factory=list)

    @classmethod
    def from_default(cls) -> "RoutingTable":
        return cls(rules=list(DEFAULT_RULES))

    @classmethod
    def load(cls, root: Path) -> "RoutingTable":
        """Build a table from the project's
        ``mythic/ai/routing.json`` overlay (if present), prepended
        to the default rules so overrides take precedence. The
        project ``config.yaml`` can also provide
        ``ai.router.routing_rules``; those rules are prepended before
        the JSON overlay so the human-edited root config wins.

        Errors are best-effort: missing file → defaults only;
        unparseable file → defaults only with no warning to avoid
        crashing the CLI. Future PH-14 (Policy Engine) might add a
        loud config-validation surface."""
        table = cls.from_default()
        config_overrides: list[RoutingRule] = []
        try:
            from ..config import ConfigStore

            loaded = ConfigStore(root).load()
            for entry in loaded.config.ai_routing_rules:
                config_overrides.append(RoutingRule.from_dict(entry))
        except Exception:  # noqa: BLE001 - routing should degrade to defaults
            config_overrides = []

        path = paths_for(root).routing_file
        if not path.is_file():
            return cls(rules=config_overrides + table.rules)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls(rules=config_overrides + table.rules)
        if not isinstance(payload, list):
            return cls(rules=config_overrides + table.rules)
        overrides: list[RoutingRule] = []
        for entry in payload:
            if isinstance(entry, dict):
                overrides.append(RoutingRule.from_dict(entry))
        # Overrides come first so a user rule shadows a default with
        # the same predicates.
        return cls(rules=config_overrides + overrides + table.rules)

    def to_dict(self) -> dict[str, Any]:
        return {"rules": [rule.to_dict() for rule in self.rules]}


# ---- Routing ----------------------------------------------------------


def route(
    table: RoutingTable,
    *,
    role: str,
    task_type: str = "*",
    hardware: HardwareProfile | None = None,
) -> RouteDecision:
    """Walk ``table.rules`` in order and return the first match.

    Always returns a :class:`RouteDecision` — the catch-all
    ``copy-paste`` rule shipped in :data:`DEFAULT_RULES` makes a
    fall-through impossible. ``reasons`` accumulates one entry per
    rule for debuggable traces.
    """
    reasons: list[str] = []
    for rule in table.rules:
        reasons.append(rule.reason(role=role, task_type=task_type, hardware=hardware))
        if rule.matches(role=role, task_type=task_type, hardware=hardware):
            return RouteDecision(
                provider=rule.provider,
                model=rule.model,
                rule_matched=rule,
                fallbacks=rule.fallbacks,
                reasons=tuple(reasons),
                role=role,
                task_type=task_type,
            )
    # Defensive: if no rule matched (shouldn't happen with the
    # default catch-all), fall through to copy-paste.
    return RouteDecision(
        provider="copy-paste",
        model="manual",
        rule_matched=None,
        fallbacks=(),
        reasons=tuple(reasons + ["fallback: no rule matched, using copy-paste"]),
        role=role,
        task_type=task_type,
    )


__all__ = [
    "DEFAULT_RULES",
    "ROUTING_FILE_DIR",
    "ROUTING_FILENAME",
    "RouteDecision",
    "RoutingRule",
    "RoutingTable",
    "route",
]
