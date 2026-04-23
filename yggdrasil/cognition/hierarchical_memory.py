"""
Hierarchical Memory Tree with Symbolic Links
============================================

Advanced memory structure that organizes data in a tree hierarchy
with symbolic links for cross-domain connections.

Unlike flat RAG, this system:
1. Organizes memories in a hierarchical directory structure
2. Uses symbolic links to connect related memories across domains
3. Enables rapid retrieval of large context sets
4. Maintains semantic relationships between memories
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memory nodes."""
    FACT = "fact"
    ENTITY = "entity"
    EVENT = "event"
    RELATIONSHIP = "relationship"
    RULE = "rule"
    PROTOCOL = "protocol"
    CHARACTER = "character"
    LOCATION = "location"
    QUEST = "quest"
    DIALOGUE = "dialogue"
    NARRATIVE = "narrative"
    WORLD_KNOWLEDGE = "world_knowledge"
    GENERAL = "general"
    EXPERIENCE = "experience"
    INTERACTION = "interaction"
    KNOWLEDGE = "knowledge"
    EMOTION = "emotion"
    COMBAT = "combat"
    PLANNING = "planning"
    MEMORY = "memory"
    ANALYSIS = "analysis"
    CREATION = "creation"
    REACTION = "reaction"
    SUMMARY = "summary"
    PROPHECY = "prophecy"


class NodeDomain(Enum):
    """Domains for organizing memories."""
    SYSTEM = "system"  # General system-level memories (sessions, metadata)
    CHARACTERS = "characters"
    LOCATIONS = "locations"
    QUESTS = "quests"
    WORLD_KNOWLEDGE = "world_knowledge"
    SOCIAL_PROTOCOLS = "social_protocols"
    CULTURAL_PRACTICES = "cultural_practices"
    HISTORICAL_EVENTS = "historical_events"
    MYTHOLOGY = "mythology"
    MAGIC_SYSTEMS = "magic_systems"
    COMBAT_RULES = "combat_rules"
    TRADE_ECONOMY = "trade_economy"
    RELIGION = "religion"
    DAILY_LIFE = "daily_life"


