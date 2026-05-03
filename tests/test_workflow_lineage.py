"""Phase 20.C (audit remediation 2026-05-03) — workflow lineage
tests.

Two layers:

- **Pure data builder** — seed a forge ledger directly (via
  ``ForgeLedger.append``), call ``build_lineage`` and inspect
  the resulting graph.
- **Markdown rendering** — `render_markdown` produces a
  Mermaid `flowchart LR` block plus a caption table.
- **CLI integration** — `workflow lineage` text + JSON paths
  through `cmd_workflow_dispatch`.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.exit_codes import SUCCESS
from mythic_vibe_cli.forge_ledger import ForgeLedger, ForgeLedgerEntry
from mythic_vibe_cli.workflow_agents import AgentInput, AgentOutput
from mythic_vibe_cli.workflow_lineage import (
    build_lineage,
    render_markdown,
)


def _seed_ledger(root: Path, workflow_id: str) -> None:
    """Write a small fixture ledger with three steps."""
    ledger = ForgeLedger(root)
    steps = [
        ("STEP-01", "Skald",       "succeeded"),
        ("STEP-02", "Architect",   "succeeded"),
        ("STEP-03", "Forge Worker", "failed"),
    ]
    for step_id, role, status in steps:
        agent_input = AgentInput(
            role=role,
            task="Test task",
            phase="build",
            workflow_id=workflow_id,
            workflow_step_id=step_id,
        )
        agent_output = (
            AgentOutput(
                role=role,
                timestamp="2026-05-03T10:01:00Z",
                workflow_id=workflow_id,
                workflow_step_id=step_id,
                summary=f"summary for {role}",
                raw_response=f"raw response from {role}",
            )
            if status == "succeeded"
            else None
        )
        entry = ForgeLedgerEntry(
            workflow_id=workflow_id,
            step_id=step_id,
            role=role,
            status=status,
            started_at=f"2026-05-03T10:00:{step_id[-2:]}Z",
            completed_at=f"2026-05-03T10:01:{step_id[-2:]}Z",
            duration_ms=60_000,
            agent_input=agent_input,
            agent_output=agent_output,
            notes=(),
        )
        ledger.append(entry)


class BuildLineageTests(unittest.TestCase):
    def test_returns_none_for_empty_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            graph = build_lineage(Path(tmp), workflow_id=None)
        self.assertIsNone(graph)

    def test_returns_none_for_unknown_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_ledger(Path(tmp), "WF-AAA")
            graph = build_lineage(Path(tmp), workflow_id="WF-NONEXISTENT")
        self.assertIsNone(graph)

    def test_resolves_latest_when_id_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_ledger(Path(tmp), "WF-AAA")
            graph = build_lineage(Path(tmp), workflow_id=None)
        self.assertIsNotNone(graph)
        self.assertEqual(graph.workflow_id, "WF-AAA")
        self.assertEqual(len(graph.steps), 3)

    def test_steps_sorted_by_step_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_ledger(Path(tmp), "WF-AAA")
            graph = build_lineage(Path(tmp), workflow_id="WF-AAA")
        self.assertEqual(
            [s.step_id for s in graph.steps],
            ["STEP-01", "STEP-02", "STEP-03"],
        )

    def test_terminal_status_is_last_step_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_ledger(Path(tmp), "WF-AAA")
            graph = build_lineage(Path(tmp), workflow_id="WF-AAA")
        self.assertEqual(graph.terminal_status, "failed")

    def test_summary_extracted_from_agent_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_ledger(Path(tmp), "WF-AAA")
            graph = build_lineage(Path(tmp), workflow_id="WF-AAA")
        skald_step = graph.steps[0]
        self.assertIn("Skald", skald_step.summary)


class RenderMarkdownTests(unittest.TestCase):
    def test_contains_mermaid_block_and_caption_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_ledger(Path(tmp), "WF-RENDER")
            graph = build_lineage(Path(tmp), workflow_id="WF-RENDER")
        markdown = render_markdown(graph)
        self.assertIn("```mermaid", markdown)
        self.assertIn("flowchart LR", markdown)
        self.assertIn("WF-RENDER", markdown)
        # Caption table.
        self.assertIn("| Step | Role | Status | Duration | Summary |", markdown)
        # Three step rows.
        for step_id in ("STEP-01", "STEP-02", "STEP-03"):
            self.assertIn(step_id, markdown)

    def test_status_styling_emitted_for_known_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_ledger(Path(tmp), "WF-STYLE")
            graph = build_lineage(Path(tmp), workflow_id="WF-STYLE")
        markdown = render_markdown(graph)
        # At least one `style ... fill:` line per status type
        # we wrote into _STATUS_STYLES.
        self.assertIn("style STEP_01 fill:#a4d4a4", markdown)  # succeeded
        self.assertIn("style STEP_03 fill:#f4a4a4", markdown)  # failed


class LineageGraphSerializationTests(unittest.TestCase):
    def test_to_dict_includes_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_ledger(Path(tmp), "WF-SER")
            graph = build_lineage(Path(tmp), workflow_id="WF-SER")
        payload = graph.to_dict()
        self.assertEqual(len(payload["edges"]), 2)  # 3 steps -> 2 edges
        self.assertEqual(payload["edges"][0]["from"], "STEP-01")
        self.assertEqual(payload["edges"][0]["to"], "STEP-02")
        json.dumps(payload)


class CmdWorkflowLineageIntegrationTests(unittest.TestCase):
    def _run(self, ns: argparse.Namespace) -> tuple[int, str]:
        from mythic_vibe_cli.commands import cmd_workflow_lineage

        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = cmd_workflow_lineage(ns)
        finally:
            sys.stdout = original
        return code, captured.getvalue()

    def test_text_output_contains_mermaid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_ledger(Path(tmp), "WF-CLI")
            code, output = self._run(argparse.Namespace(
                path=tmp, workflow="", json=False,
            ))
        self.assertEqual(code, SUCCESS)
        self.assertIn("flowchart LR", output)

    def test_json_output_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_ledger(Path(tmp), "WF-CLI-JSON")
            code, output = self._run(argparse.Namespace(
                path=tmp, workflow="WF-CLI-JSON", json=True,
            ))
            payload = json.loads(output)
        self.assertEqual(code, SUCCESS)
        self.assertTrue(payload["found"])
        self.assertEqual(payload["workflow_id"], "WF-CLI-JSON")
        self.assertEqual(len(payload["steps"]), 3)

    def test_empty_ledger_returns_success_with_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(argparse.Namespace(
                path=tmp, workflow="", json=False,
            ))
        self.assertEqual(code, SUCCESS)
        self.assertIn("No workflows found", output)

    def test_unknown_workflow_in_json_returns_found_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_ledger(Path(tmp), "WF-EXISTS")
            code, output = self._run(argparse.Namespace(
                path=tmp, workflow="WF-MISSING", json=True,
            ))
            payload = json.loads(output)
        self.assertEqual(code, SUCCESS)
        self.assertFalse(payload["found"])


if __name__ == "__main__":
    unittest.main()
