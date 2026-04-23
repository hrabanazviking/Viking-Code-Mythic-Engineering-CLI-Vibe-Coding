# muninn.py — INTERFACE.md

## Class: `MemoryNode`

A node in Muninn's memory tree.

### `to_dict()`

### `from_dict(cls, data)`

## Class: `Muninn`

The Memory Raven - Persistent Storage and Structure.

Muninn manages the long-term memory and organizational structure
of the entire Yggdrasil system. He ensures that when Huginn
brings back new information, it is properly nested in the right place.

Features:
- Hierarchical memory tree
- Multi-format support (JSON, YAML, Markdown)
- Self-healing data structures
- Automatic indexing
- Sync with Helheim for persistence

### `store(content, path, memory_type, importance, tags, metadata)`
Store content in memory.

Args:
    content: Content to store
    path: Hierarchical path (e.g., "game/characters/player")
    memory_type: Type of memory
    importance: Importance level 1-10
    tags: Tags for indexing
    metadata: Additional metadata
    
Returns:
    Node ID

### `retrieve(query, path, tags, memory_type, top_k)`
Retrieve memories matching criteria.

Args:
    query: Text query to match against content
    path: Path prefix to filter by
    tags: Tags to filter by (any match)
    memory_type: Type to filter by
    top_k: Maximum results
    
Returns:
    List of matching MemoryNodes

### `get_by_path(path)`
Get all nodes at a specific path.

### `get_children(parent_path)`
Get all child paths and their nodes.

### `update(node_id, content)`
Update an existing node.

Args:
    node_id: Node to update
    content: New content (optional)
    **kwargs: Other fields to update
    
Returns:
    Success status

### `delete(node_id)`
Delete a node from memory.

### `move(node_id, new_path)`
Move a node to a new path.

### `load_file(file_path, base_path)`
Load a file into memory.

Args:
    file_path: Path to file
    base_path: Base path prefix for stored content
    
Returns:
    List of created node IDs

### `save_to_file(path, file_path, format)`
Save memory path contents to a file.

Args:
    path: Memory path to export
    file_path: Output file path
    format: Output format (json, yaml)

### `persist_all()`
Persist all nodes to disk.

### `get_tree_structure()`
Get the hierarchical tree structure.

### `heal_structure()`
Self-healing: fix any inconsistencies in indices.

Returns:
    Number of fixes applied

### `get_stats()`
Get memory statistics.

### `dump(limit)`
Dump memory state for debugging.

---
**Contract Version**: 1.0 | v8.0.0
