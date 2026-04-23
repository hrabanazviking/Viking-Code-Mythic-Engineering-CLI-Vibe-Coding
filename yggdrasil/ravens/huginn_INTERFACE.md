# huginn.py — INTERFACE.md

## Class: `RetrievalResult`

Result from a Huginn retrieval flight.

## Class: `Huginn`

The Thought Raven - Dynamic Querying and Retrieval.

Huginn scouts ahead through the branches of Yggdrasil,
bringing back only the relevant information needed
for the current thought/query.

Features:
- Query analysis and routing
- Hierarchical index traversal
- Context compression for token efficiency
- Multi-hop reasoning chains
- Adaptive retrieval strategies

### `analyze_query(query)`
Analyze a query to determine retrieval strategy.

Args:
    query: The query to analyze
    
Returns:
    Analysis dict with strategy recommendations

### `route_query(query)`
Determine which realm/source to query.

Args:
    query: The query
    
Returns:
    Realm name to route to

### `fly(query, max_results, compress)`
Send Huginn flying to retrieve relevant information.

Args:
    query: What to search for
    max_results: Maximum results to return
    compress: Whether to compress results for token efficiency
    
Returns:
    RetrievalResult with findings

### `multi_hop_retrieve(initial_query, hop_count, max_results_per_hop)`
Perform multi-hop retrieval, chaining queries.

Args:
    initial_query: Starting query
    hop_count: Number of hops to perform
    max_results_per_hop: Results per hop
    
Returns:
    List of RetrievalResults from each hop

### `semantic_search(query, documents, top_k)`
Perform semantic search using TF-IDF.

Args:
    query: Query string
    documents: List of documents to search
    top_k: Number of results
    
Returns:
    List of (index, score) tuples

### `get_flight_stats()`
Get statistics about Huginn's flights.

---
**Contract Version**: 1.0 | v8.0.0
