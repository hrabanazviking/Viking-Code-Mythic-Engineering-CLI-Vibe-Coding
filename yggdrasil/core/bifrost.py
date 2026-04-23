"""
Bifrost - The Rainbow Bridge
============================

Routes queries and tasks between the Nine Worlds of Yggdrasil.
Like the legendary bridge connecting Asgard to Midgard,
Bifrost ensures messages reach their proper destination.

The bridge analyzes incoming requests and determines:
- Which realm(s) should handle the task
- What priority the task should have
- Whether parallel or sequential processing is needed
"""

import logging
import re
from typing import Dict, List, Any, Tuple, Set
from dataclasses import dataclass, field

from yggdrasil.core.dag import RealmAffinity, TaskType

logger = logging.getLogger(__name__)


@dataclass
class RouteDecision:
    """A routing decision from Bifrost."""
    primary_realm: RealmAffinity
    secondary_realms: List[RealmAffinity] = field(default_factory=list)
    task_type: TaskType = TaskType.PYTHON
    priority: int = 5
    parallel_ok: bool = False
    requires_llm: bool = False
    confidence: float = 1.0
    reasoning: str = ""


class RealmRouter:
    """
    Routes tasks to appropriate realms based on content analysis.
    
    Realm Responsibilities:
    - Asgard: Strategic planning, query decomposition, foresight
    - Vanaheim: Resource allocation, data preparation, harmony
    - Alfheim: Dynamic routing, path selection, illusions
    - Midgard: Final assembly, output formatting, delivery
    - Jotunheim: Heavy computation, simulations, raw power
    - Svartalfheim: Tool creation, script forging, artifacts
    - Niflheim: Verification, validation, preservation
    - Muspelheim: Critique, transformation, refinement
    - Helheim: Memory storage, retrieval, ancestral wisdom
    """
    
    # Keywords that indicate realm affinity
    REALM_KEYWORDS = {
        RealmAffinity.ASGARD: [
            "plan", "strategy", "decompose", "analyze", "outline", "design",
            "overview", "structure", "organize", "decide", "goal", "vision"
        ],
        RealmAffinity.VANAHEIM: [
            "resource", "allocate", "balance", "prepare", "seed", "grow",
            "cultivate", "nurture", "harmony", "distribute", "cache"
        ],
        RealmAffinity.ALFHEIM: [
            "route", "path", "select", "choose", "branch", "alternative",
            "option", "redirect", "navigate", "filter", "switch"
        ],
        RealmAffinity.MIDGARD: [
            "assemble", "format", "output", "deliver", "final", "combine",
            "merge", "present", "display", "summarize", "complete"
        ],
        RealmAffinity.JOTUNHEIM: [
            "calculate", "compute", "simulate", "process", "crunch", "heavy",
            "math", "physics", "data", "parallel", "batch", "execute"
        ],
        RealmAffinity.SVARTALFHEIM: [
            "forge", "create", "build", "craft", "tool", "script", "generate",
            "artifact", "template", "customize", "innovate"
        ],
        RealmAffinity.NIFLHEIM: [
            "verify", "validate", "check", "test", "confirm", "preserve",
            "snapshot", "freeze", "audit", "inspect", "assert"
        ],
        RealmAffinity.MUSPELHEIM: [
            "critique", "review", "refine", "transform", "improve", "retry",
            "evolve", "mutate", "enhance", "fix", "correct"
        ],
        RealmAffinity.HELHEIM: [
            "remember", "recall", "store", "retrieve", "archive", "history",
            "memory", "past", "ancestor", "log", "record", "search"
        ],
    }
    
    # Task type indicators
    TASK_TYPE_KEYWORDS = {
        TaskType.PYTHON: [
            "calculate", "compute", "parse", "process", "execute", "run",
            "script", "code", "function", "algorithm"
        ],
        TaskType.LLM: [
            "explain", "describe", "generate", "write", "create", "answer",
            "reason", "think", "analyze", "interpret"
        ],
        TaskType.VERIFY: [
            "verify", "validate", "check", "confirm", "test", "assert"
        ],
        TaskType.RETRIEVE: [
            "find", "search", "retrieve", "lookup", "get", "fetch", "recall"
        ],
        TaskType.STORE: [
            "save", "store", "archive", "record", "log", "persist"
        ],
        TaskType.TRANSFORM: [
            "transform", "convert", "format", "reshape", "translate"
        ],
    }
    
    def __init__(self):
        """Initialize the realm router."""
        self._route_cache: Dict[str, RouteDecision] = {}
        self._route_history: List[Tuple[str, RouteDecision]] = []
    
    def route(
        self,
        query: str,
        context: Dict[str, Any] = None,
        hints: List[RealmAffinity] = None
    ) -> RouteDecision:
        """
        Route a query to the appropriate realm(s).
        
        Args:
            query: The query or task description
            context: Additional context (current realm, history, etc.)
            hints: Suggested realms to consider
            
        Returns:
            RouteDecision with routing information
        """
        context = context or {}
        hints = hints or []
        
        # Check cache for identical queries
        cache_key = hash(query + str(context))
        if cache_key in self._route_cache:
            return self._route_cache[cache_key]
        
        query_lower = query.lower()
        
        # Score each realm
        realm_scores: Dict[RealmAffinity, float] = {}
        
        for realm, keywords in self.REALM_KEYWORDS.items():
            score = 0.0
            for keyword in keywords:
                if keyword in query_lower:
                    score += 1.0
                    # Bonus for exact word match
                    if re.search(rf'\b{keyword}\b', query_lower):
                        score += 0.5
            
            # Apply hints
            if realm in hints:
                score += 2.0
            
            realm_scores[realm] = score
        
        # Find primary and secondary realms
        sorted_realms = sorted(realm_scores.items(), key=lambda x: x[1], reverse=True)
        
        primary_realm = sorted_realms[0][0]
        primary_score = sorted_realms[0][1]
        
        # Secondary realms (score > 0 and at least half of primary)
        secondary_realms = [
            realm for realm, score in sorted_realms[1:]
            if score > 0 and score >= primary_score * 0.5
        ][:3]  # Max 3 secondary
        
        # Determine task type
        task_type = self._determine_task_type(query_lower)
        
        # Determine if LLM is required
        requires_llm = task_type == TaskType.LLM or self._requires_reasoning(query_lower)
        
        # Determine if parallel execution is OK
        parallel_ok = task_type == TaskType.PYTHON and not requires_llm
        
        # Calculate confidence
        confidence = min(1.0, primary_score / 5.0) if primary_score > 0 else 0.3
        
        # Build reasoning
        reasoning = self._build_reasoning(primary_realm, secondary_realms, task_type, query)
        
        # Priority based on task type and realm
        priority = self._calculate_priority(primary_realm, task_type, context)
        
        decision = RouteDecision(
            primary_realm=primary_realm,
            secondary_realms=secondary_realms,
            task_type=task_type,
            priority=priority,
            parallel_ok=parallel_ok,
            requires_llm=requires_llm,
            confidence=confidence,
            reasoning=reasoning,
        )
        
        # Cache and record
        self._route_cache[cache_key] = decision
        self._route_history.append((query[:100], decision))
        
        # Trim history
        if len(self._route_history) > 1000:
            self._route_history = self._route_history[-500:]
        
        logger.debug(f"Routed to {primary_realm.value}: {reasoning}")
        
        return decision
    
    def _determine_task_type(self, query_lower: str) -> TaskType:
        """Determine the task type from query."""
        type_scores = {}
        
        for task_type, keywords in self.TASK_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            type_scores[task_type] = score
        
        if not type_scores or max(type_scores.values()) == 0:
            return TaskType.PYTHON  # Default
        
        return max(type_scores.items(), key=lambda x: x[1])[0]
    
    def _requires_reasoning(self, query_lower: str) -> bool:
        """Check if the query requires LLM reasoning."""
        reasoning_indicators = [
            "why", "explain", "describe", "interpret", "understand",
            "what do you think", "how would you", "suggest", "recommend",
            "creative", "write", "compose", "imagine"
        ]
        return any(ind in query_lower for ind in reasoning_indicators)
    
    def _build_reasoning(
        self,
        primary: RealmAffinity,
        secondary: List[RealmAffinity],
        task_type: TaskType,
        query: str
    ) -> str:
        """Build human-readable reasoning for the route decision."""
        realm_descriptions = {
            RealmAffinity.ASGARD: "strategic planning and oversight",
            RealmAffinity.VANAHEIM: "resource preparation and harmony",
            RealmAffinity.ALFHEIM: "dynamic routing and path selection",
            RealmAffinity.MIDGARD: "final assembly and delivery",
            RealmAffinity.JOTUNHEIM: "heavy computation and execution",
            RealmAffinity.SVARTALFHEIM: "tool forging and creation",
            RealmAffinity.NIFLHEIM: "verification and preservation",
            RealmAffinity.MUSPELHEIM: "critique and transformation",
            RealmAffinity.HELHEIM: "memory and ancestral wisdom",
        }
        
        reason = f"Primary: {primary.value} ({realm_descriptions[primary]})"
        
        if secondary:
            secondary_names = [r.value for r in secondary]
            reason += f". Secondary: {', '.join(secondary_names)}"
        
        reason += f". Task type: {task_type.value}"
        
        return reason
    
    def _calculate_priority(
        self,
        realm: RealmAffinity,
        task_type: TaskType,
        context: Dict[str, Any]
    ) -> int:
        """Calculate priority for the task."""
        # Base priority by realm
        realm_priorities = {
            RealmAffinity.ASGARD: 8,      # Planning is high priority
            RealmAffinity.MIDGARD: 7,     # Final output important
            RealmAffinity.NIFLHEIM: 6,    # Verification matters
            RealmAffinity.MUSPELHEIM: 6,  # Critique important
            RealmAffinity.JOTUNHEIM: 5,   # Execution is normal
            RealmAffinity.HELHEIM: 5,     # Memory is normal
            RealmAffinity.SVARTALFHEIM: 4,  # Forging can wait
            RealmAffinity.VANAHEIM: 4,    # Prep can wait
            RealmAffinity.ALFHEIM: 3,     # Routing is fast
        }
        
        priority = realm_priorities.get(realm, 5)
        
        # Adjust for task type
        if task_type == TaskType.VERIFY:
            priority += 1
        elif task_type == TaskType.STORE:
            priority -= 1
        
        # Adjust for context
        if context.get("urgent"):
            priority += 2
        if context.get("background"):
            priority -= 2
        
        return max(1, min(10, priority))
    
    def get_realm_for_task_type(self, task_type: TaskType) -> RealmAffinity:
        """Get the default realm for a task type."""
        mapping = {
            TaskType.PYTHON: RealmAffinity.JOTUNHEIM,
            TaskType.LLM: RealmAffinity.ASGARD,
            TaskType.VERIFY: RealmAffinity.NIFLHEIM,
            TaskType.RETRIEVE: RealmAffinity.HELHEIM,
            TaskType.STORE: RealmAffinity.HELHEIM,
            TaskType.TRANSFORM: RealmAffinity.MUSPELHEIM,
            TaskType.ROUTE: RealmAffinity.ALFHEIM,
            TaskType.COMPOSITE: RealmAffinity.MIDGARD,
        }
        return mapping.get(task_type, RealmAffinity.MIDGARD)
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        if not self._route_history:
            return {"total_routes": 0}
        
        realm_counts = {}
        type_counts = {}
        
        for _, decision in self._route_history:
            realm = decision.primary_realm.value
            realm_counts[realm] = realm_counts.get(realm, 0) + 1
            
            task_type = decision.task_type.value
            type_counts[task_type] = type_counts.get(task_type, 0) + 1
        
        return {
            "total_routes": len(self._route_history),
            "realm_distribution": realm_counts,
            "type_distribution": type_counts,
            "cache_size": len(self._route_cache),
        }


