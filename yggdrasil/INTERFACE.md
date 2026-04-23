# Yggdrasil — INTERFACE

## `WorldTree.query(query_text, mode="sequential") -> str`
Main entry point for complex queries. Returns a woven response after processing through the Nine Worlds.

## `Huginn.fly(query, max_results=5) -> List[MemoryNode]`
Retrieves relevant memories from Muninn’s tree.

## `Muninn.store(content, path, memory_type, importance, tags) -> str`
Stores a new MemoryNode. Returns its ID.

## `Bifrost.route(query) -> RouteDecision`
Analyzes query and returns which realms should process it. Returns a dict with `primary_realm`, `secondary_realms`, `task_type`, `priority`, `parallel_safe`.

## `DAGEngine.build_and_execute(plan) -> Dict`
Executes a task graph. Plan is a list of `TaskNode` objects with dependencies.

## Rules
- All AI calls go through the `LLMQueue` – no concurrent LLM requests.
- Realms are stateless; all persistent data lives in Muninn/Helheim.