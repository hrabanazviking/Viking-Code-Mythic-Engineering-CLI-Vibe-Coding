"""
Muspelheim - Transformation & Fiery Critique
===========================================

Fire giants' blaze—rebirth, fury, refining through heat.
Burning away weakness.
"""

import logging
import random
from typing import Dict, List, Any, Callable

logger = logging.getLogger(__name__)


class Muspelheim:
    """
    Transformation & Fiery Critique.
    
    Handles critique loops, retry transformations, evolutionary refinement,
    backlash assessment, and sub-branch ignition.
    """
    
    def __init__(self, llm_queue=None):
        self.llm_queue = llm_queue
        self._critique_history: List[Dict] = []
    
    def simulate_critique(self, results: Dict[str, Any]) -> List[str]:
        """
        Analyze results for flaws and issues.
        
        Returns list of identified issues.
        """
        issues = []
        
        for key, value in results.items():
            # Check for errors
            if isinstance(value, dict):
                if value.get("error") or value.get("stderr"):
                    issues.append(f"Error in {key}: {value.get('error') or value.get('stderr')}")
                if not value.get("success", True):
                    issues.append(f"Failed task: {key}")
            
            # Check for empty results
            if value is None or value == "" or value == []:
                issues.append(f"Empty result: {key}")
            
            # Check for low confidence
            if isinstance(value, dict) and value.get("confidence", 1.0) < 0.5:
                issues.append(f"Low confidence in {key}: {value.get('confidence')}")
        
        self._critique_history.append({
            "issues_found": len(issues),
            "issues": issues[:5],  # Limit stored
        })
        
        return issues
    
    def retry_transform(self, original: Any, mutation_type: str = "retry") -> Any:
        """
        Transform a failed result for retry.
        
        Args:
            original: Original value/task
            mutation_type: Type of mutation (retry, alt, expand)
            
        Returns:
            Transformed value
        """
        if isinstance(original, str):
            return f"{original}_{mutation_type}"
        elif isinstance(original, dict):
            transformed = dict(original)
            transformed["_mutation"] = mutation_type
            transformed["_retry_count"] = transformed.get("_retry_count", 0) + 1
            return transformed
        else:
            return original
    
    def refine_results(self, results: List[Any], selector: Callable = None) -> Any:
        """
        Refine results by selecting the best.
        
        Args:
            results: List of candidate results
            selector: Optional function to score results
            
        Returns:
            Best refined result
        """
        if not results:
            return None
        
        if selector:
            scored = [(r, selector(r)) for r in results]
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[0][0]
        
        # Default: return first non-None, non-error result
        for r in results:
            if r is not None:
                if isinstance(r, dict) and r.get("error"):
                    continue
                return r
        
        return results[0]
    
    def assess_backlash(self, risks: List[float]) -> float:
        """
        Assess potential backlash/risk using Monte Carlo simulation.
        
        Args:
            risks: List of risk probabilities
            
        Returns:
            Overall risk score
        """
        if not risks:
            return 0.0
        
        # Simple Monte Carlo: average of random samples
        samples = 100
        total_risk = 0.0
        
        for _ in range(samples):
            sample_risk = sum(random.random() < r for r in risks) / len(risks)
            total_risk += sample_risk
        
        return total_risk / samples
    
    def ignite_subbranches(
        self,
        parent_task: Dict[str, Any],
        branch_count: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Ignite new sub-branches from a parent task.
        
        Args:
            parent_task: Parent task to branch from
            branch_count: Number of branches to create
            
        Returns:
            List of sub-branch tasks
        """
        branches = []
        
        parent_id = parent_task.get("id", "unknown")
        
        for i in range(branch_count):
            branch = dict(parent_task)
            branch["id"] = f"{parent_id}_sub{i}"
            branch["parent_id"] = parent_id
            branch["_is_subbranch"] = True
            
            # Modify based on branch index
            if i == 0:
                branch["_variant"] = "conservative"
            elif i == 1:
                branch["_variant"] = "aggressive"
            else:
                branch["_variant"] = f"experimental_{i}"
            
            branches.append(branch)
        
        return branches
    
    def generate_new_nodes(
        self,
        issues: List[str],
        original_dag: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate new DAG nodes to address issues.
        
        Args:
            issues: List of identified issues
            original_dag: Original DAG structure
            
        Returns:
            List of new nodes to add
        """
        new_nodes = []
        node_counter = len(original_dag.get("nodes", []))
        
        for issue in issues[:3]:  # Max 3 new nodes
            new_node = {
                "id": f"fix_node_{node_counter}",
                "type": "fix",
                "realm": "muspelheim",
                "description": f"Fix: {issue[:50]}",
                "depends_on": [],
                "_issue": issue,
            }
            new_nodes.append(new_node)
            node_counter += 1
        
        return new_nodes
    
    def should_continue_refinement(
        self,
        iteration: int,
        max_iterations: int,
        issues_count: int
    ) -> bool:
        """
        Determine if refinement should continue.
        
        Returns True if more iterations are warranted.
        """
        if iteration >= max_iterations:
            return False
        if issues_count == 0:
            return False
        
        # Diminishing returns check
        if iteration > 2 and issues_count > iteration:
            # Issues not decreasing, give up
            return False
        
        return True
    
    def get_critique_summary(self) -> Dict[str, Any]:
        """Get summary of critique history."""
        if not self._critique_history:
            return {"total_critiques": 0}
        
        total_issues = sum(c["issues_found"] for c in self._critique_history)
        
        return {
            "total_critiques": len(self._critique_history),
            "total_issues_found": total_issues,
            "avg_issues_per_critique": total_issues / len(self._critique_history),
        }
