# yggdrasil.config — INTERFACE

## Purpose
Configuration surface for the Yggdrasil package.

## Public Interface
- `yggdrasil.config` package export via `__init__.py`.
- `default.yaml` as the default runtime configuration payload.

## Contracts
- Consumers should treat `default.yaml` as baseline values and overlay environment/runtime-specific settings externally.
- Config loading should remain side-effect free and deterministic.

---
**Contract Version**: 1.0 | v8.0.0
