# {filename}_DEBUGGING.md

## Common Errors

### "RuneDrawError: Rune on cooldown"
**CAUSE**: Cooldown not expired
**FIX**: Check cooldown remaining
```python
remaining = wyrd.get_cooldown_remaining(player_id)
print(f"Wait {remaining} minutes")
```

### Fate threads resolve at wrong time
**CAUSE**: Turn count mismatch
**DEBUG**:
```python
print(f"Thread trigger: {thread.trigger_turn}")
print(f"Current turn: {engine.state.turn_count}")
```

### Well returns empty wisdom
**CAUSE**: Insufficient offering or well corrupted
**CHECK**:
```python
well = wyrd.get_well("mimir")
print(f"Corruption: {well.corruption_level}")
print(f"Last offering: {well.last_offering}")
```

### Chaos factor stuck at 0.0 or 1.0
**CHECK**: Bound enforcement
```python
# Should auto-clamp
chaos = max(0.0, min(1.0, raw_chaos))
```

## Debugging Tools

### Force Rune Draw
```python
# Bypass cooldown (debug only)
wyrd._cooldowns.clear()
rune = wyrd.draw_rune(player_id)
```

### List Active Fate Threads
```python
for thread in wyrd.active_threads:
    print(f"{thread.id}: {thread.description}")
    print(f"  Resolves in: {thread.trigger_turn - current_turn} turns")
```

### Well Diagnostics
```python
for well_name in ["mimir", "urdr", "hvergelmi"]:
    well = wyrd.get_well(well_name)
    print(f"{well_name}: corruption={well.corruption}")
```
