"""
Advanced Huginn Cognitive System
================================

Enhanced version of Huginn that works with hierarchical memory trees
and symbolic links for intelligent, context-rich retrieval.

This system can quickly pull in large amounts of cross-domain data
by traversing symbolic links and understanding hierarchical relationships.
"""

import logging
import time
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib

from .hierarchical_memory import (
    HierarchicalMemoryTree, MemoryNode, MemoryType, NodeDomain
)

logger = logging.getLogger(__name__)


class RetrievalStrategy(Enum):
    """Strategies for memory retrieval."""
    HIERARCHICAL = "hierarchical"  # Follow tree structure
    SYMBOLIC_LINKS = "symbolic_links"  # Follow symbolic links
    DOMAIN_CROSSING = "domain_crossing"  # Cross domain boundaries
    KEYWORD_EXPANSION = "keyword_expansion"  # Expand via keywords
    CONTEXTUAL = "contextual"  # Use context to guide retrieval
    HYBRID = "hybrid"  # Combine multiple strategies


class QueryComplexity(Enum):
    """Complexity levels for queries."""
    SIMPLE = "simple"  # Single fact retrieval
    MODERATE = "moderate"  # Multiple related facts
    COMPLEX = "complex"  # Cross-domain synthesis
    DEEP = "deep"  # Requires reasoning and inference


