# Pythonic Patterns for AI Programming

## Understanding the Python "Vibe"

### What Makes Code "Pythonic"?
Pythonic code isn't just about syntax correctness - it's about embracing Python's philosophy:

1. **Readability over cleverness** - Code should be easy to understand at a glance
2. **Simplicity over complexity** - The simplest solution is usually the best
3. **Explicit over implicit** - Make intentions clear
4. **Practicality over purity** - Working code beats perfect theory

## Core Pythonic Patterns for AI

### 1. **The EAFP Principle (Easier to Ask Forgiveness than Permission)**

```python
# Non-Pythonic (LBYL - Look Before You Leap)
if 'key' in my_dict:
    value = my_dict['key']
else:
    value = None

# Pythonic (EAFP)
try:
    value = my_dict['key']
except KeyError:
    value = None
```

**Why this matters for AI:**
- Teaches AIs to handle errors gracefully
- Encourages robust code that doesn't break on edge cases
- Models real-world Python development patterns

### 2. **Comprehensions - The Pythonic Way to Transform Data**

```python
# List Comprehensions
numbers = [1, 2, 3, 4, 5]
squared = [x**2 for x in numbers]  # [1, 4, 9, 16, 25]
even_squares = [x**2 for x in numbers if x % 2 == 0]  # [4, 16]

# Dictionary Comprehensions
names = ['Alice', 'Bob', 'Charlie']
name_lengths = {name: len(name) for name in names}
# {'Alice': 5, 'Bob': 3, 'Charlie': 7}

# Set Comprehensions
words = ['hello', 'world', 'hello', 'python']
unique_lengths = {len(word) for word in words}  # {5, 6}
```

**AI Learning Pattern:**
- Show transformations as data pipelines
- Emphasize readability over performance micro-optimizations
- Demonstrate how Python expresses intent clearly

### 3. **Context Managers - Resource Management Done Right**

```python
# Basic context manager pattern
with open('data.txt', 'r') as file:
    content = file.read()
# File automatically closed

# Custom context manager
from contextlib import contextmanager
from typing import Generator

@contextmanager
def timer() -> Generator[None, None, None]:
    """Context manager for timing code blocks."""
    import time
    start = time.time()
    try:
        yield
    finally:
        end = time.time()
        print(f"Execution time: {end - start:.2f} seconds")

# Usage
with timer():
    # Code to time
    result = sum(range(1000000))
```

**Why AIs Need This:**
- Teaches proper resource management
- Shows how to create reusable patterns
- Demonstrates Python's "batteries included" philosophy

### 4. **Decorators - Enhancing Functions Pythonically**

```python
from functools import wraps
from typing import Callable, Any
import time

def log_execution(func: Callable) -> Callable:
    """Decorator to log function execution."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print(f"Executing {func.__name__}...")
        result = func(*args, **kwargs)
        print(f"{func.__name__} completed")
        return result
    return wrapper

def retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator factory for retry logic."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    print(f"Attempt {attempt + 1} failed: {e}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

# Usage
@log_execution
@retry(max_attempts=3)
def fetch_data(url: str) -> str:
    """Fetch data with logging and retry logic."""
    # Implementation
    return "data"
```

**AI Pattern Recognition:**
- Shows how to add functionality without modifying core logic
- Teaches function composition
- Demonstrates Python's flexibility

### 5. **Generators - Lazy Evaluation Patterns**

```python
from typing import Generator, Iterator

def read_large_file(file_path: str) -> Generator[str, None, None]:
    """Read large file line by line (memory efficient)."""
    with open(file_path, 'r') as file:
        for line in file:
            yield line.strip()

def fibonacci() -> Generator[int, None, None]:
    """Generate Fibonacci sequence indefinitely."""
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

# Usage
for line in read_large_file('huge_data.txt'):
    process(line)  # Processes one line at a time

# Get first 10 Fibonacci numbers
fib = fibonacci()
first_10 = [next(fib) for _ in range(10)]
```

**Why This Matters for AI:**
- Teaches memory-efficient patterns
- Shows how to handle infinite sequences
- Demonstrates Python's iterator protocol

## Pythonic Data Structures

### 1. **Using Collections Module Effectively**

```python
from collections import defaultdict, Counter, deque, namedtuple
from typing import List, Dict

# defaultdict - automatic dictionary creation
word_counts: Dict[str, int] = defaultdict(int)
for word in text.split():
    word_counts[word] += 1  # No KeyError!

# Counter - frequency analysis
freq = Counter(text.split())
top_words = freq.most_common(10)

# deque - efficient queue operations
queue = deque(maxlen=100)  # Fixed-size queue
queue.append('task1')
queue.append('task2')
oldest = queue.popleft()

# namedtuple - lightweight data classes
Point = namedtuple('Point', ['x', 'y'])
p = Point(10, 20)
print(p.x, p.y)  # 10 20
```

