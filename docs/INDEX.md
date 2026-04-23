# Mythic Vibe CLI Documentation Index (Canonical)

This file is the canonical navigation and maintenance map for the active Mythic Vibe CLI documentation suite.

If two indexes disagree, this one wins.

---

## 1) Purpose of this index

This repository contains multiple code and research domains, but not all of them are active product runtime surfaces. This index helps contributors answer three questions quickly:

1. Which documents are authoritative for the CLI today?
2. Which documents are contextual/reference material?
3. What must be updated when behavior changes?

---

## 2) Fast-start reading paths

### New user (first 15 minutes)

1. [quickstart.md](quickstart.md)
2. [api.md](api.md)
3. [SYSTEM_VISION.md](SYSTEM_VISION.md)

### Contributor (first 30 minutes)

1. [ARCHITECTURE.md](ARCHITECTURE.md)
2. [DOMAIN_MAP.md](DOMAIN_MAP.md)
3. [DOCUMENTATION_STANDARDS.md](DOCUMENTATION_STANDARDS.md)
4. [../DEVLOG.md](../DEVLOG.md)

### Maintainer / release steward

1. [../CHANGELOG.md](../CHANGELOG.md)
2. [DOCUMENTATION_STANDARDS.md](DOCUMENTATION_STANDARDS.md)
3. [SESSION_HANDOFF_TEMPLATE.md](SESSION_HANDOFF_TEMPLATE.md)
4. [../README.md](../README.md)

---

## 3) Active documentation spine

| Document | Primary audience | Core responsibility |
|---|---|---|
| `../README.md` | users + contributors | project posture, install flow, command orientation |
| `quickstart.md` | users | first operational loop and troubleshooting |
| `ARCHITECTURE.md` | contributors | component boundaries and dependency law |
| `api.md` | integrators + maintainers | command contracts and compatibility expectations |
| `DOMAIN_MAP.md` | maintainers | ownership boundaries and escalation path |
| `SYSTEM_VISION.md` | product/maintainers | strategic scope, non-goals, long-horizon direction |
| `DOCUMENTATION_STANDARDS.md` | all contributors | writing quality, drift control, continuity protocol |
| `SESSION_HANDOFF_TEMPLATE.md` | session owners | structured closure and handoff continuity |
| `../DEVLOG.md` | contributors | narrative why-history and decision lineage |
| `../CHANGELOG.md` | users/release owners | externally meaningful change history |

---

## 4) Update obligations by change type

When you change behavior, update the matching documents in the same PR.

| Change type | Required doc updates |
|---|---|
| CLI command added/changed | `api.md`, `../README.md`, `../CHANGELOG.md` |
| Scaffolding behavior changed | `quickstart.md`, `ARCHITECTURE.md`, `../CHANGELOG.md` |
| Config precedence/defaults changed | `api.md`, `quickstart.md`, `../README.md` |
| Domain ownership moved | `DOMAIN_MAP.md`, `ARCHITECTURE.md`, `../DEVLOG.md` |
| Strategy/mission shift | `SYSTEM_VISION.md`, `../README.md`, `../DEVLOG.md`, `../CHANGELOG.md` |
| Documentation process change | `DOCUMENTATION_STANDARDS.md`, `SESSION_HANDOFF_TEMPLATE.md` |

If behavior and documentation diverge, treat it as a defect.

---

## 5) Canonical vs reference surfaces

### Canonical runtime docs (actively maintained)

- This `docs/` core set
- Root `README.md`
- Root `DEVLOG.md`
- Root `CHANGELOG.md`

### Reference/spec archive (contextual; not always runtime-authoritative)

- `docs/specs/` and other long-form concept packs
- root-level historic/essay documents not tied to active command contracts

When in doubt, prioritize active runtime docs for operational truth.

---

## 6) Documentation quality gate (pre-merge)

Before merging a behavior-changing PR, confirm:

- [ ] changed commands are reflected in `api.md`
- [ ] onboarding impact reflected in `quickstart.md` or `README.md`
- [ ] user-facing deltas logged in `CHANGELOG.md`
- [ ] rationale captured in `DEVLOG.md` when decisions are non-trivial
- [ ] links in this index still resolve

---

## 7) Continuity cadence

Recommended maintenance rhythm:

- **Every feature PR:** update contracts + changelog notes
- **Every significant session:** append devlog entry
- **Weekly/periodic:** run quick drift sweep across core docs
- **Before release cut:** ensure index, changelog, and README alignment

---

## 8) Related records

- [Documentation Standards and Continuity Charter](DOCUMENTATION_STANDARDS.md)
- [Session Handoff Template](SESSION_HANDOFF_TEMPLATE.md)
- [Project DEVLOG](../DEVLOG.md)
- [Project CHANGELOG](../CHANGELOG.md)

A good index does not merely list files; it protects memory by showing where truth lives.
