# {filename}_DEBUGGING.md

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
