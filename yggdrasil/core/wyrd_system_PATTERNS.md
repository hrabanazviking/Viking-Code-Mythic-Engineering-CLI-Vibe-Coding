# {filename}_PATTERNS.md

## Design Patterns Used

### 1. State Machine Pattern
**Usage**: Rune states
```python
class RuneState(Enum):
    AVAILABLE = "available"
    ON_COOLDOWN = "cooldown"
    BLESSED = "blessed"
    CURSED = "cursed"

class Rune:
    def transition(self, event: Event) -> RuneState:
        # State transitions based on events
        ...
```

### 2. Observer Pattern
**Usage**: Fate thread resolution
```python
class FateThread:
    def __init__(self):
        self._observers: List[Callable] = []
    
    def resolve(self):
        for observer in self._observers:
            observer(self)
```

### 3. Factory Pattern
**Usage**: Well creation
```python
class WellFactory:
    def create(self, well_type: str) -> Well:
        wells = {
            "mimir": MimirWell,
            "urdr": UrdrWell,
            "hvergelmi": HvergelmiWell
        }
        return wells[well_type]()
```

### 4. Decorator Pattern
**Usage**: Rune effects
```python
def blessed(rune_func):
    def wrapper(*args, **kwargs):
        result = rune_func(*args, **kwargs)
        return f"[Blessed] {result}"
    return wrapper

@blessed
def draw_rune(): ...
```

## Architectural Principles

### Deterministic Randomness
```python
# Same seed = same result (reproducible)
random.seed(character_id + rune_name)
meaning = select_meaning()
random.seed()  # Reset
```

### Temporal Decay
```python
# Effects fade over time
class TemporalEffect:
    def get_strength(self, current_time: datetime) -> float:
        elapsed = current_time - self.created_at
        return max(0.0, 1.0 - (elapsed / self.duration))
```

### Resource Management
```python
# Wells require offerings
class Well:
    def consult(self, offering: Offering) -> Wisdom:
        if not self._accept(offering):
            raise InsufficientOffering()
        return self._reveal_wisdom()
```
