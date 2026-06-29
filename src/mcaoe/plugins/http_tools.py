from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcaoe.execution.orchestrator import AnalystOrchestrator

from mcaoe.core.events import Event, EventType
from mcaoe.models.domain import Session
from mcaoe.plugins.base import PluginMetadata
from mcaoe.plugins.templates import StaticCommandPlugin
from mcaoe.parsers.whatweb import as_domain_technologies, parse_whatweb_output
from mcaoe.parsers.nikto import parse_nikto_output
from mcaoe.parsers.ffuf import parse_ffuf_output


def ingest_whatweb_output(session: Session, stdout: str, stderr: str, orchestrator: "AnalystOrchestrator") -> dict[str, int]:
    parsed = parse_whatweb_output(stdout)
    technologies = as_domain_technologies(parsed)
    session.technologies.extend(technologies)
    session.evidence.extend(parsed.evidence)

    for technology in technologies:
        orchestrator.graph.add_technology(technology)
        orchestrator._emit_event(Event(type=EventType.technology_detected, payload={"name": technology.name, "confidence": technology.confidence}))
    for evidence in parsed.evidence:
        orchestrator.graph.add_evidence(evidence)
        orchestrator._emit_event(Event(type=EventType.evidence_added, payload={"source": evidence.source, "summary": evidence.summary}))

    session.recommendations = orchestrator.recommendations.generate(session)
    orchestrator.store.save_session(session)

    return {
        "technologies": len(technologies),
        "evidence": len(parsed.evidence),
    }


def ingest_nikto_output(session: Session, stdout: str, stderr: str, orchestrator: "AnalystOrchestrator") -> dict[str, int]:
    parsed = parse_nikto_output(stdout)
    session.findings.extend(parsed.findings)
    session.evidence.extend(parsed.evidence)
    session.technologies.extend(parsed.technologies)
    session.unknowns.extend(parsed.unknowns)

    for finding in parsed.findings:
        orchestrator.graph.add_finding(finding)
        orchestrator._emit_event(Event(type=EventType.recommendation_created, payload={"finding": finding.title, "severity": finding.severity}))
    for technology in parsed.technologies:
        orchestrator.graph.add_technology(technology)
        orchestrator._emit_event(Event(type=EventType.technology_detected, payload={"name": technology.name, "confidence": technology.confidence}))
    for evidence in parsed.evidence:
        orchestrator.graph.add_evidence(evidence)
        orchestrator._emit_event(Event(type=EventType.evidence_added, payload={"source": evidence.source, "summary": evidence.summary}))
    for unknown in parsed.unknowns:
        orchestrator.graph.add_unknown(unknown)
        orchestrator._emit_event(Event(type=EventType.unknown_detected, payload={"label": unknown.label, "priority": unknown.priority}))

    session.recommendations = orchestrator.recommendations.generate(session)
    orchestrator.store.save_session(session)

    return {
        "findings": len(parsed.findings),
        "evidence": len(parsed.evidence),
        "technologies": len(parsed.technologies),
        "unknowns": len(parsed.unknowns),
    }


def ingest_ffuf_output(session: Session, stdout: str, stderr: str, orchestrator: "AnalystOrchestrator") -> dict[str, int]:
    parsed = parse_ffuf_output(stdout)
    session.findings.extend(parsed.findings)
    session.evidence.extend(parsed.evidence)
    session.unknowns.extend(parsed.unknowns)

    for finding in parsed.findings:
        orchestrator.graph.add_finding(finding)
        orchestrator._emit_event(Event(type=EventType.recommendation_created, payload={"finding": finding.title, "severity": finding.severity}))
    for evidence in parsed.evidence:
        orchestrator.graph.add_evidence(evidence)
        orchestrator._emit_event(Event(type=EventType.evidence_added, payload={"source": evidence.source, "summary": evidence.summary}))
    for unknown in parsed.unknowns:
        orchestrator.graph.add_unknown(unknown)
        orchestrator._emit_event(Event(type=EventType.unknown_detected, payload={"label": unknown.label, "priority": unknown.priority}))

    session.recommendations = orchestrator.recommendations.generate(session)
    orchestrator.store.save_session(session)

    return {
        "results": len(parsed.results),
        "findings": len(parsed.findings),
        "evidence": len(parsed.evidence),
        "unknowns": len(parsed.unknowns),
    }


def build_whatweb_plugin() -> StaticCommandPlugin:
    return StaticCommandPlugin(
        metadata=PluginMetadata(
            name="whatweb",
            description="Web fingerprinting and technology identification.",
            capability_tags=["web_security", "enumeration", "fingerprinting"],
            risk_level="low",
        ),
        command="whatweb",
        argument_factory=lambda _session, target: ["--color=never", "--log-json=-", target],
        ingest_callback=ingest_whatweb_output,
    )


def build_nikto_plugin() -> StaticCommandPlugin:
    return StaticCommandPlugin(
        metadata=PluginMetadata(
            name="nikto",
            description="Web server misconfiguration and vulnerability checks.",
            capability_tags=["web_security", "enumeration", "validation"],
            risk_level="medium",
        ),
        command="nikto",
        argument_factory=lambda _session, target: ["-h", target],
        ingest_callback=ingest_nikto_output,
    )


def build_ffuf_plugin() -> StaticCommandPlugin:
    return StaticCommandPlugin(
        metadata=PluginMetadata(
            name="ffuf",
            description="Fast web content discovery and fuzzing.",
            capability_tags=["web_security", "content_discovery"],
            risk_level="medium",
        ),
        command="ffuf",
        argument_factory=lambda _session, target: ["-u", f"{target}/FUZZ", "-w", "/usr/share/wordlists/dirb/common.txt", "-of", "json", "-o", "/dev/stdout"],
        ingest_callback=ingest_ffuf_output,
    )


def build_gobuster_plugin() -> StaticCommandPlugin:
    return StaticCommandPlugin(
        metadata=PluginMetadata(
            name="gobuster",
            description="Directory and DNS brute-force style content discovery.",
            capability_tags=["web_security", "content_discovery"],
            risk_level="medium",
        ),
        command="gobuster",
        argument_factory=lambda _session, target: ["dir", "-u", target, "-w", "/usr/share/wordlists/dirb/common.txt"],
    )
