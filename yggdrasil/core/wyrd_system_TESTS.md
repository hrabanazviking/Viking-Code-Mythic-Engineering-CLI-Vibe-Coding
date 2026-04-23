# {filename}_TESTS.md

## Test Strategy

### Unit Tests
```python
# tests/unit/test_wyrd_system.py
def test_draw_rune_basic():
    wyrd = WyrdSystem("tests/data")
    rune = wyrd.draw_rune("test_player")
    assert rune.name in ["fehu", "uruz", "thurisaz", ...]
    assert rune.meaning is not None

def test_rune_cooldown():
    wyrd = WyrdSystem("tests/data")
    
    # First draw should work
    rune1 = wyrd.draw_rune("test_player")
    assert rune1 is not None
    
    # Second draw immediately should fail or return cooldown
    with pytest.raises(RuneOnCooldownError):
        wyrd.draw_rune("test_player")

def test_chaos_factor_bounds():
    wyrd = WyrdSystem("tests/data")
    
    wyrd.modify_chaos(1.5)  # Try to exceed max
    assert wyrd.get_chaos_factor() == 1.0
    
    wyrd.modify_chaos(-2.0)  # Try to go below min
    assert wyrd.get_chaos_factor() == 0.0
```

### Fate Thread Tests
```python
def test_fate_thread_creation():
    wyrd = WyrdSystem("tests/data")
    thread = wyrd.weave_fate_thread(
        description="Test thread",
        trigger_turn=5
    )
    assert thread.id is not None
    assert thread.trigger_turn == 5

def test_fate_thread_resolution():
    wyrd = WyrdSystem("tests/data")
    thread = wyrd.weave_fate_thread(trigger_turn=5)
    
    # Should not resolve before turn 5
    assert not wyrd.should_resolve_thread(thread, current_turn=3)
    assert not wyrd.should_resolve_thread(thread, current_turn=4)
    
    # Should resolve at turn 5
    assert wyrd.should_resolve_thread(thread, current_turn=5)
```

### Well Tests
```python
def test_mimir_well():
    wyrd = WyrdSystem("tests/data")
    mimir = wyrd.get_well("mimir")
    wisdom = mimir.speak_wisdom("What is my fate?")
    assert len(wisdom) > 0
    assert isinstance(wisdom, str)

def test_well_corruption():
    wyrd = WyrdSystem("tests/data")
    well = wyrd.get_well("mimir")
    
    initial_corruption = well.corruption
    well.corrupt(amount=0.5)
    assert well.corruption == initial_corruption + 0.5
```

## Randomness Testing

### Seed Reproducibility
```python
def test_rune_reproducibility():
    wyrd1 = WyrdSystem("tests/data", seed=42)
    wyrd2 = WyrdSystem("tests/data", seed=42)
    
    rune1 = wyrd1.draw_rune("player")
    rune2 = wyrd2.draw_rune("player")
    
    assert rune1.name == rune2.name
```

### Distribution Testing
```python
def test_rune_distribution():
    wyrd = WyrdSystem("tests/data")
    draws = [wyrd.draw_rune("player") for _ in range(1000)]
    
    # Chi-square test for uniformity
    from scipy import stats
    observed = [draws.count(r) for r in set(draws)]
    chi2, p = stats.chisquare(observed)
    assert p > 0.05  # Uniform distribution
```
