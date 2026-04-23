# router.py — README_AI.md

## Purpose
Yggdrasil AI Router - All AI Calls Must Flow Through Here
==========================================================

This is the ONLY entry point for AI calls in the Norse Saga Engine.
No AI system is to bypass Yggdrasil or the Ravens.

Every AI call:
1. Receives full character data for any characters involved
2. Receives current game state and chaos factor
3. Is processed through the appropriate Yggdrasil realm
4. Has results logged comprehensively
5. Updates the Wyrd system

The Router ensure

## Technical Architecture
- **Classes**: 4 main classes
  - `AICallType`: Types of AI calls that can be routed.
  - `CharacterDataFeed`: Complete character data prepared for AI consumption.

This ensures AI ALWAYS has full character info
  - `AICallContext`: Complete context for an AI call.

Everything the AI needs to know is packaged here.
- **Functions**: 1 module-level functions

## Key Components
### `AICallType`
Types of AI calls that can be routed.

### `CharacterDataFeed`
Complete character data prepared for AI consumption.

This ensures AI ALWAYS has full character information.
**Methods**: to_ai_text, from_character_dict

### `AICallContext`
Complete context for an AI call.

Everything the AI needs to know is packaged here.
**Methods**: to_prompt_context

### `YggdrasilAIRouter`
The unified AI router. ALL AI calls MUST go through here.

This ensures:
- Full character data is always sent
- Viking social protocols are applied
- Chaos factor influences results
- Results are logg
**Methods**: __init__, _load_social_protocols, prepare_character_data, prepare_context, route_call

## Dependencies
```
import logging
import time
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum
```

---
**Last Updated**: February 18, 2026 | v8.0.0
