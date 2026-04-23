"""
Domain Crosslinker
==================

System for creating and managing symbolic links across domains.
Automatically discovers relationships between nodes in different domains
and creates symbolic links to enable cross-domain retrieval.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .hierarchical_memory import (
    HierarchicalMemoryTree, MemoryNode, SymbolicLink,
    NodeDomain
)

logger = logging.getLogger(__name__)


class RelationshipType(Enum):
    """Types of relationships between nodes."""
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    CAUSES = "causes"
    INFLUENCES = "influences"
    SIMILAR_TO = "similar_to"
    OPPOSITE_OF = "opposite_of"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    CONTAINS = "contains"
    LOCATED_IN = "located_in"
    BELONGS_TO = "belongs_to"
    CREATED_BY = "created_by"
    USES = "uses"
    AFFECTS = "affects"
    MENTIONS = "mentions"


@dataclass
class CrossDomainQuery:
    """A query that spans multiple domains."""
    query: str
    source_domain: NodeDomain
    target_domains: List[NodeDomain]
    relationship_types: List[RelationshipType]
    min_confidence: float = 0.5
    max_links: int = 10
    results: List[Tuple[MemoryNode, MemoryNode, RelationshipType, float]] = field(default_factory=list)


class DomainCrosslinker:
    """
    System for discovering and creating cross-domain relationships.
    
    Automatically analyzes nodes across domains to find:
    - Semantic similarities
    - Structural relationships
    - Temporal connections
    - Causal links
    - Thematic associations
    """
    
    def __init__(self, memory_tree: HierarchicalMemoryTree):
        """
        Initialize domain crosslinker.
        
        Args:
            memory_tree: Hierarchical memory tree to work with
        """
        self.memory_tree = memory_tree
        
        # Relationship patterns
        self._relationship_patterns: Dict[RelationshipType, List[str]] = {
            RelationshipType.RELATED_TO: ["related", "connected", "associated", "linked"],
            RelationshipType.PART_OF: ["part of", "component of", "element of", "member of"],
            RelationshipType.CAUSES: ["causes", "leads to", "results in", "triggers"],
            RelationshipType.INFLUENCES: ["influences", "affects", "impacts", "shapes"],
            RelationshipType.SIMILAR_TO: ["similar to", "like", "resembles", "analogous to"],
            RelationshipType.OPPOSITE_OF: ["opposite of", "contrary to", "inverse of"],
            RelationshipType.PRECEDES: ["precedes", "comes before", "prior to"],
            RelationshipType.FOLLOWS: ["follows", "comes after", "subsequent to"],
            RelationshipType.CONTAINS: ["contains", "includes", "holds", "encompasses"],
            RelationshipType.LOCATED_IN: ["located in", "situated in", "found in", "placed in"],
            RelationshipType.BELONGS_TO: ["belongs to", "owned by", "property of"],
            RelationshipType.CREATED_BY: ["created by", "made by", "built by", "crafted by"],
            RelationshipType.USES: ["uses", "employs", "utilizes", "applies"],
            RelationshipType.AFFECTS: ["affects", "changes", "modifies", "alters"],
            RelationshipType.MENTIONS: ["mentions", "references", "cites", "names"]
        }
        
        # Domain compatibility matrix
        self._domain_compatibility: Dict[Tuple[NodeDomain, NodeDomain], float] = {
            # Characters relate to many domains
            (NodeDomain.CHARACTERS, NodeDomain.LOCATIONS): 0.8,
            (NodeDomain.CHARACTERS, NodeDomain.QUESTS): 0.9,
            (NodeDomain.CHARACTERS, NodeDomain.SOCIAL_PROTOCOLS): 0.7,
            (NodeDomain.CHARACTERS, NodeDomain.CULTURAL_PRACTICES): 0.6,
            (NodeDomain.CHARACTERS, NodeDomain.HISTORICAL_EVENTS): 0.5,
            
            # Locations relate to characters and events
            (NodeDomain.LOCATIONS, NodeDomain.CHARACTERS): 0.8,
            (NodeDomain.LOCATIONS, NodeDomain.HISTORICAL_EVENTS): 0.7,
            (NodeDomain.LOCATIONS, NodeDomain.QUESTS): 0.6,
            (NodeDomain.LOCATIONS, NodeDomain.WORLD_KNOWLEDGE): 0.5,
            
            # Quests connect characters, locations, and events
            (NodeDomain.QUESTS, NodeDomain.CHARACTERS): 0.9,
            (NodeDomain.QUESTS, NodeDomain.LOCATIONS): 0.6,
            (NodeDomain.QUESTS, NodeDomain.HISTORICAL_EVENTS): 0.7,
            
            # World knowledge connects to everything
            (NodeDomain.WORLD_KNOWLEDGE, NodeDomain.CHARACTERS): 0.6,
            (NodeDomain.WORLD_KNOWLEDGE, NodeDomain.LOCATIONS): 0.5,
            (NodeDomain.WORLD_KNOWLEDGE, NodeDomain.HISTORICAL_EVENTS): 0.8,
            (NodeDomain.WORLD_KNOWLEDGE, NodeDomain.MYTHOLOGY): 0.9,
            (NodeDomain.WORLD_KNOWLEDGE, NodeDomain.CULTURAL_PRACTICES): 0.7,
            
            # Mythology relates to religion and cultural practices
            (NodeDomain.MYTHOLOGY, NodeDomain.RELIGION): 0.9,
            (NodeDomain.MYTHOLOGY, NodeDomain.CULTURAL_PRACTICES): 0.8,
            (NodeDomain.MYTHOLOGY, NodeDomain.WORLD_KNOWLEDGE): 0.9,
            
            # Cultural practices relate to social protocols and daily life
            (NodeDomain.CULTURAL_PRACTICES, NodeDomain.SOCIAL_PROTOCOLS): 0.8,
            (NodeDomain.CULTURAL_PRACTICES, NodeDomain.DAILY_LIFE): 0.7,
            (NodeDomain.CULTURAL_PRACTICES, NodeDomain.RELIGION): 0.6,
            
            # Social protocols relate to characters and cultural practices
            (NodeDomain.SOCIAL_PROTOCOLS, NodeDomain.CHARACTERS): 0.7,
            (NodeDomain.SOCIAL_PROTOCOLS, NodeDomain.CULTURAL_PRACTICES): 0.8,
            (NodeDomain.SOCIAL_PROTOCOLS, NodeDomain.DAILY_LIFE): 0.6,
            
            # Historical events relate to locations and characters
            (NodeDomain.HISTORICAL_EVENTS, NodeDomain.LOCATIONS): 0.7,
            (NodeDomain.HISTORICAL_EVENTS, NodeDomain.CHARACTERS): 0.5,
            (NodeDomain.HISTORICAL_EVENTS, NodeDomain.WORLD_KNOWLEDGE): 0.8,
            
            # Magic systems relate to mythology and religion
            (NodeDomain.MAGIC_SYSTEMS, NodeDomain.MYTHOLOGY): 0.8,
            (NodeDomain.MAGIC_SYSTEMS, NodeDomain.RELIGION): 0.7,
            (NodeDomain.MAGIC_SYSTEMS, NodeDomain.CULTURAL_PRACTICES): 0.6,
            
            # Combat rules relate to characters and locations
            (NodeDomain.COMBAT_RULES, NodeDomain.CHARACTERS): 0.7,
            (NodeDomain.COMBAT_RULES, NodeDomain.LOCATIONS): 0.5,
            (NodeDomain.COMBAT_RULES, NodeDomain.HISTORICAL_EVENTS): 0.6,
            
            # Trade economy relates to locations and daily life
            (NodeDomain.TRADE_ECONOMY, NodeDomain.LOCATIONS): 0.7,
            (NodeDomain.TRADE_ECONOMY, NodeDomain.DAILY_LIFE): 0.8,
            (NodeDomain.TRADE_ECONOMY, NodeDomain.CHARACTERS): 0.6,
            
            # Religion relates to mythology and cultural practices
            (NodeDomain.RELIGION, NodeDomain.MYTHOLOGY): 0.9,
            (NodeDomain.RELIGION, NodeDomain.CULTURAL_PRACTICES): 0.7,
            (NodeDomain.RELIGION, NodeDomain.SOCIAL_PROTOCOLS): 0.6,
            
            # Daily life relates to cultural practices and characters
            (NodeDomain.DAILY_LIFE, NodeDomain.CULTURAL_PRACTICES): 0.7,
            (NodeDomain.DAILY_LIFE, NodeDomain.CHARACTERS): 0.8,
            (NodeDomain.DAILY_LIFE, NodeDomain.TRADE_ECONOMY): 0.8,
        }
        
        # Make matrix symmetric
        symmetric_matrix = {}
        for (domain1, domain2), score in self._domain_compatibility.items():
            symmetric_matrix[(domain1, domain2)] = score
            symmetric_matrix[(domain2, domain1)] = score
        
        self._domain_compatibility = symmetric_matrix
    
    def find_cross_domain_relationships(self, source_node: MemoryNode,
                                       target_domain: NodeDomain,
                                       min_confidence: float = 0.3,
                                       max_results: int = 5) -> List[Tuple[MemoryNode, RelationshipType, float]]:
        """
        Find relationships between a source node and nodes in another domain.
        
        Args:
            source_node: Source node to find relationships from
            target_domain: Domain to find relationships to
            min_confidence: Minimum confidence score for relationships
            max_results: Maximum number of results to return
            
        Returns:
            List of (target_node, relationship_type, confidence_score) tuples
        """
        results = []
        
        # Get base compatibility score
        domain_pair = (source_node.domain, target_domain)
        base_compatibility = self._domain_compatibility.get(domain_pair, 0.1)
        
        if base_compatibility < min_confidence:
            return results
        
        # Get nodes from target domain
        target_nodes = self.memory_tree.get_nodes_by_domain(target_domain)
        
        for target_node in target_nodes:
            if target_node.id == source_node.id:
                continue
            
            # Analyze relationship
            relationship, confidence = self._analyze_relationship(
                source_node, target_node, base_compatibility
            )
            
            if relationship and confidence >= min_confidence:
                results.append((target_node, relationship, confidence))
        
        # Sort by confidence and limit results
        results.sort(key=lambda x: x[2], reverse=True)
        return results[:max_results]
    
    def create_cross_domain_links(self, source_node: MemoryNode,
                                 target_domain: NodeDomain,
                                 min_confidence: float = 0.5,
                                 max_links: int = 3) -> List[SymbolicLink]:
        """
        Create symbolic links between source node and nodes in another domain.
        
        Args:
            source_node: Source node to create links from
            target_domain: Domain to create links to
            min_confidence: Minimum confidence score for creating links
            max_links: Maximum number of links to create
            
        Returns:
            List of created symbolic links
        """
        created_links = []
        
        # Find relationships
        relationships = self.find_cross_domain_relationships(
            source_node, target_domain, min_confidence, max_links
        )
        
        for target_node, relationship_type, confidence in relationships:
            # Check if link already exists
            existing_link = False
            for link in source_node.symbolic_links:
                if link.target_node_id == target_node.id:
                    existing_link = True
                    break
            
            if not existing_link:
                # Create symbolic link
                link = SymbolicLink(
                    source_node_id=source_node.id,
                    target_node_id=target_node.id,
                    link_type=relationship_type.value,
                    strength=confidence,
                    bidirectional=True,
                    metadata={
                        "created_by": "domain_crosslinker",
                        "confidence": confidence,
                        "source_domain": source_node.domain.value,
                        "target_domain": target_node.domain.value
                    }
                )
                
                source_node.symbolic_links.append(link)
                
                # Create reciprocal link if bidirectional
                if link.bidirectional:
                    reciprocal_link = SymbolicLink(
                        source_node_id=target_node.id,
                        target_node_id=source_node.id,
                        link_type=relationship_type.value,
                        strength=confidence,
                        bidirectional=True,
                        metadata={
                            "created_by": "domain_crosslinker",
                            "confidence": confidence,
                            "source_domain": target_node.domain.value,
                            "target_domain": source_node.domain.value
                        }
                    )
                    target_node.symbolic_links.append(reciprocal_link)
                
                created_links.append(link)
                logger.info(f"Created cross-domain link: {source_node.id} -> {target_node.id} "
                          f"({relationship_type.value}, confidence: {confidence:.2f})")
        
        return created_links
    
    def analyze_cross_domain_query(self, query: str) -> CrossDomainQuery:
        """
        Analyze a query to determine cross-domain requirements.
        
        Args:
            query: The query to analyze
            
        Returns:
            CrossDomainQuery object with analysis results
        """
        # Extract domains from query
        domains = self._extract_domains_from_query(query)
        
        if len(domains) < 2:
            # Single domain query
            return CrossDomainQuery(
                query=query,
                source_domain=domains[0] if domains else NodeDomain.WORLD_KNOWLEDGE,
                target_domains=[],
                relationship_types=[]
            )
        
        # Multi-domain query
        source_domain = domains[0]
        target_domains = domains[1:]
        
        # Extract relationship indicators
        relationship_types = self._extract_relationships_from_query(query)
        
        return CrossDomainQuery(
            query=query,
            source_domain=source_domain,
            target_domains=target_domains,
            relationship_types=relationship_types
        )
    
    def execute_cross_domain_query(self, cross_query: CrossDomainQuery) -> CrossDomainQuery:
        """
        Execute a cross-domain query.
        
        Args:
            cross_query: CrossDomainQuery object
            
        Returns:
            Updated CrossDomainQuery with results
        """
        if not cross_query.target_domains:
            return cross_query
        
        # Find source nodes related to query
        source_nodes = self._find_source_nodes(cross_query)
        
        # Find cross-domain relationships
        all_results = []
        
        for source_node in source_nodes:
            for target_domain in cross_query.target_domains:
                relationships = self.find_cross_domain_relationships(
                    source_node, target_domain,
                    cross_query.min_confidence, cross_query.max_links
                )
                
                for target_node, relationship, confidence in relationships:
                    # Filter by relationship type if specified
                    if (cross_query.relationship_types and 
                        relationship not in cross_query.relationship_types):
                        continue
                    
                    all_results.append((source_node, target_node, relationship, confidence))
        
        # Sort by confidence
        all_results.sort(key=lambda x: x[3], reverse=True)
        
        # Update query with results
        cross_query.results = all_results[:cross_query.max_links]
        return cross_query
    
    def discover_all_cross_domain_links(self, min_confidence: float = 0.4,
                                       max_links_per_node: int = 5):
        """
        Discover and create cross-domain links for all nodes.
        
        Args:
            min_confidence: Minimum confidence score for creating links
            max_links_per_node: Maximum links to create per node
        """
        total_links_created = 0
        
        for node_id, node in list(self.memory_tree.nodes.items()):
            # Skip if node already has many links
            if len(node.symbolic_links) >= max_links_per_node * 2:
                continue
            
            # Find compatible domains
            compatible_domains = []
            for target_domain in NodeDomain:
                if target_domain == node.domain:
                    continue
                
                domain_pair = (node.domain, target_domain)
                if self._domain_compatibility.get(domain_pair, 0) >= min_confidence:
                    compatible_domains.append(target_domain)
            
            # Create links to compatible domains
            for target_domain in compatible_domains[:2]:  # Limit to top 2 domains
                created_links = self.create_cross_domain_links(
                    node, target_domain, min_confidence, max_links_per_node // 2
                )
                total_links_created += len(created_links)
        
        logger.info(f"Created {total_links_created} cross-domain links")
        return total_links_created
    
    def _analyze_relationship(self, source_node: MemoryNode,
                             target_node: MemoryNode,
                             base_compatibility: float) -> Tuple[Optional[RelationshipType], float]:
        """
        Analyze relationship between two nodes.
        
        Returns:
            Tuple of (relationship_type, confidence_score) or (None, 0.0)
        """
        # Check content for relationship indicators
        source_content = str(source_node.content).lower()
        target_content = str(target_node.content).lower()
        
        best_relationship = None
        best_confidence = 0.0
        
        for relationship_type, patterns in self._relationship_patterns.items():
            # Check if patterns appear in content
            pattern_found = False
            for pattern in patterns:
                if (pattern in source_content and 
                    any(word in target_content for word in self._get_related_words(pattern))):
                    pattern_found = True
                    break
            
            if pattern_found:
                # Calculate confidence
                confidence = base_compatibility * 0.7  # Base from domain compatibility
                
                # Boost confidence based on node importance
                importance_factor = (source_node.importance + target_node.importance) / 20.0
                confidence += importance_factor * 0.3
                
                if confidence > best_confidence:
                    best_relationship = relationship_type
                    best_confidence = confidence
        
        # Check for semantic similarity
        if not best_relationship:
            similarity = self._calculate_semantic_similarity(source_node, target_node)
            if similarity > 0.6:
                best_relationship = RelationshipType.SIMILAR_TO
                best_confidence = similarity * base_compatibility
        
        return best_relationship, best_confidence
    
    def _calculate_semantic_similarity(self, node1: MemoryNode,
                                      node2: MemoryNode) -> float:
        """Calculate semantic similarity between two nodes."""
        # Simple keyword overlap
        keywords1 = set(node1.keywords)
        keywords2 = set(node2.keywords)
        
        if not keywords1 or not keywords2:
            return 0.0
        
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _get_related_words(self, pattern: str) -> List[str]:
        """Get words related to a pattern for matching."""
        # Simple word expansion - could be enhanced with word embeddings
        word_map = {
            "related": ["connection", "association", "link"],
            "part of": ["component", "element", "member"],
            "causes": ["leads to", "results in", "triggers"],
            "influences": ["affects", "impacts", "shapes"],
            "similar to": ["like", "resembles", "analogous"],
            "opposite of": ["contrary", "inverse", "reverse"],
            "precedes": ["comes before", "prior to", "earlier"],
            "follows": ["comes after", "subsequent", "later"],
            "contains": ["includes", "holds", "encompasses"],
            "located in": ["situated in", "found in", "placed in"],
            "belongs to": ["owned by", "property of", "part of"],
            "created by": ["made by", "built by", "crafted by"],
            "uses": ["employs", "utilizes", "applies"],
            "affects": ["changes", "modifies", "alters"],
            "mentions": ["references", "cites", "names"]
        }
        
        return word_map.get(pattern, [])
    
    def _extract_domains_from_query(self, query: str) -> List[NodeDomain]:
        """Extract domains mentioned in a query."""
        query_lower = query.lower()
        domains = []
        
        domain_keywords = {
            NodeDomain.CHARACTERS: ["character", "npc", "person", "warrior", "merchant"],
            NodeDomain.LOCATIONS: ["location", "place", "city", "village", "forest"],
            NodeDomain.QUESTS: ["quest", "mission", "task", "objective"],
            NodeDomain.WORLD_KNOWLEDGE: ["world", "lore", "knowledge", "information"],
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
        
        # Default to world knowledge if no domains found
        if not domains:
            domains.append(NodeDomain.WORLD_KNOWLEDGE)
        
        return domains
    
    def _extract_relationships_from_query(self, query: str) -> List[RelationshipType]:
        """Extract relationship indicators from query."""
        query_lower = query.lower()
        relationships = []
        
        for relationship_type, patterns in self._relationship_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                relationships.append(relationship_type)
        
        return relationships
    
    def _find_source_nodes(self, cross_query: CrossDomainQuery) -> List[MemoryNode]:
        """Find source nodes relevant to a cross-domain query."""
        # Extract keywords from query
        keywords = re.findall(r'\b\w+\b', cross_query.query.lower())
        keywords = [kw for kw in keywords if len(kw) > 3][:10]
        
        # Search for nodes in source domain
        source_nodes = self.memory_tree.get_nodes_by_domain(cross_query.source_domain)
        
        # Filter by keywords
        filtered_nodes = []
        for node in source_nodes:
            node_keywords = " ".join(node.keywords).lower()
            if any(keyword in node_keywords for keyword in keywords):
                filtered_nodes.append(node)
        
        # If no keyword matches, return top nodes by importance
        if not filtered_nodes:
            source_nodes.sort(key=lambda n: n.importance, reverse=True)
            return source_nodes[:5]
        
        return filtered_nodes[:10]
    
    def get_domain_connectivity(self) -> Dict[str, Any]:
        """Get statistics about domain connectivity."""
        connectivity = {}
        
        for domain1 in NodeDomain:
            for domain2 in NodeDomain:
                if domain1 == domain2:
                    continue
                
                pair = (domain1, domain2)
                if pair in self._domain_compatibility:
                    connectivity[f"{domain1.value}_{domain2.value}"] = {
                        "compatibility": self._domain_compatibility[pair],
                        "links_count": self._count_links_between_domains(domain1, domain2)
                    }
        
        return connectivity
    
    def _count_links_between_domains(self, domain1: NodeDomain,
                                    domain2: NodeDomain) -> int:
        """Count symbolic links between two domains."""
        count = 0
        
        for node in self.memory_tree.nodes.values():
            if node.domain != domain1:
                continue
            
            for link in node.symbolic_links:
                target_node = self.memory_tree.get_node(link.target_node_id)
                if target_node and target_node.domain == domain2:
                    count += 1
        
        return count