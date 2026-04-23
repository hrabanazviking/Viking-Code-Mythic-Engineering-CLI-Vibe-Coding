# yggdrasil.worlds — INTERFACE

## Purpose
Domain model for Nine Worlds runtime environments.

## Public Interface
- `get_world(name)` factory via `__init__.py`.
- Realm modules: `asgard`, `midgard`, `vanaheim`, `alfheim`, `jotunheim`, `svartalfheim`, `muspelheim`, `niflheim`, `helheim`.

## Contracts
- Each world module exposes a world-specific class/behavior model compatible with `get_world(name)` lookup.
- Unknown world names must fail explicitly (no silent fallback).

---
**Contract Version**: 1.0 | v8.0.0
