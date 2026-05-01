"""Plugin extension points (PH-10 Slice 10.3).

Typed :class:`Protocol` classes that define the six categories of
plugin contribution. These are **descriptive** contracts —
runtime dispatch happens through the existing event-bus hooks
plus the slice 2.6 ``slash_commands`` discovery convention.
A plugin "implements" an extension point by either:

- being structurally compatible (duck-typed), or
- inheriting from / declaring conformance to the Protocol so
  static type checkers can verify the surface.

All Protocols are :func:`runtime_checkable` so plugin authors can
``isinstance(obj, RitualPlugin)`` for self-checks.

Six extension points (matches master roadmap PH-10 spec):

1. :class:`RitualPlugin` — adds new ritual / phase commands or
   hooks into existing rituals.
2. :class:`ProviderPlugin` — registers a new
   :class:`mythic_vibe_cli.ai.providers.base.AIProvider`.
3. :class:`ScannerPlugin` — adds custom rules to
   :mod:`mythic_vibe_cli.context.scanner`.
4. :class:`VerificationGatePlugin` — adds a custom Auditor gate
   to :mod:`mythic_vibe_cli.forge_verifier`.
5. :class:`ArtifactTemplatePlugin` — declares new artefact
   templates for ``mythic/templates/``.
6. :class:`SlashCommandPlugin` — declares new ``/slashname``
   commands (already used in PH-02 slice 2.6).

Cross-platform: pure stdlib.
"""

from __future__ import annotations

from typing import Any, Iterable, Protocol, runtime_checkable


# Extension-point category names — used by tests and the
# inspection layer to enumerate which categories a plugin
# satisfies.
EXTENSION_POINT_CATEGORIES: tuple[str, ...] = (
    "ritual",
    "provider",
    "scanner",
    "verification_gate",
    "artifact_template",
    "slash_command",
)


@runtime_checkable
class RitualPlugin(Protocol):
    """Plugin that contributes new ritual/phase commands.

    A ritual plugin declares one or more lifecycle hooks
    (``before_*`` / ``after_*`` per :data:`PLUGIN_HOOKS`) plus an
    optional ``rituals()`` method returning the named rituals it
    implements. Rituals are operator-facing flows like ``init``,
    ``checkin``, ``reflect``.
    """

    def rituals(self) -> Iterable[str]:
        """Iterable of ritual names this plugin contributes."""
        ...


@runtime_checkable
class ProviderPlugin(Protocol):
    """Plugin that registers a new AI provider with the
    :class:`mythic_vibe_cli.ai.registry.ProviderRegistry`.

    The plugin exposes a ``providers()`` method returning
    ``dict[str, AIProvider]``. The CLI merges these into the
    canonical registry at startup; conflicting names raise a
    clear error rather than silently overwriting."""

    def providers(self) -> dict[str, Any]:
        """Mapping of ``provider_name -> AIProvider instance``."""
        ...


@runtime_checkable
class ScannerPlugin(Protocol):
    """Plugin that contributes context-scanner rules.

    The plugin exposes a ``scanner_rules()`` method returning an
    iterable of typed rule descriptors. The scanner layer applies
    these alongside the built-in rules (binary detection, doc
    classification, etc.)."""

    def scanner_rules(self) -> Iterable[Any]:
        """Iterable of scanner-rule descriptors."""
        ...


@runtime_checkable
class VerificationGatePlugin(Protocol):
    """Plugin that contributes Auditor verification gates.

    Each gate is a callable matching the
    :data:`mythic_vibe_cli.forge_verifier.GateRunner` signature.
    The plugin exposes ``verification_gates()`` returning
    ``dict[str, GateRunner]``. Operators opt into individual
    gates via the existing ``run_auditor_gates(gates=...)`` kwarg.
    """

    def verification_gates(self) -> dict[str, Any]:
        """Mapping of ``gate_name -> GateRunner callable``."""
        ...


@runtime_checkable
class ArtifactTemplatePlugin(Protocol):
    """Plugin that contributes artefact templates.

    The plugin exposes ``artifact_templates()`` returning a
    mapping of ``template_name -> template_body_or_path``. When
    a template body is a string, it is used verbatim; when it is
    a Path, the file's contents are read at template-application
    time.
    """

    def artifact_templates(self) -> dict[str, Any]:
        """Mapping of ``template_name -> body_or_path``."""
        ...


@runtime_checkable
class SlashCommandPlugin(Protocol):
    """Plugin that contributes slash commands.

    Already exercised by PH-02 slice 2.6 — plugins expose a
    ``slash_commands()`` callable returning an iterable of
    :class:`mythic_vibe_cli.runtime.slash_commands.SlashCommandInfo`.
    The dispatcher's ``discover_slash_commands()`` merges these
    into the global slash-command catalogue.
    """

    def slash_commands(self) -> Iterable[Any]:
        """Iterable of :class:`SlashCommandInfo` items."""
        ...


def categorise_plugin(plugin_obj: Any) -> list[str]:
    """Return every extension-point category a plugin satisfies.

    Uses ``isinstance(obj, ProtocolClass)`` (each Protocol is
    runtime_checkable). Categories are returned in the canonical
    :data:`EXTENSION_POINT_CATEGORIES` order, deduplicated.
    """
    matches: list[str] = []
    if isinstance(plugin_obj, RitualPlugin):
        matches.append("ritual")
    if isinstance(plugin_obj, ProviderPlugin):
        matches.append("provider")
    if isinstance(plugin_obj, ScannerPlugin):
        matches.append("scanner")
    if isinstance(plugin_obj, VerificationGatePlugin):
        matches.append("verification_gate")
    if isinstance(plugin_obj, ArtifactTemplatePlugin):
        matches.append("artifact_template")
    if isinstance(plugin_obj, SlashCommandPlugin):
        matches.append("slash_command")
    return matches


__all__ = [
    "ArtifactTemplatePlugin",
    "EXTENSION_POINT_CATEGORIES",
    "ProviderPlugin",
    "RitualPlugin",
    "ScannerPlugin",
    "SlashCommandPlugin",
    "VerificationGatePlugin",
    "categorise_plugin",
]
