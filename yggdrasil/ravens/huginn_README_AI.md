# huginn.py — README_AI.md

## Purpose
Huginn - The Thought Raven
==========================

Odin's raven of Thought. Flies ahead to scout and retrieve,
bringing back only what is needed for the current query.

Huginn provides the FOCUS. By acting as the scout, he prevents
the main model from getting "distracted" by the entire world.
He only brings back the specific "eye-witness" data needed
for the current thought.

Features:
- Dynamic query routing
- Hierarchical retrieval
- Context compression
- Multi-hop reasoning
- Adaptive sea

## Technical Architecture
- **Classes**: 2 main classes
  - `RetrievalResult`: Result from a Huginn retrieval flight.
  - `Huginn`: The Thought Raven - Dynamic Querying and Retrieval.

Huginn scouts ahead through the branches of Ygg

## Key Components
### `RetrievalResult`
Result from a Huginn retrieval flight.

### `Huginn`
The Thought Raven - Dynamic Querying and Retrieval.

Huginn scouts ahead through the branches of Yggdrasil,
bringing back only the relevant information needed
for the current thought/query.

Features:
**Methods**: __init__, _try_import_vectorizer, analyze_query, route_query, fly

## Dependencies
```
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
```

---
**Last Updated**: February 18, 2026 | v8.0.0
