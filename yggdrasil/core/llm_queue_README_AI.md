# llm_queue.py — README_AI.md

## Purpose
LLM Queue - Sequential LLM Processing
=====================================

Ensures the local LLM model processes one query at a time,
maintaining stability and preventing cognitive overload.

Like Odin's ravens returning one at a time to whisper wisdom,
the queue ensures orderly communication with the oracle.

## Technical Architecture
- **Classes**: 4 main classes
  - `QueuePriority`: Priority levels for queued requests.
  - `LLMRequest`: A single LLM inference request.
  - `LLMQueue`: Queue for sequential LLM processing.

Ensures the local model processes one query at a time,
like ra

## Key Components
### `QueuePriority`
Priority levels for queued requests.

### `LLMRequest`
A single LLM inference request.
**Methods**: wait_time, execution_time

### `LLMQueue`
Queue for sequential LLM processing.

Ensures the local model processes one query at a time,
like ravens returning to Odin one by one.

Features:
- Priority-based queuing
- Thread-safe operation
- Tim
**Methods**: __init__, _generate_request_id, enqueue, process_next, process_all

### `MockLLM`
Mock LLM for testing.
**Methods**: __init__, __call__

## Dependencies
```
import logging
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
```

---
**Last Updated**: February 18, 2026 | v8.0.0
