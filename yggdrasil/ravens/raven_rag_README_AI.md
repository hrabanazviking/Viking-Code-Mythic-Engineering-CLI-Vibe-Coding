# raven_rag.py — README_AI.md

## Purpose
RavenRAG - The Combined Raven Intelligence System
=================================================

Unifies Huginn (Thought/Retrieval) and Muninn (Memory/Storage)
into a complete Retrieval-Augmented Generation system.

This is RAG 9.0 - elevating beyond basic retrieval with:
- Multi-hop reasoning
- Contextual compression
- Hierarchical indexing
- Anomaly detection
- Self-healing structures
- Integration with all Nine Worlds

## Technical Architecture
- **Classes**: 3 main classes
  - `RAGContext`: Context built for LLM consumption.
  - `RavenRAGError`: Exception raised by RavenRAG operations.
  - `RavenRAG`: The Combined Raven Intelligence System.

Unifies Huginn and Muninn for a complete RAG workflow:

1. 

## Key Components
### `RAGContext`
Context built for LLM consumption.
**Methods**: to_prompt_string

### `RavenRAGError`
Exception raised by RavenRAG operations.

### `RavenRAG`
The Combined Raven Intelligence System.

Unifies Huginn and Muninn for a complete RAG workflow:

1. Query Analysis (Huginn analyzes the query)
2. Route Decision (Bifrost routes to appropriate sources)
**Methods**: __init__, query, retrieve_and_generate, store, search

## Dependencies
```
import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from yggdrasil.ravens.huginn import Huginn, RetrievalResult
from yggdrasil.ravens.muninn import Muninn, MemoryNode
```

---
**Last Updated**: February 18, 2026 | v8.0.0
