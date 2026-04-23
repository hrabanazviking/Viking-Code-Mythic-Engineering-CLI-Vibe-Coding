# router_enhanced.py — README_AI.md

## Purpose
Enhanced Yggdrasil AI Router with prompt_builder Integration
=============================================================

This enhanced router integrates the prompt_builder system with Yggdrasil
to provide comprehensive AI call routing with full chart data integration.

Key Features:
1. Uses prompt_builder for all prompt construction
2. Integrates Yggdrasil cognitive context
3. Supports all AI call types with enhanced context
4. Maintains backward compatibility with existing router

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

### `EnhancedYggdrasilAIRouter`
Enhanced AI router with prompt_builder integration.

This router:
1. Uses prompt_builder for all prompt construction
2. Integrates Yggdrasil cognitive context
3. Supports all AI call types with enhanc
**Methods**: __init__, _load_social_protocols, prepare_context, route_call, _build_with_prompt_builder

## Dependencies
```
import logging
import time
import json
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum
```

---
**Last Updated**: February 18, 2026 | v8.0.0
