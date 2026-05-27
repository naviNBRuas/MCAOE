from __future__ import annotations

from mcaoe.models.domain import CapabilityName, CapabilityProfile, WorkflowStage


def build_profiles() -> list[CapabilityProfile]:
    return [
        CapabilityProfile(
            name=CapabilityName.web_security,
            description="Web application reconnaissance and validation.",
            recommended_plugins=["nmap", "whatweb", "nikto", "ffuf", "gobuster"],
            default_workflow_stage=WorkflowStage.discovery,
        ),
        CapabilityProfile(
            name=CapabilityName.infrastructure,
            description="Host and service enumeration for infrastructure targets.",
            recommended_plugins=["nmap", "sslscan", "amass", "subfinder"],
            default_workflow_stage=WorkflowStage.discovery,
        ),
        CapabilityProfile(
            name=CapabilityName.dfir,
            description="Defensive and forensic investigation workflows.",
            recommended_plugins=["log-analysis", "timeline", "artifact-review"],
            default_workflow_stage=WorkflowStage.analysis,
        ),
    ]
