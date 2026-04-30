"""Tests for the packet retriever integration (PH-05 slice 5.7)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.context.graph import GraphStore
from mythic_vibe_cli.context.packet_context import (
    DEFAULT_PACKET_CONTEXT_BUDGET,
    DEFAULT_PACKET_CONTEXT_TOP_K,
    TRUNCATION_NOTE,
    build_graph_context_section,
    derive_packet_tags,
)


class DerivePacketTagsTests(unittest.TestCase):
    def test_extracts_alphanumeric_tokens_in_order(self) -> None:
        tags = derive_packet_tags("build", "Forge Worker", "Refactor router")
        self.assertEqual(tags, ["build", "forge", "worker", "refactor", "router"])

    def test_drops_short_tokens(self) -> None:
        tags = derive_packet_tags("a b core")
        self.assertEqual(tags, ["core"])

    def test_dedups_preserving_first_seen(self) -> None:
        tags = derive_packet_tags("build", "build_pipeline", "build")
        # "build" appears once; "build_pipeline" splits to "build_pipeline"
        # since underscores are kept in the regex.
        self.assertIn("build", tags)
        self.assertEqual(tags.count("build"), 1)

    def test_empty_input_returns_empty(self) -> None:
        self.assertEqual(derive_packet_tags(), [])
        self.assertEqual(derive_packet_tags("", None, ""), [])  # type: ignore[arg-type]

    def test_punctuation_splits_tokens(self) -> None:
        tags = derive_packet_tags("packet/builder.py:cmd_codex_pack")
        for required in {"packet", "builder", "cmd_codex_pack"}:
            self.assertIn(required, tags)


class BuildGraphContextSectionTests(unittest.TestCase):
    def _seed(self, root: Path) -> None:
        with GraphStore.open(root) as store:
            a = store.upsert_entity(
                "module", "alpha", path="src/alpha.py"
            )
            b = store.upsert_entity(
                "module", "beta", path="src/beta.py"
            )
            store.upsert_entity("decision", "0001-foo")
            store.add_tag(a.id, "alpha", weight=2.0)
            store.add_tag(a.id, "router", weight=1.5)
            store.add_tag(b.id, "alpha", weight=1.0)

    def test_missing_graph_file_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                build_graph_context_section(Path(tmp), tags=["alpha"]),
                "",
            )

    def test_empty_graph_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with GraphStore.open(root):
                pass  # creates the file but no entities
            self.assertEqual(
                build_graph_context_section(root, tags=["alpha"]),
                "",
            )

    def test_empty_tags_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed(root)
            self.assertEqual(
                build_graph_context_section(root, tags=[]),
                "",
            )

    def test_no_matches_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed(root)
            self.assertEqual(
                build_graph_context_section(root, tags=["nonexistent"]),
                "",
            )

    def test_populated_graph_returns_markdown_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed(root)
            rendered = build_graph_context_section(root, tags=["alpha"])
        self.assertIn("## Relevant Graph Context", rendered)
        self.assertIn("alpha", rendered)
        # Score is rendered to two decimals.
        self.assertIn("score", rendered)
        # Path is appended for entities that have one.
        self.assertIn("src/alpha.py", rendered)

    def test_truncates_when_budget_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with GraphStore.open(root) as store:
                # Seed 50 entities sharing a tag so the rendered section
                # is long.
                for i in range(50):
                    e = store.upsert_entity(
                        "module", f"mod_{i:03d}", path=f"src/mod_{i:03d}.py"
                    )
                    store.add_tag(e.id, "bigtag", weight=1.0)
            rendered = build_graph_context_section(
                root, tags=["bigtag"], budget=400
            )
        self.assertLessEqual(len(rendered), 400)
        self.assertIn(TRUNCATION_NOTE.strip(), rendered)

    def test_zero_budget_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed(root)
            self.assertEqual(
                build_graph_context_section(
                    root, tags=["alpha"], budget=0
                ),
                "",
            )

    def test_constants_are_documented(self) -> None:
        self.assertEqual(DEFAULT_PACKET_CONTEXT_BUDGET, 12000)
        self.assertEqual(DEFAULT_PACKET_CONTEXT_TOP_K, 10)


class CodexBridgeIntegrationTests(unittest.TestCase):
    """Slice 5.7 wires `build_graph_context_section` into the codex
    bridge — packets in projects with a populated graph carry a new
    `## Relevant Graph Context` section, packets in fresh projects
    are unchanged."""

    def _build_minimal_project(self, root: Path) -> None:
        for relpath in (
            "mythic/status.json",
            "mythic/plan.md",
            "mythic/loop.md",
            "tasks/current_GOALS.md",
            "docs/ARCHITECTURE.md",
            "SYSTEM_VISION.md",
        ):
            target = root / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            if relpath.endswith(".json"):
                target.write_text("{}\n", encoding="utf-8")
            else:
                target.write_text(
                    f"# {target.name}\nMinimal scaffold.\n",
                    encoding="utf-8",
                )

    def test_packet_without_graph_has_no_graph_context_section(self) -> None:
        from mythic_vibe_cli.codex_bridge import CodexBridge, CodexPacketRequest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._build_minimal_project(root)
            bridge = CodexBridge(root)
            packet_path = bridge.create_packet(
                request=CodexPacketRequest(
                    task="refactor router",
                    phase="build",
                    audience="advanced",
                    role="Forge Worker",
                    output_format="markdown",
                )
            )
            content = Path(packet_path).read_text(encoding="utf-8")

        self.assertNotIn("## Relevant Graph Context", content)

    def test_packet_with_populated_graph_has_section(self) -> None:
        from mythic_vibe_cli.codex_bridge import CodexBridge, CodexPacketRequest

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._build_minimal_project(root)
            with GraphStore.open(root) as store:
                module = store.upsert_entity(
                    "module", "router", path="src/router.py"
                )
                store.add_tag(module.id, "router", weight=2.0)
                store.add_tag(module.id, "build", weight=1.0)

            bridge = CodexBridge(root)
            packet_path = bridge.create_packet(
                request=CodexPacketRequest(
                    task="refactor router",
                    phase="build",
                    audience="advanced",
                    role="Forge Worker",
                    output_format="markdown",
                )
            )
            content = Path(packet_path).read_text(encoding="utf-8")

        self.assertIn("## Relevant Graph Context", content)
        self.assertIn("router", content)


if __name__ == "__main__":
    unittest.main()
