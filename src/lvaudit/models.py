"""Core data models for lvaudit.

A Finding is the unit of evidence the whole tool produces. Severity is ranked
by business/user impact (the same scale used in Fernando's manual audit process),
not by raw WCAG level — a blocker is a blocker whether the spec calls it A or AA.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Severity(IntEnum):
    """Impact-ranked severity. Lower number = more severe, so sorting puts
    the most damaging findings first."""
    BLOCKER = 1      # User cannot complete the flow at all.
    SEVERE = 2       # Completable, but most users would give up.
    MODERATE = 3     # Confuses or slows down; a motivated user gets through.
    POLISH = 4       # Detracts from quality without blocking anything.

    @property
    def label(self) -> str:
        return {
            Severity.BLOCKER: "Blocker",
            Severity.SEVERE: "Severe",
            Severity.MODERATE: "Moderate",
            Severity.POLISH: "Polish",
        }[self]


@dataclass
class Finding:
    """One detected problem, with enough evidence to reproduce and cite it."""
    title: str                      # Plain-language: what happens, not jargon.
    severity: Severity
    wcag: str                       # e.g. "1.4.10 Reflow"
    condition: str                  # The test condition, e.g. "400% zoom".
    detail: str                     # The measurement that triggered it.
    location: str = ""              # CSS selector or region, when identifiable.
    evidence: str = ""              # Path to a screenshot, when captured.

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "severity": self.severity.label,
            "wcag": self.wcag,
            "condition": self.condition,
            "detail": self.detail,
            "location": self.location,
            "evidence": self.evidence,
        }


@dataclass
class AuditResult:
    """The full result for one URL across all tested conditions."""
    url: str
    findings: list[Finding] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def sorted_findings(self) -> list[Finding]:
        """Most severe first; stable within a severity level."""
        return sorted(self.findings, key=lambda f: f.severity)

    def summary(self) -> dict[str, int]:
        counts = {s.label: 0 for s in Severity}
        for f in self.findings:
            counts[f.severity.label] += 1
        return counts
