"""
World Tree - Yggdrasil Orchestrator
===================================

The central coordinator of the Nine Worlds cognitive architecture.

Yggdrasil, the World Tree, connects all nine realms and provides
the structure through which queries flow, tasks execute, and
memory persists.

This is the main interface for the entire cognitive system.
"""

import logging
import time
from typing import Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Core imports
from yggdrasil.core.dag import DAG, TaskNode, TaskType, TaskStatus, RealmAffinity
from yggdrasil.core.llm_queue import LLMQueue
from yggdrasil.core.bifrost import Bifrost

# World imports
from yggdrasil.worlds.asgard import Asgard
from yggdrasil.worlds.vanaheim import Vanaheim
from yggdrasil.worlds.alfheim import Alfheim
from yggdrasil.worlds.midgard import Midgard
from yggdrasil.worlds.jotunheim import Jotunheim
from yggdrasil.worlds.svartalfheim import Svartalfheim
from yggdrasil.worlds.niflheim import Niflheim
from yggdrasil.worlds.muspelheim import Muspelheim
from yggdrasil.worlds.helheim import Helheim

# Raven imports
from yggdrasil.ravens.huginn import Huginn
from yggdrasil.ravens.muninn import Muninn
from yggdrasil.ravens.raven_rag import RavenRAG

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """Execution modes for the World Tree."""
    SEQUENTIAL = "sequential"   # Execute DAG nodes one at a time
    PARALLEL = "parallel"       # Execute independent nodes in parallel
    ADAPTIVE = "adaptive"       # Choose based on task analysis


@dataclass
class OrchestratorResult:
    """Result from a complete orchestration cycle."""
    query: str
    final_output: Any
    success: bool
    execution_time: float
    dag_stats: Dict[str, Any]
    realm_visits: Dict[str, int]
    iterations: int
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)


