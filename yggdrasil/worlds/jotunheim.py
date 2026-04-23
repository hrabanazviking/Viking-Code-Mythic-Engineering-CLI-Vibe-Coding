"""
Jotunheim - Raw Power & Chaotic Execution
========================================

The realm of giants—wild strength, destruction, force, untamed energy.
The brute computational might.

Processes:
- Heavy Python execution bursts
- Simulations and calculations
- Parallel processing via Ray/multiprocessing
- Force application through math solvers
- Raw data crunching

This is where the giants do the heavy lifting.
"""

import logging
import subprocess
import json
import time
from typing import Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result from a Jotunheim execution."""
    task_id: str
    success: bool
    stdout: str
    stderr: str
    return_code: int
    execution_time: float
    timestamp: datetime = field(default_factory=datetime.now)


class Jotunheim:
    """
    Raw Power & Chaotic Execution.
    
    Handles:
    - Heavy Python execution bursts for simulations
    - Chaotic parallelism via thread/process pools
    - Force application through math solvers
    - Destruction of invalid paths with error handling
    - Raw data crunching with numpy/scipy
    """
    
    def __init__(self, max_workers: int = 4, use_processes: bool = False):
        """
        Initialize Jotunheim.
        
        Args:
            max_workers: Maximum parallel workers
            use_processes: Use process pool instead of thread pool
        """
        self.max_workers = max_workers
        self.use_processes = use_processes
        self._execution_history: List[ExecutionResult] = []
        self._lock = threading.Lock()
        
        # Import optional heavy libraries
        self._numpy = None
        self._sympy = None
        self._try_import_heavy_libs()
    
    def _try_import_heavy_libs(self):
        """Try to import numpy and sympy for calculations."""
        try:
            import numpy as np
            self._numpy = np
            logger.debug("Jotunheim: numpy available")
        except ImportError:
            logger.debug("Jotunheim: numpy not available")
        
        try:
            import sympy as sp
            self._sympy = sp
            logger.debug("Jotunheim: sympy available")
        except ImportError:
            logger.debug("Jotunheim: sympy not available")
    
    def execute_script(
        self,
        script: str,
        args: Dict[str, Any] = None,
        timeout: float = 30.0,
        task_id: str = None
    ) -> ExecutionResult:
        """
        Execute a Python script in subprocess.
        
        Args:
            script: Python code to execute
            args: Arguments to pass as JSON
            timeout: Execution timeout in seconds
            task_id: Optional task identifier
            
        Returns:
            ExecutionResult object
        """
        task_id = task_id or f"exec_{int(time.time())}"
        start_time = time.time()
        
        try:
            # Build command
            if script.startswith('#') or '\n' in script:
                # Inline script
                cmd = ["python3", "-c", script]
            else:
                # Script file
                cmd = ["python3", script]
            
            if args:
                cmd.append(json.dumps(args))
            
            # Execute
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            result = ExecutionResult(
                task_id=task_id,
                success=process.returncode == 0,
                stdout=process.stdout.strip(),
                stderr=process.stderr.strip(),
                return_code=process.returncode,
                execution_time=time.time() - start_time,
            )
            
        except subprocess.TimeoutExpired:
            result = ExecutionResult(
                task_id=task_id,
                success=False,
                stdout="",
                stderr="Execution timed out",
                return_code=-1,
                execution_time=timeout,
            )
        except Exception as e:
            result = ExecutionResult(
                task_id=task_id,
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-2,
                execution_time=time.time() - start_time,
            )
        
        with self._lock:
            self._execution_history.append(result)
            if len(self._execution_history) > 100:
                self._execution_history = self._execution_history[-50:]
        
        logger.debug(f"Jotunheim executed {task_id}: success={result.success}, "
                    f"time={result.execution_time:.2f}s")
        
        return result
    
    def execute_function(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        task_id: str = None
    ) -> ExecutionResult:
        """
        Execute a Python function directly.
        
        Args:
            func: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            task_id: Optional task identifier
            
        Returns:
            ExecutionResult object
        """
        task_id = task_id or f"func_{int(time.time())}"
        kwargs = kwargs or {}
        start_time = time.time()
        
        try:
            result_value = func(*args, **kwargs)
            
            result = ExecutionResult(
                task_id=task_id,
                success=True,
                stdout=str(result_value),
                stderr="",
                return_code=0,
                execution_time=time.time() - start_time,
            )
        except Exception as e:
            result = ExecutionResult(
                task_id=task_id,
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                execution_time=time.time() - start_time,
            )
        
        with self._lock:
            self._execution_history.append(result)
        
        return result
    
    def execute_parallel(
        self,
        tasks: List[Dict[str, Any]],
        timeout_per_task: float = 30.0
    ) -> List[ExecutionResult]:
        """
        Execute multiple tasks in parallel.
        
        Args:
            tasks: List of task dicts with 'script' or 'function' keys
            timeout_per_task: Timeout for each task
            
        Returns:
            List of ExecutionResult objects
        """
        results = []
        
        # Choose executor type
        executor_class = ProcessPoolExecutor if self.use_processes else ThreadPoolExecutor
        
        with executor_class(max_workers=self.max_workers) as executor:
            futures = {}
            
            for i, task in enumerate(tasks):
                task_id = task.get("id", f"parallel_{i}")
                
                if "script" in task:
                    future = executor.submit(
                        self.execute_script,
                        task["script"],
                        task.get("args"),
                        timeout_per_task,
                        task_id
                    )
                elif "function" in task:
                    future = executor.submit(
                        self.execute_function,
                        task["function"],
                        task.get("args", ()),
                        task.get("kwargs"),
                        task_id
                    )
                else:
                    continue
                
                futures[future] = task_id
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    task_id = futures[future]
                    results.append(ExecutionResult(
                        task_id=task_id,
                        success=False,
                        stdout="",
                        stderr=str(e),
                        return_code=-1,
                        execution_time=0,
                    ))
        
        logger.info(f"Jotunheim parallel: {len(results)} tasks, "
                   f"{sum(1 for r in results if r.success)} succeeded")
        
        return results
    
    def calculate(self, expression: str) -> Dict[str, Any]:
        """
        Evaluate a mathematical expression.
        
        Args:
            expression: Math expression to evaluate
            
        Returns:
            Dict with result and metadata
        """
        start_time = time.time()
        
        try:
            # Try sympy first for symbolic math
            if self._sympy and any(op in expression for op in ['solve', 'diff', 'integrate']):
                result = self._evaluate_sympy(expression)
            # Try numpy for numerical
            elif self._numpy and any(op in expression for op in ['array', 'mean', 'std', 'sum']):
                result = self._evaluate_numpy(expression)
            else:
                # Fall back to safe eval
                result = self._safe_eval(expression)
            
            return {
                "success": True,
                "result": result,
                "expression": expression,
                "execution_time": time.time() - start_time,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "expression": expression,
                "execution_time": time.time() - start_time,
            }
    
    def _safe_eval(self, expression: str) -> Any:
        """Safely evaluate a simple math expression."""
        import ast
        import operator
        
        # Allowed operations
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }
        
        def _eval(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                return operators[type(node.op)](_eval(node.left), _eval(node.right))
            elif isinstance(node, ast.UnaryOp):
                return operators[type(node.op)](_eval(node.operand))
            else:
                raise ValueError(f"Unsupported operation: {type(node)}")
        
        tree = ast.parse(expression, mode='eval')
        return _eval(tree.body)
    
    def _evaluate_sympy(self, expression: str) -> str:
        """Evaluate with sympy."""
        if not self._sympy:
            raise ImportError("sympy not available")
        
        # Create common symbols
        x, y, z = self._sympy.symbols('x y z')
        
        # Evaluate
        result = eval(expression, {"sp": self._sympy, "x": x, "y": y, "z": z})
        return str(result)
    
    def _evaluate_numpy(self, expression: str) -> Any:
        """Evaluate with numpy."""
        if not self._numpy:
            raise ImportError("numpy not available")
        
        result = eval(expression, {"np": self._numpy})
        
        # Convert numpy types to Python types
        if hasattr(result, 'tolist'):
            return result.tolist()
        return result
    
    def crunch_data(self, data: List[Any], operation: str = "mean") -> Dict[str, Any]:
        """
        Perform data operations.
        
        Args:
            data: Data to process
            operation: Operation to perform (mean, sum, std, min, max)
            
        Returns:
            Result dictionary
        """
        if not self._numpy:
            # Fallback to built-in
            if operation == "mean":
                result = sum(data) / len(data) if data else 0
            elif operation == "sum":
                result = sum(data)
            elif operation == "min":
                result = min(data) if data else None
            elif operation == "max":
                result = max(data) if data else None
            else:
                result = data
        else:
            np = self._numpy
            arr = np.array(data)
            
            ops = {
                "mean": np.mean,
                "sum": np.sum,
                "std": np.std,
                "min": np.min,
                "max": np.max,
                "median": np.median,
            }
            
            func = ops.get(operation, lambda x: x)
            result = func(arr)
            
            if hasattr(result, 'item'):
                result = result.item()
        
        return {
            "operation": operation,
            "result": result,
            "data_size": len(data),
        }
    
    def destroy_invalid(self, results: List[ExecutionResult]) -> List[ExecutionResult]:
        """
        Filter out failed results.
        
        Args:
            results: List of execution results
            
        Returns:
            List of successful results only
        """
        valid = [r for r in results if r.success]
        invalid_count = len(results) - len(valid)
        
        if invalid_count > 0:
            logger.warning(f"Jotunheim destroyed {invalid_count} invalid results")
        
        return valid
    
    def get_execution_history(self, limit: int = 10) -> List[Dict]:
        """Get recent execution summaries."""
        with self._lock:
            return [
                {
                    "task_id": r.task_id,
                    "success": r.success,
                    "return_code": r.return_code,
                    "execution_time": r.execution_time,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in self._execution_history[-limit:]
            ]
