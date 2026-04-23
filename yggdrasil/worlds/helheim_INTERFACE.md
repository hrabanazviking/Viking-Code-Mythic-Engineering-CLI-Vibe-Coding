# helheim.py — INTERFACE.md

## Class: `Memory`

A single memory entry in Helheim.

### `to_dict()`

## Class: `Helheim`

Reflection & Ancestral Memory.

Handles:
- Memory storage with SQLite persistence
- Ancestral log analysis
- Pattern resurrection and matching
- Memory compression algorithms
- Wisdom extraction from past runs

### `store(content, memory_type, realm_source, importance, tags)`
Store a memory.

Args:
    content: Content to store
    memory_type: Type of memory (fact, event, result, error, lesson)
    realm_source: Which realm created this memory
    importance: Importance level 1-10
    tags: Optional tags for indexing
    
Returns:
    Memory ID

### `retrieve(memory_id)`
Retrieve a specific memory.

Args:
    memory_id: Memory ID to retrieve
    
Returns:
    Memory object or None

### `search(query, memory_type, tags, min_importance, limit)`
Search memories.

Args:
    query: Text to search in content
    memory_type: Filter by type
    tags: Filter by tags (any match)
    min_importance: Minimum importance level
    limit: Maximum results
    
Returns:
    List of matching memories

### `retrieve_ancestral(realm, limit)`
Retrieve ancestral memories from a specific realm.

Args:
    realm: Realm to search
    limit: Maximum results
    
Returns:
    List of memories from that realm

### `analyze_logs(memory_type)`
Analyze logs/errors for patterns.

Args:
    memory_type: Type to analyze
    
Returns:
    Analysis results

### `resurrect_patterns(pattern)`
Find memories matching a pattern for resurrection/reuse.

Args:
    pattern: Pattern to match
    
Returns:
    Matching memories

### `archive_memory(data)`
Archive data with compression.

Args:
    data: Data to archive
    
Returns:
    Compressed JSON string

### `extract_wisdom(realm, limit)`
Extract wisdom (high-importance lessons) from past runs.

Args:
    realm: Optional realm filter
    limit: Maximum wisdom items
    
Returns:
    List of wisdom strings

### `dump(limit)`
Dump all memories for serialization.

Args:
    limit: Maximum memories to dump
    
Returns:
    Dictionary of all memories

### `clear(memory_type)`
Clear memories.

Args:
    memory_type: Optional type filter (clears all if None)

### `get_stats()`
Get memory statistics.

---
**Contract Version**: 1.0 | v8.0.0
