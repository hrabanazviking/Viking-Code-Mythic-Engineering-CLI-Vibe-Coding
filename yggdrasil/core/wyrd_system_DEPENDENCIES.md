# {filename}_DEPENDENCIES.md

## Internal Dependencies

### Direct Imports
```python
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import random
import yaml
```

### Data Dependencies
```
data/
├── charts/
│   ├── runes.yaml           # Rune definitions
│   └── fate_threads.yaml    # Fate thread templates
└── sessions/
    └── cooldowns/           # Rune cooldown state
```

## External Dependencies

### Required
```
pyyaml>=6.0          # Chart loading
```

### Optional
```
None                 # Pure Python implementation
```

## Dependency Injection Points

### Well Factory
```python
def __init__(
    self,
    data_path: Path,
    well_factory: Optional[WellFactory] = None
):
    self.well_factory = well_factory or DefaultWellFactory()
```

### Cooldown Storage
```python
# Pluggable storage backend
def __init__(
    self,
    storage: Optional[CooldownStorage] = None
):
    self.storage = storage or FileStorage()
```

## State Persistence

### Save Format
```yaml
# data/sessions/cooldowns/{session_id}.yaml
runes:
  fehu:
    last_drawn: "2026-02-18T10:30:00"
    cooldown_minutes: 60
fate_threads:
  - id: "thread_001"
    description: "Will face father's killer"
    trigger_turn: 15
```