### 2. **Dataclasses (Python 3.7+)**

```python
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class User:
    """Pythonic data class for user information."""
    username: str
    email: str
    created_at: datetime = field(default_factory=datetime.now)
    roles: List[str] = field(default_factory=list)
    is_active: bool = True
    
    @property
    def display_name(self) -> str:
        """Computed property."""
        return f"{self.username} ({self.email})"
    
    def add_role(self, role: str) -> None:
        """Method to add role."""
        if role not in self.roles:
            self.roles.append(role)

# Usage
user = User("alice", "alice@example.com")
print(user)  # Auto-generated __repr__
print(user.display_name)  # Property access
```

## Pythonic Error Handling

### 1. **Custom Exceptions with Context**

```python
class ValidationError(Exception):
    """Base exception for validation errors."""
    pass

class RequiredFieldError(ValidationError):
    """Exception for missing required fields."""
    def __init__(self, field_name: str):
        super().__init__(f"Required field '{field_name}' is missing")
        self.field_name = field_name

class InvalidFormatError(ValidationError):
    """Exception for invalid data format."""
    def __init__(self, field_name: str, expected_format: str):
        super().__init__(f"Field '{field_name}' must be in format: {expected_format}")
        self.field_name = field_name
        self.expected_format = expected_format

def validate_user(data: Dict[str, Any]) -> None:
    """Validate user data with informative exceptions."""
    if 'username' not in data:
        raise RequiredFieldError('username')
    
    if 'email' in data and '@' not in data['email']:
        raise InvalidFormatError('email', 'user@example.com')
```

### 2. **Context-Specific Error Handling**

```python
def process_data_safely(data: List[Any]) -> List[Any]:
    """Process data with comprehensive error handling."""
    results = []
    
    for item in data:
        try:
            # Attempt to process item
            result = complex_processing(item)
            results.append(result)
            
        except ValueError as e:
            # Handle specific error type
            print(f"Value error processing {item}: {e}")
            results.append(None)
            
        except (TypeError, AttributeError) as e:
            # Handle multiple error types
            print(f"Type/attribute error: {e}")
            results.append(None)
            
        except Exception as e:
            # Catch-all for unexpected errors
            print(f"Unexpected error: {e}")
            raise  # Re-raise for critical failures
            
    return results
```

## Pythonic Testing Patterns

### 1. **Pytest Fixtures and Parametrization**

```python
import pytest
from typing import Generator, List
import tempfile
import json

@pytest.fixture
def sample_data() -> List[Dict[str, Any]]:
    """Fixture providing sample test data."""
    return [
        {"id": 1, "name": "Alice", "score": 95},
        {"id": 2, "name": "Bob", "score": 87},
        {"id": 3, "name": "Charlie", "score": 92}
    ]

@pytest.fixture
def temp_config() -> Generator[str, None, None]:
    """Fixture for temporary configuration file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {"debug": True, "timeout": 30}
        json.dump(config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    import os
    os.unlink(temp_path)

@pytest.mark.parametrize("input_data,expected", [
    ([1, 2, 3], 6),
    ([], 0),
    ([10], 10),
    ([-1, 1], 0),
])
def test_sum_function(input_data: List[int], expected: int):
    """Parameterized test for sum function."""
    assert sum(input_data) == expected
```

### 2. **Mocking and Patching**

```python
from unittest.mock import Mock, patch, MagicMock
import requests

def test_api_integration():
    """Test API integration with mocking."""
    # Create mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True, "data": [1, 2, 3]}
    
    # Patch the requests.get function
    with patch('requests.get', return_value=mock_response) as mock_get:
        # Call the function under test
        result = fetch_data_from_api('https://api.example.com/data')
        
        # Verify the mock was called correctly
        mock_get.assert_called_once_with(
            'https://api.example.com/data',
            timeout=30
        )
        
        # Verify the result
        assert result == [1, 2, 3]
```

## Pythonic Performance Patterns

### 1. **Using Built-in Functions Effectively**

```python
# Use built-ins instead of manual loops
numbers = [1, 2, 3, 4, 5]

# Instead of:
total = 0
for n in numbers:
    total += n

# Use:
total = sum(numbers)

# Instead of:
max_val = numbers[0]
for n in numbers:
    if n > max_val:
        max_val = n

# Use:
max_val = max(numbers)

# Instead of:
filtered = []
for n in numbers:
    if n % 2 == 0:
        filtered.append(n)

# Use:
filtered = list(filter(lambda x: x % 2 == 0, numbers))
# Or better:
filtered = [n for n in numbers if n % 2 == 0]
```

