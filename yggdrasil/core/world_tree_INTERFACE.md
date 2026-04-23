# world_tree.py — INTERFACE.md

## Class: `ExecutionMode`

Execution modes for the World Tree.

## Class: `OrchestratorResult`

Result from a complete orchestration cycle.

## Class: `WorldTree`

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

### `process(query, context, memory_paths)`
Process a query through the World Tree.

This is the main entry point for the cognitive system.

Args:
    query: The query to process
    context: Additional context
    memory_paths: Paths to include from memory
    
Returns:
    OrchestratorResult with final output and metadata

### `query(query)`
Simple query interface - returns just the output.

Args:
    query: The query string
    **kwargs: Additional process arguments
    
Returns:
    Final output string

### `remember(content, path)`
Store something in memory.

Args:
    content: Content to remember
    path: Memory path
    **kwargs: Additional storage arguments
    
Returns:
    Memory node ID

### `recall(query, path)`
Recall from memory.

Args:
    query: Search query
    path: Memory path
    **kwargs: Additional search arguments
    
Returns:
    List of recalled content

### `fly(query)`
Send Huginn to retrieve information.

Args:
    query: What to retrieve
    **kwargs: Additional retrieval arguments
    
Returns:
    Retrieval results

### `get_stats()`
Get comprehensive system statistics.

### `heal()`
Self-healing across all systems.

### `persist()`
Persist all data to disk.

### `get_execution_history(limit)`
Get recent execution summaries.

---
**Contract Version**: 1.0 | v8.0.0
