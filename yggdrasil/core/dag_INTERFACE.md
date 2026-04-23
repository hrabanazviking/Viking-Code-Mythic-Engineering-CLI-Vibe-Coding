# dag.py — INTERFACE.md

## Class: `TaskType`

Types of tasks that can be executed.

## Class: `TaskStatus`

Status of a task in the DAG.

## Class: `RealmAffinity`

Which realm a task belongs to.

## Class: `TaskNode`

A single task node in the DAG.

### `to_dict()`
Serialize to dictionary.

### `from_dict(cls, data)`
Deserialize from dictionary.

## Class: `DAG`

Directed Acyclic Graph for task orchestration.

The tree's skeleton—handles dependencies, ready tasks, and execution order.
Like Yggdrasil's roots connecting the nine worlds.

### `add_node(node)`
Add a node to the DAG.

Args:
    node: TaskNode object or dict with node data
    
Returns:
    Node ID

### `remove_node(node_id)`
Remove a node from the DAG.

### `get_ready_tasks()`
Get all tasks that are ready to execute.

A task is ready when all its dependencies are completed.

Returns:
    List of ready TaskNode objects, sorted by priority

### `mark_completed(node_id, result)`
Mark a node as completed.

### `mark_failed(node_id, error)`
Mark a node as failed.

### `mark_running(node_id)`
Mark a node as running.

### `is_finished()`
Check if the DAG has finished (all tasks complete or failed).

### `has_pending()`
Check if there are still pending tasks.

### `get_results()`
Get all results from completed tasks.

### `get_errors()`
Get all errors from failed tasks.

### `get_nodes_by_realm(realm)`
Get all nodes belonging to a specific realm.

### `get_nodes_by_type(task_type)`
Get all nodes of a specific type.

### `get_execution_order()`
Get the topological order for execution.

Returns:
    List of node IDs in execution order

### `validate()`
Validate the DAG for cycles and missing dependencies.

Returns:
    List of error messages (empty if valid)

### `to_dict()`
Serialize the DAG to dictionary.

### `from_dict(cls, data)`
Deserialize from dictionary.

## Module Functions

### `create_simple_dag(tasks)`
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

### `merge_dags(dag1, dag2, prefix)`
Merge two DAGs into one.

Args:
    dag1: First DAG
    dag2: Second DAG  
    prefix: Prefix for second DAG's node IDs to avoid conflicts
    
Returns:
    Merged DAG

---
**Contract Version**: 1.0 | v8.0.0
