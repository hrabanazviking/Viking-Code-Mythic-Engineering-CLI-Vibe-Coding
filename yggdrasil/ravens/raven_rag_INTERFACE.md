# raven_rag.py — INTERFACE.md

## Class: `RAGContext`

Context built for LLM consumption.

### `to_prompt_string(max_tokens)`
Convert context to a prompt-friendly string.

## Class: `RavenRAGError`

Exception raised by RavenRAG operations.

## Class: `RavenRAG`

The Combined Raven Intelligence System.

Unifies Huginn and Muninn for a complete RAG workflow:

1. Query Analysis (Huginn analyzes the query)
2. Route Decision (Bifrost routes to appropriate sources)
3. Retrieval (Huginn flies to retrieve relevant data)
4. Memory Enhancement (Muninn adds persistent context)
5. Compression (Prepare for LLM consumption)
6. Response Integration (Final assembly)

Features:
- Multi-hop reasoning chains
- Contextual compression for token efficiency
- Automatic memory storage of results
- Anomaly detection for stale data
- Self-healing data structures

### `query(query, memory_paths, use_multi_hop, compress, store_result)`
Execute a RAG query.

Args:
    query: The query string
    memory_paths: Specific memory paths to include
    use_multi_hop: Use multi-hop retrieval
    compress: Compress context for token efficiency
    store_result: Store query in memory
    
Returns:
    RAGContext with all relevant information

### `retrieve_and_generate(query, llm_callable, system_prompt)`
Full RAG pipeline: retrieve context and generate response.

Args:
    query: User query
    llm_callable: Function to call LLM
    system_prompt: Optional system prompt
    **query_kwargs: Additional arguments for query()
    
Returns:
    (response, context) tuple

### `store(content, path)`
Store content in Muninn's memory.

Args:
    content: Content to store
    path: Memory path
    **kwargs: Additional store arguments
    
Returns:
    Node ID

### `search(query, top_k)`
Search Muninn's memory.

Args:
    query: Search query
    top_k: Maximum results
    **kwargs: Additional search arguments
    
Returns:
    List of matching nodes

### `detect_anomalies()`
Detect anomalies in stored data.

Checks for:
- Stale data (not accessed in long time)
- Orphaned nodes
- Duplicate content

Returns:
    List of detected anomalies

### `heal()`
Self-healing: fix data issues.

Returns:
    Summary of fixes applied

### `get_stats()`
Get RAG system statistics.

### `export_state()`
Export full state for backup/migration.

---
**Contract Version**: 1.0 | v8.0.0
