"""
Muninn - The Memory Raven
=========================

Odin's raven of Memory. Manages the persistent storage and structure
of all knowledge within Yggdrasil.

"I fear for Huginn, that he come not back,
yet more anxious am I for Muninn."

Muninn is the grounding. When the AI starts to drift into
"stochastic panic," Muninn is the weight of accumulated wisdom
that says, "No, this is who we are. Look at the root."

Features:
- Persistent memory storage
- Hierarchical organization
- Self-healing data structures
- Format-agnostic storage
- Sync with Helheim archives
"""

import logging
import json
import yaml
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


@dataclass
class MemoryNode:
    """A node in Muninn's memory tree."""

    id: str
    content: Any
    path: str  # Hierarchical path like "characters/npcs/merchants"
    memory_type: str  # fact, entity, event, relationship, rule
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    importance: int = 5  # 1-10
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "path": self.path,
            "memory_type": self.memory_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "access_count": self.access_count,
            "importance": self.importance,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryNode":
        return cls(
            id=data["id"],
            content=data["content"],
            path=data["path"],
            memory_type=data.get("memory_type", "fact"),
            created_at=datetime.fromisoformat(data["created_at"])
            if "created_at" in data
            else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if "updated_at" in data
            else datetime.now(),
            access_count=data.get("access_count", 0),
            importance=data.get("importance", 5),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


class Muninn:
    """
    The Memory Raven - Persistent Storage and Structure.

    Muninn manages the long-term memory and organizational structure
    of the entire Yggdrasil system. He ensures that when Huginn
    brings back new information, it is properly nested in the right place.

    Features:
    - Hierarchical memory tree
    - Multi-format support (JSON, YAML, Markdown)
    - Self-healing data structures
    - Automatic indexing
    - Sync with Helheim for persistence
    """

    SUPPORTED_FORMATS = ["json", "yaml", "md", "txt"]
    MAX_QUERY_RESULTS = 100

    def __init__(
        self,
        data_path: str = None,
        helheim: "Helheim" = None,
        auto_persist: bool = True,
        dispatcher=None,
    ):
        """
        Initialize Muninn.

        Args:
            data_path: Path to store persistent data
            helheim: Reference to Helheim for deep storage
            auto_persist: Automatically persist changes
        """
        self.data_path = Path(data_path) if data_path else None
        self.helheim = helheim
        self.auto_persist = auto_persist
        self.dispatcher = dispatcher
        self.max_nodes = 20000

        # Memory tree
        self._tree: Dict[str, MemoryNode] = {}  # id -> node
        self._path_index: Dict[str, List[str]] = {}  # path -> [node_ids]
        self._tag_index: Dict[str, List[str]] = {}  # tag -> [node_ids]
        self._type_index: Dict[str, List[str]] = {}  # type -> [node_ids]

        self._lock = threading.RLock()

        # Initialize data directory
        if self.data_path:
            self.data_path.mkdir(parents=True, exist_ok=True)
            self._load_from_disk()

        if self.dispatcher:
            self._setup_event_listeners()

    def _setup_event_listeners(self):
        # Local import to prevent circular dependencies
        from systems.event_dispatcher import EventType

        self.dispatcher.subscribe(EventType.PLAYER_ACTION.value, self._on_player_action)

    def _on_player_action(self, event_type: str, context: Dict[str, Any]):
        """Automatically log player actions into the timeline memory."""
        action = context.get("action", "")
        turn_number = context.get("turn_number", 1)

        if not action:
            return

        self.store(
            content=action,
            path=f"timeline/turn/{turn_number}",
            memory_type="event",
            importance=5,
            tags=["player_action", f"turn_{turn_number}"],
        )

    def _normalize_path(self, path: str) -> str:
        """Normalize memory path to a safe, compact tree path."""
        if not isinstance(path, str):
            return "misc/unknown"
        normalized = re.sub(r"[^a-zA-Z0-9_\-\./]", "_", path.strip())
        normalized = re.sub(r"/+", "/", normalized).strip("/")
        return normalized[:200] if normalized else "misc/unknown"

    def _safe_json(self, value: Any) -> str:
        """Serialize data safely for comparison and hashing."""
        try:
            return json.dumps(value, default=str, sort_keys=True)
        except Exception:
            return repr(value)

    def _apply_backpressure(self):
        """Prevent unbounded growth by pruning lowest-priority old nodes."""
        overflow = len(self._tree) - self.max_nodes
        if overflow <= 0:
            return

        victims = sorted(
            self._tree.values(),
            key=lambda n: (n.importance, n.access_count, n.updated_at.timestamp()),
        )[:overflow]
        for node in victims:
            self.delete(node.id)
        logger.warning("Muninn backpressure pruned %s nodes", len(victims))

    def _generate_node_id(self, content: Any, path: str) -> str:
        """Generate unique node ID."""
        content_str = self._safe_json(content)
        hash_input = f"{path}:{content_str}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def store(
        self,
        content: Any,
        path: str,
        memory_type: str = "fact",
        importance: int = 5,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """
        Store content in memory.

        Args:
            content: Content to store
            path: Hierarchical path (e.g., "game/characters/player")
            memory_type: Type of memory
            importance: Importance level 1-10
            tags: Tags for indexing
            metadata: Additional metadata

        Returns:
            Node ID
        """
        node_id = self._generate_node_id(content, path)
        tags = [str(t).strip().lower()[:64] for t in (tags or []) if str(t).strip()]
        metadata = metadata or {}
        path = self._normalize_path(path)
        importance = max(1, min(int(importance), 10))

        node = MemoryNode(
            id=node_id,
            content=content,
            path=path,
            memory_type=memory_type,
            importance=importance,
            tags=tags,
            metadata=metadata,
        )

        with self._lock:
            # Store node
            self._tree[node_id] = node

            # Update path index
            if path not in self._path_index:
                self._path_index[path] = []
            if node_id not in self._path_index[path]:
                self._path_index[path].append(node_id)

            # Update tag index
            for tag in tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = []
                if node_id not in self._tag_index[tag]:
                    self._tag_index[tag].append(node_id)

            # Update type index
            if memory_type not in self._type_index:
                self._type_index[memory_type] = []
            if node_id not in self._type_index[memory_type]:
                self._type_index[memory_type].append(node_id)

        # Persist
        if self.auto_persist:
            self._persist_node(node)

        # Sync to Helheim
        if self.helheim:
            self.helheim.store(
                content={"node_id": node_id, "content": content},
                memory_type=memory_type,
                realm_source="muninn",
                importance=importance,
                tags=tags + [path],
            )

        logger.debug(f"Muninn stored {node_id} at {path}")

        self._apply_backpressure()

        return node_id

    def retrieve(
        self,
        query: str = None,
        path: str = None,
        tags: List[str] = None,
        memory_type: str = None,
        top_k: int = 5,
    ) -> List[MemoryNode]:
        """
        Retrieve memories matching criteria.

        Args:
            query: Text query to match against content
            path: Path prefix to filter by
            tags: Tags to filter by (any match)
            memory_type: Type to filter by
            top_k: Maximum results

        Returns:
            List of matching MemoryNodes
        """
        candidates = []
        top_k = max(1, min(int(top_k), self.MAX_QUERY_RESULTS))

        with self._lock:
            # Start with all nodes or filtered by type
            if memory_type and memory_type in self._type_index:
                node_ids = self._type_index[memory_type]
            else:
                node_ids = list(self._tree.keys())

            for node_id in node_ids:
                node = self._tree.get(node_id)
                if not node:
                    continue

                # Filter by path
                if path and not node.path.startswith(path):
                    continue

                # Filter by tags
                if tags and not any(t in node.tags for t in tags):
                    continue

                # Filter by query
                if query:
                    content_str = self._safe_json(node.content).lower()
                    if query.lower() not in content_str:
                        continue

                # Update access count
                node.access_count += 1
                node.updated_at = datetime.now()

                candidates.append(node)

        # Sort by importance and recency
        candidates.sort(
            key=lambda n: (n.importance, n.updated_at.timestamp()), reverse=True
        )

        return candidates[:top_k]

    def get_by_path(self, path: str) -> List[MemoryNode]:
        """Get all nodes at a specific path."""
        with self._lock:
            node_ids = self._path_index.get(path, [])
            return [self._tree[nid] for nid in node_ids if nid in self._tree]

    def get_children(self, parent_path: str) -> Dict[str, List[MemoryNode]]:
        """Get all child paths and their nodes."""
        children = {}

        with self._lock:
            for path, node_ids in self._path_index.items():
                if path.startswith(parent_path) and path != parent_path:
                    children[path] = [
                        self._tree[nid] for nid in node_ids if nid in self._tree
                    ]

        return children

    def update(self, node_id: str, content: Any = None, **kwargs) -> bool:
        """
        Update an existing node.

        Args:
            node_id: Node to update
            content: New content (optional)
            **kwargs: Other fields to update

        Returns:
            Success status
        """
        with self._lock:
            if node_id not in self._tree:
                return False

            node = self._tree[node_id]

            if content is not None:
                node.content = content

            for key, value in kwargs.items():
                if hasattr(node, key):
                    setattr(node, key, value)

            node.updated_at = datetime.now()

        if self.auto_persist:
            self._persist_node(node)

        return True

    def delete(self, node_id: str) -> bool:
        """Delete a node from memory."""
        with self._lock:
            if node_id not in self._tree:
                return False

            node = self._tree[node_id]

            # Remove from indices
            if node.path in self._path_index:
                self._path_index[node.path] = [
                    nid for nid in self._path_index[node.path] if nid != node_id
                ]

            for tag in node.tags:
                if tag in self._tag_index:
                    self._tag_index[tag] = [
                        nid for nid in self._tag_index[tag] if nid != node_id
                    ]

            if node.memory_type in self._type_index:
                self._type_index[node.memory_type] = [
                    nid for nid in self._type_index[node.memory_type] if nid != node_id
                ]

            del self._tree[node_id]

        return True

    def move(self, node_id: str, new_path: str) -> bool:
        """Move a node to a new path."""
        with self._lock:
            if node_id not in self._tree:
                return False

            node = self._tree[node_id]
            old_path = node.path

            # Update path index
            if old_path in self._path_index:
                self._path_index[old_path] = [
                    nid for nid in self._path_index[old_path] if nid != node_id
                ]

            safe_new_path = self._normalize_path(new_path)
            if safe_new_path not in self._path_index:
                self._path_index[safe_new_path] = []
            if node_id not in self._path_index[safe_new_path]:
                self._path_index[safe_new_path].append(node_id)

            node.path = safe_new_path
            node.updated_at = datetime.now()

        if self.auto_persist:
            self._persist_node(node)

        return True

    # ========================================================================
    # FILE FORMAT SUPPORT
    # ========================================================================

    def load_file(self, file_path: Union[str, Path], base_path: str = "") -> List[str]:
        """
        Load a file into memory.

        Args:
            file_path: Path to file
            base_path: Base path prefix for stored content

        Returns:
            List of created node IDs
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return []

        suffix = file_path.suffix.lower().lstrip(".")

        try:
            if suffix == "json":
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
            elif suffix in ["yaml", "yml"]:
                with open(file_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            elif suffix in ["md", "txt"]:
                with open(file_path, encoding="utf-8") as f:
                    data = f.read()
            else:
                logger.warning(f"Unsupported format: {suffix}")
                return []

            # Store
            storage_path = (
                f"{base_path}/{file_path.stem}" if base_path else file_path.stem
            )
            node_id = self.store(
                content=data,
                path=storage_path,
                memory_type="file",
                metadata={"source_file": str(file_path), "format": suffix},
            )

            return [node_id]

        except Exception as e:
            logger.error(f"Failed to load file {file_path}: {e}")
            return []

    def save_to_file(
        self, path: str, file_path: Union[str, Path], format: str = "json"
    ):
        """
        Save memory path contents to a file.

        Args:
            path: Memory path to export
            file_path: Output file path
            format: Output format (json, yaml)
        """
        nodes = self.get_by_path(path)

        if not nodes:
            logger.warning(f"No nodes found at path: {path}")
            return

        # Collect content
        if len(nodes) == 1:
            data = nodes[0].content
        else:
            data = [n.content for n in nodes]

        file_path = Path(file_path)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                if format == "json":
                    json.dump(data, f, indent=2, default=str)
                elif format in ["yaml", "yml"]:
                    yaml.dump(data, f, default_flow_style=False)
                else:
                    f.write(str(data))

            logger.info(f"Saved {path} to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save to {file_path}: {e}")

    # ========================================================================
    # PERSISTENCE
    # ========================================================================

    def _persist_node(self, node: MemoryNode):
        """Persist a single node to disk."""
        if not self.data_path:
            return

        # Create path directory
        path_dir = self.data_path / node.path.replace("/", "_")
        path_dir.mkdir(parents=True, exist_ok=True)

        # Save node
        node_file = path_dir / f"{node.id}.json"
        try:
            with open(node_file, "w", encoding="utf-8") as f:
                json.dump(node.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to persist node {node.id}: {e}")

    def _load_from_disk(self):
        """Load all nodes from disk."""
        if not self.data_path or not self.data_path.exists():
            return

        for json_file in self.data_path.rglob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)

                node = MemoryNode.from_dict(data)

                with self._lock:
                    self._tree[node.id] = node

                    # Rebuild indices
                    if node.path not in self._path_index:
                        self._path_index[node.path] = []
                    if node.id not in self._path_index[node.path]:
                        self._path_index[node.path].append(node.id)

                    for tag in node.tags:
                        if tag not in self._tag_index:
                            self._tag_index[tag] = []
                        if node.id not in self._tag_index[tag]:
                            self._tag_index[tag].append(node.id)

                    if node.memory_type not in self._type_index:
                        self._type_index[node.memory_type] = []
                    if node.id not in self._type_index[node.memory_type]:
                        self._type_index[node.memory_type].append(node.id)

            except Exception as e:
                logger.warning(f"Failed to load {json_file}: {e}")
                try:
                    corrupt_file = json_file.with_suffix(".corrupt")
                    json_file.rename(corrupt_file)
                except Exception as rename_exc:
                    logger.warning(
                        "Failed to quarantine corrupt node %s: %s",
                        json_file,
                        rename_exc,
                    )

        logger.info(f"Muninn loaded {len(self._tree)} nodes from disk")
        self.heal_structure()

    def persist_all(self):
        """Persist all nodes to disk."""
        with self._lock:
            for node in self._tree.values():
                self._persist_node(node)

        logger.info(f"Muninn persisted {len(self._tree)} nodes")

    # ========================================================================
    # TREE OPERATIONS
    # ========================================================================

    def get_tree_structure(self) -> Dict[str, Any]:
        """Get the hierarchical tree structure."""
        tree = {}

        with self._lock:
            for path in sorted(self._path_index.keys()):
                parts = path.split("/")
                current = tree

                for part in parts:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                current["_nodes"] = len(self._path_index[path])

        return tree

    def heal_structure(self) -> int:
        """
        Self-healing: fix any inconsistencies in indices.

        Returns:
            Number of fixes applied
        """
        fixes = 0

        with self._lock:
            # Rebuild all indices from scratch
            new_path_index = {}
            new_tag_index = {}
            new_type_index = {}

            for node_id, node in self._tree.items():
                # Path index
                if node.path not in new_path_index:
                    new_path_index[node.path] = []
                new_path_index[node.path].append(node_id)

                # Tag index
                for tag in node.tags:
                    if tag not in new_tag_index:
                        new_tag_index[tag] = []
                    new_tag_index[tag].append(node_id)

                # Type index
                if node.memory_type not in new_type_index:
                    new_type_index[node.memory_type] = []
                new_type_index[node.memory_type].append(node_id)

            # Count fixes
            fixes = (
                len(set(self._path_index.keys()) ^ set(new_path_index.keys()))
                + len(set(self._tag_index.keys()) ^ set(new_tag_index.keys()))
                + len(set(self._type_index.keys()) ^ set(new_type_index.keys()))
            )

            self._path_index = new_path_index
            self._tag_index = new_tag_index
            self._type_index = new_type_index

        if fixes > 0:
            logger.info(f"Muninn healed {fixes} index inconsistencies")

        return fixes

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        with self._lock:
            return {
                "total_nodes": len(self._tree),
                "unique_paths": len(self._path_index),
                "unique_tags": len(self._tag_index),
                "memory_types": list(self._type_index.keys()),
                "type_counts": {t: len(ids) for t, ids in self._type_index.items()},
            }

    # ── SRD condition event storage ────────────────────────────────────────

    # Canonical SRD condition names for tag normalization
    _SRD_CONDITIONS = frozenset({
        "blinded", "charmed", "deafened", "exhaustion", "frightened",
        "grappled", "incapacitated", "invisible", "paralyzed", "petrified",
        "poisoned", "prone", "restrained", "stunned", "unconscious",
    })

    def store_condition_event(
        self,
        character_id: str,
        conditions: List[str],
        turn: int,
        location_id: str = "",
        exhaustion_level: int = 0,
        extra_metadata: Dict[str, Any] = None,
    ) -> str:
        """Store an SRD condition event as a memory node.

        Automatically tags the node with 'condition_event', each individual
        condition name, and 'near_death' / 'combat' as appropriate.
        The node can then be retrieved by Huginn via tag filter.

        Returns the node ID.
        """
        try:
            norm_conditions = [
                c.lower().strip() for c in (conditions or [])
                if c.lower().strip() in self._SRD_CONDITIONS
            ]
            tags: List[str] = ["condition_event", "combat"]
            tags.extend(norm_conditions)
            if exhaustion_level:
                tags.append("exhaustion")
            severe = {"unconscious", "paralyzed", "petrified"}
            if any(c in severe for c in norm_conditions):
                tags.append("near_death")
                importance = 8
            elif norm_conditions:
                importance = 6
            else:
                importance = 4

            cond_str = ", ".join(norm_conditions) if norm_conditions else "none"
            exh_str = f" exhaustion={exhaustion_level}" if exhaustion_level else ""
            content = {
                "character_id": character_id,
                "conditions": norm_conditions,
                "exhaustion_level": exhaustion_level,
                "turn": turn,
                "location_id": location_id,
                "summary": f"{character_id}: {cond_str}{exh_str} at turn {turn}",
            }
            metadata = dict(extra_metadata or {})
            metadata.update({
                "character_id": character_id,
                "turn": turn,
                "location_id": location_id,
                "srd_conditions": norm_conditions,
            })
            path = f"characters/{character_id}/conditions"
            return self.store(
                content=content,
                path=path,
                memory_type="condition_event",
                importance=importance,
                tags=tags,
                metadata=metadata,
            )
        except Exception as exc:
            logger.warning("Muninn.store_condition_event failed: %s", exc)
            return ""

    def dump(self, limit: int = 50) -> Dict[str, Any]:
        """Dump memory state for debugging."""
        with self._lock:
            nodes = sorted(
                self._tree.values(), key=lambda n: n.importance, reverse=True
            )[:limit]

            stats = {
                "total_nodes": len(self._tree),
                "unique_paths": len(self._path_index),
                "unique_tags": len(self._tag_index),
                "memory_types": list(self._type_index.keys()),
                "type_counts": {t: len(ids) for t, ids in self._type_index.items()},
            }
            return {
                "stats": stats,
                "nodes": [n.to_dict() for n in nodes],
            }
