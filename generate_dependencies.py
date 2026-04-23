#!/usr/bin/env python3
"""Generate DEPENDENCIES.md for all Python files - Dependency graphs and injection points."""

from pathlib import Path
import ast
import re

DEPENDENCIES_TEMPLATES = {
    "engine": """# {filename}_DEPENDENCIES.md

## Internal Dependencies

### Direct Imports
```python
from ai.openrouter import OpenRouterClient          # AI communication
from ai.prompt_builder import PromptBuilder         # Prompt construction
from systems.wyrd_system import WyrdSystem          # Chaos/fate mechanics
from systems.memory_system import MemorySystem      # Persistence
from session.memory_manager import MemoryManager    # Session management
from yggdrasil.router import YggdrasilAIRouter      # AI routing (v8.0.0+)
```

### Dependency Graph
```
engine.py
├── ai/
│   ├── openrouter.py
│   ├── prompt_builder.py
│   └── local_providers.py
├── systems/
│   ├── wyrd_system.py
│   ├── memory_system.py
│   ├── chaos_system.py
│   └── ...
├── session/
│   ├── memory_manager.py
│   └── session_manager.py
├── yggdrasil/
│   └── router.py
└── generators/
    └── character_generator.py
```

## External Dependencies

### Required Packages
```
pyyaml>=6.0          # YAML parsing
requests>=2.28.0     # HTTP for OpenRouter
aiohttp>=3.8.0       # Async HTTP
rich>=13.0.0         # Terminal UI
```

### Optional Packages
```
tiktoken>=0.5.0      # Token counting
psutil>=5.9.0        # System metrics
```

## Dependency Injection Points

### Constructor Injection
```python
def __init__(
    self,
    ai_client: Optional[AIClient] = None,      # Injectable AI
    data_path: Path = Path("data"),              # Data location
    config: Optional[Dict] = None,               # Configuration
    comprehensive_logger = None                   # Logging
):
    self.ai_client = ai_client
```

### Factory Methods
```python
@staticmethod
def create_with_openrouter(api_key: str) -> "NorseSagaEngine":
    ai_client = OpenRouterClient(api_key)
    return NorseSagaEngine(ai_client=ai_client)
```

## Circular Dependencies

### Potential Issues
- **engine.py** ↔ **systems/wyrd_system.py**: Both reference GameState
- **ai/prompt_builder.py** ↔ **core/engine.py**: PromptBuilder needs GameContext

### Resolution
Use forward references and late imports:
```python
if TYPE_CHECKING:
    from core.engine import GameContext  # Forward ref only for type checking
```
""",
    "prompt_builder": """# {filename}_DEPENDENCIES.md

## Internal Dependencies

### Direct Imports
```python
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import random
from dataclasses import dataclass
```

### Data Dependencies
```
data/
├── charts/
│   ├── gm_mindset.yaml
│   ├── viking_values.yaml
│   ├── norse_culture.yaml
│   └── ...
└── rag_index/           # BM25 index files
```

## External Dependencies

### Required
```
pyyaml>=6.0          # Chart loading
numpy>=1.24.0        # RAG vector operations
rank-bm25>=0.2.2     # BM25 search
```

## Dependency Injection Points

### RAG Strategy Injection
```python
def __init__(
    self,
    data_path: str,
    rag_strategy: Optional[RAGStrategy] = None,  # Pluggable RAG
    yggdrasil = None                              # Optional Yggdrasil
):
    self.rag = rag_strategy or BM25Strategy()
```

### Chart Loading
```python
# Charts loaded at init, but can be reloaded
def reload_charts(self) -> None:
    self.charts = self._load_all_charts()
```

## Version Compatibility

### Breaking Changes
- v8.0.0: Added Yggdrasil integration (optional)
- v4.5.0: Added 18-layer system (backward compatible)
- v4.0.0: Major refactor of chart format
""",
    "wyrd_system": """# {filename}_DEPENDENCIES.md

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
""",
    "default": """# {filename}_DEPENDENCIES.md

## Internal Dependencies

### Direct Imports
```python
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
```

## External Dependencies

### Required
```python
# List from requirements.txt or imports
pyyaml>=6.0
requests>=2.28.0
```

## Dependency Injection Points

### Constructor
```python
def __init__(
    self,
    data_path: Path = Path("data"),
    config: Optional[Dict] = None,
    logger: Optional[logging.Logger] = None
):
    self.data_path = data_path
    self.config = config or {}
    self.logger = logger or logging.getLogger(__name__)
```

## Dependency Graph

```
{filename}.py
├── Standard Library
│   ├── pathlib
│   ├── typing
│   └── logging
└── Third Party
    └── pyyaml
```
"""
}

def get_template(filename: str) -> str:
    filename_lower = filename.lower()
    for key in DEPENDENCIES_TEMPLATES:
        if key in filename_lower:
            return DEPENDENCIES_TEMPLATES[key]
    return DEPENDENCIES_TEMPLATES["default"]

def main():
    root = Path(".")
    py_files = list(root.rglob("*.py"))
    
    print(f"Generating DEPENDENCIES.md for {len(py_files)} Python files...")
    
    created = 0
    for filepath in py_files:
        if "__pycache__" in str(filepath):
            continue
        
        template = get_template(filepath.stem)
        
        deps_path = filepath.parent / f"{filepath.stem}_DEPENDENCIES.md"
        deps_path.write_text(template, encoding='utf-8')
        
        created += 1
        print(f"  Created: {deps_path.name}")
    
    print(f"\n✅ Done! Created {created} DEPENDENCIES.md files.")

if __name__ == "__main__":
    main()
