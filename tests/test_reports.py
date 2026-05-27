from pathlib import Path

from mcaoe.core.events import Event, EventType
from mcaoe.models.domain import CapabilityName, CommandExecution, Session
from mcaoe.reports import build_session_report, render_session_report_json, render_session_report_markdown


def test_session_report_renders_markdown_and_json(tmp_path: Path) -> None:
    session = Session(name="report-test", capability=CapabilityName.web_security)
    session.workflow.target = "https://example.com"
    session.targets.append("https://example.com")
    events = [Event(type=EventType.target_added, payload={"target": "https://example.com"})]

    report = build_session_report(session, events)

    markdown = render_session_report_markdown(report)
    json_text = render_session_report_json(report)

    assert "MCAOE Session Report" in markdown
    assert "Coverage score" in markdown
    assert "Execution audit" in markdown
    assert "Event breakdown" in markdown
    assert "Policy decisions" in markdown
    assert "Workflow readiness" in markdown
    assert "report-test" in json_text
    assert report.coverage.coverage_score < 100


def test_session_report_includes_execution_audit_lines(tmp_path: Path) -> None:
    session = Session(name="report-audit-test", capability=CapabilityName.web_security)
    session.workflow.target = "https://example.com"
    session.targets.append("https://example.com")
    session.commands.append(
        CommandExecution(
            command="whatweb",
            arguments=["--log-json=-", "https://example.com"],
            exit_code=0,
            approved_by_user=True,
            backend="docker",
            duration_seconds=1.23,
        )
    )
    events = [Event(type=EventType.task_completed, payload={"command": "whatweb", "exit_code": 0})]

    report = build_session_report(session, events)
    markdown = render_session_report_markdown(report)
    json_text = render_session_report_json(report)

    assert report.execution_audit
    assert "whatweb" in report.execution_audit[0]
    assert "Execution audit" in markdown
    assert "execution_audit" in json_text


def test_session_report_includes_policy_decisions_and_event_counts(tmp_path: Path) -> None:
    session = Session(name="report-policy-test", capability=CapabilityName.web_security)
    events = [
        Event(
            type=EventType.policy_decision_recorded,
            payload={
                "plugin": "whatweb",
                "allowed": True,
                "risk_level": "low",
                "policy_profile": "web_security",
                "reason": "Allowed under profile",
            },
        ),
        Event(type=EventType.task_started, payload={"command": "whatweb"}),
    ]

    report = build_session_report(session, events)
    markdown = render_session_report_markdown(report)
    json_text = render_session_report_json(report)

    assert report.event_counts.get("policy_decision_recorded") == 1
    assert report.event_counts.get("task_started") == 1
    assert report.policy_decisions
    assert "whatweb" in report.policy_decisions[0]
    assert "policy_decision_recorded: 1" in markdown
    assert "Policy decisions" in markdown
    assert "Workflow readiness" in markdown
    assert "Reporting gate allowed" in markdown
    assert report.workflow_readiness["reporting"]["allowed"] is False
    assert "policy_decisions" in json_text
    assert "workflow_readiness" in json_text