@dataclass
class SymbolicLink:
    """Symbolic link connecting memory nodes across domains."""
    source_node_id: str
    target_node_id: str
    link_type: str  # "related_to", "part_of", "causes", "influences", "similar_to"
    strength: float = 1.0  # 0.0 to 1.0
    bidirectional: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class MemoryNode:
    """A node in the hierarchical memory tree."""
    id: str
    content: Any
    path: str  # Hierarchical path like "characters/npcs/merchants/blacksmith"
    memory_type: MemoryType
    domain: NodeDomain
    importance: int = 5  # 1-10
    access_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    
    # Hierarchical relationships
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)
    
    # Symbolic links to other nodes
    symbolic_links: List[SymbolicLink] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Content embeddings for semantic search
    embedding: Optional[List[float]] = None
    keywords: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "path": self.path,
            "memory_type": self.memory_type.value,
            "domain": self.domain.value,
            "importance": self.importance,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
            "symbolic_links": [
                {
                    "source_node_id": link.source_node_id,
                    "target_node_id": link.target_node_id,
                    "link_type": link.link_type,
                    "strength": link.strength,
                    "bidirectional": link.bidirectional,
                    "metadata": link.metadata,
                    "created_at": link.created_at.isoformat()
                }
                for link in self.symbolic_links
            ],
            "tags": self.tags,
            "metadata": self.metadata,
            "keywords": self.keywords
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryNode":
        """Create node from dictionary."""
        # Convert symbolic links
        symbolic_links = []
        for link_data in data.get("symbolic_links", []):
            symbolic_links.append(SymbolicLink(
                source_node_id=link_data["source_node_id"],
                target_node_id=link_data["target_node_id"],
                link_type=link_data["link_type"],
                strength=link_data.get("strength", 1.0),
                bidirectional=link_data.get("bidirectional", False),
                metadata=link_data.get("metadata", {}),
                created_at=datetime.fromisoformat(link_data["created_at"])
            ))
        
        return cls(
            id=data["id"],
            content=data["content"],
            path=data["path"],
            memory_type=MemoryType(data["memory_type"]),
            domain=NodeDomain(data["domain"]),
            importance=data.get("importance", 5),
            access_count=data.get("access_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            parent_id=data.get("parent_id"),
            child_ids=data.get("child_ids", []),
            symbolic_links=symbolic_links,
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            keywords=data.get("keywords", [])
        )
    
    def add_symbolic_link(self, target_node: "MemoryNode", link_type: str, 
                         strength: float = 1.0, bidirectional: bool = False,
                         metadata: Dict[str, Any] = None):
        """Add symbolic link to another node."""
        link = SymbolicLink(
            source_node_id=self.id,
            target_node_id=target_node.id,
            link_type=link_type,
            strength=strength,
            bidirectional=bidirectional,
            metadata=metadata or {}
        )
        self.symbolic_links.append(link)
        
        if bidirectional:
            target_node.symbolic_links.append(SymbolicLink(
                source_node_id=target_node.id,
                target_node_id=self.id,
                link_type=link_type,
                strength=strength,
                bidirectional=True,
                metadata=metadata or {}
            ))
    
    def get_linked_nodes(self, link_type: Optional[str] = None, 
                        min_strength: float = 0.0) -> List[Tuple[str, str, float]]:
        """Get all nodes linked to this node."""
        results = []
        for link in self.symbolic_links:
            if link_type and link.link_type != link_type:
                continue
            if link.strength < min_strength:
                continue
            results.append((link.target_node_id, link.link_type, link.strength))
        return results


class HierarchicalMemoryTree:
    """
    Advanced hierarchical memory tree with symbolic links.
    
    Organizes memories in a tree structure with:
    - Hierarchical directory organization
    - Symbolic links across domains
    - Fast traversal and retrieval
    - Automatic relationship discovery
    """
    
    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize the memory tree.
        
        Args:
            data_path: Path to store memory data (optional)
        """
        self.data_path = Path(data_path) if data_path else None
        self.nodes: Dict[str, MemoryNode] = {}
        self.path_index: Dict[str, List[str]] = {}  # path -> node_ids
        self.domain_index: Dict[NodeDomain, List[str]] = {}
        self.type_index: Dict[MemoryType, List[str]] = {}
        
        # For fast keyword search
        self.keyword_index: Dict[str, List[str]] = {}
        
        # Load existing data if path exists
        if self.data_path and self.data_path.exists():
            self.load_from_disk()
    
    def add_node(self, node: MemoryNode) -> str:
        """Add a node to the memory tree."""
        self.nodes[node.id] = node
        
        # Update path index
        if node.path not in self.path_index:
            self.path_index[node.path] = []
        self.path_index[node.path].append(node.id)
        
        # Update domain index
        if node.domain not in self.domain_index:
            self.domain_index[node.domain] = []
        self.domain_index[node.domain].append(node.id)
        
        # Update type index
        if node.memory_type not in self.type_index:
            self.type_index[node.memory_type] = []
        self.type_index[node.memory_type].append(node.id)
        
        # Update keyword index
        for keyword in node.keywords:
            if keyword not in self.keyword_index:
                self.keyword_index[keyword] = []
            self.keyword_index[keyword].append(node.id)
        
        # Update parent-child relationships
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node.id not in parent.child_ids:
                parent.child_ids.append(node.id)
        
        return node.id
    
    def create_node(self, content: Any, path: str, memory_type: MemoryType,
                   domain: NodeDomain, importance: int = 5, 
                   parent_id: Optional[str] = None, tags: List[str] = None,
                   metadata: Dict[str, Any] = None, keywords: List[str] = None) -> MemoryNode:
        """Create and add a new node."""
        node_id = str(uuid.uuid4())
        node = MemoryNode(
            id=node_id,
            content=content,
            path=path,
            memory_type=memory_type,
            domain=domain,
            importance=importance,
            parent_id=parent_id,
            tags=tags or [],
            metadata=metadata or {},
            keywords=keywords or []
        )
        
        self.add_node(node)
        return node
    
    def get_node(self, node_id: str) -> Optional[MemoryNode]:
        """Get a node by ID."""
        node = self.nodes.get(node_id)
        if node:
            node.access_count += 1
            node.last_accessed = datetime.now()
        return node
    
    def get_nodes_by_path(self, path: str, recursive: bool = False) -> List[MemoryNode]:
        """Get all nodes at a specific path."""
        node_ids = self.path_index.get(path, [])
        nodes = [self.get_node(node_id) for node_id in node_ids]
        
        if recursive:
            # Get all child paths
            for subpath in self.path_index.keys():
                if subpath.startswith(path + "/"):
                    nodes.extend(self.get_nodes_by_path(subpath, recursive=False))
        
        return [n for n in nodes if n is not None]
    
    def get_nodes_by_domain(self, domain: NodeDomain) -> List[MemoryNode]:
        """Get all nodes in a specific domain."""
        node_ids = self.domain_index.get(domain, [])
        return [self.get_node(node_id) for node_id in node_ids if self.get_node(node_id)]
    
    def get_nodes_by_type(self, memory_type: MemoryType) -> List[MemoryNode]:
        """Get all nodes of a specific type."""
        node_ids = self.type_index.get(memory_type, [])
        return [self.get_node(node_id) for node_id in node_ids if self.get_node(node_id)]
    
    def search_by_keywords(self, keywords: List[str], 
                          operator: str = "OR") -> List[MemoryNode]:
        """Search nodes by keywords."""
        if operator == "OR":
            # Union of all keyword matches
            node_ids = set()
            for keyword in keywords:
                if keyword in self.keyword_index:
                    node_ids.update(self.keyword_index[keyword])
        else:  # AND
            # Intersection of all keyword matches
            node_sets = []
            for keyword in keywords:
                if keyword in self.keyword_index:
                    node_sets.append(set(self.keyword_index[keyword]))
                else:
                    node_sets.append(set())
            
            if not node_sets:
                return []
            
            node_ids = set.intersection(*node_sets)
        
        return [self.get_node(node_id) for node_id in node_ids if self.get_node(node_id)]
    
    def traverse_tree(self, start_path: str = "", max_depth: int = 3) -> Dict[str, Any]:
        """Traverse the memory tree hierarchy."""
        result = {
            "path": start_path,
            "nodes": [],
            "children": {}
        }
        
        # Get nodes at current path
        nodes = self.get_nodes_by_path(start_path)
        result["nodes"] = [node.id for node in nodes]
        
        # Get child paths
        if max_depth > 0:
            child_paths = set()
            for path in self.path_index.keys():
                if path.startswith(start_path + "/") and path != start_path:
                    # Get immediate child path
                    relative_path = path[len(start_path):].lstrip("/")
                    if "/" not in relative_path:  # Immediate child
                        child_paths.add(path)
            
            for child_path in child_paths:
                result["children"][child_path] = self.traverse_tree(
                    child_path, max_depth - 1
                )
        
        return result
    
    def find_related_nodes(self, node_id: str, max_links: int = 10, 
                          min_strength: float = 0.3) -> List[MemoryNode]:
        """Find nodes related through symbolic links."""
        node = self.get_node(node_id)
        if not node:
            return []
        
        related_nodes = []
        visited = {node_id}
        
        # Direct links
        for link in node.symbolic_links:
            if link.strength >= min_strength and link.target_node_id not in visited:
                target_node = self.get_node(link.target_node_id)
                if target_node:
                    related_nodes.append(target_node)
                    visited.add(link.target_node_id)
        
        # Follow bidirectional links
        for other_node in self.nodes.values():
            if other_node.id in visited:
                continue
            
            for link in other_node.symbolic_links:
                if (link.target_node_id == node_id and link.strength >= min_strength and
                    link.bidirectional):
                    related_nodes.append(other_node)
                    visited.add(other_node.id)
                    break
        
        return related_nodes[:max_links]
    
    def save_to_disk(self):
        """Save memory tree to disk."""
        if not self.data_path:
            return
        
        # Create directory if it doesn't exist
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # Save nodes
        nodes_file = self.data_path / "memory_nodes.json"
        nodes_data = {node_id: node.to_dict() for node_id, node in self.nodes.items()}
        
        with open(nodes_file, 'w', encoding='utf-8') as f:
            json.dump(nodes_data, f, indent=2, default=str)
        
        logger.info(f"Saved {len(self.nodes)} memory nodes to {nodes_file}")
    
    def load_from_disk(self):
        """Load memory tree from disk."""
        if not self.data_path:
            return
        
        nodes_file = self.data_path / "memory_nodes.json"
        if not nodes_file.exists():
            return
        
        try:
            with open(nodes_file, 'r', encoding='utf-8') as f:
                nodes_data = json.load(f)
            
            # Clear existing data
            self.nodes.clear()
            self.path_index.clear()
            self.domain_index.clear()
            self.type_index.clear()
            self.keyword_index.clear()
            
            # Load nodes
            for node_id, node_dict in nodes_data.items():
                try:
                    node = MemoryNode.from_dict(node_dict)
                    self.add_node(node)
                except Exception as e:
                    logger.error(f"Error loading node {node_id}: {e}")
            
            logger.info(f"Loaded {len(self.nodes)} memory nodes from {nodes_file}")
            
        except Exception as e:
            logger.error(f"Error loading memory tree: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the memory tree."""
        return {
            "total_nodes": len(self.nodes),
            "domains": {domain.value: len(nodes) for domain, nodes in self.domain_index.items()},
            "memory_types": {mem_type.value: len(nodes) for mem_type, nodes in self.type_index.items()},
            "unique_paths": len(self.path_index),
            "unique_keywords": len(self.keyword_index),
            "total_symbolic_links": sum(len(node.symbolic_links) for node in self.nodes.values()),
            "avg_importance": sum(node.importance for node in self.nodes.values()) / len(self.nodes) if self.nodes else 0,
            "avg_access_count": sum(node.access_count for node in self.nodes.values()) / len(self.nodes) if self.nodes else 0
        }