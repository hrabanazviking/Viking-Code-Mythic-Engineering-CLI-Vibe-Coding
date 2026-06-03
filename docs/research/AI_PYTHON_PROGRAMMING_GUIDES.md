# AI Python Programming Guides Collection

## Overview
This collection contains open-source Python programming guides specifically curated to help AIs learn how to "vibe code" Python - understanding not just syntax, but Pythonic patterns, best practices, and the unique culture of Python programming.

## Core Philosophy Guides

### 1. **The Zen of Python (PEP 20)**
```python
import this

# The Zen of Python, by Tim Peters

# Beautiful is better than ugly.
# Explicit is better than implicit.
# Simple is better than complex.
# Complex is better than complicated.
# Flat is better than nested.
# Sparse is better than dense.
# Readability counts.
# Special cases aren't special enough to break the rules.
# Although practicality beats purity.
# Errors should never pass silently.
# Unless explicitly silenced.
# In the face of ambiguity, refuse the temptation to guess.
# There should be one-- and preferably only one --obvious way to do it.
# Although that way may not be obvious at first unless you're Dutch.
# Now is better than never.
# Although never is often better than *right* now.
# If the implementation is hard to explain, it's a bad idea.
# If the implementation is easy to explain, it may be a good idea.
# Namespaces are one honking great idea -- let's do more of those!
```

### 2. **Pythonic Patterns Guide**

#### **List Comprehensions vs Loops**
```python
# Non-Pythonic
result = []
for i in range(10):
    if i % 2 == 0:
        result.append(i * 2)

# Pythonic
result = [i * 2 for i in range(10) if i % 2 == 0]
```

#### **Dictionary Comprehensions**
```python
# Transform list to dict
names = ['Alice', 'Bob', 'Charlie']
name_lengths = {name: len(name) for name in names}

# Filter dictionary
data = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
filtered = {k: v for k, v in data.items() if v > 2}
```

#### **Context Managers (with statements)**
```python
# Manual file handling
file = open('data.txt', 'r')
try:
    data = file.read()
finally:
    file.close()

# Pythonic file handling
with open('data.txt', 'r') as file:
    data = file.read()
```

### 3. **Type Hinting Guide (PEP 484)**

```python
from typing import List, Dict, Optional, Union, Any, Callable, Tuple

def process_data(
    items: List[str],
    config: Dict[str, Any],
    callback: Optional[Callable[[str], bool]] = None
) -> Tuple[List[str], int]:
    """Process data with type hints."""
    # Function implementation
    return items, len(items)

# Using TypeAlias
from typing import TypeAlias

UserId: TypeAlias = int
UserData: TypeAlias = Dict[str, Union[str, int, List[str]]]

def get_user(user_id: UserId) -> Optional[UserData]:
    """Get user data with custom type aliases."""
    return None
```

## Advanced Python Patterns

### 1. **Decorators**
```python
from functools import wraps
import time
from typing import Callable

def timer(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} took {end_time - start_time:.4f} seconds")
        return result
    return wrapper

def retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator to retry failed function calls."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

@timer
@retry(max_attempts=3)
def fetch_data(url: str) -> str:
    """Fetch data from URL with retry logic and timing."""
    # Implementation
    return "data"
```

### 2. **Context Managers**
```python
from contextlib import contextmanager
import sqlite3
from typing import Generator

@contextmanager
def database_connection(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# Usage
with database_connection('app.db') as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    results = cursor.fetchall()
```

### 3. **Generators and Yield**
```python
def read_large_file(file_path: str) -> Generator[str, None, None]:
    """Read large file line by line using generator."""
    with open(file_path, 'r') as file:
        for line in file:
            yield line.strip()

def fibonacci_sequence(limit: int) -> Generator[int, None, None]:
    """Generate Fibonacci sequence up to limit."""
    a, b = 0, 1
    while a <= limit:
        yield a
        a, b = b, a + b

# Usage
for number in fibonacci_sequence(100):
    print(number)
```

## Error Handling Patterns

