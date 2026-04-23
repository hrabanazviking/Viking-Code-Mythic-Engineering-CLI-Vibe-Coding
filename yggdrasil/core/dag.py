"""
DAG (Directed Acyclic Graph) Engine
===================================

The skeleton of Yggdrasil's task management - handles dependencies,
ready tasks, and execution order across the Nine Worlds.

Like the roots of the World Tree, it connects all realms while
maintaining the proper order of operations.
"""

import logging
from collections import defaultdict
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks that can be executed."""
    PYTHON = "python"      # Python script execution
    LLM = "llm"            # LLM inference call
    VERIFY = "verify"      # Verification task
    ROUTE = "route"        # Routing decision
    TRANSFORM = "transform"  # Data transformation
    RETRIEVE = "retrieve"  # Memory retrieval
    STORE = "store"        # Memory storage
    COMPOSITE = "composite"  # Multi-step task


class TaskStatus(Enum):
    """Status of a task in the DAG."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class RealmAffinity(Enum):
    """Which realm a task belongs to."""
    ASGARD = "asgard"           # Planning
    VANAHEIM = "vanaheim"       # Resources
    ALFHEIM = "alfheim"         # Routing
    MIDGARD = "midgard"         # Assembly
    JOTUNHEIM = "jotunheim"     # Execution
    SVARTALFHEIM = "svartalfheim"  # Forging
    NIFLHEIM = "niflheim"       # Verification
    MUSPELHEIM = "muspelheim"   # Critique
    HELHEIM = "helheim"         # Memory


@dataclass
class TaskNode:
    """A single task node in the DAG."""
    id: str
    task_type: TaskType
    realm: RealmAffinity
    
    # Execution details
    script: Optional[str] = None      # For Python tasks
    prompt: Optional[str] = None      # For LLM tasks
    function: Optional[Callable] = None  # For callable tasks
    args: Dict[str, Any] = field(default_factory=dict)
    
    # Dependencies
    depends_on: List[str] = field(default_factory=list)
    
    # State
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    
    # Metadata
    priority: int = 5  # 1-10, higher = more important
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 60
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "realm": self.realm.value,
            "script": self.script,
            "prompt": self.prompt,
            "args": self.args,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "priority": self.priority,
            "retry_count": self.retry_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskNode":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            task_type=TaskType(data.get("task_type", "python")),
            realm=RealmAffinity(data.get("realm", "midgard")),
            script=data.get("script"),
            prompt=data.get("prompt"),
            args=data.get("args", {}),
            depends_on=data.get("depends_on", []),
            status=TaskStatus(data.get("status", "pending")),
            priority=data.get("priority", 5),
            max_retries=data.get("max_retries", 3),
        )


