"""Tests for `mythic-vibe graph` subcommands (PH-05 slices 5.5 + 5.6)."""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mythic_vibe_cli.app import build_parser
from mythic_vibe_cli.commands import COMMAND_HANDLERS
from mythic_vibe_cli.context.graph import GraphStore
from mythic_vibe_cli.context.visualize import render_dot, render_mermaid
from mythic_vibe_cli.runtime.slash_commands import BUILTIN_SLASH_COMMANDS


def _seed_graph(root: Path) -> None:
    """Populate the project's graph with a small fixture so the CLI
    subcommands have something to surface."""
    with GraphStore.open(root) as store:
        a = store.upsert_entity("module", "alpha", path="src/alpha.py")
        b = store.upsert_entity("module", "beta", path="src/beta.py")
        store.upsert_entity("decision", "0001-foo")
        store.add_tag(a.id, "cli", weight=2.0)
        store.add_tag(b.id, "cli", weight=1.0)
        store.upsert_edge(a.id, b.id, "references")


# ---- argparse -----------------------------------------------------------


class GraphArgparseTests(unittest.TestCase):
    def test_query_subcommand_parses(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(
            ["graph", "query", "--tag", "cli", "--top-k", "5", "--no-expand"]
        )
        self.assertEqual(ns.command, "graph")
        self.assertEqual(ns.graph_command, "query")
        self.assertEqual(ns.tag, ["cli"])
        self.assertEqual(ns.top_k, 5)
        self.assertTrue(ns.no_expand)

    def test_entity_subcommand_parses(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["graph", "entity", "--kind", "module", "--name", "a"])
        self.assertEqual(ns.graph_command, "entity")
        self.assertEqual(ns.kind, "module")

    def test_edges_subcommand_parses(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["graph", "edges", "--kind", "references"])
        self.assertEqual(ns.graph_command, "edges")

    def test_brief_subcommand_parses(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["graph", "brief", "--phase", "build"])
        self.assertEqual(ns.graph_command, "brief")
        self.assertEqual(ns.phase, "build")

    def test_visualize_default_format_is_mermaid(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["graph", "visualize"])
        self.assertEqual(ns.format, "mermaid")

    def test_visualize_dot_format_accepted(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["graph", "visualize", "--format", "dot"])
        self.assertEqual(ns.format, "dot")


# ---- Dispatch + JSON envelopes ----------------------------------------


class GraphDispatchTests(unittest.TestCase):
    def test_handler_registered(self) -> None:
        from mythic_vibe_cli.commands import cmd_graph_dispatch

        self.assertIs(COMMAND_HANDLERS["graph"], cmd_graph_dispatch)

    def test_unknown_subcommand_user_input_error(self) -> None:
        from mythic_vibe_cli.commands import cmd_graph_dispatch
        from mythic_vibe_cli.exit_codes import USER_INPUT_ERROR

        ns = argparse.Namespace(graph_command="bogus", path=".")
        # write_error goes to stderr; we just care about exit code.
        self.assertEqual(cmd_graph_dispatch(ns), USER_INPUT_ERROR)

    def test_query_json_envelope(self) -> None:
        from mythic_vibe_cli.commands import cmd_graph_query

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_graph(root)
            ns = argparse.Namespace(
                path=str(root),
                tag=["cli"],
                top_k=5,
                no_expand=False,
                json=True,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_graph_query(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["command"], "graph query")
        self.assertEqual(payload["tags"], ["cli"])
        # alpha + beta + the decision (neighbour-of:alpha) → at least 2.
        self.assertGreaterEqual(len(payload["results"]), 2)

    def test_entity_text_lists_filter_match(self) -> None:
        from mythic_vibe_cli.commands import cmd_graph_entity

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_graph(root)
            ns = argparse.Namespace(
                path=str(root),
                kind="module",
                name="",
                name_path="",
                json=False,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_graph_entity(ns)
        rendered = buf.getvalue()
        self.assertIn("alpha", rendered)
        self.assertIn("beta", rendered)

    def test_edges_json_envelope_lists_seeded_edge(self) -> None:
        from mythic_vibe_cli.commands import cmd_graph_edges

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_graph(root)
            ns = argparse.Namespace(
                path=str(root),
                kind="references",
                src_id=0,
                dst_id=0,
                json=True,
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_graph_edges(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(payload["command"], "graph edges")
        self.assertEqual(len(payload["edges"]), 1)
        self.assertEqual(payload["edges"][0]["kind"], "references")

    def test_brief_text_renders_phase(self) -> None:
        from mythic_vibe_cli.commands import cmd_graph_brief

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_graph(root)
            ns = argparse.Namespace(path=str(root), phase="build", json=False)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_graph_brief(ns)
        self.assertIn("Session brief", buf.getvalue())


# ---- Visualize (slice 5.6) --------------------------------------------


class GraphVisualizeTests(unittest.TestCase):
    def test_mermaid_renders_nodes_and_edges(self) -> None:
        with GraphStore.open_in_memory() as store:
            a = store.upsert_entity("module", "alpha")
            b = store.upsert_entity("module", "beta")
            store.upsert_edge(a.id, b.id, "references")
            rendered = render_mermaid(store)
        self.assertIn("graph LR", rendered)
        self.assertIn("module:alpha", rendered)
        self.assertIn("module:beta", rendered)
        self.assertIn("|references|", rendered)

    def test_dot_renders_digraph(self) -> None:
        with GraphStore.open_in_memory() as store:
            a = store.upsert_entity("module", "alpha")
            b = store.upsert_entity("module", "beta")
            store.upsert_edge(a.id, b.id, "references")
            rendered = render_dot(store)
        self.assertIn("digraph mythic", rendered)
        self.assertIn("alpha", rendered)
        self.assertIn('label="references"', rendered)

    def test_focus_node_restricts_subgraph(self) -> None:
        with GraphStore.open_in_memory() as store:
            a = store.upsert_entity("module", "a")
            b = store.upsert_entity("module", "b")
            c = store.upsert_entity("module", "c")
            store.upsert_edge(a.id, b.id, "references")
            store.upsert_edge(b.id, c.id, "references")
            # Focus on a — only a + b should appear; c is two hops away.
            rendered = render_mermaid(store, focus_node=a.id)
        self.assertIn("module:a", rendered)
        self.assertIn("module:b", rendered)
        self.assertNotIn("module:c", rendered)

    def test_visualize_command_emits_mermaid(self) -> None:
        from mythic_vibe_cli.commands import cmd_graph_visualize

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_graph(root)
            ns = argparse.Namespace(
                path=str(root), format="mermaid", node=0
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_graph_visualize(ns)
        rendered = buf.getvalue()
        self.assertIn("graph LR", rendered)
        self.assertIn("module:alpha", rendered)


class GraphSlashCatalogTests(unittest.TestCase):
    def test_slash_catalog_contains_graph(self) -> None:
        names = {entry.name for entry in BUILTIN_SLASH_COMMANDS}
        self.assertIn("graph", names)

    def test_tui_runner_forwards_path_for_graph(self) -> None:
        from mythic_vibe_cli.tui.runner import command_for_builtin

        with tempfile.TemporaryDirectory() as tmp:
            spec = command_for_builtin("graph", project_root=Path(tmp))
        self.assertIn("--path", spec.argv)
        self.assertIn(str(Path(tmp)), spec.argv)


if __name__ == "__main__":
    unittest.main()
