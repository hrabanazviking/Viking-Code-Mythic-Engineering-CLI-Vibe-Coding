"""
Yggdrasil Cognition Integration Layer
======================================

Integrates the advanced hierarchical memory system with the Yggdrasil router.
This provides the router with access to the Huginn/Muninn cognitive system
for intelligent memory retrieval and cross-domain linking.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from .cognition import (
    MemoryOrchestrator,
    NodeDomain,
    MemoryType
)

logger = logging.getLogger(__name__)


class YggdrasilCognitionSystem:
    """
    Main integration class that connects the Yggdrasil router
    with the advanced cognitive memory system.
    
    This class serves as the bridge between:
    - YggdrasilAIRouter (AI routing layer)
    - MemoryOrchestrator (hierarchical memory management)
    - HuginnAdvanced (intelligent retrieval)
    - DomainCrosslinker (cross-domain linking)
    """
    
    def __init__(self, data_path: str = None):
        """
        Initialize the Yggdrasil cognition system.
        
        Args:
            data_path: Path for storing memory data
        """
        self.data_path = Path(data_path) if data_path else Path("data") / "yggdrasil" / "cognition"
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize cognitive subsystems
        self.memory_orchestrator = MemoryOrchestrator(str(self.data_path))
        self.memory_tree = self.memory_orchestrator.memory_tree
        self.huginn = self.memory_orchestrator.huginn
        self.crosslinker = self.memory_orchestrator.crosslinker
        
        # Memory domain mapping for game concepts
        self._domain_mapping = {
            "character": NodeDomain.CHARACTERS,
            "location": NodeDomain.LOCATIONS,
            "quest": NodeDomain.QUESTS,
            "world": NodeDomain.WORLD_KNOWLEDGE,
            "social": NodeDomain.SOCIAL_PROTOCOLS,
            "culture": NodeDomain.CULTURAL_PRACTICES,
            "history": NodeDomain.HISTORICAL_EVENTS,
            "mythology": NodeDomain.MYTHOLOGY,
            "magic": NodeDomain.MAGIC_SYSTEMS,
            "combat": NodeDomain.COMBAT_RULES,
            "trade": NodeDomain.TRADE_ECONOMY,
            "religion": NodeDomain.RELIGION,
            "daily": NodeDomain.DAILY_LIFE
        }
        
        # Memory type mapping
        self._memory_type_mapping = {
            "dialogue": MemoryType.DIALOGUE,
            "narration": MemoryType.NARRATIVE,
            "combat": MemoryType.COMBAT,
            "planning": MemoryType.PLANNING,
            "memory": MemoryType.MEMORY,
            "analysis": MemoryType.ANALYSIS,
            "creation": MemoryType.CREATION,
            "reaction": MemoryType.REACTION,
            "summary": MemoryType.SUMMARY,
            "prophecy": MemoryType.PROPHECY
        }
        
        logger.info("YggdrasilCognitionSystem initialized")
    
    def store_game_event(self, event_type: str, content: str, context: Dict[str, Any],
                        importance: int = 5, tags: List[str] = None) -> str:
        """
        Store a game event in the hierarchical memory system.
        
        Args:
            event_type: Type of event (dialogue, narration, combat, etc.)
            content: The event content
            context: Game context including characters, location, etc.
            importance: Importance score (1-10)
            tags: List of tags for categorization
            
        Returns:
            Node ID of the stored memory
        """
        # Determine domain from context
        domain = self._determine_domain(context)
        
        # Determine memory type
        memory_type = self._memory_type_mapping.get(event_type, MemoryType.GENERAL)
        
        # Create hierarchical path
        path = self._create_memory_path(event_type, context)
        
        # Extract keywords from content
        keywords = self._extract_keywords(content)
        
        # Prepare metadata
        metadata = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "context": context,
            "source": "game_event"
        }
        
        # Store the memory
        try:
            result = self.memory_orchestrator.store_memory(
                content=content,
                path=path,
                memory_type=memory_type,
                domain=domain,
                importance=importance,
                tags=tags,
                metadata=metadata,
                keywords=keywords
            )

            if result.success:
                logger.info(f"Stored game event: {event_type} (node: {result.node_id})")
                return result.node_id
            logger.error(f"Failed to store game event: {result.error}")
            return None
        except Exception as exc:
            logger.error("Failed to store game event '%s': %s", event_type, exc)
            return None
    
    def retrieve_relevant_memories(self, query: str, context: Dict[str, Any],
                                 max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve memories relevant to a query and context.
        
        Args:
            query: Search query
            context: Game context for domain determination
            max_results: Maximum number of memories to retrieve
            
        Returns:
            List of relevant memories with metadata
        """
        # Determine strategy based on query complexity
        strategy = self._determine_retrieval_strategy(query, context)
        
        # Perform retrieval
        try:
            result = self.memory_orchestrator.retrieve_memory(
                query=query,
                strategy=strategy,
                max_nodes=max_results,
                min_confidence=0.3,
                cross_domain=True
            )
        except Exception as exc:
            logger.warning("Memory retrieval failed for query '%s': %s", query, exc)
            return []

        if not result.success:
            logger.warning(f"Memory retrieval failed: {result.error}")
            return []
        
        # Format results
        memories = []
        for node in result.nodes:
            memory = {
                "id": node.id,
                "content": node.content,
                "domain": node.domain.value,
                "memory_type": node.memory_type.value,
                "importance": node.importance,
                "path": node.path,
                "tags": node.tags,
                "metadata": node.metadata,
                "created_at": node.created_at.isoformat() if node.created_at else None,
                "confidence": getattr(node, 'relevance_score', 0.5)
            }
            memories.append(memory)
        
        # Add cross-domain results if available
        if result.cross_query_result and result.cross_query_result.results:
            for source_node, target_node, relationship, confidence in result.cross_query_result.results:
                memory = {
                    "id": target_node.id,
                    "content": target_node.content,
                    "domain": target_node.domain.value,
                    "memory_type": target_node.memory_type.value,
                    "importance": target_node.importance,
                    "path": target_node.path,
                    "tags": target_node.tags,
                    "metadata": target_node.metadata,
                    "created_at": target_node.created_at.isoformat() if target_node.created_at else None,
                    "confidence": confidence,
                    "relationship": relationship.value,
                    "source_domain": source_node.domain.value,
                    "cross_domain": True
                }
                memories.append(memory)
        
        # Sort by confidence and limit
        memories.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return memories[:max_results]
    
    def retrieve_relevant_memories_batch(self, queries: List[str], context: Dict[str, Any],
                                          total_max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve memories for multiple queries in a single batched pass.

        Runs one orchestrator call per query but deduplicates at the raw node
        level before formatting, avoiding redundant object allocation and
        repeated sort passes.

        Args:
            queries: List of search queries to run
            context: Game context for strategy determination
            total_max_results: Maximum unique memories to return across all queries

        Returns:
            Deduplicated list of memories sorted by confidence
        """
        if not queries:
            return []

        seen_ids: set = set()
        all_raw_memories: List[Dict[str, Any]] = []

        for query in queries:
            strategy = self._determine_retrieval_strategy(query, context)
            try:
                result = self.memory_orchestrator.retrieve_memory(
                    query=query,
                    strategy=strategy,
                    max_nodes=total_max_results,
                    min_confidence=0.3,
                    cross_domain=True,
                )
            except Exception as exc:
                logger.warning("Batch memory retrieval failed for query '%s': %s", query, exc)
                continue

            if not result.success:
                continue

            for node in result.nodes:
                if node.id in seen_ids:
                    continue
                seen_ids.add(node.id)
                all_raw_memories.append({
                    "id": node.id,
                    "content": node.content,
                    "domain": node.domain.value,
                    "memory_type": node.memory_type.value,
                    "importance": node.importance,
                    "path": node.path,
                    "tags": node.tags,
                    "metadata": node.metadata,
                    "created_at": node.created_at.isoformat() if node.created_at else None,
                    "confidence": getattr(node, "relevance_score", 0.5),
                })

            if result.cross_query_result and result.cross_query_result.results:
                for source_node, target_node, relationship, confidence in result.cross_query_result.results:
                    if target_node.id in seen_ids:
                        continue
                    seen_ids.add(target_node.id)
                    all_raw_memories.append({
                        "id": target_node.id,
                        "content": target_node.content,
                        "domain": target_node.domain.value,
                        "memory_type": target_node.memory_type.value,
                        "importance": target_node.importance,
                        "path": target_node.path,
                        "tags": target_node.tags,
                        "metadata": target_node.metadata,
                        "created_at": target_node.created_at.isoformat() if target_node.created_at else None,
                        "confidence": confidence,
                        "relationship": relationship.value,
                        "source_domain": source_node.domain.value,
                        "cross_domain": True,
                    })

            # Early-exit: no point querying further if we already have plenty
            if len(all_raw_memories) >= total_max_results * 3:
                break

        all_raw_memories.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return all_raw_memories[:total_max_results]

    def analyze_context_for_ai(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze game context and retrieve relevant memories for AI processing.

        Args:
            context: Game context including characters, location, etc.

        Returns:
            Enhanced context with relevant memories
        """
        enhanced_context = context.copy()

        # Extract key elements for memory retrieval
        queries = self._generate_queries_from_context(context)

        # Single batched retrieval — deduplication happens inside the batch method
        unique_memories = self.retrieve_relevant_memories_batch(
            queries, context, total_max_results=10
        )

        # Add to enhanced context
        enhanced_context["relevant_memories"] = unique_memories

        # Add memory statistics
        enhanced_context["memory_stats"] = {
            "total_memories_retrieved": len(unique_memories),
            "domains_represented": len(set(m.get("domain") for m in unique_memories)),
            "cross_domain_memories": sum(1 for m in unique_memories if m.get("cross_domain", False))
        }

        return enhanced_context
    
    def create_cross_domain_links_for_context(self, context: Dict[str, Any]):
        """
        Create cross-domain links based on current game context.
        
        Args:
            context: Game context to analyze for cross-domain linking
        """
        # Extract entities from context
        entities = self._extract_entities_from_context(context)
        
        for entity_type, entity_data in entities.items():
            if not entity_data:
                continue
            
            # Create memory node for entity
            node_id = self.store_game_event(
                event_type="analysis",
                content=f"{entity_type}: {entity_data}",
                context=context,
                importance=7,
                tags=[entity_type]
            )
            
            if node_id:
                # Find node and create cross-domain links
                node = self.memory_tree.get_node(node_id)
                if node:
                    # Create links to compatible domains
                    self.crosslinker.create_cross_domain_links(
                        node, NodeDomain.WORLD_KNOWLEDGE, min_confidence=0.4
                    )
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the cognitive system.
        
        Returns:
            Dictionary with system statistics
        """
        # Get memory tree statistics
        tree_stats = self.memory_tree.get_statistics()
        
        # Get performance report
        perf_report = self.memory_orchestrator.get_performance_report()
        
        # Get domain connectivity
        domain_connectivity = self.crosslinker.get_domain_connectivity()
        
        # Get Huginn statistics
        huginn_stats = self.huginn.get_performance_statistics()
        
        return {
            "memory_tree": tree_stats,
            "performance": perf_report,
            "domain_connectivity": domain_connectivity,
            "huginn": huginn_stats,
            "total_nodes": len(self.memory_tree.nodes),
            "total_links": sum(len(node.symbolic_links) for node in self.memory_tree.nodes.values())
        }
    
    def _determine_domain(self, context: Dict[str, Any]) -> NodeDomain:
        """Determine the appropriate domain for a memory based on context."""
        # Check for character presence
        if context.get("player_character") or context.get("involved_characters"):
            return NodeDomain.CHARACTERS
        
        # Check for location
        if context.get("location_name") or context.get("location_description"):
            return NodeDomain.LOCATIONS
        
        # Check for quest/mission
        if context.get("quest") or context.get("mission"):
            return NodeDomain.QUESTS
        
        # Check for combat
        if context.get("combat") or context.get("battle"):
            return NodeDomain.COMBAT_RULES
        
        # Default to world knowledge
        return NodeDomain.WORLD_KNOWLEDGE
    
    def _create_memory_path(self, event_type: str, context: Dict[str, Any]) -> str:
        """Create a hierarchical path for a memory."""
        path_parts = []
        
        # Add domain
        domain = self._determine_domain(context)
        path_parts.append(domain.value.lower())
        
        # Add event type
        path_parts.append(event_type.lower())
        
        # Add timestamp component
        timestamp = datetime.now().strftime("%Y%m%d")
        path_parts.append(timestamp)
        
        # Add location if available
        if context.get("location_name"):
            location_slug = context["location_name"].lower().replace(" ", "_")
            path_parts.append(location_slug)
        
        # Add character if available
        if context.get("player_character"):
            pc = context["player_character"]
            # character dict nests name under identity.name; top-level "name" may be absent
            pc_name = (
                pc.get("name")
                or (pc.get("identity") or {}).get("name")
                or "unknown"
            )
            pc_slug = pc_name.lower().replace(" ", "_")
            path_parts.append(pc_slug)
        
        return "/".join(path_parts)
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content."""
        # Simple keyword extraction - could be enhanced with NLP
        words = content.lower().split()
        
        # Filter out common words and keep meaningful ones
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        
        # Limit to top 10 keywords
        return keywords[:10]
    
    def _determine_retrieval_strategy(self, query: str, context: Dict[str, Any]):
        """Determine the best retrieval strategy for a query."""
        # Import here to avoid circular imports
        from .cognition import RetrievalStrategy
        
        query_lower = query.lower()
        
        # Simple strategy determination based on query content
        if any(word in query_lower for word in ["who", "person", "character", "npc"]):
            return RetrievalStrategy.CONTEXTUAL  # Character-centric queries need context
        
        if any(word in query_lower for word in ["where", "location", "place", "city"]):
            return RetrievalStrategy.HIERARCHICAL  # Location queries benefit from hierarchy
        
        if any(word in query_lower for word in ["what happened", "event", "history"]):
            return RetrievalStrategy.HYBRID  # Temporal queries need hybrid approach
        
        if any(word in query_lower for word in ["how", "process", "method", "way"]):
            return RetrievalStrategy.KEYWORD_EXPANSION  # Process queries benefit from keyword expansion
        
        if any(word in query_lower for word in ["why", "reason", "cause", "because"]):
            return RetrievalStrategy.CONTEXTUAL  # Causal queries need context
        
        if len(query.split()) > 10:  # Long query
            return RetrievalStrategy.HYBRID  # Complex queries need hybrid approach
        
        # Check for cross-domain queries
        domains_in_context = set()
        if context.get("player_character"):
            domains_in_context.add("characters")
        if context.get("location_name"):
            domains_in_context.add("locations")
        if context.get("combat"):
            domains_in_context.add("combat")
        
        if len(domains_in_context) > 1:
            return RetrievalStrategy.DOMAIN_CROSSING
        
        # Default to contextual retrieval
        return RetrievalStrategy.CONTEXTUAL
    
    def _generate_queries_from_context(self, context: Dict[str, Any]) -> List[str]:
        """Generate search queries from game context."""
        queries = []
        
        # Add character-based queries
        if context.get("player_character"):
            pc = context["player_character"]
            queries.append(f"character {pc.get('name', 'player')}")
            queries.append(f"{pc.get('role', 'adventurer')} {pc.get('name', 'player')}")
        
        # Add location-based queries
        if context.get("location_name"):
            queries.append(f"location {context['location_name']}")
            queries.append(f"place {context['location_name']}")
        
        # Add event-based queries
        if context.get("recent_events"):
            for event in context["recent_events"][:3]:  # Last 3 events
                queries.append(event)
        
        # Add general context queries
        queries.append("norse viking saga")
        queries.append("game context")
        
        return queries
    
    def _extract_entities_from_context(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Extract entities from game context for cross-domain linking."""
        entities = {}
        
        # Extract character entities
        if context.get("player_character"):
            pc = context["player_character"]
            entities["player_character"] = f"{pc.get('name', 'Unknown')} - {pc.get('role', 'Adventurer')}"
        
        # Extract location entities
        if context.get("location_name"):
            entities["location"] = context["location_name"]
            if context.get("location_description"):
                entities["location_description"] = context["location_description"][:100]
        
        # Extract event entities
        if context.get("recent_events"):
            entities["recent_events"] = "; ".join(context["recent_events"][:3])
        
        # Extract game state entities
        if context.get("chaos_factor"):
            entities["chaos_factor"] = f"Chaos: {context['chaos_factor']}/9"
        
        if context.get("time_of_day"):
            entities["time"] = f"Time: {context['time_of_day']}"
        
        if context.get("weather"):
            entities["weather"] = f"Weather: {context['weather']}"
        
        return entities