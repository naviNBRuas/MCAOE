from __future__ import annotations

from dataclasses import dataclass, field

from mcaoe.ai.provider import LLMProvider, create_provider
from mcaoe.analysis.gaps import analyze_session_gaps
from mcaoe.models.domain import Finding, Recommendation, Session, Technology, Unknown


@dataclass(slots=True)
class AnalystAssistant:
    llm_provider: LLMProvider | None = None
    llm_enabled: bool = False
    _provider_name: str = field(default="gemini")

    def __post_init__(self) -> None:
        if self.llm_provider is None and self.llm_enabled:
            try:
                self.llm_provider = create_provider(self._provider_name)
            except Exception:
                self.llm_enabled = False

    def enable_llm(self, provider_name: str = "gemini") -> None:
        self._provider_name = provider_name
        try:
            self.llm_provider = create_provider(provider_name)
            self.llm_enabled = True
        except Exception:
            self.llm_enabled = False

    def _llm_summarize(self, session: Session) -> str | None:
        if not self.llm_enabled or self.llm_provider is None:
            return None
        gaps = analyze_session_gaps(session)
        prompt = (
            f"Summarize this cybersecurity reconnaissance session in 3-4 sentences:\n"
            f"- Session: {session.name}\n"
            f"- Capability: {session.capability.value}\n"
            f"- Stage: {session.workflow.stage.value}\n"
            f"- Target: {session.workflow.target or 'not set'}\n"
            f"- Hosts: {len(session.hosts)}, Services: {len(session.services)}, "
            f"Technologies: {len(session.technologies)}\n"
            f"- Findings: {len(session.findings)}, Unknowns: {len(session.unknowns)}\n"
            f"- Coverage: {gaps.coverage_score}/100\n"
            f"- Gaps: {'; '.join(item.label for item in gaps.items[:3])}\n"
            f"Keep it concise and actionable."
        )
        try:
            return self.llm_provider.generate(prompt)
        except Exception:
            return None

    def summarize(self, session: Session) -> str:
        llm_summary = self._llm_summarize(session)
        gaps = analyze_session_gaps(session)
        lines = []

        if llm_summary:
            lines.append(llm_summary)
            lines.append("")

        lines.extend([
            f"Session: {session.name}",
            f"Capability profile: {session.capability.value}",
            f"Workflow stage: {session.workflow.stage.value}",
            f"Target: {session.workflow.target or 'not set'}",
            f"Inventory: {len(session.hosts)} hosts | {len(session.services)} services | {len(session.technologies)} technologies",
            f"Signals: {len(session.findings)} findings | {len(session.unknowns)} unknowns | {len(session.evidence)} evidence items | {len(session.commands)} commands",
            gaps.summary(),
        ])

        ordered_recommendations = self._ordered_recommendations(session)
        if ordered_recommendations:
            lines.append(f"Top recommendation: {self._describe_recommendation(ordered_recommendations[0])}")

        highlights = self.highlights(session)
        if highlights:
            lines.append("Highlights:")
            lines.extend(f"  - {highlight}" for highlight in highlights)

        if self.llm_enabled and self.llm_provider is not None:
            lines.append(f"LLM back-end: {self.llm_provider.name()}")

        return "\n".join(lines)

    def highlights(self, session: Session, limit: int = 5) -> list[str]:
        highlights: list[str] = []

        top_findings = self._top_findings(session.findings, limit=2)
        if top_findings:
            highlights.append("Key findings: " + "; ".join(top_findings))

        top_unknowns = self._top_unknowns(session.unknowns, limit=2)
        if top_unknowns:
            highlights.append("Verification gaps: " + "; ".join(top_unknowns))

        top_technologies = self._top_technologies(session.technologies, limit=3)
        if top_technologies:
            highlights.append("Detected technologies: " + ", ".join(top_technologies))

        ordered = self._ordered_recommendations(session)[:limit]
        if ordered:
            highlights.append("Recommended next actions: " + "; ".join(self._describe_recommendation(item) for item in ordered))

        gaps = analyze_session_gaps(session)
        if gaps.items:
            highlights.append("Open coverage gaps: " + "; ".join(f"{item.label} [{item.priority}]" for item in gaps.items[:limit]))

        return highlights

    def session_card(self, session: Session) -> dict[str, object]:
        return {
            "session": session.name,
            "capability": session.capability.value,
            "workflow_stage": session.workflow.stage.value,
            "target": session.workflow.target,
            "coverage_score": analyze_session_gaps(session).coverage_score,
            "counts": {
                "targets": len(session.targets),
                "hosts": len(session.hosts),
                "services": len(session.services),
                "technologies": len(session.technologies),
                "findings": len(session.findings),
                "unknowns": len(session.unknowns),
                "evidence": len(session.evidence),
                "commands": len(session.commands),
            },
            "top_recommendations": [self._describe_recommendation(item) for item in self._ordered_recommendations(session)[:3]],
            "highlights": self.highlights(session),
        }

    def contextual_hint(self, recommendation: Recommendation) -> str:
        confidence = f"{recommendation.confidence:.0%}"
        return f"{recommendation.title}: {recommendation.rationale} (confidence {confidence}, priority {recommendation.priority})"

    def next_steps(self, session: Session, limit: int = 3) -> list[str]:
        return [self.contextual_hint(recommendation) for recommendation in self._ordered_recommendations(session)[:limit]]

    def _ordered_recommendations(self, session: Session) -> list[Recommendation]:
        return sorted(session.recommendations, key=lambda recommendation: (recommendation.priority, -recommendation.confidence))

    def _describe_recommendation(self, recommendation: Recommendation) -> str:
        return f"{recommendation.title} ({recommendation.workflow_relevance or 'general'}, {recommendation.confidence:.0%})"

    def _top_findings(self, findings: list[Finding], limit: int = 2) -> list[str]:
        ordered = sorted(findings, key=lambda finding: (finding.severity != "informational", finding.title.lower()))
        return [f"{finding.title} [{finding.severity}]" for finding in ordered[:limit]]

    def _top_unknowns(self, unknowns: list[Unknown], limit: int = 2) -> list[str]:
        ordered = sorted(unknowns, key=lambda unknown: (unknown.priority, unknown.label.lower()))
        return [f"{unknown.label} (priority {unknown.priority})" for unknown in ordered[:limit]]

    def _top_technologies(self, technologies: list[Technology], limit: int = 3) -> list[str]:
        ordered = sorted(technologies, key=lambda technology: (-technology.confidence, technology.name.lower()))
        return [technology.name for technology in ordered[:limit]]
