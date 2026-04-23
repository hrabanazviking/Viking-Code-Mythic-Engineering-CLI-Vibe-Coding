"""
Graph Weaver: Data Ingestion & Graph Construction Engine
========================================================

Evolves the legacy ChartIntelligence by parsing structured local files
and weaving them into a NetworkX Directed Acyclic Graph (DAG) in memory.
"""

import logging
import yaml
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import networkx as nx
except ImportError:
    nx = None
    logging.warning("NetworkX not installed. GraphWeaver requires networkx>=3.1")

from yggdrasil.cognition.contracts import EntityContextNode, CausalLink
from systems.crash_reporting import CrashReporter

logger = logging.getLogger(__name__)


class LoreIngestionEngine:
    """
    Traverses data directories, parsing files and weaving them into a networkx DAG.
    """

    def __init__(self, data_path: str, crash_reporter: Optional[CrashReporter] = None):
        self.data_path = Path(data_path)
        self.crash_reporter = crash_reporter

        # We use a MultiDiGraph to allow multiple directed edges between the same two nodes
        # (e.g., A might be a quest_prerequisite for B, and also have a blood_debt to B).
        if nx:
            self.graph = nx.MultiDiGraph()
        else:
            self.graph = None
            logger.error("GraphWeaver cannot initialize without NetworkX.")

        self._parsed_files_count = 0
        self._failed_files_count = 0

    def build_graph(self) -> bool:
        """
        Main entry point to build the in-memory knowledge graph.
        Parses data/charts/, data/world/, and data/quests/.
        """
        if self.graph is None:
            return False

        logger.info("[WEAVER] Starting graph construction from %s...", self.data_path)

        directories_to_scan = [
            self.data_path / "charts",
            self.data_path / "world",
            self.data_path / "quests",
            self.data_path
            / "characters",  # Also ingest characters for social ledger ties
        ]

        for directory in directories_to_scan:
            if not directory.exists() or not directory.is_dir():
                logger.debug(f"[WEAVER] Skipping missing directory: {directory}")
                continue

            for filepath in directory.rglob("*"):
                if filepath.is_file() and filepath.suffix in [
                    ".yaml",
                    ".yml",
                    ".json",
                    ".md",
                ]:
                    self._parse_and_ingest_file(filepath)

        logger.info(
            "[WEAVER] Graph construction complete. Nodes: %d, Edges: %d. Parsed files: %d (Failed: %d)",
            self.graph.number_of_nodes(),
            self.graph.number_of_edges(),
            self._parsed_files_count,
            self._failed_files_count,
        )
        return True

    def _parse_and_ingest_file(self, filepath: Path):
        """Parses a single file and extracts entities and causal links."""
        try:
            filename = filepath.name
            parent_dir = filepath.parent.name

            if filepath.suffix in [".yaml", ".yml"]:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data:
                    self._process_structured_data(
                        filepath.stem, data, parent_dir, str(filepath)
                    )
            elif filepath.suffix == ".json":
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data:
                    self._process_structured_data(
                        filepath.stem, data, parent_dir, str(filepath)
                    )
            elif filepath.suffix == ".md":
                self._process_markdown_file(filepath)

            self._parsed_files_count += 1

        except Exception as e:
            self._failed_files_count += 1
            logger.error(f"[WEAVER] Error parsing file {filepath}: {e}")
            if self.crash_reporter:
                self.crash_reporter.report_event(
                    "lore_ingestion_error",
                    {"file": str(filepath), "error": str(e)},
                    severity="warning",
                )

    def _process_structured_data(
        self, root_name: str, data: Any, category: str, source_path: str
    ):
        """
        Processes parsed YAML/JSON dicts/lists.
        Creates Entity Nodes and extracts relationships based on nested structures or naming conventions.
        """
        if isinstance(data, dict):
            # E.g., elder_futhark.yaml has {"runes": [...]}
            # Or quest_causality_templates.yaml has {"version": 1, "templates": [...]}

            # Look for top-level lists of entities
            for key, value in data.items():
                if (
                    isinstance(value, list)
                    and len(value) > 0
                    and isinstance(value[0], dict)
                ):
                    for item in value:
                        self._ingest_entity_item(
                            item,
                            source_category=f"{category}/{key}",
                            source_path=source_path,
                        )
                elif isinstance(value, dict):
                    # Nested dict might represent relationships or a sub-entity
                    self._ingest_entity_item(
                        {"id": key, **value},
                        source_category=category,
                        source_path=source_path,
                    )
                    # Add edge from root schema file to this entity (macro connection)
                    self._add_edge(
                        root_name, key, relationship_type="contains_definition"
                    )

            # If the dict itself has an 'id' or 'name', treat the whole file as one entity
            if "id" in data or "name" in data:
                self._ingest_entity_item(
                    data, source_category=category, source_path=source_path
                )

        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    self._ingest_entity_item(
                        item, source_category=category, source_path=source_path
                    )

    def _ingest_entity_item(
        self, item: Dict[str, Any], source_category: str, source_path: str
    ):
        """Adds a specific dict as a node and recursively searches for links."""
        entity_id = str(item.get("id") or item.get("name") or "")
        if not entity_id:
            return

        entity_name = str(item.get("name") or entity_id)

        # Normalize ID slightly
        entity_id = entity_id.lower().replace(" ", "_").strip()

        # Add node
        if not self.graph.has_node(entity_id):
            self.graph.add_node(
                entity_id,
                name=entity_name,
                category=source_category,
                source=source_path,
                raw_data=json.dumps(
                    item
                ),  # Store raw JSON string natively in NetworkX attributes
            )
        else:
            # Merge data if it exists
            existing_raw = self.graph.nodes[entity_id].get("raw_data", "{}")
            try:
                existing_dict = json.loads(existing_raw)
                existing_dict.update(item)
                self.graph.nodes[entity_id]["raw_data"] = json.dumps(existing_dict)
            except json.JSONDecodeError:
                pass

        # Extract relationships (The Causal Links)
        self._extract_relationships(entity_id, item)

    def _extract_relationships(self, source_id: str, item: Dict[str, Any]):
        """
        Scans data dictionaries for fields that imply a connection to another entity.
        Creates directed edges in the MultiDiGraph.
        """
        # Common keys that indicate relationships
        relationship_keys = {
            "prerequisites": "quest_prerequisite",
            "depends_on": "dependency",
            "allies": "alliance",
            "enemies": "blood_feud",
            "debts": "blood_debt",
            "location": "located_in",
            "faction": "faction_member",
            "runes": "associated_rune",
            "nodes": "quest_node_sequence",  # specific to quest causality templates
            "recovery_paths": "recovery_path",
        }

        for key, rel_type in relationship_keys.items():
            if key in item:
                targets = item[key]
                if isinstance(targets, str):
                    targets = [targets]
                if isinstance(targets, list):
                    for idx, target in enumerate(targets):
                        if isinstance(target, str):
                            target_id = target.lower().replace(" ", "_").strip()

                            # If it's a sequence, maybe link A -> B -> C
                            if key == "nodes" and idx > 0:
                                prev_target_id = (
                                    targets[idx - 1].lower().replace(" ", "_").strip()
                                )
                                self._add_edge(prev_target_id, target_id, rel_type)
                            else:
                                self._add_edge(source_id, target_id, rel_type)

                        elif isinstance(target, dict) and (
                            "id" in target or "name" in target
                        ):
                            target_id = (
                                str(target.get("id") or target.get("name"))
                                .lower()
                                .replace(" ", "_")
                                .strip()
                            )
                            self._add_edge(source_id, target_id, rel_type)

    def _add_edge(
        self, source: str, target: str, relationship_type: str, context: str = ""
    ):
        """Adds a directed edge between two nodes, creating missing nodes on-the-fly."""
        if not source or not target:
            return

        if not self.graph.has_node(source):
            self.graph.add_node(
                source,
                name=source,
                category="implicit",
                source="implicit_link",
                raw_data="{}",
            )
        if not self.graph.has_node(target):
            self.graph.add_node(
                target,
                name=target,
                category="implicit",
                source="implicit_link",
                raw_data="{}",
            )

        self.graph.add_edge(
            source,
            target,
            relationship_type=relationship_type,
            historical_context=context,
        )

    def _process_markdown_file(self, filepath: Path):
        """
        Parses Markdown files. Extracts YAML frontmatter for metadata,
        and uses Markdown headers (##) to infer relationship categories.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            entity_name = filepath.stem
            metadata = {}

            # Simple frontmatter parsing
            frontmatter_match = re.match(
                r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL
            )
            if frontmatter_match:
                try:
                    metadata = yaml.safe_load(frontmatter_match.group(1)) or {}
                    content = content[frontmatter_match.end() :]
                except yaml.YAMLError:
                    pass

            # Extract distinct headers
            sections = re.split(r"\n(#{1,3})\s+(.+)", content)

            item_data = {
                "name": entity_name,
                "type": metadata.get("type", "lore_document"),
                "era": metadata.get("era", "unknown"),
                "summary": content[:500]
                if len(sections) <= 1
                else sections[0][:500],  # First text block as summary
            }

            # Map headers to relationships
            current_header = None
            for i in range(1, len(sections), 3):
                if i + 2 < len(sections):
                    header_level = sections[i]
                    header_text = sections[i + 1].strip().lower()
                    section_content = sections[i + 2].strip()

                    if (
                        "relation" in header_text
                        or "allies" in header_text
                        or "enemies" in header_text
                    ):
                        # Very naive extraction of bolded names or bullet points in relation sections
                        links = re.findall(r"\*\*(.*?)\*\*", section_content)
                        bullets = re.findall(
                            r"^-\s+(.*?)(?:$|\n)", section_content, re.MULTILINE
                        )

                        rel_type = (
                            "historical_alliance"
                            if "allies" in header_text
                            else "historical_conflict"
                        )
                        if "enemies" in header_text:
                            rel_type = "blood_feud"

                        targets = set(links + bullets)
                        if targets:
                            item_data[rel_type] = list(targets)

            self._ingest_entity_item(
                item_data, source_category="markdown_lore", source_path=str(filepath)
            )

        except Exception as e:
            logger.warning(f"[WEAVER] Failed to parse Markdown {filepath}: {e}")

    def extract_subgraph_context(
        self, target_entity: str, depth: int = 2
    ) -> List[EntityContextNode]:
        """
        Pulls the local neighborhood around a given target_entity using NetworkX ego_graph.
        Formats data directly into Pydantic contracts.
        """
        if not self.graph:
            return []

        normalized_target = target_entity.lower().replace(" ", "_").strip()

        # If target doesn't exist directly, try fuzzy matching
        if not self.graph.has_node(normalized_target):
            # Try finding a node where the name contains the target
            matches = [
                n for n in self.graph.nodes if normalized_target in str(n).lower()
            ]
            if not matches:
                # One more attempt: check if target is in the node's 'name' attribute
                matches = [
                    n
                    for n, attr in self.graph.nodes(data=True)
                    if normalized_target in str(attr.get("name", "")).lower()
                ]

            if not matches:
                logger.debug(
                    f"[WEAVER] Target entity '{target_entity}' not found in graph."
                )
                return []

            # Pick the shortest matching ID as the most likely root
            normalized_target = min(matches, key=len)

        try:
            # Pull the neighborhood graph up to `depth` distance
            # Using undirected logic to get both incoming and outgoing dependencies
            subgraph = nx.ego_graph(
                self.graph, normalized_target, radius=depth, undirected=True
            )

            context_nodes = []

            for node_id in subgraph.nodes:
                node_data = subgraph.nodes[node_id]

                # Calculate simple relevance score based on shortest path length
                try:
                    path_len = nx.shortest_path_length(
                        subgraph, source=normalized_target, target=node_id
                    )
                    # Score decays by depth: 1.0 (self), 0.75 (dist 1), 0.5 (dist 2)
                    relevance = max(0.25, 1.0 - (path_len * 0.25))
                except nx.NetworkXNoPath:
                    relevance = 0.5

                # Build causal links originating FROM this node in the subgraph
                causal_links = []
                for _, adj_target, key, edge_data in subgraph.out_edges(
                    node_id, keys=True, data=True
                ):
                    causal_links.append(
                        CausalLink(
                            source_entity=str(node_id),
                            target_entity=str(adj_target),
                            relationship_type=edge_data.get(
                                "relationship_type", "unknown_link"
                            ),
                            historical_context=edge_data.get("historical_context", ""),
                        )
                    )

                # Fetch social ledger data (Stubbed for now, normally queries SocialLedgerEngine)
                # In actual integration, you would query systems.social_ledger here
                social_ledger_info = {}
                try:
                    raw_dict = json.loads(node_data.get("raw_data", "{}"))
                    if "honor" in raw_dict or "debt" in raw_dict:
                        social_ledger_info = {
                            "honor": int(raw_dict.get("honor", 0)),
                            "debt": int(raw_dict.get("debt", 0)),
                        }
                except (json.JSONDecodeError, ValueError):
                    pass

                context_node = EntityContextNode(
                    entity_name=node_data.get("name", str(node_id)),
                    relevance_score=relevance,
                    causal_links=causal_links,
                    social_ledger_summary=social_ledger_info,
                    raw_content=node_data.get("raw_data", ""),
                )
                context_nodes.append(context_node)

            # Sort by relevance
            context_nodes.sort(key=lambda x: x.relevance_score, reverse=True)
            return context_nodes

        except Exception as e:
            logger.error(
                f"[WEAVER] Failed to extract subgraph for {target_entity}: {e}"
            )
            return []
