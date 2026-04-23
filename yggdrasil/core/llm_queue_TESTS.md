# llm_queue_TESTS.md

## Test Strategy

### Unit Tests
```python
# tests/unit/test_llm_queue.py
import pytest
from yggdrasil.core.llm_queue import LlmQueue

@pytest.fixture
def instance():
    return LlmQueue(data_path="tests/data")

def test_basic_operation(instance):
    result = instance.process("test_input")
    assert result is not None

def test_error_handling(instance):
    with pytest.raises(ValueError):
        instance.process(None)
```

### Integration Tests
```python
def test_with_real_data(instance):
    result = instance.process("realistic_input")
    assert result.status == "success"
```

## Test Coverage Checklist

- [ ] All public methods tested
- [ ] Edge cases covered (empty, None, max values)
- [ ] Error conditions tested
- [ ] Type hints verified with mypy
- [ ] Fixtures created for test data

## Running Tests

```bash
# All tests
python -m pytest tests/unit/test_llm_queue.py -v

# With coverage
python -m pytest tests/unit/test_llm_queue.py --cov=yggdrasil.core.llm_queue

# Specific test
python -m pytest tests/unit/test_llm_queue.py::test_basic_operation -v
```
