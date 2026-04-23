# Cartographer Deep-Document Pack Template

Use this checklist when producing large mapping artifacts.

## 1) System Atlas

- Top-level domains and ownership
- Product vs imported vs vendored boundaries
- Package/install boundaries vs source-tree convenience imports
- Known dormant zones

## 2) Capabilities Catalog

For each major domain:

- What code exists
- What it currently does
- What appears planned but disconnected
- Runtime assumptions and missing prerequisites

## 3) Dependency Ledger

- Import graph highlights
- Ghost imports / unresolved modules
- Duplicate packages and potential install collisions
- Optional dependency mismatch risks

## 4) Data Flow Narrative

- Inputs / ingress points
- Transformation pipelines
- Persistence locations
- Output channels
- Observability / diagnostics streams

## 5) Change Impact Matrix

- Local impact
- Cross-island impact
- Tooling/test impact
- Migration impact

## 6) Actionable Next Steps

- Stabilize source of truth
- Remove or quarantine duplicates
- Add contract tests at seams
- Establish documented integration plan
