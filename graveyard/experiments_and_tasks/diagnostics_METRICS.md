# {filename}_METRICS.md

## Performance Targets

### Response Times
| Operation | Target | Critical Threshold |
|-----------|--------|-------------------|
| Function Call | < 10ms | > 100ms |
| File I/O | < 50ms | > 500ms |
| Memory Operation | < 1ms | > 10ms |

### Resource Usage
| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Memory per Instance | < 10MB | 50MB | 100MB |
| CPU Usage | < 5% | 20% | 50% |
| Disk I/O | < 1MB/s | 10MB/s | 50MB/s |

## Benchmarking

### Basic Timing
```python
import time

start = time.time()
result = function_to_benchmark()
elapsed = time.time() - start

print(f"Elapsed: {elapsed*1000:.1f}ms")
```

### Memory Profiling
```python
from memory_profiler import profile

@profile
def function_to_profile():
    # Your code here
    pass
```

## Optimization Checklist

- [ ] Profile before optimizing
- [ ] Use appropriate data structures
- [ ] Minimize I/O operations
- [ ] Cache repeated calculations
- [ ] Use lazy loading where possible
