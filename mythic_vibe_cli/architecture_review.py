"""Phase 20.H — quarterly architecture review helper.

A reviewer-facing checklist generator. Walks the active
governance artefacts (`docs/ADRS/`, `docs/ARCHITECTURE.md`,
`docs/DOMAIN_MAP.md`) and the live drift output (re-using
`drift.scan_for_drift`), then emits a structured review
checklist. Pure read; no mutation.

Two outputs:

- **Markdown** — paste-ready meeting agenda + per-section
  checklist with current counts.
- **JSON** — structured payload (`adr_count`, `drift_summary`,
  `governance_files_present`) for downstream tooling.

The cadence side of the slice is documented in
`docs/governance/quarterly_review.md` (committed alongside this
module). The CLI command surfaces "did the operator run the
review this quarter?" indirectly via the absence/presence of a
checked-in review log under `mythic/governance/`.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


GOVERNANCE_DOCS: tuple[str, ...] = (
    "docs/ARCHITECTURE.md",
    "docs/DOMAIN_MAP.md",
    "docs/DATA_FLOW.md",
    "docs/ACTIVE_PRODUCT_BOUNDARY.md",
    "docs/PHILOSOPHY.md",
)


@dataclass
class ReviewReport:
    governance_files: dict[str, bool] = field(default_factory=dict)
    adr_count: int = 0
    drift_total: int = 0
    drift_by_severity: dict[str, int] = field(default_factory=dict)
    open_questions: list[str] = field(default_factory=list)

    @property
    def all_governance_files_present(self) -> bool:
        return all(self.governance_files.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "governance_files": dict(self.governance_files),
            "all_governance_files_present": self.all_governance_files_present,
            "adr_count": self.adr_count,
            "drift_total": self.drift_total,
            "drift_by_severity": dict(self.drift_by_severity),
            "open_questions": list(self.open_questions),
        }


def _count_adrs(root: Path) -> int:
    adr_dir = root / "docs" / "ADRS"
    if not adr_dir.is_dir():
        return 0
    return sum(
        1
        for path in adr_dir.glob("ADR-*.md")
        if path.is_file()
    )


def build_review_report(root: Path) -> ReviewReport:
    """Run the read-only review pass against ``root`` and
    return a :class:`ReviewReport`."""
    from .drift import scan_for_drift, summarize_findings

    governance = {
        rel: (root / rel).is_file()
        for rel in GOVERNANCE_DOCS
    }
    adr_count = _count_adrs(root)
    findings = scan_for_drift(root)
    severity_summary = summarize_findings(findings)

    open_questions: list[str] = []
    if not governance.get("docs/ARCHITECTURE.md", False):
        open_questions.append(
            "ARCHITECTURE.md missing — restore or document why it was removed."
        )
    if not governance.get("docs/DOMAIN_MAP.md", False):
        open_questions.append(
            "DOMAIN_MAP.md missing — domain ownership is undocumented."
        )
    if adr_count == 0:
        open_questions.append(
            "No ADRs present in docs/ADRS/ — record at least one architectural decision."
        )
    if severity_summary.get("error", 0) > 0:
        open_questions.append(
            f"{severity_summary['error']} error-severity drift findings outstanding."
        )

    return ReviewReport(
        governance_files=governance,
        adr_count=adr_count,
        drift_total=len(findings),
        drift_by_severity=severity_summary,
        open_questions=open_questions,
    )


def render_review_markdown(report: ReviewReport) -> str:
    lines: list[str] = []
    lines.append("# Architecture Review")
    lines.append("")
    lines.append(
        "Run quarterly. See `docs/governance/quarterly_review.md` "
        "for the full cadence + agenda."
    )
    lines.append("")

    lines.append("## Governance artefacts")
    lines.append("")
    lines.append("| File | Present |")
    lines.append("|------|---------|")
    for path, present in report.governance_files.items():
        lines.append(f"| `{path}` | {'yes' if present else 'NO'} |")
    lines.append("")

    lines.append("## ADRs")
    lines.append("")
    lines.append(f"- ADR count: **{report.adr_count}**")
    lines.append("")

    lines.append("## Drift")
    lines.append("")
    lines.append(f"- Total findings: **{report.drift_total}**")
    by_sev = report.drift_by_severity
    for sev in ("info", "warning", "error"):
        lines.append(f"- `{sev}`: {by_sev.get(sev, 0)}")
    lines.append("")

    lines.append("## Open questions")
    lines.append("")
    if report.open_questions:
        for question in report.open_questions:
            lines.append(f"- {question}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Reviewer checklist")
    lines.append("")
    lines.append("- [ ] Confirm boundary between active runtime + dormant islands.")
    lines.append("- [ ] Walk every ADR; mark `Superseded` ones explicitly.")
    lines.append("- [ ] Triage every `warning`/`error` drift finding.")
    lines.append("- [ ] Compare CHANGELOG `[Unreleased]` against the period's commits.")
    lines.append("- [ ] Capture this review under `mythic/governance/review-<YYYY-MM-DD>.md`.")
    return "\n".join(lines) + "\n"


__all__ = [
    "GOVERNANCE_DOCS",
    "ReviewReport",
    "build_review_report",
    "render_review_markdown",
]
