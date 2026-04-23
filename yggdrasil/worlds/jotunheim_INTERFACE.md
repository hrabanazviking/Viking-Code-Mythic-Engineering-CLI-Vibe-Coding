# jotunheim.py — INTERFACE.md

## Class: `ExecutionResult`

Result from a Jotunheim execution.

## Class: `Jotunheim`

Raw Power & Chaotic Execution.

Handles:
- Heavy Python execution bursts for simulations
- Chaotic parallelism via thread/process pools
- Force application through math solvers
- Destruction of invalid paths with error handling
- Raw data crunching with numpy/scipy

### `execute_script(script, args, timeout, task_id)`
Execute a Python script in subprocess.

Args:
    script: Python code to execute
    args: Arguments to pass as JSON
    timeout: Execution timeout in seconds
    task_id: Optional task identifier
    
Returns:
    ExecutionResult object

### `execute_function(func, args, kwargs, task_id)`
Execute a Python function directly.

Args:
    func: Function to execute
    args: Positional arguments
    kwargs: Keyword arguments
    task_id: Optional task identifier
    
Returns:
    ExecutionResult object

### `execute_parallel(tasks, timeout_per_task)`
Execute multiple tasks in parallel.

Args:
    tasks: List of task dicts with 'script' or 'function' keys
    timeout_per_task: Timeout for each task
    
Returns:
    List of ExecutionResult objects

### `calculate(expression)`
Evaluate a mathematical expression.

Args:
    expression: Math expression to evaluate
    
Returns:
    Dict with result and metadata

### `crunch_data(data, operation)`
Perform data operations.

Args:
    data: Data to process
    operation: Operation to perform (mean, sum, std, min, max)
    
Returns:
    Result dictionary

### `destroy_invalid(results)`
Filter out failed results.

Args:
    results: List of execution results
    
Returns:
    List of successful results only

### `get_execution_history(limit)`
Get recent execution summaries.

---
**Contract Version**: 1.0 | v8.0.0
