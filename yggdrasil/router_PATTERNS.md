# {filename}_PATTERNS.md

## Design Patterns Used

### 1. Dependency Injection
**Usage**: Loose coupling
```python
class Service:
    def __init__(self, dependency: DependencyInterface):
        self.dependency = dependency
```

### 2. Repository Pattern
**Usage**: Data access
```python
class Repository(ABC):
    def get(self, id: str) -> Entity: pass
    def save(self, entity: Entity) -> None: pass
    def delete(self, id: str) -> None: pass
```

### 3. Unit of Work Pattern
**Usage**: Transaction management
```python
class UnitOfWork:
    def __enter__(self):
        self.session = create_session()
        return self
    
    def __exit__(self, exc_type, ...):
        if exc_type:
            self.session.rollback()
        else:
            self.session.commit()
```

## Architectural Principles

### Fail Fast
```python
def process(self, data):
    if not data:
        raise ValueError("Data required")
    # Process...
```

### Defensive Programming
```python
def get_value(self, key: str, default=None):
    return self.data.get(key) or default
```

### Single Responsibility
Each class/function does ONE thing well.
