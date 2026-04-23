# alfheim_AI_HINTS.md

## ⚠️ CRITICAL RULES

### When Modifying This File
1. **Maintain type hints** - All functions need type annotations
2. **Add docstrings** - Every public method needs documentation
3. **Handle errors gracefully** - Never crash the engine
4. **Log appropriately** - Use logger, not print()

### Common Pitfalls
- Circular imports with core modules
- Not handling None/empty inputs
- Memory leaks in long-running processes
- Breaking backward compatibility

### Testing Requirements
- Unit test all public methods
- Test error conditions
- Test with edge cases (empty, None, max values)
- Verify no regressions in existing tests

### Code Style
- Follow PEP 8
- Use pathlib for paths
- Prefer dataclasses over dicts
- Use enums for constants
