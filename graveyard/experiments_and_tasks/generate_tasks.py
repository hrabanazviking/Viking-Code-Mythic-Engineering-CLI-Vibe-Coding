#!/usr/bin/env python3
"""Generate TASKS.md for all Python files - Actionable work items and backlog."""

from pathlib import Path
from datetime import datetime

# Tasks templates based on file patterns
TASKS_TEMPLATES = {
    "engine": """# {filename}_TASKS.md

## 🚀 Current Sprint (Active)
- [ ] Optimize NPC loading with caching (residents cache, visitors refresh)
- [ ] Add Yggdrasil realm transition effects (visual + narrative)
- [ ] Implement save game compression (YAML too large)
- [ ] Add multiplayer session support (lobby system)
- [ ] Fix memory leak in process_action() (unbounded growth)

## 📋 Backlog (Prioritized)
### High Priority
- [ ] Add session replay functionality (record/playback)
- [ ] Implement auto-save every 5 minutes
- [ ] Add export to PDF (session log)
- [ ] Optimize RAG search with vector DB (currently BM25)

### Medium Priority
- [ ] Add achievement system (saga milestones)
- [ ] Implement difficulty settings (chaos scaling)
- [ ] Add tutorial mode for new players
- [ ] Create admin dashboard (session monitoring)

### Low Priority
- [ ] Add voice input support (STT)
- [ ] Implement VR mode (3D locations)
- [ ] Add multiplayer PvP arena
- [ ] Create mobile companion app

## 🐛 Known Issues
- [ ] Session save fails with >100 NPCs (timeout)
- [ ] Memory usage grows 10MB per hour (leak)
- [ ] AI response time >5s on slow connections
- [ ] Location transitions sometimes lose NPC context

## ✅ Recently Completed
- [x] FIXED: BUG-005 closure issue (v8.0.0)
- [x] ADDED: Yggdrasil router integration (v8.0.0)
- [x] ADDED: Myth Engine v4.2.0 (v8.0.0)
- [x] FIXED: BUG-003 missing well methods (v8.0.0)

---
**Last Updated**: {date}
**Sprint**: v4.7.0 Preparation
""",
    "prompt_builder": """# {filename}_TASKS.md

## 🚀 Current Sprint (Active)
- [ ] Add vector DB for RAG (Pinecone/Weaviate)
- [ ] Implement prompt versioning (A/B testing)
- [ ] Add prompt compression (reduce token usage)
- [ ] Create prompt performance metrics (latency tracking)

## 📋 Backlog (Prioritized)
### High Priority
- [ ] Add multi-language support (i18n)
- [ ] Implement dynamic layer ordering (configurable)
- [ ] Add prompt caching (Redis)
- [ ] Create prompt editor UI (web interface)

### Medium Priority
- [ ] Add semantic search for RAG (embeddings)
- [ ] Implement prompt templates (user-defined)
- [ ] Add prompt diff viewer (version comparison)
- [ ] Create prompt testing framework

### Low Priority
- [ ] Add GPT-4 vision support (image inputs)
- [ ] Implement prompt chaining (multi-step)
- [ ] Add voice prompt input
- [ ] Create prompt marketplace

## 🐛 Known Issues
- [ ] RAG context sometimes exceeds token limit
- [ ] Prompt building slow with >50 charts
- [ ] Yggdrasil context not always relevant
- [ ] Memory leaks in RAG cache

## ✅ Recently Completed
- [x] ADDED: Yggdrasil integration (v8.0.0)
- [x] ADDED: connect_yggdrasil() method (v8.0.0)
- [x] FIXED: RAG truncation bug (v8.0.0)
- [x] ADDED: 18-layer system (v4.5.0)

---
**Last Updated**: {date}
**Sprint**: v4.7.0 Preparation
""",
    "wyrd_system": """# {filename}_TASKS.md

## 🚀 Current Sprint (Active)
- [ ] Add rune interpretation AI (meanings vary by context)
- [ ] Implement fate thread visualization (web UI)
- [ ] Add well blessing/curse mechanics
- [ ] Create rune casting mini-game

## 📋 Backlog (Prioritized)
### High Priority
- [ ] Add more rune layouts (past/present/future)
- [ ] Implement fate thread branching (multiple outcomes)
- [ ] Add well corruption mechanics (overuse penalties)
- [ ] Create wyrd event calendar (scheduled events)

### Medium Priority
- [ ] Add rune combinations (pairs, triplets)
- [ ] Implement prophecy fulfillment tracking
- [ ] Add well maintenance (offerings required)
- [ ] Create fate thread sharing (between players)

### Low Priority
- [ ] Add AR rune casting (phone camera)
- [ ] Implement rune crafting (create custom)
- [ ] Add well avatar NPCs (visual representation)
- [ ] Create wyrd music/sound effects

## 🐛 Known Issues
- [ ] Rune cooldowns not persisting across sessions
- [ ] Fate threads sometimes resolve early
- [ ] Well responses too similar (need more variety)
- [ ] Chaos factor calculation opaque to players

## ✅ Recently Completed
- [x] FIXED: BUG-003 missing methods (v8.0.0)
- [x] ADDED: speak_wisdom() to Mimir (v8.0.0)
- [x] ADDED: speak_prophecy() to Hvergelmi (v8.0.0)
- [x] ADDED: RuneCooldownManager (v4.5.0)

---
**Last Updated**: {date}
**Sprint**: v4.7.0 Preparation
""",
    "character_generator": """# {filename}_TASKS.md

## 🚀 Current Sprint (Active)
- [ ] Add portrait generation (Stable Diffusion)
- [ ] Implement backstory consistency checker
- [ ] Add character relationship mapping
- [ ] Create character export to D&D Beyond

## 📋 Backlog (Prioritized)
### High Priority
- [ ] Add more cultures (Finnish, Baltic, etc.)
- [ ] Implement character aging (over time)
- [ ] Add character family trees
- [ ] Create character voice synthesis

### Medium Priority
- [ ] Add character animation (portrait emotions)
- [ ] Implement character quest hooks
- [ ] Add character reputation system
- [ ] Create character diary/journal

### Low Priority
- [ ] Add 3D character models
- [ ] Implement character DNA (inheritance)
- [ ] Add character social media (in-game)
- [ ] Create character merchandise (real world)

## 🐛 Known Issues
- [ ] Generated names sometimes duplicate
- [ ] Stats not always optimized for class
- [ ] Cultural accuracy needs review
- [ ] Portrait matching hit-or-miss

## ✅ Recently Completed
- [x] ADDED: Advanced character generator (v4.5.0)
- [x] ADDED: Personality systems (v4.4.0)
- [x] ADDED: Batch generation (v4.3.0)
- [x] FIXED: Stat distribution bug (v4.2.0)

---
**Last Updated**: {date}
**Sprint**: v4.7.0 Preparation
""",
    "default": """# {filename}_TASKS.md

## 🚀 Current Sprint (Active)
- [ ] Add comprehensive error handling
- [ ] Implement unit tests (coverage >80%)
- [ ] Add type hints to all functions
- [ ] Create documentation examples

## 📋 Backlog (Prioritized)
### High Priority
- [ ] Refactor for performance optimization
- [ ] Add logging throughout
- [ ] Implement configuration validation
- [ ] Create integration tests

### Medium Priority
- [ ] Add async support where applicable
- [ ] Implement caching layer
- [ ] Add metrics/monitoring
- [ ] Create CLI interface

### Low Priority
- [ ] Add web API wrapper
- [ ] Implement plugin system
- [ ] Add GUI interface
- [ ] Create Docker container

## 🐛 Known Issues
- [ ] Error messages not user-friendly
- [ ] Performance degrades with large inputs
- [ ] Missing input validation
- [ ] No retry logic on failures

## ✅ Recently Completed
- [x] Initial implementation
- [x] Basic documentation
- [x] Core functionality

---
**Last Updated**: {date}
**Sprint**: v4.7.0 Preparation
"""
}

def get_template(filename: str) -> str:
    """Select appropriate template based on filename."""
    filename_lower = filename.lower()
    for key in TASKS_TEMPLATES:
        if key in filename_lower:
            return TASKS_TEMPLATES[key]
    return TASKS_TEMPLATES["default"]

def main():
    root = Path(".")
    py_files = list(root.rglob("*.py"))
    
    print(f"Generating TASKS.md for {len(py_files)} Python files...")
    
    created = 0
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    for filepath in py_files:
        if "__pycache__" in str(filepath):
            continue
        
        template = get_template(filepath.stem)
        content = template.format(filename=filepath.stem, date=current_date)
        
        tasks_path = filepath.parent / f"{filepath.stem}_TASKS.md"
        tasks_path.write_text(content, encoding='utf-8')
        
        created += 1
        print(f"  Created: {tasks_path.name}")
    
    print(f"\n✅ Done! Created {created} TASKS.md files.")

if __name__ == "__main__":
    main()
