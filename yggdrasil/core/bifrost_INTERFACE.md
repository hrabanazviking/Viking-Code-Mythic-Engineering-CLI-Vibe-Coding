# bifrost.py — INTERFACE.md

## Class: `RouteDecision`

A routing decision from Bifrost.

## Class: `RealmRouter`

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

### `route(query, context, hints)`
Route a query to the appropriate realm(s).

Args:
    query: The query or task description
    context: Additional context (current realm, history, etc.)
    hints: Suggested realms to consider
    
Returns:
    RouteDecision with routing information

### `get_realm_for_task_type(task_type)`
Get the default realm for a task type.

### `get_routing_stats()`
Get routing statistics.

## Class: `Bifrost`

The Bifrost Bridge - Main routing interface.

Coordinates between the RealmRouter and provides
additional features like multi-realm routing and
route optimization.

### `open_bridge(realm)`
Open the bridge to a realm.

### `close_bridge(realm)`
Close the bridge to a realm.

### `is_bridge_open(realm)`
Check if bridge to realm is open.

### `route(query)`
Route a query across Bifrost.

Args:
    query: The query to route
    **kwargs: Additional routing parameters
    
Returns:
    RouteDecision

### `route_multi(queries)`
Route multiple queries and group by realm.

Args:
    queries: List of queries to route
    **kwargs: Additional routing parameters
    
Returns:
    Dict mapping realms to lists of (query, decision) tuples

### `get_bridge_status()`
Get status of all bridges.

### `get_active_bridges()`
Get list of active bridge names.

---
**Contract Version**: 1.0 | v8.0.0
