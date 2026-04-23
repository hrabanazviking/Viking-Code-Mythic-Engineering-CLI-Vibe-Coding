# alfheim.py — INTERFACE.md

## Class: `Alfheim`

Illusion & Agile Routing.

Handles dynamic routing, probabilistic branching, path filtering,
decoy generation, and route recalculation.

### `route_node_type(query)`
Determine best route based on query heuristics.

### `probabilistic_branching(options, weights)`
Select branches probabilistically.

### `filter_heavy_paths(paths, threshold)`
Filter out computationally heavy paths.

### `generate_decoys(data, count)`
Generate decoy data for testing.

### `recalculate_path(graph, start, end)`
Simple BFS path finding.

### `get_route_stats()`
Get routing statistics.

---
**Contract Version**: 1.0 | v8.0.0
