"""
Alfheim - Illusion & Agile Routing
=================================

Light elves' realm—swift, elusive, deceptive paths.
Clever redirection and choices.
"""

import logging
import random
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


class Alfheim:
    """
    Illusion & Agile Routing.
    
    Handles dynamic routing, probabilistic branching, path filtering,
    decoy generation, and route recalculation.
    """
    
    ROUTE_HEURISTICS = {
        "python": ["calculate", "compute", "process", "data", "script"],
        "llm": ["explain", "describe", "analyze", "generate", "write"],
        "verify": ["check", "validate", "confirm", "test"],
        "memory": ["remember", "recall", "store", "retrieve"],
    }
    
    def __init__(self):
        self._route_history: List[Tuple[str, str]] = []
    
    def route_node_type(self, query: str) -> str:
        """Determine best route based on query heuristics."""
        query_lower = query.lower()
        
        for route_type, keywords in self.ROUTE_HEURISTICS.items():
            if any(kw in query_lower for kw in keywords):
                self._route_history.append((query[:50], route_type))
                return route_type
        
        return "python"  # Default
    
    def probabilistic_branching(self, options: List[str], weights: List[float] = None) -> List[str]:
        """Select branches probabilistically."""
        if not weights:
            weights = [1.0] * len(options)
        
        # Normalize weights
        total = sum(weights)
        probs = [w / total for w in weights]
        
        # Select multiple with probability
        selected = []
        for opt, prob in zip(options, probs):
            if random.random() < prob:
                selected.append(opt)
        
        return selected if selected else [options[0]]
    
    def filter_heavy_paths(self, paths: List[Dict], threshold: float = 0.5) -> List[Dict]:
        """Filter out computationally heavy paths."""
        return [p for p in paths if p.get("weight", 0) < threshold]
    
    def generate_decoys(self, data: Any, count: int = 2) -> List[Dict]:
        """Generate decoy data for testing."""
        decoys = []
        for i in range(count):
            decoys.append({
                "decoy": f"{str(data)[:20]}_{i}",
                "is_real": False
            })
        return decoys
    
    def recalculate_path(self, graph: Dict[str, List[str]], start: str, end: str) -> List[str]:
        """Simple BFS path finding."""
        if start == end:
            return [start]
        
        visited = {start}
        queue = [[start]]
        
        while queue:
            path = queue.pop(0)
            node = path[-1]
            
            for neighbor in graph.get(node, []):
                if neighbor == end:
                    return path + [end]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        
        return [start, end]  # Direct path as fallback
    
    def get_route_stats(self) -> Dict[str, int]:
        """Get routing statistics."""
        stats = {}
        for _, route in self._route_history:
            stats[route] = stats.get(route, 0) + 1
        return stats
