"""Reference plugin for the Mythic Vibe CLI.

Exercises every plugin extension point + every event-bus hook.
Operators can install this in editable mode to confirm the
plugin pipeline works end-to-end:

    pip install -e examples/plugins/mythic_vibe_example_plugin
    mythic-vibe plugin discover
    mythic-vibe plugin install mythic_vibe_example
    mythic-vibe plugin inspect mythic_vibe_example

Plugin authors should treat this file as a starting template —
copy, rename, edit. The PLUGIN_AUTHORING_GUIDE.md walkthrough
references each section here.

This plugin's hooks intentionally do nothing significant: they
just append a log line to ``./mythic/plugins/example.log`` so
operators can confirm hooks fired. No external deps, no network,
no surprising side-effects.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable


__version__ = "0.1.0"


# ---- Helpers ---------------------------------------------------------


def _log_dir(payload: dict[str, Any]) -> Path:
    """Resolve the project's mythic/plugins/ directory from the
    payload's ``path`` field, with a defensive fallback to cwd."""
    project_root = payload.get("path") if isinstance(payload, dict) else None
    if not project_root:
        project_root = os.getcwd()
    return Path(str(project_root)) / "mythic" / "plugins"


def _append_log(payload: dict[str, Any], hook: str) -> None:
    """Append a one-line entry to the plugin log. Best-effort —
    swallow any exception so plugin hooks never crash the host."""
    try:
        log_dir = _log_dir(payload)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "example.log"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(f"{hook}\n")
    except Exception:  # noqa: BLE001 — never crash the host
        pass


# ---- The plugin object ----------------------------------------------


class ExamplePlugin:
    """Reference plugin instance. The ``plugin`` symbol exported
    below is what the entry-point ``mythic_vibe_example_plugin:plugin``
    resolves to.

    Implements every extension-point Protocol from
    :mod:`mythic_vibe_cli.plugins.extension_points` AND every hook
    in :data:`mythic_vibe_cli.plugins.api.PLUGIN_HOOKS`.
    """

    MYTHIC_HOOKS = [
        "before_scan",
        "after_scan",
        "before_packet",
        "after_packet",
        "before_verify",
        "after_verify",
        "before_reflect",
        "after_reflect",
    ]

    __version__ = __version__

    # ---- Hooks -------------------------------------------------------

    def before_scan(self, payload: dict[str, Any]) -> None:
        _append_log(payload, "before_scan")

    def after_scan(self, payload: dict[str, Any]) -> None:
        _append_log(payload, "after_scan")

    def before_packet(self, payload: dict[str, Any]) -> None:
        _append_log(payload, "before_packet")

    def after_packet(self, payload: dict[str, Any]) -> None:
        _append_log(payload, "after_packet")

    def before_verify(self, payload: dict[str, Any]) -> None:
        _append_log(payload, "before_verify")

    def after_verify(self, payload: dict[str, Any]) -> None:
        _append_log(payload, "after_verify")

    def before_reflect(self, payload: dict[str, Any]) -> None:
        _append_log(payload, "before_reflect")

    def after_reflect(self, payload: dict[str, Any]) -> None:
        _append_log(payload, "after_reflect")

    # ---- Extension points -------------------------------------------

    def rituals(self) -> Iterable[str]:
        """RitualPlugin contribution. The example plugin doesn't
        actually register new ritual flows; this just demonstrates
        the contract surface."""
        return ["example_ritual"]

    def providers(self) -> dict[str, Any]:
        """ProviderPlugin contribution. Returns an empty dict —
        adding a real provider requires implementing the
        AIProvider Protocol, which the reference plugin keeps out
        of scope so it stays a documentation example, not a
        working router."""
        return {}

    def scanner_rules(self) -> Iterable[Any]:
        """ScannerPlugin contribution. Empty rule set — same
        reasoning as providers()."""
        return []

    def verification_gates(self) -> dict[str, Any]:
        """VerificationGatePlugin contribution — one always-pass
        gate for demonstration."""
        return {"example.always_pass": _example_gate}

    def artifact_templates(self) -> dict[str, Any]:
        """ArtifactTemplatePlugin contribution — one minimal
        markdown template."""
        return {
            "example_artefact": (
                "# {title}\n\n"
                "Example artefact body. Plugin: mythic_vibe_example_plugin "
                f"v{__version__}.\n"
            ),
        }

    def slash_commands(self) -> Iterable[Any]:
        """SlashCommandPlugin contribution. Returns one
        :class:`SlashCommandInfo` so operators can see plugin-
        contributed slashes via ``/slash list``.

        The import is local so installing the plugin doesn't
        require the CLI to already be on sys.path at import time
        (useful for sdist test environments).
        """
        try:
            from mythic_vibe_cli.runtime.slash_commands import (  # type: ignore[import-not-found]
                SlashCommandInfo,
            )
            from mythic_vibe_cli.runtime.source_info import (  # type: ignore[import-not-found]
                SourceInfo,
            )
        except ImportError:
            return []
        return [
            SlashCommandInfo(
                name="example",
                source="plugin",
                source_info=SourceInfo(
                    path="mythic_vibe_example_plugin",
                    source="plugin:mythic_vibe_example_plugin",
                    scope="user",
                    origin="package",
                ),
                description="Reference plugin's slash command.",
                argv=("status", "--path", "."),
            ),
        ]


def _example_gate(plan: Any, agent_input: Any, agent_output: Any, root: Any) -> Any:
    """Always-pass verification gate. Imports VerificationResult
    locally so the plugin module's import doesn't fail when the
    CLI isn't installed."""
    try:
        from mythic_vibe_cli.workflow_agents import (  # type: ignore[import-not-found]
            VerificationResult,
        )
    except ImportError:
        # Plugin gate runners returning None gracefully degrade
        # via the run_auditor_gates contract.
        return None
    return VerificationResult(
        name="example.always_pass",
        passed=True,
        detail="reference plugin always-pass gate",
    )


# Module-level singleton — what the entry-point resolves to.
plugin = ExamplePlugin()


__all__ = ["ExamplePlugin", "plugin"]