### 1. **EAFP vs LBYL**
```python
# LBYL (Look Before You Leap) - Non-Pythonic
if key in my_dict:
    value = my_dict[key]
else:
    value = default_value

# EAFP (Easier to Ask for Forgiveness than Permission) - Pythonic
try:
    value = my_dict[key]
except KeyError:
    value = default_value
```

### 2. **Custom Exceptions**
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

def validate_user_data(data: Dict[str, Any]) -> None:
    """Validate user data with custom exceptions."""
    if 'username' not in data:
        raise RequiredFieldError('username')
    
    if 'email' in data and '@' not in data['email']:
        raise InvalidFormatError('email', 'user@example.com')
```

## Data Structures and Algorithms

### 1. **Collections Module Patterns**
```python
from collections import defaultdict, Counter, deque, namedtuple

# defaultdict for automatic key creation
word_counts = defaultdict(int)
for word in text.split():
    word_counts[word] += 1

# Counter for frequency analysis
word_freq = Counter(text.split())
most_common = word_freq.most_common(10)

# deque for efficient queue operations
queue = deque(maxlen=100)
queue.append('task1')
queue.append('task2')
task = queue.popleft()

# namedtuple for simple data classes
Point = namedtuple('Point', ['x', 'y'])
p = Point(10, 20)
```

### 2. **Dataclasses (Python 3.7+)**
```python
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class User:
    """User data class with automatic methods."""
    username: str
    email: str
    created_at: datetime = field(default_factory=datetime.now)
    roles: List[str] = field(default_factory=list)
    is_active: bool = True
    
    @property
    def display_name(self) -> str:
        """Property for display name."""
        return f"{self.username} ({self.email})"
    
    def add_role(self, role: str) -> None:
        """Add role to user."""
        if role not in self.roles:
            self.roles.append(role)
```

## Async/Await Patterns

### 1. **Async Context Managers**
```python
import aiohttp
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

@asynccontextmanager
async def async_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Async context manager for HTTP sessions."""
    session = aiohttp.ClientSession()
    try:
        yield session
    finally:
        await session.close()

async def fetch_multiple_urls(urls: List[str]) -> List[str]:
    """Fetch multiple URLs concurrently."""
    async with async_session() as session:
        tasks = [session.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [await resp.text() for resp in responses]
```

### 2. **Async Generators**
```python
import asyncio
from typing import AsyncGenerator

async def stream_data(source: str) -> AsyncGenerator[str, None]:
    """Async generator for streaming data."""
    # Simulate streaming
    for i in range(10):
        await asyncio.sleep(0.1)
        yield f"Data chunk {i} from {source}"

async def process_stream():
    """Process async stream."""
    async for chunk in stream_data("database"):
        print(f"Processing: {chunk}")
```

## Testing Patterns

### 1. **Pytest Fixtures**
```python
import pytest
from typing import Generator
import tempfile
import json

@pytest.fixture
def temp_config_file() -> Generator[str, None, None]:
    """Fixture for temporary config file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {"debug": True, "timeout": 30}
        json.dump(config, f)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    import os
    os.unlink(temp_path)

@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """Fixture for sample user data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user", "admin"]
    }

def test_user_creation(temp_config_file: str, sample_user_data: Dict[str, Any]):
    """Test user creation with fixtures."""
    # Test implementation
    assert sample_user_data["username"] == "testuser"
```

### 2. **Mocking Patterns**
```python
from unittest.mock import Mock, patch, MagicMock
import requests

def test_api_call():
    """Test API call with mocking."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    
    with patch('requests.get', return_value=mock_response) as mock_get:
        response = requests.get('https://api.example.com/data')
        
        mock_get.assert_called_once_with('https://api.example.com/data')
        assert response.status_code == 200
        assert response.json()["success"] is True
```

## Performance Optimization

### 1. **Profiling and Optimization**
```python
import cProfile
import pstats
from functools import lru_cache
from typing import List