class DAG:
    """
    Directed Acyclic Graph for task orchestration.
    
    The tree's skeleton—handles dependencies, ready tasks, and execution order.
    Like Yggdrasil's roots connecting the nine worlds.
    """
    
    def __init__(self, nodes: List[TaskNode] = None):
        """
        Initialize the DAG.
        
        Args:
            nodes: List of TaskNode objects or dicts
        """
        self.nodes: Dict[str, TaskNode] = {}
        self.deps: Dict[str, Set[str]] = defaultdict(set)      # node -> dependencies
        self.children: Dict[str, Set[str]] = defaultdict(set)  # node -> dependents
        self.completed: Set[str] = set()
        self.failed: Set[str] = set()
        
        if nodes:
            for node in nodes:
                self.add_node(node)
    
    def add_node(self, node: Any) -> str:
        """
        Add a node to the DAG.
        
        Args:
            node: TaskNode object or dict with node data
            
        Returns:
            Node ID
        """
        if isinstance(node, dict):
            node = TaskNode.from_dict(node)
        
        self.nodes[node.id] = node
        
        # Set up dependencies
        for dep_id in node.depends_on:
            self.deps[node.id].add(dep_id)
            self.children[dep_id].add(node.id)
        
        return node.id
    
    def remove_node(self, node_id: str) -> bool:
        """Remove a node from the DAG."""
        if node_id not in self.nodes:
            return False
        
        # Remove from children of dependencies
        for dep_id in self.deps[node_id]:
            self.children[dep_id].discard(node_id)
        
        # Remove from dependencies of children
        for child_id in self.children[node_id]:
            self.deps[child_id].discard(node_id)
        
        # Clean up
        del self.nodes[node_id]
        del self.deps[node_id]
        del self.children[node_id]
        self.completed.discard(node_id)
        self.failed.discard(node_id)
        
        return True
    
    def get_ready_tasks(self) -> List[TaskNode]:
        """
        Get all tasks that are ready to execute.
        
        A task is ready when all its dependencies are completed.
        
        Returns:
            List of ready TaskNode objects, sorted by priority
        """
        ready = []
        
        for node_id, node in self.nodes.items():
            if node_id in self.completed or node_id in self.failed:
                continue
            if node.status in [TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.FAILED]:
                continue
            
            # Check if all dependencies are satisfied
            deps_satisfied = self.deps[node_id] <= self.completed
            
            if deps_satisfied:
                node.status = TaskStatus.READY
                ready.append(node)
        
        # Sort by priority (highest first)
        ready.sort(key=lambda n: n.priority, reverse=True)
        
        return ready
    
    def mark_completed(self, node_id: str, result: Any = None):
        """Mark a node as completed."""
        if node_id in self.nodes:
            self.nodes[node_id].status = TaskStatus.COMPLETED
            self.nodes[node_id].result = result
            self.nodes[node_id].completed_at = datetime.now()
            self.completed.add(node_id)
            logger.debug(f"Task {node_id} completed")
    
    def mark_failed(self, node_id: str, error: str = None):
        """Mark a node as failed."""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            
            # Check for retries
            if node.retry_count < node.max_retries:
                node.retry_count += 1
                node.status = TaskStatus.RETRYING
                logger.warning(f"Task {node_id} failed, retry {node.retry_count}/{node.max_retries}")
                return False  # Not permanently failed
            
            node.status = TaskStatus.FAILED
            node.error = error
            node.completed_at = datetime.now()
            self.failed.add(node_id)
            logger.error(f"Task {node_id} permanently failed: {error}")
            return True  # Permanently failed
    
    def mark_running(self, node_id: str):
        """Mark a node as running."""
        if node_id in self.nodes:
            self.nodes[node_id].status = TaskStatus.RUNNING
            self.nodes[node_id].started_at = datetime.now()
    
    def is_finished(self) -> bool:
        """Check if the DAG has finished (all tasks complete or failed)."""
        return len(self.completed) + len(self.failed) >= len(self.nodes)
    
    def has_pending(self) -> bool:
        """Check if there are still pending tasks."""
        return not self.is_finished()
    
    def get_results(self) -> Dict[str, Any]:
        """Get all results from completed tasks."""
        return {
            node_id: node.result
            for node_id, node in self.nodes.items()
            if node.status == TaskStatus.COMPLETED
        }
    
    def get_errors(self) -> Dict[str, str]:
        """Get all errors from failed tasks."""
        return {
            node_id: node.error
            for node_id, node in self.nodes.items()
            if node.status == TaskStatus.FAILED and node.error
        }
    
    def get_nodes_by_realm(self, realm: RealmAffinity) -> List[TaskNode]:
        """Get all nodes belonging to a specific realm."""
        return [n for n in self.nodes.values() if n.realm == realm]
    
    def get_nodes_by_type(self, task_type: TaskType) -> List[TaskNode]:
        """Get all nodes of a specific type."""
        return [n for n in self.nodes.values() if n.task_type == task_type]
    
    def get_execution_order(self) -> List[str]:
        """
        Get the topological order for execution.
        
        Returns:
            List of node IDs in execution order
        """
        # Kahn's algorithm for topological sort
        in_degree = {node_id: len(deps) for node_id, deps in self.deps.items()}
        
        # Add nodes with no dependencies
        for node_id in self.nodes:
            if node_id not in in_degree:
                in_degree[node_id] = 0
        
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        order = []
        
        while queue:
            # Sort by priority
            queue.sort(key=lambda x: self.nodes[x].priority, reverse=True)
            node_id = queue.pop(0)
            order.append(node_id)
            
            for child_id in self.children[node_id]:
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    queue.append(child_id)
        
        return order
    
    def validate(self) -> List[str]:
        """
        Validate the DAG for cycles and missing dependencies.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check for missing dependencies
        for node_id, node in self.nodes.items():
            for dep_id in node.depends_on:
                if dep_id not in self.nodes:
                    errors.append(f"Node {node_id} depends on missing node {dep_id}")
        
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            
            for child_id in self.children[node_id]:
                if child_id not in visited:
                    if has_cycle(child_id):
                        return True
                elif child_id in rec_stack:
                    return True
            
            rec_stack.remove(node_id)
            return False
        
        for node_id in self.nodes:
            if node_id not in visited:
                if has_cycle(node_id):
                    errors.append(f"Cycle detected involving node {node_id}")
                    break
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the DAG to dictionary."""
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "completed": list(self.completed),
            "failed": list(self.failed),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DAG":
        """Deserialize from dictionary."""
        dag = cls()
        
        for node_data in data.get("nodes", []):
            dag.add_node(TaskNode.from_dict(node_data))
        
        dag.completed = set(data.get("completed", []))
        dag.failed = set(data.get("failed", []))
        
        return dag
    
    def __len__(self) -> int:
        return len(self.nodes)
    
    def __repr__(self) -> str:
        return f"DAG(nodes={len(self.nodes)}, completed={len(self.completed)}, failed={len(self.failed)})"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_simple_dag(tasks: List[Dict[str, Any]]) -> DAG:
    """
    Create a simple DAG from a list of task dictionaries.
    
    Args:
        tasks: List of dicts with keys:
            - id: Task ID
            - type: python, llm, verify, etc.
            - realm: Which realm (optional, defaults to midgard)
            - depends_on: List of dependency IDs
            - script/prompt: Execution details
            
    Returns:
        DAG object
    """
    dag = DAG()
    
    for task in tasks:
        node = TaskNode(
            id=task["id"],
            task_type=TaskType(task.get("type", "python")),
            realm=RealmAffinity(task.get("realm", "midgard")),
            script=task.get("script"),
            prompt=task.get("prompt"),
            args=task.get("args", {}),
            depends_on=task.get("depends_on", []),
            priority=task.get("priority", 5),
        )
        dag.add_node(node)
    
    return dag


def merge_dags(dag1: DAG, dag2: DAG, prefix: str = "merged_") -> DAG:
    """
    Merge two DAGs into one.
    
    Args:
        dag1: First DAG
        dag2: Second DAG  
        prefix: Prefix for second DAG's node IDs to avoid conflicts
        
    Returns:
        Merged DAG
    """
    merged = DAG()
    
    # Add all nodes from dag1
    for node in dag1.nodes.values():
        merged.add_node(node)
    
    # Add all nodes from dag2 with prefixed IDs
    for node in dag2.nodes.values():
        new_node = TaskNode(
            id=f"{prefix}{node.id}",
            task_type=node.task_type,
            realm=node.realm,
            script=node.script,
            prompt=node.prompt,
            args=node.args,
            depends_on=[f"{prefix}{d}" for d in node.depends_on],
            priority=node.priority,
        )
        merged.add_node(new_node)
    
    return merged
