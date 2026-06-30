from __future__ import annotations

from mcaoe.models.domain import CapabilityName, CapabilityProfile, WorkflowStage


def build_profiles() -> list[CapabilityProfile]:
    return [
        CapabilityProfile(
            name=CapabilityName.web_security,
            description="Web application analysis, fingerprinting, and content discovery.",
            recommended_plugins=["nmap", "whatweb", "nikto", "ffuf", "gobuster"],
            default_workflow_stage=WorkflowStage.discovery,
        ),
        CapabilityProfile(
            name=CapabilityName.infrastructure,
            description="Network and service enumeration for infrastructure targets.",
            recommended_plugins=["nmap", "sslscan", "amass", "subfinder"],
            default_workflow_stage=WorkflowStage.discovery,
        ),
        CapabilityProfile(
            name=CapabilityName.active_directory,
            description="Directory, identity, and trust workflow support.",
            recommended_plugins=["nmap", "amass", "subfinder"],
            default_workflow_stage=WorkflowStage.enumeration,
        ),
        CapabilityProfile(
            name=CapabilityName.cloud,
            description="Cloud discovery, exposure review, and attack surface analysis.",
            recommended_plugins=["amass", "subfinder", "nmap"],
            default_workflow_stage=WorkflowStage.discovery,
        ),
        CapabilityProfile(
            name=CapabilityName.dfir,
            description="Defensive investigation and artifact review workflows.",
            recommended_plugins=["timeline", "artifact-review"],
            default_workflow_stage=WorkflowStage.analysis,
        ),
        CapabilityProfile(
            name=CapabilityName.threat_hunting,
            description="Hunting-oriented triage and correlation workflows.",
            recommended_plugins=["timeline", "correlation"],
            default_workflow_stage=WorkflowStage.analysis,
        ),
        CapabilityProfile(
            name=CapabilityName.malware_analysis,
            description="Static and dynamic analysis support.",
            recommended_plugins=["strings", "floss", "yara"],
            default_workflow_stage=WorkflowStage.analysis,
        ),
        CapabilityProfile(
            name=CapabilityName.osint,
            description="Open-source intelligence and passive discovery.",
            recommended_plugins=["subfinder", "amass"],
            default_workflow_stage=WorkflowStage.discovery,
        ),
        CapabilityProfile(
            name=CapabilityName.ctf,
            description="Challenge-oriented practice mode.",
            recommended_plugins=["nmap", "whatweb", "ffuf", "gobuster"],
            default_workflow_stage=WorkflowStage.discovery,
        ),
    ]


__all__ = ["build_profiles"]
