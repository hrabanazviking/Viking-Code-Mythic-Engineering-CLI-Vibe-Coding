#!/usr/bin/env python3
"""Generate DEBUGGING.md for all Python files - Troubleshooting guide."""

from pathlib import Path

DEBUGGING_TEMPLATES = {
    "engine": """# {filename}_DEBUGGING.md

## Common Errors

### "UnboundLocalError: local variable 'combined' referenced before assignment"
**CAUSE**: Variable defined after early return
**FIX**: Move `combined = []` to top of function
**SEE**: BUG-005 fix (v8.0.0)
```python
# WRONG
def method():
    if condition:
        return
    combined = []  # Unbound if early return!

# RIGHT
def method():
    combined = []  # Define first
    if condition:
        return combined
```

### AI returns empty or None response
**CHECK**:
1. API key valid? Check `config.yaml`
2. Model name correct? (e.g., "anthropic/claude-3.5-sonnet")
3. Rate limit hit? Check logs for 429 errors
4. Internet connection working?

**DEBUG**:
```python
# Enable debug logging
engine.initialize_ai(api_key, debug=True)
# Check logs/game.log
```

### Session won't save/load
**CHECK**:
1. Disk space available?
2. File permissions correct?
3. YAML syntax valid? (check colons, indentation)
4. Character ID exists in data/characters/

**DEBUG**:
```python
import yaml
with open("session.yaml") as f:
    yaml.safe_load(f)  # Will throw if invalid
```

### Memory usage growing unbounded
**CAUSE**: Caches not cleared
**FIX**: 
```python
# Clear caches periodically
engine.npc_cache.clear()
engine.memory_manager.trim()
```

### NPCs not appearing at location
**CHECK**:
1. Location ID correct?
2. NPC pool populated? `_populate_location_npcs()`
3. NPCs not filtered out? (dead, moved away)

## Debugging Tools

### Verbose Mode
```python
python main.py --debug
```

### Session Inspection
```python
# Print full state
import json
print(json.dumps(engine.state.__dict__, indent=2))
```

### Performance Profiling
```python
import cProfile
cProfile.run('engine.process_action("test")')
```

## Log Analysis

### Key Log Locations
- `logs/game.log` - Main game events
- `logs/ai.log` - AI requests/responses
- `logs/error.log` - Exceptions

### Common Log Patterns
```
# Normal flow
[INFO] Session loaded: volmarr_saga
[INFO] Processing action: 'go north'
[INFO] AI response received (1.2s)

# Warning signs
[WARN] Chaos factor exceeded 0.9
[WARN] NPC cache miss rate high
[ERROR] AI request failed: 429 Too Many Requests
```
""",
    "prompt_builder": """# {filename}_DEBUGGING.md

## Common Errors

### "TokenLimitError: Prompt exceeds 8000 tokens"
**CAUSE**: RAG context too long
**FIX**: Reduce max_tokens parameter
```python
rag_context = pb.get_rag_context(
    action="pray",
    context=ctx,
    max_tokens=800  # Was 1200
)
```

### Prompt missing layers
**CAUSE**: Layer order modified
**FIX**: Check `LAYER_ORDER` constant, restore original order

### Yggdrasil context not appearing
**CAUSE**: `include_yggdrasil=False` or Yggdrasil not initialized
**FIX**:
```python
# Check Yggdrasil available
from yggdrasil import HAS_YGGDRASIL
print(HAS_YGGDRASIL)

# Enable in prompt
pb.build_narrator_prompt(..., include_yggdrasil=True)
```

### RAG returns irrelevant results
**CHECK**:
1. BM25 index built? (first run)
2. Charts loaded? Check `data/charts/`
3. Query too short? (min 3 chars)

**REBUILD INDEX**:
```python
pb.rag_system.rebuild_index()
```

## Debugging Tools

### Inspect Full Prompt
```python
prompt = pb.build_narrator_prompt(ctx, "test")
print(prompt)
print(f"Length: {len(prompt)} chars")
print(f"Layers: {prompt.count('===') // 2}")
```

### Layer-by-Layer Debug
```python
# Build each layer separately
layers = {
    "personality": pb.build_base_personality(),
    "cultural": pb.build_cultural_filter(),
    "scene": pb.build_scene_context(ctx),
    # ... etc
}
for name, content in layers.items():
    print(f"{name}: {len(content)} chars")
```

### Token Count
```python
import tiktoken
enc = tiktoken.encoding_for_model("gpt-4")
tokens = enc.encode(prompt)
print(f"Tokens: {len(tokens)}")
```
""",
    "wyrd_system": """# {filename}_DEBUGGING.md

## Common Errors

### "RuneDrawError: Rune on cooldown"
**CAUSE**: Cooldown not expired
**FIX**: Check cooldown remaining
```python
remaining = wyrd.get_cooldown_remaining(player_id)
print(f"Wait {remaining} minutes")
```

### Fate threads resolve at wrong time
**CAUSE**: Turn count mismatch
**DEBUG**:
```python
print(f"Thread trigger: {thread.trigger_turn}")
print(f"Current turn: {engine.state.turn_count}")
```

### Well returns empty wisdom
**CAUSE**: Insufficient offering or well corrupted
**CHECK**:
```python
well = wyrd.get_well("mimir")
print(f"Corruption: {well.corruption_level}")
print(f"Last offering: {well.last_offering}")
```

### Chaos factor stuck at 0.0 or 1.0
**CHECK**: Bound enforcement
```python
# Should auto-clamp
chaos = max(0.0, min(1.0, raw_chaos))
```

## Debugging Tools

### Force Rune Draw
```python
# Bypass cooldown (debug only)
wyrd._cooldowns.clear()
rune = wyrd.draw_rune(player_id)
```

### List Active Fate Threads
```python
for thread in wyrd.active_threads:
    print(f"{thread.id}: {thread.description}")
    print(f"  Resolves in: {thread.trigger_turn - current_turn} turns")
```

### Well Diagnostics
```python
for well_name in ["mimir", "urdr", "hvergelmi"]:
    well = wyrd.get_well(well_name)
    print(f"{well_name}: corruption={well.corruption}")
```
""",
    "default": """# {filename}_DEBUGGING.md

## Common Errors

### ImportError: No module named 'X'
**FIX**: 
```bash
pip install -r requirements.txt
```

### FileNotFoundError
**CHECK**:
1. Path correct? Use `Path(__file__).parent`
2. File exists? `path.exists()`
3. Permissions? `chmod 644 file`

### TypeError: 'NoneType' object is not callable
**CAUSE**: Function/variable is None
**FIX**: Add guard clause
```python
if func is None:
    raise ValueError("Function not initialized")
result = func()
```

### Performance Issues
**PROFILE**:
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
# ... code ...
profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

## Debugging Techniques

### Add Logging
```python
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Variable x = {x}")
```

### Interactive Debugger
```python
import pdb; pdb.set_trace()
# Commands: n (next), s (step), c (continue), p (print)
```

### Unit Test Isolation
```python
# Test specific function
python -m pytest test_file.py::test_function -v
```
"""
}

def get_template(filename: str) -> str:
    filename_lower = filename.lower()
    for key in DEBUGGING_TEMPLATES:
        if key in filename_lower:
            return DEBUGGING_TEMPLATES[key]
    return DEBUGGING_TEMPLATES["default"]

def main():
    root = Path(".")
    py_files = list(root.rglob("*.py"))
    
    print(f"Generating DEBUGGING.md for {len(py_files)} Python files...")
    
    created = 0
    for filepath in py_files:
        if "__pycache__" in str(filepath):
            continue
        
        template = get_template(filepath.stem)
        
        debugging_path = filepath.parent / f"{filepath.stem}_DEBUGGING.md"
        debugging_path.write_text(template, encoding='utf-8')
        
        created += 1
        print(f"  Created: {debugging_path.name}")
    
    print(f"\n✅ Done! Created {created} DEBUGGING.md files.")

if __name__ == "__main__":
    main()
