# {filename}_PROMPTS.md

## General Development Prompts

### Add Error Handling
```
Add comprehensive error handling to [function_name]:
1. Identify all possible failure points
2. Add specific exception types
3. Include helpful error messages
4. Add logging at appropriate levels
5. Create fallback behavior
6. Add retry logic for transient errors
```

### Add Type Hints
```
Add type hints to [file_name]:
1. Function parameters and returns
2. Class attributes
3. Use typing imports (Optional, List, Dict)
4. Add mypy-compatible annotations
5. Fix any revealed type errors
6. Maintain Python 3.10+ compatibility
```

### Add Documentation
```
Add documentation to [file_name]:
1. Module docstring (purpose, usage)
2. Class docstrings
3. Method docstrings (Args, Returns, Raises)
4. Inline comments for complex logic
5. README section if needed
6. Example usage code
```

### Refactor for Clarity
```
Refactor [function_name] for better readability:
1. Extract magic numbers to constants
2. Rename unclear variables
3. Break up long functions (max 20 lines)
4. Add early returns
5. Use list/dict comprehensions
6. Maintain exact behavior
```

### Optimize Performance
```
Optimize [function_name]:
1. Profile current performance
2. Identify bottlenecks
3. Implement algorithm improvements
4. Add caching if applicable
5. Reduce memory allocations
6. Verify with benchmarks
```

## Testing Prompts

### Create Unit Test
```
Create unit tests for [class/function]:
1. Test normal operation
2. Test edge cases
3. Test error conditions
4. Use pytest
5. Mock dependencies
6. Aim for >80% coverage
```

### Debug Issue
```
Debug this error: [error_message]
1. Analyze stack trace
2. Identify root cause
3. Create minimal reproduction
4. Implement fix
5. Add regression test
6. Verify fix works
```
