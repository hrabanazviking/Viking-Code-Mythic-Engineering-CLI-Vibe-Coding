# {filename}_EXAMPLES.md

## Basic Usage

### Drawing a Rune
```python
from systems.wyrd_system import WyrdSystem

wyrd = WyrdSystem(data_path="data")

# Draw single rune (respects cooldowns)
rune = wyrd.draw_rune(player_id="volmarr")
print(f"You drew: {rune.name} - {rune.meaning}")

# Check if rune on cooldown
if wyrd.is_rune_on_cooldown(player_id="volmarr", rune="fehu"):
    remaining = wyrd.get_cooldown_remaining(player_id="volmarr")
    print(f"Wait {remaining} minutes before next draw")
```

### Consulting the Wells
```python
# Mimir's Well - Wisdom
mimir = wyrd.get_well("mimir")
wisdom = mimir.speak_wisdom(question="Should I trust this stranger?")
print(wisdom)  # Cryptic but insightful

# Urdar's Well - Fate threads
urdr = wyrd.get_well("urdr")
threads = urdr.weave_fate_threads(
    character_id="volmarr",
    n_threads=3
)
for thread in threads:
    print(f"Fate: {thread.description} (Resolves in {thread.turns} turns)")

# Hvergelmi's Well - Prophecy
hvergelmi = wyrd.get_well("hvergelmi")
prophecy = hvergelmi.speak_prophecy(
    subject="the coming battle"
)
print(prophecy)  # Ominous foreshadowing
```

### Chaos Factor Management
```python
# Get current chaos
chaos = wyrd.get_chaos_factor()
print(f"Current chaos: {chaos:.2f}")

# Increase chaos (player doing risky things)
wyrd.modify_chaos(delta=0.1)

# Decrease chaos (resting, safe actions)
wyrd.modify_chaos(delta=-0.05)

# Check for chaos events
if chaos > 0.7:
    event = wyrd.generate_chaos_event()
    print(f"Event triggered: {event}")
```

## Advanced Patterns

### Fate Thread Resolution
```python
# Create fate thread	hread = wyrd.weave_fate_thread(
    description="Volmarr will face his father's killer",
    trigger_turn=5,
    resolution="combat_or_reconciliation"
)

# Check each turn
if wyrd.should_resolve_thread(thread, current_turn=5):
    resolution = wyrd.resolve_thread(thread)
    print(f"Fate resolves: {resolution}")
```
