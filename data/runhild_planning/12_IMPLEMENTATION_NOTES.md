# Implementation Notes for Immediate Action

## First 10 Actions
1. Create `planning/` package and wire interfaces.
2. Add `schemas/` for plan, world-event, and lore assertion.
3. Implement basic plan scorer and comparator.
4. Add unit tests for scoring determinism.
5. Add memory provenance support in storage model.
6. Build contradiction detector prototype.
7. Add telemetry envelope middleware.
8. Create docs index and architecture map.
9. Add bug template and incident template.
10. Stand up weekly KPI report generator.

## Suggested File Additions (Future)
- `systems/planning_engine.py`
- `systems/world_graph.py`
- `systems/contradiction_detector.py`
- `systems/telemetry_envelope.py`
- `docs/architecture/atlas.md`
- `docs/runbooks/incident_response.md`

## Sequencing Principle
- Build observability before optimization.
- Build validation before automation.
- Build reliability before scale.
