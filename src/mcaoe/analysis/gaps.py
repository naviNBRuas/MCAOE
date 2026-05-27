from __future__ import annotations

from dataclasses import dataclass, field

from mcaoe.models.domain import Session


@dataclass(slots=True)
class GapItem:
    label: str
    details: str
    priority: int = 3


@dataclass(slots=True)
class GapAnalysis:
    coverage_score: int
    items: list[GapItem] = field(default_factory=list)

    @property
    def open_count(self) -> int:
        return len(self.items)

    def summary(self) -> str:
        if not self.items:
            return f"Coverage score: {self.coverage_score}/100 | No open gaps"
        preview = "; ".join(item.label for item in self.items[:4])
        return f"Coverage score: {self.coverage_score}/100 | Open gaps: {preview}"


def analyze_session_gaps(session: Session) -> GapAnalysis:
    items: list[GapItem] = []
    score = 100

    if not session.workflow.target:
        items.append(GapItem(label="Target not set", details="The session has not been anchored to a target yet.", priority=1))
        score -= 20

    if not session.hosts:
        items.append(GapItem(label="No hosts discovered", details="No host discovery results have been recorded.", priority=2))
        score -= 15

    if session.services and any(service.version is None for service in session.services):
        items.append(GapItem(label="Service versions missing", details="At least one discovered service lacks a version string.", priority=2))
        score -= 10

    if any(service.name.lower() in {"http", "https", "ssl", "tls"} or service.port in {80, 443} for service in session.services):
        has_tls_technology = any(technology.name.lower() in {"tls", "https"} for technology in session.technologies)
        if not has_tls_technology:
            items.append(GapItem(label="TLS posture unverified", details="Web-facing services exist but TLS verification evidence is missing.", priority=2))
            score -= 10

    if session.workflow.target and not session.technologies:
        items.append(GapItem(label="Fingerprinting incomplete", details="No technology fingerprints have been captured yet.", priority=3))
        score -= 10

    if not session.evidence:
        items.append(GapItem(label="No evidence captured", details="The session does not yet contain structured evidence artifacts.", priority=3))
        score -= 5

    if session.unknowns:
        items.append(GapItem(label="Open unknowns remain", details=f"{len(session.unknowns)} unresolved unknown(s) still need verification.", priority=2))
        score -= min(15, len(session.unknowns) * 5)

    if session.targets and not session.workflow.target:
        items.append(GapItem(label="Target selection pending", details="A target has been recorded but the workflow target is not set.", priority=2))
        score -= 5

    if score < 0:
        score = 0

    items.sort(key=lambda item: (item.priority, item.label.lower()))
    return GapAnalysis(coverage_score=score, items=items)