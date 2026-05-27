from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from mcaoe.ai.assistant import AnalystAssistant
from mcaoe.analysis.gaps import GapAnalysis, analyze_session_gaps
from mcaoe.core.workflow import evaluate_stage_gate
from mcaoe.core.events import Event
from mcaoe.models.domain import Session, WorkflowStage
from mcaoe.observability import SessionReplay


@dataclass(slots=True)
class SessionReport:
    generated_at: datetime
    session: Session
    coverage: GapAnalysis
    summary: str
    highlights: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    execution_audit: list[str] = field(default_factory=list)
    event_counts: dict[str, int] = field(default_factory=dict)
    policy_decisions: list[str] = field(default_factory=list)
    workflow_readiness: dict[str, Any] = field(default_factory=dict)
    timeline: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "session": self.session.model_dump(mode="json"),
            "coverage": {
                "coverage_score": self.coverage.coverage_score,
                "open_count": self.coverage.open_count,
                "items": [
                    {"label": item.label, "details": item.details, "priority": item.priority}
                    for item in self.coverage.items
                ],
            },
            "summary": self.summary,
            "highlights": self.highlights,
            "next_steps": self.next_steps,
            "execution_audit": self.execution_audit,
            "event_counts": self.event_counts,
            "policy_decisions": self.policy_decisions,
            "workflow_readiness": self.workflow_readiness,
            "timeline": self.timeline,
        }


def build_session_report(session: Session, events: list[Event]) -> SessionReport:
    assistant = AnalystAssistant()
    coverage = analyze_session_gaps(session)
    replay = SessionReplay.from_session(session, events)
    return SessionReport(
        generated_at=datetime.now(timezone.utc),
        session=session,
        coverage=coverage,
        summary=assistant.summarize(session),
        highlights=assistant.highlights(session),
        next_steps=assistant.next_steps(session),
        execution_audit=_execution_audit(session),
        event_counts=_event_counts(events),
        policy_decisions=_policy_decisions(events),
        workflow_readiness=_workflow_readiness(session),
        timeline=replay.timeline(),
    )


def render_session_report_json(report: SessionReport) -> str:
    return json.dumps(report.to_dict(), indent=2)


def render_session_report_markdown(report: SessionReport) -> str:
    session = report.session
    lines = [
        f"# MCAOE Session Report — {session.name}",
        "",
        f"- Generated: {report.generated_at.isoformat()}",
        f"- Capability: {session.capability.value}",
        f"- Target: {session.workflow.target or 'not set'}",
        f"- Workflow stage: {session.workflow.stage.value}",
        f"- Coverage score: {report.coverage.coverage_score}/100",
        f"- Hosts: {len(session.hosts)}",
        f"- Services: {len(session.services)}",
        f"- Technologies: {len(session.technologies)}",
        f"- Findings: {len(session.findings)}",
        f"- Unknowns: {len(session.unknowns)}",
        f"- Evidence items: {len(session.evidence)}",
        "",
        "## Executive summary",
        "",
        report.summary,
        "",
        "## Coverage gaps",
    ]

    if report.coverage.items:
        for item in report.coverage.items:
            lines.append(f"- **{item.label}** — {item.details} (priority {item.priority})")
    else:
        lines.append("- None")

    lines.extend(["", "## Highlights"])
    if report.highlights:
        lines.extend(f"- {item}" for item in report.highlights)
    else:
        lines.append("- None")

    lines.extend(["", "## Recommended next steps"])
    if report.next_steps:
        lines.extend(f"- {item}" for item in report.next_steps)
    else:
        lines.append("- None")

    lines.extend(["", "## Execution audit"])
    if report.execution_audit:
        lines.extend(f"- {item}" for item in report.execution_audit)
    else:
        lines.append("- No commands executed")

    lines.extend(["", "## Event breakdown"])
    if report.event_counts:
        for event_type, count in sorted(report.event_counts.items()):
            lines.append(f"- {event_type}: {count}")
    else:
        lines.append("- No events recorded")

    lines.extend(["", "## Policy decisions"])
    if report.policy_decisions:
        lines.extend(f"- {item}" for item in report.policy_decisions)
    else:
        lines.append("- No policy decisions recorded")

    lines.extend(["", "## Workflow readiness"])
    reporting = report.workflow_readiness.get("reporting", {})
    lines.append(f"- Reporting gate allowed: {reporting.get('allowed')}")
    lines.append(f"- Reporting gate coverage score: {reporting.get('coverage_score')}")
    reasons = reporting.get("reasons") or []
    if reasons:
        lines.append("- Reporting gate reasons:")
        lines.extend(f"  - {reason}" for reason in reasons)
    else:
        lines.append("- Reporting gate reasons: none")

    lines.extend(["", "## Timeline"])
    if report.timeline:
        lines.extend(f"- {entry}" for entry in report.timeline)
    else:
        lines.append("- No events recorded")

    return "\n".join(lines).rstrip() + "\n"


def _execution_audit(session: Session) -> list[str]:
    audit: list[str] = []
    for command in session.commands:
        duration = f"{command.duration_seconds:.2f}s" if command.duration_seconds is not None else "unknown duration"
        backend = command.backend or "unknown backend"
        risk_level = command.risk_level or "unknown-risk"
        policy_profile = command.policy_profile or "unknown-profile"
        policy_reason = command.policy_reason or "no policy rationale recorded"
        approval = "approved" if command.approved_by_user else "unapproved"
        argument_text = " ".join(command.arguments).strip()
        rendered_command = f"{command.command} {argument_text}".strip()
        audit.append(
            f"{rendered_command} | exit={command.exit_code} | {approval} | {backend} | risk={risk_level} | profile={policy_profile} | {duration} | {policy_reason}"
        )
    return audit


def _event_counts(events: list[Event]) -> dict[str, int]:
    counts = Counter(event.type.value for event in events)
    return dict(counts)


def _policy_decisions(events: list[Event]) -> list[str]:
    decisions: list[str] = []
    for event in events:
        if event.type.value != "policy_decision_recorded":
            continue
        payload = event.payload
        plugin = payload.get("plugin", "unknown-plugin")
        allowed = payload.get("allowed")
        risk = payload.get("risk_level", "unknown")
        profile = payload.get("policy_profile", "unknown")
        reason = payload.get("reason", "no reason")
        decisions.append(f"plugin={plugin} allowed={allowed} risk={risk} profile={profile} reason={reason}")
    return decisions


def _workflow_readiness(session: Session) -> dict[str, Any]:
    reporting_gate = evaluate_stage_gate(session, WorkflowStage.reporting)
    return {
        "current_stage": session.workflow.stage.value,
        "reporting": {
            "allowed": reporting_gate.allowed,
            "coverage_score": reporting_gate.coverage_score,
            "reasons": list(reporting_gate.reasons),
        },
    }