from __future__ import annotations

from dataclasses import dataclass

from mcaoe.analysis.gaps import analyze_session_gaps
from mcaoe.models.domain import Finding, Recommendation, Service, Session, Technology, Unknown
from mcaoe.workflows import build_mvp_capability_profiles


@dataclass(slots=True)
class RecommendationEngine:
    def generate(self, session: Session) -> list[Recommendation]:
        recommendations: list[Recommendation] = []
        profiles = {profile.name: profile for profile in build_mvp_capability_profiles()}
        profile = profiles.get(session.capability)

        if profile is not None:
            session.workflow.capability = profile.name
            session.workflow.stage = profile.default_workflow_stage

            existing_titles = {recommendation.title.lower() for recommendation in recommendations}
            missing_plugins = [plugin_name for plugin_name in profile.recommended_plugins if plugin_name.lower() not in existing_titles]
            if missing_plugins:
                recommendations.append(
                    Recommendation(
                        title=f"Use {profile.name.value.replace('_', ' ')} toolkit",
                        rationale=f"Recommended tooling for this mode includes: {', '.join(missing_plugins)}.",
                        confidence=0.75,
                        priority=3,
                        workflow_relevance=profile.default_workflow_stage.value,
                    )
                )

        if any(isinstance(item, Service) and item.version is None for item in session.services):
            recommendations.append(
                Recommendation(
                    title="Run version detection",
                    rationale="At least one service is present without a version string.",
                    confidence=0.9,
                    priority=2,
                    workflow_relevance="fingerprinting",
                )
            )

        gaps = analyze_session_gaps(session)
        if any(item.label == "Target not set" for item in gaps.items):
            recommendations.append(
                Recommendation(
                    title="Record a target",
                    rationale="The session has no active target yet, so discovery cannot be grounded.",
                    confidence=0.98,
                    priority=1,
                    workflow_relevance="discovery",
                )
            )
        if any(item.label == "No hosts discovered" for item in gaps.items):
            recommendations.append(
                Recommendation(
                    title="Run initial discovery",
                    rationale="No hosts have been discovered yet, so the attack surface is still unmeasured.",
                    confidence=0.9,
                    priority=2,
                    workflow_relevance="discovery",
                )
            )
        if any(item.label == "Fingerprinting incomplete" for item in gaps.items):
            recommendations.append(
                Recommendation(
                    title="Capture fingerprints",
                    rationale="A target exists, but no structured technologies have been identified yet.",
                    confidence=0.88,
                    priority=2,
                    workflow_relevance="fingerprinting",
                )
            )

        technology_names = {technology.name.lower() for technology in session.technologies if isinstance(technology, Technology)}
        if {"web service", "https", "tls"} & technology_names:
            recommendations.append(
                Recommendation(
                    title="Validate TLS posture",
                    rationale="The session now contains web-facing or TLS-related technologies that should be verified.",
                    confidence=0.82,
                    priority=2,
                    workflow_relevance="validation",
                )
            )

        if {"nginx", "apache httpd", "iis"} & technology_names:
            recommendations.append(
                Recommendation(
                    title="Review web server fingerprinting",
                    rationale="Identified web-server technologies warrant deeper fingerprinting and misconfiguration checks.",
                    confidence=0.78,
                    priority=3,
                    workflow_relevance="fingerprinting",
                )
            )

        if session.unknowns:
            recommendations.append(
                Recommendation(
                    title="Reduce enumeration gaps",
                    rationale="The session already tracks unresolved unknowns that should be verified.",
                    confidence=0.85,
                    priority=2,
                    workflow_relevance="validation",
                )
            )

        if any(isinstance(finding, Finding) and finding.severity != "informational" for finding in session.findings):
            recommendations.append(
                Recommendation(
                    title="Review higher-severity findings",
                    rationale="The session contains non-informational findings that deserve analyst attention.",
                    confidence=0.8,
                    priority=1,
                    workflow_relevance="analysis",
                )
            )

        if any(
            isinstance(finding, Finding) and finding.title in {"Interesting content discovered", "Restricted content discovered"}
            for finding in session.findings
        ):
            recommendations.append(
                Recommendation(
                    title="Review discovered content",
                    rationale="Fuzzing found interesting or restricted endpoints that should be triaged manually.",
                    confidence=0.84,
                    priority=2,
                    workflow_relevance="enumeration",
                )
            )

        if not recommendations:
            recommendations.append(
                Recommendation(
                    title="Start discovery",
                    rationale="No actionable intelligence has been recorded yet.",
                    confidence=0.6,
                    priority=3,
                    workflow_relevance="discovery",
                )
            )

        return recommendations
