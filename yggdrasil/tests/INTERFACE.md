# yggdrasil.tests — INTERFACE

## Purpose
Verification surface for package-level and integration-level behavior.

## Public Interface
- `test_yggdrasil.py` as primary system behavior test module.
- Additional package tests discovered by test runners from this directory.

## Contracts
- Tests validate externally visible behavior, not incidental internals.
- Test fixtures should remain isolated and reproducible.

---
**Contract Version**: 1.0 | v8.0.0