@lru_cache(maxsize=128)
def fibonacci(n: int) -> int:
    """Memoized Fibonacci with LRU cache."""
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def profile_function(func, *args, **kwargs):
    """Profile a function's performance."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = func(*args, **kwargs)
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
    
    return result
```

### 2. **Memory Efficient Patterns**
```python
import sys
from array import array
from typing import Generator

def memory_efficient_processing(data: List[int]) -> Generator[int, None, None]:
    """Process data efficiently using generators."""
    for item in data:
        # Process item
        yield item * 2

# Using array for memory efficiency
numbers = array('i', [1, 2, 3, 4, 5])  # 'i' for signed integers
print(f"Memory usage: {sys.getsizeof(numbers)} bytes")
```

## Best Practices Summary

### 1. **Code Organization**
```
project/
├── src/
│   ├── __init__.py
│   ├── module1/
│   │   ├── __init__.py
│   │   └── core.py
│   └── module2/
│       ├── __init__.py
│       └── utils.py
├── tests/
│   ├── __init__.py
│   ├── test_module1.py
│   └── test_module2.py
├── docs/
├── requirements.txt
└── setup.py
```

### 2. **Import Organization**
```python
# Standard library imports
import os
import sys
from typing import Dict, List, Optional

# Third-party imports
import requests
from rich.console import Console

# Local application imports
from .models import User
from .utils import helper_function
```

### 3. **Documentation Standards**
```python
def calculate_statistics(data: List[float], method: str = "mean") -> float:
    """
    Calculate statistical measures for a dataset.
    
    Args:
        data: List of numerical values to analyze
        method: Statistical method to apply. Options: 
                "mean", "median", "mode", "std"
    
    Returns:
        Calculated statistical value
    
    Raises:
        ValueError: If method is not supported
        StatisticsError: If data is empty
    
    Examples:
        >>> calculate_statistics([1, 2, 3, 4, 5], "mean")
        3.0
        >>> calculate_statistics([1, 2, 2, 3, 4], "mode")
        2
    """
    if not data:
        raise StatisticsError("Cannot calculate statistics on empty data")
    
    # Implementation
    return result
```

## Resources for Further Learning

### Open Source Guides:
1. **The Hitchhiker's Guide to Python** - https://docs.python-guide.org/
2. **Real Python Tutorials** - https://realpython.com/
3. **Python Official Documentation** - https://docs.python.org/3/
4. **Google Python Style Guide** - https://google.github.io/styleguide/pyguide.html
5. **PEP 8 - Style Guide** - https://www.python.org/dev/peps/pep-0008/

### Advanced Topics:
1. **Design Patterns in Python** - https://refactoring.guru/design-patterns/python
2. **Python Concurrency** - https://realpython.com/python-concurrency/
3. **Metaprogramming** - https://realpython.com/python-metaclasses/
4. **Type Hints Complete Guide** - https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html
5. **Async Python** - https://realpython.com/async-io-python/

### Community Resources:
1. **Python Discord** - https://discord.gg/python
2. **r/learnpython** - https://www.reddit.com/r/learnpython/
3. **Stack Overflow Python Tag** - https://stackoverflow.com/questions/tagged/python
4. **PyCon Talks** - https://www.youtube.com/c/PyConUS
5. **Python Weekly Newsletter** - https://www.pythonweekly.com/

## AI-Specific Python Patterns

### 1. **AI Code Generation Patterns**
```python
def generate_ai_response(prompt: str, context: Dict[str, Any]) -> str:
    """
    Generate AI response with proper context handling.
    
    Patterns for AI code generation:
    1. Always include type hints
    2. Use descriptive variable names
    3. Include comprehensive docstrings
    4. Handle edge cases explicitly
    5. Follow PEP 8 formatting
    """
    # AI-specific implementation patterns
    return "Generated response"

def validate_ai_generated_code(code: str) -> bool:
    """
    Validate AI-generated Python code.
    
    Checks:
    - Syntax validity
    - Import statements
    - Function definitions
    - Error handling
    - Documentation
    """
    try:
        compile(code, '<string>', 'exec')
        return True
    except SyntaxError:
        return False
```

This guide provides AIs with the essential patterns, idioms, and best practices needed to write Python code that not only works but embodies the Pythonic philosophy.