### 2. **Efficient String Building**

```python
# Inefficient (creates many intermediate strings)
result = ""
for word in words:
    result += word + " "

# Efficient (uses join)
result = " ".join(words)

# For complex formatting
formatted = " ".join(f"{word}:{len(word)}" for word in words)
```

## Pythonic Code Organization

### 1. **Module Structure**

```python
# mymodule/__init__.py
"""Main module package."""

from .core import CoreClass, main_function
from .utils import helper_function, AnotherClass
from .exceptions import CustomError

__version__ = "1.0.0"
__all__ = [
    'CoreClass',
    'main_function',
    'helper_function',
    'AnotherClass',
    'CustomError'
]

# mymodule/core.py
"""Core functionality module."""

import logging
from typing import List, Optional
from .exceptions import CustomError

logger = logging.getLogger(__name__)

def main_function(data: List[str]) -> Optional[str]:
    """Main processing function."""
    try:
        # Implementation
        return processed_data
    except Exception as e:
        logger.error(f"Error in main_function: {e}")
        raise CustomError(f"Processing failed: {e}") from e
```

### 2. **Import Organization**

```python
# Standard library imports (alphabetical)
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Third-party imports (alphabetical)
import requests
from rich.console import Console
from sqlalchemy import create_engine

# Local application imports (relative)
from .models import User, Session
from .utils import helper_function, validate_input
from .exceptions import ValidationError
```

## Pythonic Documentation

### 1. **Comprehensive Docstrings**

```python
def calculate_statistics(
    data: List[float], 
    method: str = "mean",
    weights: Optional[List[float]] = None
) -> float:
    """
    Calculate statistical measures for numerical data.
    
    This function supports multiple statistical methods including
    mean, median, mode, and weighted averages. It handles edge
    cases like empty data lists and provides informative error
    messages.
    
    Args:
        data: List of numerical values to analyze. Must contain
              at least one element for most methods.
        method: Statistical method to apply. Supported values:
                - "mean": Arithmetic mean
                - "median": Median value
                - "mode": Most frequent value
                - "weighted_mean": Weighted average (requires weights)
        weights: Optional list of weights for weighted mean.
                 Must be same length as data if provided.
    
    Returns:
        Calculated statistical value as float.
    
    Raises:
        ValueError: If method is not supported or data is invalid.
        StatisticsError: If data is empty for methods that require data.
    
    Examples:
        >>> calculate_statistics([1, 2, 3, 4, 5], "mean")
        3.0
        >>> calculate_statistics([1, 2, 2, 3, 4], "mode")
        2
        >>> calculate_statistics([1, 2, 3], "weighted_mean", [0.1, 0.3, 0.6])
        2.5
    
    Notes:
        - For large datasets, consider using numpy for better performance.
        - The mode implementation returns the first mode if multiple exist.
    """
    # Implementation
    return result
```

## Teaching AIs Pythonic Thinking

### 1. **Pattern Recognition Exercises**

```python
# Exercise: Convert non-Pythonic code to Pythonic

# Non-Pythonic version
def process_items(items):
    result = []
    for i in range(len(items)):
        if items[i] % 2 == 0:
            result.append(items[i] * 2)
    return result

# Pythonic version
def process_items_pythonic(items):
    return [item * 2 for item in items if item % 2 == 0]

# Exercise: Error handling patterns

def get_value_safe(dictionary, key, default=None):
    """
    Get value from dictionary with safe fallback.
    Implement using EAFP principle.
    """
    try:
        return dictionary[key]
    except KeyError:
        return default
```

### 2. **Code Review Patterns for AI**

When reviewing AI-generated code, look for:

1. **Readability**: Can a human understand this quickly?
2. **Simplicity**: Is this the simplest solution?
3. **Pythonic constructs**: Are comprehensions, generators, context managers used appropriately?
4. **Error handling**: Are exceptions handled gracefully?
5. **Type hints**: Are types clearly specified?
6. **Documentation**: Are docstrings comprehensive?

## Conclusion: The Pythonic Mindset

Teaching AIs to code Pythonically means teaching them to:

1. **Value readability** over cleverness
2. **Embrace simplicity** in solutions
3. **Handle errors gracefully** with EAFP
4. **Use Python's built-in features** effectively
5. **Write self-documenting code** with clear naming and structure
6. **Think in patterns** that are idiomatic to Python

By internalizing these patterns, AIs can generate code that not only works but feels "right" to Python developers - code that is maintainable, readable, and truly Pythonic.