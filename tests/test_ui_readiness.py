from __future__ import annotations

from mcaoe.models.domain import CapabilityName, CommandExecution, Evidence, Finding, Host, Service, Session, Technology
from mcaoe.ui.readiness import build_stage_checklist, render_readiness_scorecard


def test_readiness_scorecard_blocks_reporting_for_empty_session() -> None:
    session = Session(name="ui-readiness-empty", capability=CapabilityName.web_security)

    lines = render_readiness_scorecard(session)

    assert any("Readiness scorecard" in line for line in lines)
    assert any("Reporting gate: BLOCKED" in line for line in lines)
    assert any("reporting" in line and "Collect evidence before reporting" in line for line in lines)


def test_stage_checklist_marks_reporting_ready_when_requirements_met() -> None:
    session = Session(name="ui-readiness-ready", capability=CapabilityName.web_security)
    session.workflow.target = "https://example.com"
    session.targets.append("https://example.com")

    host = Host(address="192.0.2.1", hostname="example.com")
    session.hosts.append(host)
    session.services.append(Service(host_id=host.id, name="https", port=443, version="1.2"))
    session.technologies.append(Technology(name="https", confidence=0.9))
    session.evidence.append(Evidence(source="manual", summary="Collected baseline evidence"))
    session.findings.append(Finding(title="Sample finding", description="desc", severity="low"))
    session.commands.append(CommandExecution(command="whatweb", arguments=["https://example.com"], exit_code=0, approved_by_user=True))

    checklist = build_stage_checklist(session)
    reporting_item = next(item for item in checklist if item.stage.value == "reporting")

    assert reporting_item.status == "ready"
    assert reporting_item.allowed is True
    assert reporting_item.reasons == []