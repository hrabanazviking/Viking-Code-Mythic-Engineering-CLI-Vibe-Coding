"""Hermes TCL — Tool Calling Library (Python in-process surface).

The Pythonic face of Hermes. Wraps :class:`HermesCore` with
ergonomic methods so an in-process agent can write::

    from mythic_vibe_cli.agent_api import HermesAgent

    agent = HermesAgent(root="/path/to/project")
    agent.status()
    agent.checkin(phase="build", update="...")
    agent.invoke("packet_create", task="...", phase="build", role="Forge Worker")

The curated tool surface is built by :func:`build_default_agent`.
Each tool is a hand-validated wrapper over a high-value CLI
operation; the JSON Schema is what an external tool-calling
agent (Anthropic Tool Use, OpenAI function calling, etc.) sees.

Capability declarations follow the PH-20.3 vocabulary so
operators auditing via ``mythic-vibe plugin doctor`` see what
Hermes can actually touch.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .core import HermesCore, Invocation, InvocationResult, ToolSpec


# ---------------------------------------------------------------------------
# Tool implementations — each is a small wrapper around an existing
# command/handler. They MUST NOT raise into HermesCore.invoke()
# (the invoker catches everything anyway, but tools should still
# be defensive).
# ---------------------------------------------------------------------------


def _result(value: Any = None) -> InvocationResult:
    return InvocationResult(status="ok", value=value)


def _error(error: str) -> InvocationResult:
    return InvocationResult(status="error", error=error)


def _build_namespace(args: dict[str, Any], **defaults: Any) -> argparse.Namespace:
    """Build an argparse-shaped Namespace from a tool-args dict
    plus defaults. CLI handlers expect an argparse Namespace;
    this lets us reuse them without rebuilding their logic."""
    merged = {**defaults, **args}
    return argparse.Namespace(**merged)


def _tool_status(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..workflow import MythicWorkflow

    workflow = MythicWorkflow(core.root)
    return _result({
        "summary": workflow.status_summary(),
        "path": str(core.root),
    })


def _tool_doctor(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..workflow import MythicWorkflow

    workflow = MythicWorkflow(core.root)
    repo_boundary = bool(args.get("repo_boundary", False))
    report = workflow.doctor_report(
        repo_boundary=repo_boundary,
        project_scaffold=not repo_boundary,
    )
    return _result({
        "ok": bool(report["ok"]),
        "errors": list(report["errors"]),
        "warnings": list(report["warnings"]),
        "sections": report["sections"],
        "repo_boundary": repo_boundary,
    })


def _tool_drift(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..drift import build_dashboard_payload, scan_for_drift, to_payload

    findings = scan_for_drift(core.root)
    if args.get("dashboard"):
        return _result(build_dashboard_payload(findings))
    return _result(to_payload(findings))


def _tool_state_show(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..persistence.json_store import JsonStateStore

    store = JsonStateStore(core.root)
    payload = store.read_payload()
    if payload is None:
        return _result({
            "found": False,
            "path": str(store.status_path),
        })
    return _result({"found": True, "path": str(store.status_path), **payload})


def _tool_checkin(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..workflow import MythicWorkflow

    workflow = MythicWorkflow(core.root)
    try:
        status_file, devlog_file = workflow.check_in(
            phase=str(args["phase"]),
            update=str(args["update"]),
        )
    except ValueError as exc:
        return _error(str(exc))
    return _result({
        "status_path": str(status_file),
        "devlog_path": str(devlog_file),
        "summary": workflow.status_summary(),
    })


def _tool_packet_create(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..codex_bridge import CodexPacketRequest, PacketBuilder

    builder = PacketBuilder(core.root)
    request = CodexPacketRequest(
        task=str(args["task"]),
        phase=str(args["phase"]),
        role=str(args.get("role", "Forge Worker")),
        audience=str(args.get("audience", "advanced")),
        output_format=str(args.get("format", "markdown")),
    )
    try:
        path = builder.create_packet(request)
    except (ValueError, OSError) as exc:
        return _error(f"{type(exc).__name__}: {exc}")
    return _result({
        "packet_path": str(path),
        "task": request.task,
        "phase": request.phase,
        "role": request.role,
    })


def _tool_packet_lint(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..packet_lint import lint_packet_text

    file_arg = args.get("file")
    if file_arg:
        target = Path(file_arg)
        if not target.is_absolute():
            target = (core.root / target).resolve()
        if not target.is_file():
            return _error(f"packet file not found: {target}")
        try:
            text = target.read_text(encoding="utf-8")
        except OSError as exc:
            return _error(f"cannot read {target}: {exc}")
        report = lint_packet_text(text)
        return _result({"source": str(target), **report.to_dict()})

    return _error(
        "packet_lint: provide 'file' arg with the packet markdown path"
    )


def _tool_verify(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    """Verify wrapper. Calls cmd_verify with the requested gate
    selection. Captures stdout for the agent."""
    import io
    import sys

    from .. import commands as cli_commands

    ns = _build_namespace(
        args,
        path=str(core.root),
        commands=bool(args.get("commands", True)),
        changed_files=bool(args.get("changed_files", False)),
        docs=bool(args.get("docs", False)),
        invariants=bool(args.get("invariants", False)),
        record=bool(args.get("record", False)),
        json=True,
        replay=False,
    )
    captured = io.StringIO()
    original = sys.stdout
    sys.stdout = captured
    try:
        code = cli_commands.cmd_verify(ns)
    finally:
        sys.stdout = original
    text = captured.getvalue()
    import json as _json
    try:
        payload = _json.loads(text) if text.strip() else {}
    except (ValueError, _json.JSONDecodeError):
        payload = {"raw_output": text}
    return _result({"exit_code": code, **payload})


def _tool_reflect(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..handoff import build_handoff_record, write_handoff_record

    record = build_handoff_record(
        core.root,
        objective=str(args.get("objective", "")) or None,
        next_step=str(args.get("next_step", "")) or None,
        note=str(args.get("note", "")) or None,
        session_type=str(args.get("session_type", "reflect")),
    )
    md_path, json_path = write_handoff_record(core.root, record)
    return _result({
        "handoff_id": record.handoff_id,
        "markdown_path": str(md_path),
        "json_path": str(json_path),
        "next_recommended_action": record.next_steps[0] if record.next_steps else None,
    })


def _tool_review_architecture(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..architecture_review import build_review_report

    report = build_review_report(core.root)
    return _result(report.to_dict())


def _tool_ai_recommend(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..ai.recommend import RecommendationCriteria, recommend_models

    criteria = RecommendationCriteria(
        task=str(args.get("task", "")),
        max_context=int(args.get("max_context", 0) or 0),
        vision_required=bool(args.get("vision", False)),
        cost_class=args.get("cost_class") or None,
        family=args.get("family") or None,
    )
    top_n = int(args.get("top", 3) or 3)
    recs = recommend_models(criteria, top_n=top_n)
    return _result({
        "criteria": criteria.to_dict(),
        "top_n": top_n,
        "recommendations": [r.to_dict() for r in recs],
    })


def _tool_provenance_verify(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..plunder.verify import verify_provenance

    report = verify_provenance(core.root)
    return _result(report.to_dict())


def _tool_workflow_lineage(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..workflow_lineage import build_lineage

    workflow_id = (args.get("workflow") or "") or None
    graph = build_lineage(core.root, workflow_id=workflow_id)
    if graph is None:
        return _result({
            "found": False,
            "workflow_id": workflow_id or "",
        })
    return _result({"found": True, **graph.to_dict()})


def _tool_persona_show(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..personas import load_active_persona

    state = load_active_persona(core.root)
    return _result(state.to_dict())


def _tool_plugin_doctor(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..plugins.capabilities import audit_capabilities
    from ..plugins.registry import PluginRegistry

    registry = PluginRegistry(core.root)
    rows: list[dict[str, Any]] = []
    for record in registry.list(include_disabled=True):
        cap_audit = audit_capabilities(tuple(record.capabilities))
        rows.append({
            "entrypoint": record.entrypoint,
            "enabled": record.enabled,
            "version": record.version,
            "hooks": list(record.hooks),
            "capabilities": cap_audit.to_dict(),
        })
    return _result({"plugins": rows})


def _tool_read_artifact(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    relpath = str(args["path"])
    target = (core.root / relpath).resolve()
    # Defence: refuse to escape the project root.
    try:
        target.relative_to(core.root)
    except ValueError:
        return _error(f"path escapes project root: {relpath!r}")
    if not target.is_file():
        return _error(f"file not found: {relpath}")
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _error(f"cannot read {relpath}: {exc}")
    max_bytes = int(args.get("max_bytes", 65_536))
    truncated = False
    if len(text) > max_bytes:
        text = text[:max_bytes]
        truncated = True
    return _result({
        "path": relpath,
        "bytes": len(text),
        "truncated": truncated,
        "content": text,
    })


def _tool_list_artifacts(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    under = str(args.get("under", "mythic"))
    target = (core.root / under).resolve()
    try:
        target.relative_to(core.root)
    except ValueError:
        return _error(f"path escapes project root: {under!r}")
    if not target.is_dir():
        return _result({"under": under, "exists": False, "entries": []})
    entries: list[dict[str, Any]] = []
    glob_pattern = str(args.get("glob", "**/*"))
    limit = int(args.get("limit", 200))
    for path in sorted(target.glob(glob_pattern)):
        if not path.is_file():
            continue
        rel = path.relative_to(core.root)
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        entries.append({
            "path": str(rel).replace("\\", "/"),
            "bytes": size,
        })
        if len(entries) >= limit:
            break
    return _result({
        "under": under,
        "glob": glob_pattern,
        "exists": True,
        "count": len(entries),
        "entries": entries,
    })


def _tool_recent_events(core: HermesCore, args: dict[str, Any]) -> InvocationResult:
    from ..runtime.event_log import event_log_path_for, read_recent

    limit = int(args.get("limit", 20))
    log_path = event_log_path_for(core.root)
    entries = read_recent(log_path, limit=limit)
    return _result({
        "log_path": str(log_path),
        "count": len(entries),
        "entries": [e.to_dict() for e in entries],
    })


# ---------------------------------------------------------------------------
# Tool registry — every entry above gets a hand-written ToolSpec
# with JSON Schema input + capability + side-effect declarations.
# ---------------------------------------------------------------------------


def _default_tools() -> list[tuple[ToolSpec, Any]]:
    return [
        (
            ToolSpec(
                name="status",
                description="Return the current Mythic project status summary.",
                input_schema={"type": "object", "properties": {}, "required": []},
                capabilities=("read",),
            ),
            _tool_status,
        ),
        (
            ToolSpec(
                name="doctor",
                description="Run project diagnostics (errors / warnings / sections).",
                input_schema={
                    "type": "object",
                    "properties": {
                        "repo_boundary": {
                            "type": "boolean",
                            "description": "Run repo-boundary checks instead of project-scaffold checks.",
                        }
                    },
                    "required": [],
                },
                capabilities=("read",),
            ),
            _tool_doctor,
        ),
        (
            ToolSpec(
                name="drift",
                description="Scan for docs<->code drift. Set 'dashboard' true for the rolled-up scorecard.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "dashboard": {"type": "boolean"},
                    },
                    "required": [],
                },
                capabilities=("read",),
            ),
            _tool_drift,
        ),
        (
            ToolSpec(
                name="state_show",
                description="Read the schema-versioned project state from mythic/status.json.",
                input_schema={"type": "object", "properties": {}, "required": []},
                capabilities=("read",),
            ),
            _tool_state_show,
        ),
        (
            ToolSpec(
                name="checkin",
                description="Log a Mythic phase update and advance tracking. Writes mythic/status.json + docs/DEVLOG.md.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "phase": {
                            "type": "string",
                            "enum": [
                                "intent", "constraints", "architecture",
                                "plan", "build", "verify", "reflect",
                            ],
                        },
                        "update": {"type": "string", "description": "Short progress update."},
                    },
                    "required": ["phase", "update"],
                },
                capabilities=("read", "file-write"),
                side_effects=("writes mythic/status.json", "appends docs/DEVLOG.md"),
            ),
            _tool_checkin,
        ),
        (
            ToolSpec(
                name="packet_create",
                description="Create a reusable packet artifact under mythic/packets/.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "phase": {
                            "type": "string",
                            "enum": [
                                "intent", "constraints", "architecture",
                                "plan", "build", "verify", "reflect",
                            ],
                        },
                        "role": {"type": "string"},
                        "audience": {"type": "string"},
                        "format": {"type": "string", "enum": ["markdown", "json"]},
                    },
                    "required": ["task", "phase"],
                },
                capabilities=("read", "file-write"),
                side_effects=("writes mythic/packets/PKT-NNNNNN.{md,json,meta.json}",),
            ),
            _tool_packet_create,
        ),
        (
            ToolSpec(
                name="packet_lint",
                description="Run the heuristic packet-quality linter against an explicit file.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file": {"type": "string", "description": "Project-relative or absolute path to the packet markdown."},
                    },
                    "required": ["file"],
                },
                capabilities=("read",),
            ),
            _tool_packet_lint,
        ),
        (
            ToolSpec(
                name="verify",
                description="Run verification gates (commands / changed-files / docs / invariants) and optionally record the artifact.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "commands": {"type": "boolean"},
                        "changed_files": {"type": "boolean"},
                        "docs": {"type": "boolean"},
                        "invariants": {"type": "boolean"},
                        "record": {"type": "boolean", "description": "Promote the verification artifact to latest.json."},
                    },
                    "required": [],
                },
                capabilities=("read", "subprocess", "file-write"),
                side_effects=(
                    "writes mythic/verifications/VER-*.json",
                    "may run pytest / ruff / mypy via subprocess",
                ),
            ),
            _tool_verify,
        ),
        (
            ToolSpec(
                name="reflect",
                description="Create a reflection handoff record for the current session.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "objective": {"type": "string"},
                        "next_step": {"type": "string"},
                        "note": {"type": "string"},
                        "session_type": {"type": "string", "enum": ["reflect", "implementation", "refactor", "documentation", "investigation", "triage"]},
                    },
                    "required": [],
                },
                capabilities=("read", "file-write"),
                side_effects=("writes mythic/handoffs/HND-*.{md,json}",),
            ),
            _tool_reflect,
        ),
        (
            ToolSpec(
                name="review_architecture",
                description="Quarterly architecture review checklist (read-only governance audit).",
                input_schema={"type": "object", "properties": {}, "required": []},
                capabilities=("read",),
            ),
            _tool_review_architecture,
        ),
        (
            ToolSpec(
                name="ai_recommend",
                description="Pure-policy DSL scoring catalog models against task constraints. Zero provider calls.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "max_context": {"type": "integer"},
                        "vision": {"type": "boolean"},
                        "cost_class": {"type": "string", "enum": ["cheap", "standard", "premium"]},
                        "family": {"type": "string"},
                        "top": {"type": "integer"},
                    },
                    "required": [],
                },
                capabilities=("read",),
            ),
            _tool_ai_recommend,
        ),
        (
            ToolSpec(
                name="provenance_verify",
                description="Verify SHA-256 of every plunder-imported file against recorded provenance.",
                input_schema={"type": "object", "properties": {}, "required": []},
                capabilities=("read",),
            ),
            _tool_provenance_verify,
        ),
        (
            ToolSpec(
                name="workflow_lineage",
                description="Render one workflow's per-step graph from forge_ledger.json.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "workflow": {"type": "string", "description": "Workflow id; default = most recent in ledger."},
                    },
                    "required": [],
                },
                capabilities=("read",),
            ),
            _tool_workflow_lineage,
        ),
        (
            ToolSpec(
                name="persona_show",
                description="Show the active operator persona (or none if no preset is applied).",
                input_schema={"type": "object", "properties": {}, "required": []},
                capabilities=("read",),
            ),
            _tool_persona_show,
        ),
        (
            ToolSpec(
                name="plugin_doctor",
                description="Audit installed plugins: declared capabilities + unknown-token warnings.",
                input_schema={"type": "object", "properties": {}, "required": []},
                capabilities=("read",),
            ),
            _tool_plugin_doctor,
        ),
        (
            ToolSpec(
                name="read_artifact",
                description="Read a project-relative file (refuses paths that escape the project root).",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Project-relative file path."},
                        "max_bytes": {"type": "integer", "description": "Truncation limit (default 65536)."},
                    },
                    "required": ["path"],
                },
                capabilities=("read",),
            ),
            _tool_read_artifact,
        ),
        (
            ToolSpec(
                name="list_artifacts",
                description="List files under a project-relative directory (refuses paths that escape the project root).",
                input_schema={
                    "type": "object",
                    "properties": {
                        "under": {"type": "string", "description": "Project-relative directory (default 'mythic')."},
                        "glob": {"type": "string", "description": "Glob pattern (default '**/*')."},
                        "limit": {"type": "integer", "description": "Max entries (default 200)."},
                    },
                    "required": [],
                },
                capabilities=("read",),
            ),
            _tool_list_artifacts,
        ),
        (
            ToolSpec(
                name="recent_events",
                description="Read recent entries from mythic/events.jsonl.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Max entries (default 20)."},
                    },
                    "required": [],
                },
                capabilities=("read",),
            ),
            _tool_recent_events,
        ),
    ]


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------


def build_default_agent(root: Path | str = ".") -> "HermesAgent":
    """Construct a HermesAgent pre-loaded with the curated default
    tool registry. Most callers want this; advanced callers can
    construct ``HermesCore`` directly and register custom tools."""
    core = HermesCore(root=root)
    for spec, fn in _default_tools():
        core.register(spec, fn)
    return HermesAgent(core)


class HermesAgent:
    """Pythonic wrapper over :class:`HermesCore`. Primary
    in-process surface for an agent. Methods that map to a single
    tool delegate to ``invoke``; convenience methods like
    ``status()`` and ``list_tools()`` provide the most common
    queries without requiring the agent to know tool names.
    """

    def __init__(self, core: HermesCore):
        self.core = core

    @property
    def root(self) -> Path:
        return self.core.root

    def list_tools(self) -> list[dict[str, Any]]:
        """Return JSON-Schema tool descriptors. Suitable for direct
        use as the ``tools`` argument in Anthropic Tool Use or
        OpenAI function calling."""
        return [spec.to_dict() for spec in self.core.list_tools()]

    def has_tool(self, name: str) -> bool:
        return self.core.has_tool(name)

    def invoke(self, tool: str, **args: Any) -> InvocationResult:
        """Run a tool by name. Returns the full
        :class:`InvocationResult` (status / value / error)."""
        return self.core.invoke(Invocation(tool=tool, args=args))

    # -- convenience wrappers (most common queries) ---------------

    def status(self) -> Any:
        return self.invoke("status").value

    def doctor(self, *, repo_boundary: bool = False) -> Any:
        return self.invoke("doctor", repo_boundary=repo_boundary).value

    def state(self) -> Any:
        return self.invoke("state_show").value

    def checkin(self, *, phase: str, update: str) -> Any:
        return self.invoke("checkin", phase=phase, update=update).value

    def reflect(self, **kwargs: Any) -> Any:
        return self.invoke("reflect", **kwargs).value

    def list_artifacts(self, *, under: str = "mythic", **kwargs: Any) -> Any:
        return self.invoke("list_artifacts", under=under, **kwargs).value

    def read_artifact(self, path: str, *, max_bytes: int = 65_536) -> Any:
        return self.invoke("read_artifact", path=path, max_bytes=max_bytes).value

    def recent_events(self, *, limit: int = 20) -> Any:
        return self.invoke("recent_events", limit=limit).value


__all__ = [
    "HermesAgent",
    "build_default_agent",
]
