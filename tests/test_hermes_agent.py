"""Hermes Agent — TCL (in-process) tests.

Covers the H.0 core data model + the H.1 default tool registry
+ the HermesAgent wrapper. The HTTP API surface is tested
separately in test_hermes_http.py.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.agent_api import (
    HermesAgent,
    HermesCore,
    Invocation,
    InvocationResult,
    ToolSpec,
    build_default_agent,
)
from mythic_vibe_cli.agent_api.core import (
    _safe_serialise,
    _validate_against_schema,
)


class SafeSerialiseTests(unittest.TestCase):
    def test_primitives_pass_through(self) -> None:
        for value in (None, True, 42, 1.5, "hello"):
            self.assertEqual(_safe_serialise(value), value)

    def test_path_serialises_to_string(self) -> None:
        self.assertEqual(_safe_serialise(Path("/tmp/x")), str(Path("/tmp/x")))

    def test_dict_recurses(self) -> None:
        self.assertEqual(
            _safe_serialise({"k": Path("/x"), "n": 1}),
            {"k": str(Path("/x")), "n": 1},
        )

    def test_list_recurses(self) -> None:
        self.assertEqual(_safe_serialise([1, "a", Path("/x")]), [1, "a", str(Path("/x"))])

    def test_max_depth_truncates(self) -> None:
        deep = {"k": {"k": {"k": {"k": {"k": "leaf"}}}}}
        result = _safe_serialise(deep, max_depth=2)
        # At depth 2 the inner value gets truncated.
        self.assertIn("truncated", json.dumps(result))

    def test_to_dict_method_used(self) -> None:
        class Obj:
            def to_dict(self):
                return {"hello": "world"}
        self.assertEqual(_safe_serialise(Obj()), {"hello": "world"})

    def test_unserialisable_falls_back_safely(self) -> None:
        class Weird:
            def __repr__(self):
                return "<weird>"
        result = _safe_serialise(Weird())
        # Either the json.dumps(default=str) path or the
        # unserialisable fallback is acceptable.
        self.assertIsInstance(result, str)


class ValidateAgainstSchemaTests(unittest.TestCase):
    def test_missing_required_arg(self) -> None:
        errors = _validate_against_schema(
            {"required": ["x"], "properties": {"x": {"type": "string"}}},
            {},
        )
        self.assertTrue(any("missing required arg" in e for e in errors))

    def test_type_mismatch(self) -> None:
        errors = _validate_against_schema(
            {"properties": {"x": {"type": "integer"}}},
            {"x": "not-an-int"},
        )
        self.assertTrue(any("expected integer" in e for e in errors))

    def test_enum_violation(self) -> None:
        errors = _validate_against_schema(
            {"properties": {"x": {"enum": ["a", "b"]}}},
            {"x": "c"},
        )
        self.assertTrue(any("not in allowed enum" in e for e in errors))

    def test_clean_validation(self) -> None:
        errors = _validate_against_schema(
            {
                "required": ["phase"],
                "properties": {
                    "phase": {"type": "string", "enum": ["build", "verify"]},
                },
            },
            {"phase": "build"},
        )
        self.assertEqual(errors, [])


class ToolSpecSerializationTests(unittest.TestCase):
    def test_to_dict_contains_expected_keys(self) -> None:
        spec = ToolSpec(
            name="t",
            description="d",
            input_schema={"type": "object"},
            capabilities=("read",),
            side_effects=("writes x",),
        )
        payload = spec.to_dict()
        for key in ("name", "description", "input_schema", "capabilities", "side_effects"):
            self.assertIn(key, payload)
        json.dumps(payload)


class HermesCoreRegistryTests(unittest.TestCase):
    def test_register_then_invoke(self) -> None:
        core = HermesCore(root=tempfile.gettempdir())
        spec = ToolSpec(
            name="echo",
            description="echo back the args",
            input_schema={"type": "object", "properties": {"msg": {"type": "string"}}, "required": ["msg"]},
        )
        core.register(spec, lambda c, args: InvocationResult(status="ok", value={"echo": args["msg"]}))
        result = core.invoke(Invocation(tool="echo", args={"msg": "hi"}))
        self.assertTrue(result.ok)
        self.assertEqual(result.value, {"echo": "hi"})
        self.assertGreaterEqual(result.elapsed_ms, 0.0)

    def test_register_duplicate_raises(self) -> None:
        core = HermesCore(root=tempfile.gettempdir())
        spec = ToolSpec(name="t", description="", input_schema={"type": "object"})
        core.register(spec, lambda c, a: InvocationResult(status="ok"))
        with self.assertRaises(ValueError):
            core.register(spec, lambda c, a: InvocationResult(status="ok"))

    def test_unknown_tool_returns_unknown_status(self) -> None:
        core = HermesCore(root=tempfile.gettempdir())
        result = core.invoke(Invocation(tool="missing"))
        self.assertEqual(result.status, "unknown_tool")
        self.assertFalse(result.ok)
        self.assertIn("missing", result.error)

    def test_validation_error_returned(self) -> None:
        core = HermesCore(root=tempfile.gettempdir())
        spec = ToolSpec(
            name="t",
            description="",
            input_schema={"required": ["x"], "properties": {"x": {"type": "string"}}},
        )
        core.register(spec, lambda c, a: InvocationResult(status="ok"))
        result = core.invoke(Invocation(tool="t", args={}))
        self.assertEqual(result.status, "validation_error")

    def test_tool_exception_caught_into_error_status(self) -> None:
        core = HermesCore(root=tempfile.gettempdir())

        def boom(c, a):
            raise RuntimeError("boom")

        core.register(
            ToolSpec(name="x", description="", input_schema={"type": "object"}),
            boom,
        )
        result = core.invoke(Invocation(tool="x"))
        self.assertEqual(result.status, "error")
        self.assertIn("RuntimeError", result.error)
        self.assertIn("boom", result.error)

    def test_list_tools_alphabetical(self) -> None:
        core = HermesCore(root=tempfile.gettempdir())
        core.register(
            ToolSpec(name="zeta", description="", input_schema={"type": "object"}),
            lambda c, a: InvocationResult(status="ok"),
        )
        core.register(
            ToolSpec(name="alpha", description="", input_schema={"type": "object"}),
            lambda c, a: InvocationResult(status="ok"),
        )
        names = [s.name for s in core.list_tools()]
        self.assertEqual(names, ["alpha", "zeta"])


class DefaultAgentTests(unittest.TestCase):
    """The build_default_agent factory + curated tool surface."""

    def test_factory_returns_hermes_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            self.assertIsInstance(agent, HermesAgent)
            self.assertEqual(agent.root, Path(tmp).resolve())

    def test_default_tool_set_contains_expected_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            names = {t["name"] for t in agent.list_tools()}
        for required in (
            "status", "doctor", "drift", "state_show",
            "checkin", "packet_create", "packet_lint",
            "verify", "reflect", "review_architecture",
            "ai_recommend", "provenance_verify",
            "workflow_lineage", "persona_show", "plugin_doctor",
            "read_artifact", "list_artifacts", "recent_events",
        ):
            self.assertIn(required, names, f"missing tool: {required}")

    def test_every_tool_has_capabilities_declared(self) -> None:
        """v1.0: every Hermes tool MUST declare its capabilities
        so operators auditing via plugin doctor see the surface
        accurately."""
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            for tool in agent.list_tools():
                self.assertIsInstance(
                    tool["capabilities"], list,
                    f"{tool['name']}: capabilities missing",
                )
                # Every tool reads at minimum.
                self.assertIn(
                    "read", tool["capabilities"],
                    f"{tool['name']}: should declare 'read' capability at minimum",
                )

    def test_tool_specs_are_json_serialisable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            payload = agent.list_tools()
        json.dumps(payload)


class DefaultToolBehaviourTests(unittest.TestCase):
    """Smoke tests on the curated tool implementations against
    a fresh empty project root."""

    def test_status_returns_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            payload = agent.status()
        self.assertIn("summary", payload)

    def test_doctor_returns_ok_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            payload = agent.doctor()
        for key in ("ok", "errors", "warnings", "sections"):
            self.assertIn(key, payload)

    def test_drift_returns_findings_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            result = agent.invoke("drift")
        self.assertTrue(result.ok)
        # drift returns a dict with 'findings' or 'by_category' depending on dashboard flag.
        self.assertIsInstance(result.value, dict)

    def test_drift_dashboard_returns_rollup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            result = agent.invoke("drift", dashboard=True)
        self.assertTrue(result.ok)
        self.assertIn("by_category", result.value)

    def test_state_show_when_no_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            payload = agent.state()
        self.assertFalse(payload["found"])

    def test_read_artifact_refuses_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            result = agent.invoke("read_artifact", path="../../../etc/passwd")
        self.assertEqual(result.status, "error")
        self.assertIn("escape", result.error.lower())

    def test_list_artifacts_handles_missing_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            payload = agent.list_artifacts(under="nonexistent_dir")
        self.assertFalse(payload["exists"])
        self.assertEqual(payload["entries"], [])

    def test_persona_show_returns_none_when_unset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            payload = agent.invoke("persona_show").value
        self.assertIsNone(payload["preset"])

    def test_review_architecture_returns_governance_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            payload = agent.invoke("review_architecture").value
        for key in ("governance_files", "adr_count", "drift_total", "open_questions"):
            self.assertIn(key, payload)

    def test_ai_recommend_returns_recommendations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            payload = agent.invoke(
                "ai_recommend", task="Build a CLI", top=2
            ).value
        self.assertIn("recommendations", payload)
        self.assertEqual(payload["top_n"], 2)

    def test_recent_events_handles_empty_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            # Trigger one event by invoking another tool.
            agent.status()
            payload = agent.invoke("recent_events", limit=5).value
        self.assertIn("entries", payload)
        # The status() invocation above wrote an audit event.
        self.assertGreater(payload["count"], 0)

    def test_audit_emission_writes_event_log(self) -> None:
        """Every Hermes invocation must append one event-log
        line so operators see exactly what an agent did."""
        with tempfile.TemporaryDirectory() as tmp:
            agent = build_default_agent(root=tmp)
            agent.invoke("status")
            log = Path(tmp) / "mythic" / "events.jsonl"
            self.assertTrue(log.exists())
            content = log.read_text(encoding="utf-8")
            self.assertIn("hermes_invoke", content)


if __name__ == "__main__":
    unittest.main()
