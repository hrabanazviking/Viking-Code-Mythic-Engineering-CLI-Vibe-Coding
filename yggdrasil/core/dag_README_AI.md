# dag.py — README_AI.md

## Purpose
DAG (Directed Acyclic Graph) Engine
===================================

The skeleton of Yggdrasil's task management - handles dependencies,
ready tasks, and execution order across the Nine Worlds.

Like the roots of the World Tree, it connects all realms while
maintaining the proper order of operations.

## Technical Architecture
- **Classes**: 5 main classes
  - `TaskType`: Types of tasks that can be executed.
  - `TaskStatus`: Status of a task in the DAG.
  - `RealmAffinity`: Which realm a task belongs to.
- **Functions**: 2 module-level functions

## Key Components
### `TaskType`
Types of tasks that can be executed.

### `TaskStatus`
Status of a task in the DAG.

### `RealmAffinity`
Which realm a task belongs to.

### `TaskNode`
A single task node in the DAG.
**Methods**: to_dict, from_dict

### `DAG`
Directed Acyclic Graph for task orchestration.

The tree's skeleton—handles dependencies, ready tasks, and execution order.
Like Yggdrasil's roots connecting the nine worlds.
**Methods**: __init__, add_node, remove_node, get_ready_tasks, mark_completed

## Dependencies
```
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
```

---
**Last Updated**: February 18, 2026 | v8.0.0