class Bifrost:
    """
    The Bifrost Bridge - Main routing interface.
    
    Coordinates between the RealmRouter and provides
    additional features like multi-realm routing and
    route optimization.
    """
    
    def __init__(self):
        """Initialize Bifrost."""
        self.router = RealmRouter()
        self._active_bridges: Set[str] = set()
        self._bridge_status: Dict[str, bool] = {
            realm.value: True for realm in RealmAffinity
        }
    
    def open_bridge(self, realm: RealmAffinity):
        """Open the bridge to a realm."""
        self._bridge_status[realm.value] = True
        self._active_bridges.add(realm.value)
        logger.info(f"Bifrost bridge to {realm.value} opened")
    
    def close_bridge(self, realm: RealmAffinity):
        """Close the bridge to a realm."""
        self._bridge_status[realm.value] = False
        self._active_bridges.discard(realm.value)
        logger.info(f"Bifrost bridge to {realm.value} closed")
    
    def is_bridge_open(self, realm: RealmAffinity) -> bool:
        """Check if bridge to realm is open."""
        return self._bridge_status.get(realm.value, False)
    
    def route(self, query: str, **kwargs) -> RouteDecision:
        """
        Route a query across Bifrost.
        
        Args:
            query: The query to route
            **kwargs: Additional routing parameters
            
        Returns:
            RouteDecision
        """
        decision = self.router.route(query, **kwargs)
        
        # Check if bridge is open
        if not self.is_bridge_open(decision.primary_realm):
            # Find alternative
            for realm in decision.secondary_realms:
                if self.is_bridge_open(realm):
                    logger.warning(f"Primary bridge closed, rerouting to {realm.value}")
                    decision.primary_realm = realm
                    decision.secondary_realms = [
                        r for r in decision.secondary_realms if r != realm
                    ]
                    break
            else:
                # Default to Midgard if all closed
                decision.primary_realm = RealmAffinity.MIDGARD
                logger.warning("All bridges closed, defaulting to Midgard")
        
        return decision
    
    def route_multi(
        self,
        queries: List[str],
        **kwargs
    ) -> Dict[RealmAffinity, List[Tuple[str, RouteDecision]]]:
        """
        Route multiple queries and group by realm.
        
        Args:
            queries: List of queries to route
            **kwargs: Additional routing parameters
            
        Returns:
            Dict mapping realms to lists of (query, decision) tuples
        """
        grouped = {}
        
        for query in queries:
            decision = self.route(query, **kwargs)
            realm = decision.primary_realm
            
            if realm not in grouped:
                grouped[realm] = []
            grouped[realm].append((query, decision))
        
        return grouped
    
    def get_bridge_status(self) -> Dict[str, bool]:
        """Get status of all bridges."""
        return dict(self._bridge_status)
    
    def get_active_bridges(self) -> List[str]:
        """Get list of active bridge names."""
        return list(self._active_bridges)
