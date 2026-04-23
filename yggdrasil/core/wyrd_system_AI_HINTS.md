# wyrd_system_AI_HINTS.md

## ⚠️ CRITICAL RULES

### When Modifying This File
1. **Chaos factor is GLOBAL** - Affects entire game session
2. **Fate threads are IMMUTABLE** - Once set, cannot change
3. **Runes have cooldowns** - Respect RuneCooldownManager
4. **Wells are SINGLETONS** - One per session

### Common Pitfalls
- Forgetting to save chaos factor to session
- Not checking rune cooldowns before draw
- Modifying fate threads after creation
- Memory leaks in well event listeners

### Testing Requirements
- Test chaos factor bounds (0.0-1.0)
- Test rune draw cooldown enforcement
- Test well interactions (Mimir, Urdar, Hvergelmi)
- Test fate thread resolution

### Sacred Constants
- MAX_CHAOS = 1.0
- MIN_CHAOS = 0.0
- DEFAULT_CHAOS = 0.5
- RUNE_COOLDOWN_MINUTES = 60
