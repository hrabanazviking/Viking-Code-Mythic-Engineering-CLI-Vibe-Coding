"""
Memory Orchestrator
====================

Orchestrates the hierarchical memory tree, Huginn advanced retrieval,
and domain crosslinker to provide unified memory operations.

This is the main interface for the Yggdrasil cognitive system.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .hierarchical_memory import HierarchicalMemoryTree, MemoryNode, NodeDomain, MemoryType
from .huginn_advanced import HuginnAdvanced, CognitiveRetrieval, RetrievalStrategy
from .domain_crosslinker import DomainCrosslinker, CrossDomainQuery, RelationshipType

logger = logging.getLogger(__name__)


class MemoryOperation(Enum):
    """Types of memory operations."""
    STORE = "store"
    RETRIEVE = "retrieve"
    UPDATE = "update"
    DELETE = "delete"
    LINK = "link"
    TRAVERSE = "traverse"
    SEARCH = "search"
    ANALYZE = "analyze"


@dataclass
class MemoryOperationResult:
    """Result of a memory operation."""
    operation: MemoryOperation
    success: bool
    node_id: Optional[str] = None
    nodes: List[MemoryNode] = field(default_factory=list)
    retrieval_result: Optional[CognitiveRetrieval] = None
    cross_query_result: Optional[CrossDomainQuery] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class MemoryOrchestrator:
    """
    Orchestrates all memory operations for the Yggdrasil system.
    
    Provides a unified interface for:
    - Storing and retrieving memories
    - Cross-domain linking and retrieval
    - Intelligent query processing
    - Memory analysis and statistics
    """
    
    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize memory orchestrator.
        
        Args:
            data_path: Path for storing memory data
        """
        self.memory_tree = HierarchicalMemoryTree(data_path)
        self.huginn = HuginnAdvanced(self.memory_tree)
        self.crosslinker = DomainCrosslinker(self.memory_tree)
        
        # Operation statistics
        self._operation_stats: Dict[MemoryOperation, List[float]] = {
            op: [] for op in MemoryOperation
        }
        
        # Performance metrics
        self._performance_metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "avg_retrieval_time": 0.0,
            "total_nodes": 0,
            "total_links": 0
        }
        
        logger.info("Memory orchestrator initialized")
    
    def store_memory(self, content: Any, path: str, memory_type: MemoryType,
                    domain: NodeDomain, importance: int = 5,
                    parent_id: Optional[str] = None, tags: List[str] = None,
                    metadata: Dict[str, Any] = None, keywords: List[str] = None) -> MemoryOperationResult:
        """
        Store a memory in the hierarchical tree.
        
        Args:
            content: The memory content
            path: Hierarchical path for the memory
            memory_type: Type of memory
            domain: Domain of the memory
            importance: Importance score (1-10)
            parent_id: ID of parent node (optional)
            tags: List of tags
            metadata: Additional metadata
            keywords: Keywords for indexing
            
        Returns:
            MemoryOperationResult with operation status
        """
        start_time = time.time()
        
        try:
            node = self.memory_tree.create_node(
                content=content,
                path=path,
                memory_type=memory_type,
                domain=domain,
                importance=importance,
                parent_id=parent_id,
                tags=tags,
                metadata=metadata,
                keywords=keywords
            )
            
            # Auto-create cross-domain links
            self._auto_create_links(node)
            
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.STORE, execution_time, success=True)
            
            return MemoryOperationResult(
                operation=MemoryOperation.STORE,
                success=True,
                node_id=node.id,
                execution_time=execution_time,
                metadata={"node_path": node.path, "domain": domain.value}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.STORE, execution_time, success=False)
            
            return MemoryOperationResult(
                operation=MemoryOperation.STORE,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def retrieve_memory(self, query: str, strategy: Optional[RetrievalStrategy] = None,
                       max_nodes: int = 20, min_confidence: float = 0.3,
                       cross_domain: bool = True) -> MemoryOperationResult:
        """
        Retrieve memories using intelligent strategies.
        
        Args:
            query: Query string
            strategy: Retrieval strategy (auto-determined if None)
            max_nodes: Maximum nodes to retrieve
            min_confidence: Minimum confidence score
            cross_domain: Whether to perform cross-domain retrieval
            
        Returns:
            MemoryOperationResult with retrieval results
        """
        start_time = time.time()
        
        try:
            if cross_domain and hasattr(self, 'crosslinker') and self.crosslinker:
                # Perform cross-domain analysis and retrieval
                cross_query = self.crosslinker.analyze_cross_domain_query(query)
                cross_query.min_confidence = min_confidence
                cross_query.max_links = max_nodes // 2
                
                cross_query = self.crosslinker.execute_cross_domain_query(cross_query)
                
                # Also perform standard retrieval
                retrieval = self.huginn.retrieve(
                    query=query,
                    strategy=strategy,
                    max_nodes=max_nodes,
                    min_confidence=min_confidence
                )
                
                # Combine results
                all_nodes = retrieval.primary_nodes + [
                    target_node for _, target_node, _, _ in cross_query.results
                ]
                
                # Deduplicate
                seen_ids = set()
                combined_nodes = []
                for node in all_nodes:
                    if node.id not in seen_ids:
                        combined_nodes.append(node)
                        seen_ids.add(node.id)
                
                execution_time = time.time() - start_time
                self._update_stats(MemoryOperation.RETRIEVE, execution_time, success=True)
                
                return MemoryOperationResult(
                    operation=MemoryOperation.RETRIEVE,
                    success=True,
                    nodes=combined_nodes[:max_nodes],
                    retrieval_result=retrieval,
                    cross_query_result=cross_query,
                    execution_time=execution_time,
                    metadata={
                        "strategy": retrieval.retrieval_strategy.value,
                        "cross_domain": True,
                        "domains_involved": len(set([n.domain for n in combined_nodes]))
                    }
                )
            else:
                # Standard retrieval only
                if not hasattr(self, 'huginn') or not self.huginn:
                    raise ValueError("Huginn not initialized")
                
                retrieval = self.huginn.retrieve(
                    query=query,
                    strategy=strategy,
                    max_nodes=max_nodes,
                    min_confidence=min_confidence
                )
                
                execution_time = time.time() - start_time
                self._update_stats(MemoryOperation.RETRIEVE, execution_time, success=True)
                
                return MemoryOperationResult(
                    operation=MemoryOperation.RETRIEVE,
                    success=True,
                    nodes=retrieval.primary_nodes,
                    retrieval_result=retrieval,
                    execution_time=execution_time,
                    metadata={
                        "strategy": retrieval.retrieval_strategy.value,
                        "cross_domain": False
                    }
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.RETRIEVE, execution_time, success=False)
            
            return MemoryOperationResult(
                operation=MemoryOperation.RETRIEVE,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def update_memory(self, node_id: str, content: Any = None,
                     importance: Optional[int] = None,
                     tags: Optional[List[str]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> MemoryOperationResult:
        """
        Update an existing memory.
        
        Args:
            node_id: ID of node to update
            content: New content (optional)
            importance: New importance score (optional)
            tags: New tags (optional)
            metadata: New metadata (optional)
            
        Returns:
            MemoryOperationResult with update status
        """
        start_time = time.time()
        
        try:
            node = self.memory_tree.get_node(node_id)
            if not node:
                raise ValueError(f"Node {node_id} not found")
            
            # Update fields
            if content is not None:
                node.content = content
            
            if importance is not None:
                node.importance = importance
            
            if tags is not None:
                node.tags = tags
            
            if metadata is not None:
                node.metadata.update(metadata)
            
            node.updated_at = datetime.now()
            
            # Re-index if keywords changed
            if content is not None:
                # Extract new keywords from content
                # This is simplified - in practice would use NLP
                if isinstance(content, str):
                    words = re.findall(r'\b\w+\b', content.lower())
                    node.keywords = [w for w in words if len(w) > 3][:20]
            
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.UPDATE, execution_time, success=True)
            
            return MemoryOperationResult(
                operation=MemoryOperation.UPDATE,
                success=True,
                node_id=node_id,
                execution_time=execution_time,
                metadata={"updated_fields": ["content" if content else None, 
                                          "importance" if importance else None,
                                          "tags" if tags else None,
                                          "metadata" if metadata else None]}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.UPDATE, execution_time, success=False)
            
            return MemoryOperationResult(
                operation=MemoryOperation.UPDATE,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def delete_memory(self, node_id: str) -> MemoryOperationResult:
        """
        Delete a memory from the tree.
        
        Args:
            node_id: ID of node to delete
            
        Returns:
            MemoryOperationResult with deletion status
        """
        start_time = time.time()
        
        try:
            # Note: In a real implementation, would need to handle:
            # 1. Removing from indexes
            # 2. Updating parent-child relationships
            # 3. Removing symbolic links
            # For now, just remove from nodes dict
            if node_id in self.memory_tree.nodes:
                del self.memory_tree.nodes[node_id]
                
                # Note: Would need to update indexes too
                # This is simplified
                
                execution_time = time.time() - start_time
                self._update_stats(MemoryOperation.DELETE, execution_time, success=True)
                
                return MemoryOperationResult(
                    operation=MemoryOperation.DELETE,
                    success=True,
                    node_id=node_id,
                    execution_time=execution_time
                )
            else:
                raise ValueError(f"Node {node_id} not found")
                
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.DELETE, execution_time, success=False)
            
            return MemoryOperationResult(
                operation=MemoryOperation.DELETE,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def create_link(self, source_node_id: str, target_node_id: str,
                   link_type: RelationshipType, strength: float = 1.0,
                   bidirectional: bool = True,
                   metadata: Dict[str, Any] = None) -> MemoryOperationResult:
        """
        Create a symbolic link between two nodes.
        
        Args:
            source_node_id: Source node ID
            target_node_id: Target node ID
            link_type: Type of relationship
            strength: Strength of link (0.0 to 1.0)
            bidirectional: Whether link is bidirectional
            metadata: Additional link metadata
            
        Returns:
            MemoryOperationResult with link creation status
        """
        start_time = time.time()
        
        try:
            source_node = self.memory_tree.get_node(source_node_id)
            target_node = self.memory_tree.get_node(target_node_id)
            
            if not source_node:
                raise ValueError(f"Source node {source_node_id} not found")
            if not target_node:
                raise ValueError(f"Target node {target_node_id} not found")
            
            # Create link
            source_node.add_symbolic_link(
                target_node=target_node,
                link_type=link_type.value,
                strength=strength,
                bidirectional=bidirectional,
                metadata=metadata
            )
            
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.LINK, execution_time, success=True)
            
            return MemoryOperationResult(
                operation=MemoryOperation.LINK,
                success=True,
                node_id=source_node_id,
                execution_time=execution_time,
                metadata={
                    "target_node_id": target_node_id,
                    "link_type": link_type.value,
                    "strength": strength,
                    "bidirectional": bidirectional
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.LINK, execution_time, success=False)
            
            return MemoryOperationResult(
                operation=MemoryOperation.LINK,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def traverse_memory_tree(self, start_path: str = "", max_depth: int = 3) -> MemoryOperationResult:
        """
        Traverse the memory tree hierarchy.
        
        Args:
            start_path: Starting path for traversal
            max_depth: Maximum depth to traverse
            
        Returns:
            MemoryOperationResult with traversal results
        """
        start_time = time.time()
        
        try:
            tree_structure = self.memory_tree.traverse_tree(start_path, max_depth)
            
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.TRAVERSE, execution_time, success=True)
            
            return MemoryOperationResult(
                operation=MemoryOperation.TRAVERSE,
                success=True,
                execution_time=execution_time,
                metadata={"tree_structure": tree_structure}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.TRAVERSE, execution_time, success=False)
            
            return MemoryOperationResult(
                operation=MemoryOperation.TRAVERSE,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def search_memories(self, keywords: List[str], operator: str = "OR",
                       domain: Optional[NodeDomain] = None,
                       memory_type: Optional[MemoryType] = None,
                       min_importance: int = 1) -> MemoryOperationResult:
        """
        Search memories by keywords and filters.
        
        Args:
            keywords: List of keywords to search for
            operator: "AND" or "OR" for keyword matching
            domain: Filter by domain (optional)
            memory_type: Filter by memory type (optional)
            min_importance: Minimum importance score
            
        Returns:
            MemoryOperationResult with search results
        """
        start_time = time.time()
        
        try:
            # Start with keyword search
            nodes = self.memory_tree.search_by_keywords(keywords, operator)
            
            # Apply filters
            filtered_nodes = []
            for node in nodes:
                if domain and node.domain != domain:
                    continue
                if memory_type and node.memory_type != memory_type:
                    continue
                if node.importance < min_importance:
                    continue
                filtered_nodes.append(node)
            
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.SEARCH, execution_time, success=True)
            
            return MemoryOperationResult(
                operation=MemoryOperation.SEARCH,
                success=True,
                nodes=filtered_nodes,
                execution_time=execution_time,
                metadata={
                    "keyword_count": len(keywords),
                    "operator": operator,
                    "domain": domain.value if domain else None,
                    "memory_type": memory_type.value if memory_type else None,
                    "min_importance": min_importance,
                    "results_count": len(filtered_nodes)
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.SEARCH, execution_time, success=False)
            
            return MemoryOperationResult(
                operation=MemoryOperation.SEARCH,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def analyze_memory_system(self) -> MemoryOperationResult:
        """
        Analyze the memory system and generate statistics.
        
        Returns:
            MemoryOperationResult with analysis
        """
        start_time = time.time()
        
        try:
            # Get tree statistics
            tree_stats = self.memory_tree.get_statistics()
            
            # Get Huginn performance statistics
            huginn_stats = self.huginn.get_performance_statistics()
            
            # Get domain connectivity
            domain_connectivity = self.crosslinker.get_domain_connectivity()
            
            # Calculate cross-domain link statistics
            cross_domain_links = 0
            for node in self.memory_tree.nodes.values():
                for link in node.symbolic_links:
                    target_node = self.memory_tree.get_node(link.target_node_id)
                    if target_node and target_node.domain != node.domain:
                        cross_domain_links += 1
            
            analysis = {
                "tree_statistics": tree_stats,
                "huginn_performance": huginn_stats,
                "domain_connectivity": domain_connectivity,
                "cross_domain_links": cross_domain_links,
                "total_nodes": len(self.memory_tree.nodes),
                "total_operations": self._performance_metrics["total_operations"],
                "success_rate": (
                    self._performance_metrics["successful_operations"] / 
                    self._performance_metrics["total_operations"] * 100 
                    if self._performance_metrics["total_operations"] > 0 else 0
                )
            }
            
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.ANALYZE, execution_time, success=True)
            
            return MemoryOperationResult(
                operation=MemoryOperation.ANALYZE,
                success=True,
                execution_time=execution_time,
                metadata={"analysis": analysis}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_stats(MemoryOperation.ANALYZE, execution_time, success=False)
            
            return MemoryOperationResult(
                operation=MemoryOperation.ANALYZE,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    def _auto_create_links(self, node: MemoryNode):
        """Automatically create cross-domain links for a new node."""
        # Find compatible domains
        compatible_domains = []
        for target_domain in NodeDomain:
            if target_domain == node.domain:
                continue
            
            domain_pair = (node.domain, target_domain)
            if self.crosslinker._domain_compatibility.get(domain_pair, 0) >= 0.5:
                compatible_domains.append(target_domain)
        
        # Create links to top 2 compatible domains
        for target_domain in compatible_domains[:2]:
            self.crosslinker.create_cross_domain_links(
                node, target_domain, min_confidence=0.4, max_links=2
            )
    
    def _update_stats(self, operation: MemoryOperation, execution_time: float, success: bool):
        """Update operation statistics."""
        self._operation_stats[operation].append(execution_time)
        self._performance_metrics["total_operations"] += 1
        
        if success:
            self._performance_metrics["successful_operations"] += 1
        else:
            self._performance_metrics["failed_operations"] += 1
        
        # Update average retrieval time
        if operation == MemoryOperation.RETRIEVE:
            times = self._operation_stats[operation]
            self._performance_metrics["avg_retrieval_time"] = sum(times) / len(times) if times else 0
        
        # Update node and link counts
        self._performance_metrics["total_nodes"] = len(self.memory_tree.nodes)
        self._performance_metrics["total_links"] = sum(
            len(node.symbolic_links) for node in self.memory_tree.nodes.values()
        )
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        report = {
            "performance_metrics": self._performance_metrics.copy(),
            "operation_statistics": {},
            "memory_system_statistics": self.memory_tree.get_statistics(),
            "huginn_statistics": self.huginn.get_performance_statistics()
        }
        
        for operation, times in self._operation_stats.items():
            if times:
                report["operation_statistics"][operation.value] = {
                    "total_calls": len(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "success_rate": (
                        self._performance_metrics["successful_operations"] / 
                        self._performance_metrics["total_operations"] * 100 
                        if self._performance_metrics["total_operations"] > 0 else 0
                    )
                }
        
        return report