class WorldTree:
    """
    The Yggdrasil World Tree - Central Cognitive Orchestrator.
    
    Coordinates all nine realms to process queries through a
    structured DAG-based workflow:
    
    1. Asgard plans the approach
    2. Vanaheim prepares resources
    3. Alfheim routes to appropriate realms
    4. Jotunheim executes heavy tasks
    5. Svartalfheim forges tools as needed
    6. Niflheim verifies results
    7. Muspelheim critiques and refines
    8. Helheim stores for memory
    9. Midgard assembles final output
    
    The Ravens (Huginn & Muninn) provide retrieval and storage
    capabilities throughout the process.
    """
    
    def __init__(
        self,
        llm_callable: Callable[[str], str] = None,
        data_path: str = None,
        execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL,
        max_iterations: int = 3
    ):
        """
        Initialize the World Tree.
        
        Args:
            llm_callable: Function to call for LLM inference
            data_path: Path for persistent data storage
            execution_mode: How to execute DAG tasks
            max_iterations: Maximum refinement iterations
        """
        self.execution_mode = execution_mode
        self.max_iterations = max_iterations
        
        # Initialize LLM Queue
        self.llm_queue = LLMQueue(llm_callable) if llm_callable else None
        
        # Initialize Helheim first (memory foundation)
        self.helheim = Helheim(in_memory=data_path is None)
        
        # Initialize Ravens
        self.muninn = Muninn(data_path=data_path, helheim=self.helheim)
        self.huginn = Huginn(muninn=self.muninn, helheim=self.helheim)
        self.raven_rag = RavenRAG(huginn=self.huginn, muninn=self.muninn, helheim=self.helheim)
        
        # Initialize the Nine Worlds
        self.asgard = Asgard(llm_queue=self.llm_queue)
        self.vanaheim = Vanaheim()
        self.alfheim = Alfheim()
        self.midgard = Midgard(llm_queue=self.llm_queue)
        self.jotunheim = Jotunheim()
        self.svartalfheim = Svartalfheim()
        self.niflheim = Niflheim()
        self.muspelheim = Muspelheim(llm_queue=self.llm_queue)
        
        # Initialize Bifrost
        self.bifrost = Bifrost()
        
        # World registry for dynamic access
        self._worlds = {
            RealmAffinity.ASGARD: self.asgard,
            RealmAffinity.VANAHEIM: self.vanaheim,
            RealmAffinity.ALFHEIM: self.alfheim,
            RealmAffinity.MIDGARD: self.midgard,
            RealmAffinity.JOTUNHEIM: self.jotunheim,
            RealmAffinity.SVARTALFHEIM: self.svartalfheim,
            RealmAffinity.NIFLHEIM: self.niflheim,
            RealmAffinity.MUSPELHEIM: self.muspelheim,
            RealmAffinity.HELHEIM: self.helheim,
        }
        
        # Execution history
        self._execution_history: List[OrchestratorResult] = []
        
        logger.info("Yggdrasil World Tree initialized")
    
    def process(
        self,
        query: str,
        context: Dict[str, Any] = None,
        memory_paths: List[str] = None
    ) -> OrchestratorResult:
        """
        Process a query through the World Tree.
        
        This is the main entry point for the cognitive system.
        
        Args:
            query: The query to process
            context: Additional context
            memory_paths: Paths to include from memory
            
        Returns:
            OrchestratorResult with final output and metadata
        """
        start_time = time.time()
        context = context or {}
        memory_paths = memory_paths or []
        realm_visits = {r.value: 0 for r in RealmAffinity}
        
        try:
            # ================================================================
            # PHASE 1: ASGARD - Strategic Planning
            # ================================================================
            realm_visits["asgard"] += 1
            
            # Get divine foresight
            foresight = self.asgard.divine_foresight(query, context)
            plan = foresight["plan"]
            
            logger.info(f"Asgard planned: {len(plan.nodes)} nodes, "
                       f"complexity={plan.estimated_complexity}")
            
            # ================================================================
            # PHASE 2: VANAHEIM - Resource Preparation
            # ================================================================
            realm_visits["vanaheim"] += 1
            
            # Allocate resources based on plan
            resources = self.vanaheim.allocate_resources(len(plan.branches))
            
            # ================================================================
            # PHASE 3: HUGINN - Retrieval
            # ================================================================
            # Send Huginn to retrieve relevant context
            rag_context = self.raven_rag.query(
                query,
                memory_paths=memory_paths,
                use_multi_hop=plan.estimated_complexity > 5
            )
            
            # ================================================================
            # PHASE 4: BUILD AND EXECUTE DAG
            # ================================================================
            dag = DAG(plan.nodes)
            
            # Validate DAG
            errors = dag.validate()
            if errors:
                logger.warning(f"DAG validation errors: {errors}")
            
            # Execute DAG
            iteration = 0
            
            while dag.has_pending() and iteration < self.max_iterations:
                # Get ready tasks
                ready_tasks = dag.get_ready_tasks()
                
                if not ready_tasks:
                    break
                
                # Execute tasks
                for task in ready_tasks:
                    result = self._execute_task(task, context, rag_context)
                    realm_visits[task.realm.value] += 1
                    
                    if result.get("success", True):
                        dag.mark_completed(task.id, result)
                    else:
                        permanently_failed = dag.mark_failed(task.id, result.get("error"))
                        if not permanently_failed:
                            continue  # Will retry
                
                # ============================================================
                # PHASE 5: MUSPELHEIM - Critique
                # ============================================================
                if dag.is_finished() or iteration > 0:
                    realm_visits["muspelheim"] += 1
                    
                    issues = self.muspelheim.simulate_critique(dag.get_results())
                    
                    if issues and iteration < self.max_iterations - 1:
                        # Generate fix nodes
                        new_nodes = self.muspelheim.generate_new_nodes(issues, {"nodes": plan.nodes})
                        
                        for node_data in new_nodes:
                            node = TaskNode.from_dict(node_data)
                            dag.add_node(node)
                        
                        logger.info(f"Muspelheim added {len(new_nodes)} fix nodes")
                    
                    if not issues:
                        break
                
                iteration += 1
            
            # ================================================================
            # PHASE 6: NIFLHEIM - Verification
            # ================================================================
            realm_visits["niflheim"] += 1
            
            results = dag.get_results()
            verification = self.niflheim.verify_result(
                results,
                checks=[
                    {"type": "exists"},
                    {"type": "not_empty"},
                ]
            )
            
            # ================================================================
            # PHASE 7: MIDGARD - Final Assembly
            # ================================================================
            realm_visits["midgard"] += 1
            
            output = self.midgard.assemble_from_dag(results, query)
            
            # ================================================================
            # PHASE 8: HELHEIM - Store Results
            # ================================================================
            realm_visits["helheim"] += 1
            
            # Store successful execution
            self.helheim.store(
                content={
                    "query": query,
                    "output_preview": str(output.content)[:200],
                    "success": True,
                },
                memory_type="result",
                realm_source="orchestrator",
                importance=5,
                tags=["execution", "success"],
            )
            
            # Also store in Muninn for structured access
            self.muninn.store(
                content=output.content,
                path="executions/results",
                memory_type="result",
                importance=5,
            )
            
            # Build result
            execution_time = time.time() - start_time
            
            result = OrchestratorResult(
                query=query,
                final_output=output.content,
                success=True,
                execution_time=execution_time,
                dag_stats={
                    "total_nodes": len(dag),
                    "completed": len(dag.completed),
                    "failed": len(dag.failed),
                },
                realm_visits=realm_visits,
                iterations=iteration + 1,
                confidence=output.completeness * verification["success_rate"],
            )
            
            self._execution_history.append(result)
            
            logger.info(f"World Tree completed: {execution_time:.2f}s, "
                       f"confidence={result.confidence:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"World Tree execution failed: {e}")
            
            execution_time = time.time() - start_time
            
            # Store failure
            self.helheim.store(
                content={"query": query, "error": str(e)},
                memory_type="error",
                realm_source="orchestrator",
                importance=7,
                tags=["execution", "failure"],
            )
            
            return OrchestratorResult(
                query=query,
                final_output=f"Execution failed: {e}",
                success=False,
                execution_time=execution_time,
                dag_stats={},
                realm_visits=realm_visits,
                iterations=0,
                confidence=0.0,
            )
    
    def _execute_task(
        self,
        task: TaskNode,
        context: Dict[str, Any],
        rag_context: Any
    ) -> Dict[str, Any]:
        """
        Execute a single task in the appropriate realm.
        
        Args:
            task: Task to execute
            context: Execution context
            rag_context: RAG context from Huginn
            
        Returns:
            Execution result dictionary
        """
        realm = task.realm
        world = self._worlds.get(realm)
        
        if not world:
            return {"success": False, "error": f"Unknown realm: {realm}"}
        
        task.status = TaskStatus.RUNNING
        
        try:
            if task.task_type == TaskType.PYTHON:
                # Execute in Jotunheim
                if task.script:
                    result = self.jotunheim.execute_script(
                        task.script,
                        args=task.args,
                        task_id=task.id
                    )
                    return {
                        "success": result.success,
                        "output": result.stdout,
                        "error": result.stderr if not result.success else None,
                    }
                elif task.function:
                    result = self.jotunheim.execute_function(
                        task.function,
                        args=task.args.get("args", ()),
                        kwargs=task.args.get("kwargs", {}),
                        task_id=task.id
                    )
                    return {
                        "success": result.success,
                        "output": result.stdout,
                        "error": result.stderr if not result.success else None,
                    }
                else:
                    return {"success": True, "output": "No script provided"}
            
            elif task.task_type == TaskType.LLM:
                # Process through LLM Queue
                if self.llm_queue and task.prompt:
                    response, error = self.llm_queue.process_sync(
                        task.prompt,
                        realm=realm.value
                    )
                    return {
                        "success": error is None,
                        "output": response,
                        "error": error,
                    }
                else:
                    return {"success": False, "error": "No LLM queue available"}
            
            elif task.task_type == TaskType.VERIFY:
                # Verify in Niflheim
                confidence = self.niflheim.score_confidence(context.get("last_result"))
                return {
                    "success": confidence > 0.5,
                    "confidence": confidence,
                    "output": f"Verification confidence: {confidence:.2f}",
                }
            
            elif task.task_type == TaskType.RETRIEVE:
                # Retrieve using Huginn
                retrieval = self.huginn.fly(task.prompt or str(task.args))
                return {
                    "success": True,
                    "output": retrieval.results,
                    "sources": retrieval.source_realm,
                }
            
            elif task.task_type == TaskType.STORE:
                # Store using Muninn
                node_id = self.muninn.store(
                    content=task.args.get("content", task.prompt),
                    path=task.args.get("path", "default"),
                    memory_type=task.args.get("memory_type", "fact"),
                )
                return {
                    "success": True,
                    "output": node_id,
                }
            
            elif task.task_type == TaskType.TRANSFORM:
                # Transform in Muspelheim
                transformed = self.muspelheim.retry_transform(
                    task.args.get("input", task.prompt),
                    mutation_type=task.args.get("mutation", "transform")
                )
                return {
                    "success": True,
                    "output": transformed,
                }
            
            else:
                # Default: just mark as complete
                return {"success": True, "output": f"Task {task.id} completed"}
            
        except Exception as e:
            logger.error(f"Task execution failed: {task.id}: {e}")
            return {"success": False, "error": str(e)}
    
    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================
    
    def query(self, query: str, **kwargs) -> str:
        """
        Simple query interface - returns just the output.
        
        Args:
            query: The query string
            **kwargs: Additional process arguments
            
        Returns:
            Final output string
        """
        result = self.process(query, **kwargs)
        return result.final_output
    
    def remember(
        self,
        content: Any,
        path: str = "memories",
        **kwargs
    ) -> str:
        """
        Store something in memory.
        
        Args:
            content: Content to remember
            path: Memory path
            **kwargs: Additional storage arguments
            
        Returns:
            Memory node ID
        """
        return self.muninn.store(content, path, **kwargs)
    
    def recall(
        self,
        query: str = None,
        path: str = None,
        **kwargs
    ) -> List[Any]:
        """
        Recall from memory.
        
        Args:
            query: Search query
            path: Memory path
            **kwargs: Additional search arguments
            
        Returns:
            List of recalled content
        """
        nodes = self.muninn.retrieve(query=query, path=path, **kwargs)
        return [n.content for n in nodes]
    
    def fly(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Send Huginn to retrieve information.
        
        Args:
            query: What to retrieve
            **kwargs: Additional retrieval arguments
            
        Returns:
            Retrieval results
        """
        result = self.huginn.fly(query, **kwargs)
        return {
            "results": result.results,
            "source": result.source_realm,
            "confidence": sum(result.relevance_scores) / max(1, len(result.relevance_scores)),
        }
    
    # ========================================================================
    # STATISTICS AND MANAGEMENT
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        return {
            "executions": len(self._execution_history),
            "avg_execution_time": sum(e.execution_time for e in self._execution_history) / max(1, len(self._execution_history)),
            "avg_confidence": sum(e.confidence for e in self._execution_history) / max(1, len(self._execution_history)),
            "success_rate": sum(1 for e in self._execution_history if e.success) / max(1, len(self._execution_history)),
            "llm_queue": self.llm_queue.get_metrics() if self.llm_queue else None,
            "raven_rag": self.raven_rag.get_stats(),
            "helheim": self.helheim.get_stats(),
            "muninn": self.muninn.get_stats(),
            "bifrost": self.bifrost.get_bridge_status(),
        }
    
    def heal(self) -> Dict[str, int]:
        """Self-healing across all systems."""
        fixes = {}
        
        # Heal RAG system
        rag_fixes = self.raven_rag.heal()
        fixes["rag"] = sum(rag_fixes.values())
        
        # Heal Muninn
        fixes["muninn"] = self.muninn.heal_structure()
        
        logger.info(f"World Tree healed: {fixes}")
        
        return fixes
    
    def persist(self):
        """Persist all data to disk."""
        self.muninn.persist_all()
        logger.info("World Tree persisted to disk")
    
    def get_execution_history(self, limit: int = 10) -> List[Dict]:
        """Get recent execution summaries."""
        return [
            {
                "query": e.query[:50],
                "success": e.success,
                "execution_time": e.execution_time,
                "confidence": e.confidence,
                "iterations": e.iterations,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in self._execution_history[-limit:]
        ]


# ============================================================================
# CONVENIENCE ALIAS
# ============================================================================

YggdrasilOrchestrator = WorldTree
