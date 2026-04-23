# wyrd_system.py — README_AI.md

## Purpose
Wyrd System - The Three Sacred Wells
=====================================

In Norse cosmology, three sacred wells lie at the roots of Yggdrasil:

1. URÐARBRUNNR (Well of Urd/Fate) - The Past
   - Where the Norns dwell
   - Records all that has happened
   - Stores completed events and their consequences

2. MÍMISBRUNNR (Mimir's Well) - The Present/Wisdom
   - Source of all knowledge
   - Where Odin sacrificed his eye
   - Stores current state and active knowledge

3. HVERGELMIR (Roaring Kettle)

## Technical Architecture
- **Classes**: 7 main classes
  - `WellType`: The three sacred wells.
  - `NornType`: The three Norns who tend the wells.
  - `WyrdThread`: A single thread of fate.
- **Functions**: 1 module-level functions

## Key Components
### `WellType`
The three sacred wells.

### `NornType`
The three Norns who tend the wells.

### `WyrdThread`
A single thread of fate.

### `WellContents`
Contents of a sacred well.

### `SacredWell`
A single sacred well that stores threads of fate.
**Methods**: __init__, _generate_thread_id, add_thread, get_thread, get_threads_by_type

## Dependencies
```
import logging
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import threading
```

---
**Last Updated**: February 18, 2026 | v8.0.0
