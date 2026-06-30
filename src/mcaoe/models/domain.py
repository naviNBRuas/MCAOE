from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from mcaoe._compat.pydantic import BaseModel, Field


class CapabilityName(str, Enum):
    web_security = "web_security"
    infrastructure = "infrastructure"
    active_directory = "active_directory"
    cloud = "cloud"
    dfir = "dfir"
    threat_hunting = "threat_hunting"
    malware_analysis = "malware_analysis"
    osint = "osint"
    ctf = "ctf"


class WorkflowStage(str, Enum):
    discovery = "discovery"
    enumeration = "enumeration"
    fingerprinting = "fingerprinting"
    validation = "validation"
    correlation = "correlation"
    analysis = "analysis"
    reporting = "reporting"


class BaseEntity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Host(BaseEntity):
    address: str
    hostname: str | None = None
    tags: list[str] = Field(default_factory=list)


class Service(BaseEntity):
    host_id: UUID
    name: str
    port: int
    protocol: Literal["tcp", "udp"] = "tcp"
    product: str | None = None
    version: str | None = None


class Technology(BaseEntity):
    name: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    evidence_ids: list[UUID] = Field(default_factory=list)


class VulnerabilityReference(BaseEntity):
    identifier: str
    source: str | None = None
    url: str | None = None
    severity: str | None = None


class Evidence(BaseEntity):
    source: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class Finding(BaseEntity):
    title: str
    description: str
    severity: str = "informational"
    evidence_ids: list[UUID] = Field(default_factory=list)
    status: str = "open"


class Recommendation(BaseEntity):
    title: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    priority: int = Field(ge=1, le=5, default=3)
    evidence_ids: list[UUID] = Field(default_factory=list)
    workflow_relevance: str | None = None
    requires_approval: bool = True


class Unknown(BaseEntity):
    label: str
    details: str | None = None
    priority: int = Field(ge=1, le=5, default=3)


class CommandExecution(BaseEntity):
    command: str
    arguments: list[str] = Field(default_factory=list)
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    approved_by_user: bool = False
    timeout_seconds: int = 300
    backend: str | None = None
    risk_level: str | None = None
    policy_profile: str | None = None
    policy_reason: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None


class WorkflowState(BaseEntity):
    target: str | None = None
    stage: WorkflowStage = WorkflowStage.discovery
    capability: CapabilityName = CapabilityName.web_security
    notes: list[str] = Field(default_factory=list)


class Session(BaseEntity):
    name: str
    capability: CapabilityName = CapabilityName.web_security
    targets: list[str] = Field(default_factory=list)
    hosts: list[Host] = Field(default_factory=list)
    services: list[Service] = Field(default_factory=list)
    technologies: list[Technology] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    unknowns: list[Unknown] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    commands: list[CommandExecution] = Field(default_factory=list)
    workflow: WorkflowState = Field(default_factory=WorkflowState)

    def add_target(self, target: str) -> None:
        if target not in self.targets:
            self.targets.append(target)

    def add_host(self, host: Host) -> None:
        if not any(existing.address == host.address for existing in self.hosts):
            self.hosts.append(host)

    def add_service(self, service: Service) -> None:
        if not any(
            existing.port == service.port and existing.protocol == service.protocol and existing.host_id == service.host_id
            for existing in self.services
        ):
            self.services.append(service)

    def add_technology(self, technology: Technology) -> None:
        if not any(existing.name == technology.name for existing in self.technologies):
            self.technologies.append(technology)

    def add_finding(self, finding: Finding) -> None:
        if not any(existing.title == finding.title for existing in self.findings):
            self.findings.append(finding)

    def add_unknown(self, unknown: Unknown) -> None:
        if not any(existing.label == unknown.label for existing in self.unknowns):
            self.unknowns.append(unknown)


class CapabilityProfile(BaseEntity):
    name: CapabilityName
    description: str
    recommended_plugins: list[str] = Field(default_factory=list)
    default_workflow_stage: WorkflowStage = WorkflowStage.discovery