@dataclass
class CognitiveRetrieval:
    """Result of an advanced cognitive retrieval."""
    query: str
    primary_nodes: List[MemoryNode]
    related_nodes: List[MemoryNode]
    context_nodes: List[MemoryNode]
    retrieval_strategy: RetrievalStrategy
    query_complexity: QueryComplexity
    retrieval_time: float
    confidence_score: float  # 0.0 to 1.0
    cross_domain_connections: int
    symbolic_links_traversed: int
    hierarchical_depth: int = 0
    retrieval_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_combined_context(self, max_tokens: int = 4000) -> str:
        """Combine retrieved nodes into a coherent context string."""
        context_parts = []
        
        # Add primary nodes first
        for node in self.primary_nodes:
            context_parts.append(f"=== {node.path} ===")
            context_parts.append(str(node.content))
        
        # Add related nodes
        if self.related_nodes:
            context_parts.append("\n=== RELATED INFORMATION ===")
            for node in self.related_nodes[:10]:  # Limit related nodes
                context_parts.append(f"--- {node.path} ---")
                context_parts.append(str(node.content)[:500])  # Truncate
        
        # Add context nodes if space allows
        if self.context_nodes and len("\n".join(context_parts)) < max_tokens * 0.7:
            context_parts.append("\n=== ADDITIONAL CONTEXT ===")
            for node in self.context_nodes[:5]:
                context_parts.append(f"* {node.path}: {str(node.content)[:200]}...")
        
        context = "\n".join(context_parts)
        
        # Truncate if too long
        if len(context) > max_tokens * 4:  # Rough character estimate
            context = context[:max_tokens * 4] + "..."
        
        return context
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get retrieval statistics."""
        return {
            "total_nodes": len(self.primary_nodes) + len(self.related_nodes) + len(self.context_nodes),
            "primary_nodes": len(self.primary_nodes),
            "related_nodes": len(self.related_nodes),
            "context_nodes": len(self.context_nodes),
            "retrieval_strategy": self.retrieval_strategy.value,
            "query_complexity": self.query_complexity.value,
            "retrieval_time": self.retrieval_time,
            "confidence_score": self.confidence_score,
            "cross_domain_connections": self.cross_domain_connections,
            "symbolic_links_traversed": self.symbolic_links_traversed,
            "hierarchical_depth": self.hierarchical_depth
        }


class HuginnAdvanced:
    """
    Advanced Huginn cognitive system for intelligent memory retrieval.
    
    Features:
    - Hierarchical memory traversal
    - Symbolic link following
    - Cross-domain data integration
    - Context-aware retrieval strategies
    - Adaptive query analysis
    - Intelligent result synthesis
    """
    
    def __init__(self, memory_tree: HierarchicalMemoryTree):
        """
        Initialize advanced Huginn.
        
        Args:
            memory_tree: Hierarchical memory tree to work with
        """
        self.memory_tree = memory_tree
        
        # Query analysis cache — bounded to prevent unbounded memory growth in long sessions.
        self._query_cache: Dict[str, Dict[str, Any]] = {}
        self._QUERY_CACHE_MAX = 256
        
        # Strategy performance tracking
        self._strategy_performance: Dict[RetrievalStrategy, List[float]] = {
            strategy: [] for strategy in RetrievalStrategy
        }
        
        # Domain expertise tracking
        self._domain_expertise: Dict[NodeDomain, int] = {
            domain: 0 for domain in NodeDomain
        }
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Deep analysis of a query to determine retrieval strategy.
        
        Returns:
            Dictionary with analysis results
        """
        start_time = time.time()
        
        try:
            # Check cache
            query_hash = hashlib.md5(query.encode()).hexdigest()
            if query_hash in self._query_cache:
                return self._query_cache[query_hash]
            
            # Perform analysis with fallbacks
            analysis = {
                "query": query,
                "keywords": self._extract_keywords(query) if hasattr(self, '_extract_keywords') else [],
                "domains": self._identify_domains(query) if hasattr(self, '_identify_domains') else [],
                "memory_types": self._identify_memory_types(query) if hasattr(self, '_identify_memory_types') else [],
                "complexity": self._assess_complexity(query) if hasattr(self, '_assess_complexity') else QueryComplexity.SIMPLE,
                "expected_depth": self._estimate_depth(query) if hasattr(self, '_estimate_depth') else 1,
                "requires_cross_domain": self._requires_cross_domain(query) if hasattr(self, '_requires_cross_domain') else False,
                "timestamp": datetime.now()
            }
            
            # Determine best strategy
            analysis["recommended_strategy"] = self._determine_strategy(analysis) if hasattr(self, '_determine_strategy') else RetrievalStrategy.HYBRID
            
            # Cache the analysis — evict oldest entry (FIFO) when full.
            if len(self._query_cache) >= self._QUERY_CACHE_MAX:
                oldest_key = next(iter(self._query_cache))
                del self._query_cache[oldest_key]
            self._query_cache[query_hash] = analysis
            
            analysis["analysis_time"] = time.time() - start_time
            return analysis
            
        except Exception as e:
            # Return fallback analysis
            logger.warning(f"Query analysis failed for '{query}': {e}")
            return {
                "query": query,
                "keywords": [],
                "domains": [],
                "memory_types": [],
                "complexity": QueryComplexity.SIMPLE,
                "expected_depth": 1,
                "requires_cross_domain": False,
                "recommended_strategy": RetrievalStrategy.HYBRID,
                "timestamp": datetime.now(),
                "analysis_time": time.time() - start_time,
                "analysis_error": str(e)
            }
    
    def retrieve(self, query: str, strategy: Optional[RetrievalStrategy] = None,
                max_nodes: int = 20, min_confidence: float = 0.3) -> CognitiveRetrieval:
        """
        Perform intelligent memory retrieval.
        
        Args:
            query: The query to retrieve information for
            strategy: Retrieval strategy to use (auto-determined if None)
            max_nodes: Maximum number of nodes to retrieve
            min_confidence: Minimum confidence score for nodes
            
        Returns:
            CognitiveRetrieval object with results
        """
        start_time = time.time()
        
        try:
            # Analyze query
            analysis = self.analyze_query(query)
            
            # Determine strategy
            if strategy is None:
                strategy = analysis.get("recommended_strategy", RetrievalStrategy.HYBRID)
            
            # Perform retrieval based on strategy
            if strategy == RetrievalStrategy.HIERARCHICAL:
                result = self._hierarchical_retrieval(query, analysis, max_nodes, min_confidence)
            elif strategy == RetrievalStrategy.SYMBOLIC_LINKS:
                result = self._symbolic_link_retrieval(query, analysis, max_nodes, min_confidence)
            elif strategy == RetrievalStrategy.DOMAIN_CROSSING:
                result = self._domain_crossing_retrieval(query, analysis, max_nodes, min_confidence)
            elif strategy == RetrievalStrategy.KEYWORD_EXPANSION:
                result = self._keyword_expansion_retrieval(query, analysis, max_nodes, min_confidence)
            elif strategy == RetrievalStrategy.CONTEXTUAL:
                result = self._contextual_retrieval(query, analysis, max_nodes, min_confidence)
            else:  # HYBRID
                result = self._hybrid_retrieval(query, analysis, max_nodes, min_confidence)
            
            # Update performance tracking
            retrieval_time = time.time() - start_time
            if hasattr(self, '_strategy_performance'):
                self._strategy_performance[strategy].append(retrieval_time)
            
            # Update domain expertise
            if hasattr(self, '_domain_expertise'):
                for domain in analysis.get("domains", []):
                    self._domain_expertise[domain] = self._domain_expertise.get(domain, 0) + 1
            
            return result
            
        except Exception as e:
            # Return empty retrieval result
            retrieval_time = time.time() - start_time
            logger.warning(f"Retrieval failed for query '{query}': {e}")
            
            return CognitiveRetrieval(
                query=query,
                primary_nodes=[],
                related_nodes=[],
                context_nodes=[],
                retrieval_strategy=strategy or RetrievalStrategy.HYBRID,
                query_complexity=QueryComplexity.SIMPLE,
                retrieval_time=retrieval_time,
                confidence_score=0.0,
                cross_domain_connections=0,
                symbolic_links_traversed=0,
                retrieval_error=str(e)
            )
    
    def _hierarchical_retrieval(self, query: str, analysis: Dict[str, Any],
                               max_nodes: int, min_confidence: float) -> CognitiveRetrieval:
        """Retrieve using hierarchical tree traversal."""
        method_start_time = time.time()
        primary_nodes = []
        related_nodes = []
        context_nodes = []
        
        try:
            # Start with keyword search
            keyword_nodes = self.memory_tree.search_by_keywords(analysis.get("keywords", []))
            
            # Organize by path hierarchy
            path_groups: Dict[str, List[MemoryNode]] = {}
            for node in keyword_nodes:
                if node.path not in path_groups:
                    path_groups[node.path] = []
                path_groups[node.path].append(node)
            
            # Get nodes from most relevant paths
            for path, nodes in path_groups.items():
                if len(primary_nodes) >= max_nodes // 2:
                    break
                
                # Add nodes from this path
                primary_nodes.extend(nodes[:3])
                
                # Get parent and sibling nodes for context
                parent_path = "/".join(path.split("/")[:-1])
                if parent_path:
                    parent_nodes = self.memory_tree.get_nodes_by_path(parent_path, recursive=False)
                    context_nodes.extend(parent_nodes[:2])
            
            # Get related nodes through hierarchical relationships
            for node in primary_nodes[:5]:
                if node.parent_id:
                    parent = self.memory_tree.get_node(node.parent_id)
                    if parent:
                        related_nodes.append(parent)
                
                for child_id in node.child_ids[:3]:
                    child = self.memory_tree.get_node(child_id)
                    if child:
                        related_nodes.append(child)
            
            return CognitiveRetrieval(
                query=query,
                primary_nodes=primary_nodes[:max_nodes//2],
                related_nodes=related_nodes[:max_nodes//4],
                context_nodes=context_nodes[:max_nodes//4],
                retrieval_strategy=RetrievalStrategy.HIERARCHICAL,
                query_complexity=analysis.get("complexity", QueryComplexity.SIMPLE),
                retrieval_time=time.time() - method_start_time,
                confidence_score=self._calculate_confidence(primary_nodes, analysis) if hasattr(self, '_calculate_confidence') else 0.5,
                cross_domain_connections=0,
                symbolic_links_traversed=0,
                hierarchical_depth=analysis.get("expected_depth", 1)
            )
        except Exception as e:
            # Return empty retrieval result
            logger.warning(f"Hierarchical retrieval failed for query '{query}': {e}")
            return CognitiveRetrieval(
                query=query,
                primary_nodes=[],
                related_nodes=[],
                context_nodes=[],
                retrieval_strategy=RetrievalStrategy.HIERARCHICAL,
                query_complexity=QueryComplexity.SIMPLE,
                retrieval_time=time.time() - method_start_time,
                confidence_score=0.0,
                cross_domain_connections=0,
                symbolic_links_traversed=0,
                hierarchical_depth=1,
                retrieval_error=str(e)
            )
    
    def _symbolic_link_retrieval(self, query: str, analysis: Dict[str, Any],
                                max_nodes: int, min_confidence: float) -> CognitiveRetrieval:
        """Retrieve by following symbolic links."""
        method_start_time = time.time()
        
        try:
            # Start with direct matches
            direct_nodes = self.memory_tree.search_by_keywords(analysis.get("keywords", []))
            primary_nodes = direct_nodes[:max_nodes//3]
            
            # Follow symbolic links
            related_nodes = []
            symbolic_links_traversed = 0
            
            for node in primary_nodes[:10]:
                linked_nodes = self.memory_tree.find_related_nodes(
                    node.id, max_links=5, min_strength=min_confidence
                )
                related_nodes.extend(linked_nodes)
                symbolic_links_traversed += len(linked_nodes)
            
            # Remove duplicates
            seen_ids = {node.id for node in primary_nodes}
            unique_related = []
            for node in related_nodes:
                if node.id not in seen_ids:
                    unique_related.append(node)
                    seen_ids.add(node.id)
            
            # Get context from domains
            context_nodes = []
            domains_covered = set()
            for node in primary_nodes + unique_related:
                if node.domain not in domains_covered:
                    domain_nodes = self.memory_tree.get_nodes_by_domain(node.domain)
                    context_nodes.extend(domain_nodes[:2])
                    domains_covered.add(node.domain)
            
            return CognitiveRetrieval(
                query=query,
                primary_nodes=primary_nodes,
                related_nodes=unique_related[:max_nodes//3],
                context_nodes=context_nodes[:max_nodes//3],
                retrieval_strategy=RetrievalStrategy.SYMBOLIC_LINKS,
                query_complexity=analysis.get("complexity", QueryComplexity.SIMPLE),
                retrieval_time=time.time() - method_start_time,
                confidence_score=self._calculate_confidence(primary_nodes + unique_related, analysis) if hasattr(self, '_calculate_confidence') else 0.5,
                cross_domain_connections=len(domains_covered),
                symbolic_links_traversed=symbolic_links_traversed,
                hierarchical_depth=1
            )
        except Exception as e:
            # Return empty retrieval result
            logger.warning(f"Symbolic link retrieval failed for query '{query}': {e}")
            return CognitiveRetrieval(
                query=query,
                primary_nodes=[],
                related_nodes=[],
                context_nodes=[],
                retrieval_strategy=RetrievalStrategy.SYMBOLIC_LINKS,
                query_complexity=QueryComplexity.SIMPLE,
                retrieval_time=time.time() - method_start_time,
                confidence_score=0.0,
                cross_domain_connections=0,
                symbolic_links_traversed=0,
                hierarchical_depth=1,
                retrieval_error=str(e)
            )
    
    def _domain_crossing_retrieval(self, query: str, analysis: Dict[str, Any],
                                  max_nodes: int, min_confidence: float) -> CognitiveRetrieval:
        """Retrieve across multiple domains."""
        method_start_time = time.time()
        primary_nodes = []
        domains_covered = set()
        
        # Get nodes from each identified domain
        for domain in analysis["domains"][:3]:  # Limit to top 3 domains
            domain_nodes = self.memory_tree.get_nodes_by_domain(domain)
            
            # Filter by keywords
            filtered_nodes = []
            for node in domain_nodes:
                if any(keyword in " ".join(node.keywords).lower() 
                      for keyword in analysis["keywords"]):
                    filtered_nodes.append(node)
            
            # Add best matches from this domain
            primary_nodes.extend(filtered_nodes[:max_nodes//len(analysis["domains"])])
            domains_covered.add(domain)
        
        # Find connections between domains
        related_nodes = []
        cross_domain_connections = 0
        
        for i, node1 in enumerate(primary_nodes[:5]):
            for node2 in primary_nodes[i+1:5]:
                if node1.domain != node2.domain:
                    # Check if nodes are linked
                    links1 = node1.get_linked_nodes()
                    links2 = node2.get_linked_nodes()
                    
                    # Check for direct or indirect connections
                    if (any(link[0] == node2.id for link in links1) or
                        any(link[0] == node1.id for link in links2)):
                        cross_domain_connections += 1
        
        return CognitiveRetrieval(
            query=query,
            primary_nodes=primary_nodes,
            related_nodes=related_nodes,
            context_nodes=[],
            retrieval_strategy=RetrievalStrategy.DOMAIN_CROSSING,
            query_complexity=analysis["complexity"],
            retrieval_time=time.time() - method_start_time,
            confidence_score=self._calculate_confidence(primary_nodes, analysis),
            cross_domain_connections=cross_domain_connections,
            symbolic_links_traversed=0,
            hierarchical_depth=analysis["expected_depth"]
        )
    
    def _keyword_expansion_retrieval(self, query: str, analysis: Dict[str, Any],
                                    max_nodes: int, min_confidence: float) -> CognitiveRetrieval:
        """Retrieve by expanding keywords."""
        method_start_time = time.time()
        # Start with original keywords
        original_nodes = self.memory_tree.search_by_keywords(analysis["keywords"])
        primary_nodes = original_nodes[:max_nodes//2]
        
        # Expand keywords
        expanded_keywords = self._expand_keywords(analysis["keywords"], primary_nodes)
        
        # Search with expanded keywords
        expanded_nodes = self.memory_tree.search_by_keywords(expanded_keywords)
        
        # Combine and deduplicate
        all_nodes = primary_nodes + expanded_nodes
        seen_ids = set()
        combined_nodes = []
        
        for node in all_nodes:
            if node.id not in seen_ids:
                combined_nodes.append(node)
                seen_ids.add(node.id)
        
        # Split into primary and related
        primary_nodes = combined_nodes[:max_nodes//2]
        related_nodes = combined_nodes[max_nodes//2:max_nodes]
        
        return CognitiveRetrieval(
            query=query,
            primary_nodes=primary_nodes,
            related_nodes=related_nodes,
            context_nodes=[],
            retrieval_strategy=RetrievalStrategy.KEYWORD_EXPANSION,
            query_complexity=analysis["complexity"],
            retrieval_time=time.time() - method_start_time,
            confidence_score=self._calculate_confidence(primary_nodes, analysis),
            cross_domain_connections=0,
            symbolic_links_traversed=0,
            hierarchical_depth=1
        )
    
    def _contextual_retrieval(self, query: str, analysis: Dict[str, Any],
                             max_nodes: int, min_confidence: float) -> CognitiveRetrieval:
        """Retrieve using contextual understanding."""
        method_start_time = time.time()
        
        try:
            # This is a simplified version - in practice would use LLM
            # to understand query context better
            
            # Start with standard retrieval
            base_result = self._hierarchical_retrieval(query, analysis, max_nodes, min_confidence)
            
            # Add contextual nodes based on query understanding
            context_nodes = []
            
            # Look for narrative context
            if any(word in query.lower() for word in ["story", "narrative", "tale", "saga"]):
                narrative_nodes = self.memory_tree.get_nodes_by_type(MemoryType.NARRATIVE)
                context_nodes.extend(narrative_nodes[:3])
            
            # Look for character context
            if any(word in query.lower() for word in ["character", "npc", "person", "villager"]):
                character_nodes = self.memory_tree.get_nodes_by_type(MemoryType.CHARACTER)
                context_nodes.extend(character_nodes[:3])
            
            # Look for location context
            if any(word in query.lower() for word in ["location", "place", "city", "village"]):
                location_nodes = self.memory_tree.get_nodes_by_type(MemoryType.LOCATION)
                context_nodes.extend(location_nodes[:3])
            
            base_result.context_nodes.extend(context_nodes[:5])
            
            return base_result
        except Exception as e:
            # Return empty retrieval result
            logger.warning(f"Contextual retrieval failed for query '{query}': {e}")
            return CognitiveRetrieval(
                query=query,
                primary_nodes=[],
                related_nodes=[],
                context_nodes=[],
                retrieval_strategy=RetrievalStrategy.CONTEXTUAL,
                query_complexity=QueryComplexity.SIMPLE,
                retrieval_time=time.time() - method_start_time,
                confidence_score=0.0,
                cross_domain_connections=0,
                symbolic_links_traversed=0,
                hierarchical_depth=1,
                retrieval_error=str(e)
            )
    
    def _hybrid_retrieval(self, query: str, analysis: Dict[str, Any],
                         max_nodes: int, min_confidence: float) -> CognitiveRetrieval:
        """Combine multiple retrieval strategies."""
        method_start_time = time.time()
        
        try:
            # Get results from multiple strategies
            hierarchical_result = self._hierarchical_retrieval(
                query, analysis, max_nodes//3, min_confidence
            )
            symbolic_result = self._symbolic_link_retrieval(
                query, analysis, max_nodes//3, min_confidence
            )
            domain_result = self._domain_crossing_retrieval(
                query, analysis, max_nodes//3, min_confidence
            )
            
            # Combine results
            all_nodes = (
                hierarchical_result.primary_nodes +
                symbolic_result.primary_nodes +
                domain_result.primary_nodes
            )
            
            # Deduplicate
            seen_ids = set()
            primary_nodes = []
            for node in all_nodes:
                if node.id not in seen_ids:
                    primary_nodes.append(node)
                    seen_ids.add(node.id)
            
            # Combine related nodes
            related_nodes = (
                hierarchical_result.related_nodes +
                symbolic_result.related_nodes +
                domain_result.related_nodes
            )
            
            # Deduplicate related nodes
            related_nodes_dedup = []
            for node in related_nodes:
                if node.id not in seen_ids:
                    related_nodes_dedup.append(node)
                    seen_ids.add(node.id)
            
            # Combine context nodes
            context_nodes = (
                hierarchical_result.context_nodes +
                symbolic_result.context_nodes +
                domain_result.context_nodes
            )
            
            # Deduplicate context nodes
            context_nodes_dedup = []
            for node in context_nodes:
                if node.id not in seen_ids:
                    context_nodes_dedup.append(node)
                    seen_ids.add(node.id)
            
            # Calculate combined statistics
            cross_domain = (
                hierarchical_result.cross_domain_connections +
                symbolic_result.cross_domain_connections +
                domain_result.cross_domain_connections
            )
            
            symbolic_links = (
                hierarchical_result.symbolic_links_traversed +
                symbolic_result.symbolic_links_traversed +
                domain_result.symbolic_links_traversed
            )
            
            confidence = max(
                hierarchical_result.confidence_score,
                symbolic_result.confidence_score,
                domain_result.confidence_score
            )
            
            return CognitiveRetrieval(
                query=query,
                primary_nodes=primary_nodes[:max_nodes//2],
                related_nodes=related_nodes_dedup[:max_nodes//4],
                context_nodes=context_nodes_dedup[:max_nodes//4],
                retrieval_strategy=RetrievalStrategy.HYBRID,
                query_complexity=analysis.get("complexity", QueryComplexity.SIMPLE),
                retrieval_time=time.time() - method_start_time,
                confidence_score=confidence,
                cross_domain_connections=cross_domain,
                symbolic_links_traversed=symbolic_links,
                hierarchical_depth=max(
                    hierarchical_result.hierarchical_depth,
                    symbolic_result.hierarchical_depth,
                    domain_result.hierarchical_depth
                )
            )
        except Exception as e:
            # Return empty retrieval result
            logger.warning(f"Hybrid retrieval failed for query '{query}': {e}")
            return CognitiveRetrieval(
                query=query,
                primary_nodes=[],
                related_nodes=[],
                context_nodes=[],
                retrieval_strategy=RetrievalStrategy.HYBRID,
                query_complexity=QueryComplexity.SIMPLE,
                retrieval_time=time.time() - method_start_time,
                confidence_score=0.0,
                cross_domain_connections=0,
                symbolic_links_traversed=0,
                hierarchical_depth=1,
                retrieval_error=str(e)
            )
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query."""
        # Simple keyword extraction - could be enhanced with NLP
        words = re.findall(r'\b\w+\b', query.lower())
        
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", 
                     "to", "for", "of", "with", "by", "is", "are", "was", "were"}
        
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Add n-grams
        for i in range(len(words) - 1):
            bigram = f"{words[i]}_{words[i+1]}"
            if words[i] not in stop_words and words[i+1] not in stop_words:
                keywords.append(bigram)
        
        return list(set(keywords))
    
    def _identify_domains(self, query: str) -> List[NodeDomain]:
        """Identify relevant domains for a query."""
        query_lower = query.lower()
        domains = []
        
        # Map keywords to domains
        domain_keywords = {
            NodeDomain.CHARACTERS: ["character", "npc", "person", "villager", "warrior"],
            NodeDomain.LOCATIONS: ["location", "place", "city", "village", "forest"],
            NodeDomain.QUESTS: ["quest", "mission", "task", "objective"],
            NodeDomain.WORLD_KNOWLEDGE: ["world", "lore", "history", "knowledge"],
            NodeDomain.SOCIAL_PROTOCOLS: ["social", "protocol", "custom", "tradition"],
            NodeDomain.CULTURAL_PRACTICES: ["culture", "practice", "ritual", "ceremony"],
            NodeDomain.HISTORICAL_EVENTS: ["history", "event", "battle", "war"],
            NodeDomain.MYTHOLOGY: ["myth", "god", "goddess", "legend"],
            NodeDomain.MAGIC_SYSTEMS: ["magic", "spell", "rune", "trolldom"],
            NodeDomain.COMBAT_RULES: ["combat", "fight", "battle", "attack"],
            NodeDomain.TRADE_ECONOMY: ["trade", "economy", "coin", "merchant"],
            NodeDomain.RELIGION: ["religion", "faith", "worship", "temple"],
            NodeDomain.DAILY_LIFE: ["daily", "life", "food", "clothing", "house"]
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                domains.append(domain)
        
        # Default to world knowledge if no specific domain found
        if not domains:
            domains.append(NodeDomain.WORLD_KNOWLEDGE)
        
        return domains
    
    def _identify_memory_types(self, query: str) -> List[MemoryType]:
        """Identify relevant memory types for a query."""
        query_lower = query.lower()
        types = []
        
        # Map keywords to memory types
        type_keywords = {
            MemoryType.FACT: ["fact", "information", "detail"],
            MemoryType.ENTITY: ["entity", "thing", "object", "item"],
            MemoryType.EVENT: ["event", "happening", "occurrence"],
            MemoryType.RELATIONSHIP: ["relationship", "connection", "link"],
            MemoryType.RULE: ["rule", "law", "principle"],
            MemoryType.PROTOCOL: ["protocol", "procedure", "method"],
            MemoryType.CHARACTER: ["character", "person", "npc"],
            MemoryType.LOCATION: ["location", "place", "area"],
            MemoryType.QUEST: ["quest", "mission", "task"],
            MemoryType.DIALOGUE: ["dialogue", "conversation", "speech"],
            MemoryType.NARRATIVE: ["narrative", "story", "tale"],
            MemoryType.WORLD_KNOWLEDGE: ["world", "lore", "knowledge"]
        }
        
        for mem_type, keywords in type_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                types.append(mem_type)
        
        # Default to fact if no specific type found
        if not types:
            types.append(MemoryType.FACT)
        
        return types
    
    def _assess_complexity(self, query: str) -> QueryComplexity:
        """Assess query complexity."""
        word_count = len(query.split())
        
        if word_count < 5:
            return QueryComplexity.SIMPLE
        elif word_count < 10:
            return QueryComplexity.MODERATE
        elif word_count < 20:
            return QueryComplexity.COMPLEX
        else:
            return QueryComplexity.DEEP
    
    def _estimate_depth(self, query: str) -> int:
        """Estimate required hierarchical depth for query."""
        # Simple heuristic based on query complexity
        complexity = self._assess_complexity(query)
        
        depth_map = {
            QueryComplexity.SIMPLE: 1,
            QueryComplexity.MODERATE: 2,
            QueryComplexity.COMPLEX: 3,
            QueryComplexity.DEEP: 4
        }
        
        return depth_map[complexity]
    
    def _requires_cross_domain(self, query: str) -> bool:
        """Determine if query requires cross-domain retrieval."""
        domains = self._identify_domains(query)
        return len(domains) > 1
    
    def _determine_strategy(self, analysis: Dict[str, Any]) -> RetrievalStrategy:
        """Determine best retrieval strategy for query analysis."""
        if analysis["requires_cross_domain"]:
            return RetrievalStrategy.DOMAIN_CROSSING
        
        if analysis["complexity"] == QueryComplexity.DEEP:
            return RetrievalStrategy.HYBRID
        
        if analysis["expected_depth"] > 2:
            return RetrievalStrategy.HIERARCHICAL
        
        # Check if symbolic links would be useful
        if any(mem_type in [MemoryType.RELATIONSHIP, MemoryType.ENTITY] 
              for mem_type in analysis["memory_types"]):
            return RetrievalStrategy.SYMBOLIC_LINKS
        
        return RetrievalStrategy.KEYWORD_EXPANSION
    
    def _expand_keywords(self, original_keywords: List[str], 
                        context_nodes: List[MemoryNode]) -> List[str]:
        """Expand keywords based on context nodes."""
        expanded = set(original_keywords)
        
        for node in context_nodes[:5]:
            # Add node keywords
            expanded.update(node.keywords)
            
            # Add tags
            expanded.update(node.tags)
            
            # Extract words from content
            if isinstance(node.content, str):
                content_words = re.findall(r'\b\w+\b', node.content.lower())
                expanded.update([w for w in content_words if len(w) > 3][:10])
        
        return list(expanded)
    
    def _calculate_confidence(self, nodes: List[MemoryNode], 
                             analysis: Dict[str, Any]) -> float:
        """Calculate confidence score for retrieval results."""
        if not nodes:
            return 0.0
        
        # Base confidence on node importance and relevance
        total_importance = sum(node.importance for node in nodes)
        avg_importance = total_importance / len(nodes)
        
        # Normalize to 0-1 range (importance is 1-10)
        importance_score = avg_importance / 10.0
        
        # Factor in query complexity
        complexity_factor = {
            QueryComplexity.SIMPLE: 1.0,
            QueryComplexity.MODERATE: 0.9,
            QueryComplexity.COMPLEX: 0.8,
            QueryComplexity.DEEP: 0.7
        }[analysis["complexity"]]
        
        return min(importance_score * complexity_factor, 1.0)
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get performance statistics for all strategies."""
        stats = {}
        
        for strategy, times in self._strategy_performance.items():
            if times:
                stats[strategy.value] = {
                    "total_queries": len(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times)
                }
            else:
                stats[strategy.value] = {
                    "total_queries": 0,
                    "avg_time": 0,
                    "min_time": 0,
                    "max_time": 0
                }
        
        # Domain expertise
        total_queries = sum(self._domain_expertise.values())
        if total_queries > 0:
            domain_percentages = {
                domain.value: (count / total_queries) * 100
                for domain, count in self._domain_expertise.items()
                if count > 0
            }
            stats["domain_expertise"] = domain_percentages
        
        return stats
    
    def clear_cache(self):
        """Clear query cache."""
        self._query_cache.clear()
    
    def optimize_strategy(self, feedback: Dict[str, Any]):
        """
        Optimize retrieval strategy based on feedback.
        
        Args:
            feedback: Dictionary with feedback data including:
                - query: Original query
                - strategy: Strategy used
                - success_score: 0.0 to 1.0
                - retrieval_time: Time taken
        """
        # In a real implementation, this would adjust strategy selection
        # based on historical performance
        logger.info(f"Received feedback for optimization: {feedback}")