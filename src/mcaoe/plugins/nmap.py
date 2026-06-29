from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcaoe.execution.orchestrator import AnalystOrchestrator

from mcaoe.core.events import Event, EventType
from mcaoe.execution.provider import ExecutionTask
from mcaoe.models.domain import Session
from mcaoe.plugins.base import PluginMetadata
from mcaoe.parsers.nmap_xml import parse_nmap_xml


@dataclass(slots=True)
class NmapPlugin:
    metadata: PluginMetadata = field(
        default_factory=lambda: PluginMetadata(
            name="nmap",
            description="Structured network discovery and service fingerprinting.",
            capability_tags=["infrastructure", "web_security", "enumeration"],
            risk_level="medium",
        )
    )

    def build_task(self, session: Session, target: str) -> ExecutionTask:
        return ExecutionTask(
            command="nmap",
            arguments=["-sV", "-oX", "-", target],
            timeout_seconds=600,
            requires_approval=True,
            profile=session.capability.value,
            plugin_name=self.metadata.name,
            risk_level=self.metadata.risk_level,
        )

    def ingest_output(self, session: Session, stdout: str, stderr: str, orchestrator: "AnalystOrchestrator") -> dict[str, int]:
        if not stdout:
            return {}
        parsed = parse_nmap_xml(stdout)
        session.hosts.extend(parsed.hosts)
        session.services.extend(parsed.services)
        session.evidence.extend(parsed.evidence)
        session.technologies.extend(parsed.technologies)

        for host in parsed.hosts:
            orchestrator.graph.add_host(host)
            orchestrator._emit_event(Event(type=EventType.target_added, payload={"address": host.address, "hostname": host.hostname}))
        for service in parsed.services:
            orchestrator.graph.add_service(service)
            orchestrator._emit_event(Event(type=EventType.service_identified, payload={"name": service.name, "port": service.port, "protocol": service.protocol}))
        for evidence in parsed.evidence:
            orchestrator.graph.add_evidence(evidence)
            orchestrator._emit_event(Event(type=EventType.evidence_added, payload={"source": evidence.source, "summary": evidence.summary}))
        for technology in parsed.technologies:
            orchestrator.graph.add_technology(technology)
            orchestrator._emit_event(Event(type=EventType.technology_detected, payload={"name": technology.name, "confidence": technology.confidence}))

        session.recommendations = orchestrator.recommendations.generate(session)
        orchestrator.store.save_session(session)

        return {
            "hosts": len(parsed.hosts),
            "services": len(parsed.services),
            "evidence": len(parsed.evidence),
            "technologies": len(parsed.technologies),
        }
