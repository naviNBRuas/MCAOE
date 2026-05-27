import asyncio
from pathlib import Path
from uuid import uuid4

from mcaoe.core.events import EventBus, EventType
from mcaoe.database.store import SQLiteStore
from mcaoe.execution.orchestrator import AnalystOrchestrator
from mcaoe.execution.provider import ExecutionResult, ExecutionTask
from mcaoe.graph.engine import KnowledgeGraphEngine
from mcaoe.models.domain import CapabilityName, Evidence, Session, Unknown
from mcaoe.policy import SafetyPolicy
from mcaoe.plugins.registry import PluginRegistry
from mcaoe.recommendations.engine import RecommendationEngine


SAMPLE_NMAP_XML = """
<nmaprun>
    <host>
        <status state="up" />
        <address addr="192.0.2.10" />
        <hostnames>
            <hostname name="example.local" />
        </hostnames>
        <ports>
            <port protocol="tcp" portid="80">
                <state state="open" />
                <service name="http" product="nginx" version="1.24" />
            </port>
        </ports>
    </host>
</nmaprun>
"""


def test_workflow_transition_emits_event_and_persists(tmp_path: Path) -> None:
    session = Session(name="workflow-test", capability=CapabilityName.infrastructure)
    bus = EventBus()
    orchestrator = AnalystOrchestrator(
        bus=bus,
        registry=PluginRegistry.with_defaults(),
        policy=SafetyPolicy(),
        graph=KnowledgeGraphEngine(),
        recommendations=RecommendationEngine(),
        store=SQLiteStore(tmp_path / "mcaoe.sqlite3"),
    )

    session.workflow.target = "https://example.com"
    session.targets.append("https://example.com")
    session.evidence.append(Evidence(source="manual", summary="seed"))
    session.unknowns.append(Unknown(label="open", priority=2))

    asyncio.run(orchestrator.advance_workflow(session, "analysis"))

    assert session.workflow.stage.value == "analysis"
    assert bus.history[-1].type is EventType.workflow_transitioned
    loaded = orchestrator.store.load_session(str(session.id))
    assert loaded is not None
    assert loaded.workflow.stage.value == "analysis"


def test_workflow_transition_blocks_reporting_when_gates_fail(tmp_path: Path) -> None:
    session = Session(name="gate-block-test", capability=CapabilityName.web_security)
    orchestrator = AnalystOrchestrator(
        bus=EventBus(),
        registry=PluginRegistry.with_defaults(),
        policy=SafetyPolicy(),
        graph=KnowledgeGraphEngine(),
        recommendations=RecommendationEngine(),
        store=SQLiteStore(tmp_path / "mcaoe.sqlite3"),
    )

    try:
        asyncio.run(orchestrator.advance_workflow(session, "reporting"))
    except PermissionError as exc:
        assert "Workflow transition blocked" in str(exc)
    else:
        raise AssertionError("Expected reporting transition to be blocked")


def test_workflow_transition_override_allows_reporting_with_approval(tmp_path: Path) -> None:
    session = Session(name="gate-override-test", capability=CapabilityName.web_security)
    bus = EventBus()
    orchestrator = AnalystOrchestrator(
        bus=bus,
        registry=PluginRegistry.with_defaults(),
        policy=SafetyPolicy(),
        graph=KnowledgeGraphEngine(),
        recommendations=RecommendationEngine(),
        store=SQLiteStore(tmp_path / "mcaoe.sqlite3"),
    )

    asyncio.run(orchestrator.advance_workflow(session, "reporting", approved_by_user=True, force=True))

    assert session.workflow.stage.value == "reporting"
    assert session.workflow.notes
    assert "Override applied" in session.workflow.notes[-1]
    assert bus.history[-1].type is EventType.workflow_transitioned
    assert bus.history[-1].payload["override"] is True


def test_record_target_updates_session_and_emits_event(tmp_path: Path) -> None:
    session = Session(name="target-test", capability=CapabilityName.web_security)
    bus = EventBus()
    orchestrator = AnalystOrchestrator(
        bus=bus,
        registry=PluginRegistry.with_defaults(),
        policy=SafetyPolicy(),
        graph=KnowledgeGraphEngine(),
        recommendations=RecommendationEngine(),
        store=SQLiteStore(tmp_path / "mcaoe.sqlite3"),
    )

    asyncio.run(orchestrator.record_target(session, "https://example.com"))

    assert session.workflow.target == "https://example.com"
    assert "https://example.com" in session.targets
    assert bus.history[-1].type is EventType.target_added


def test_plan_tool_run_emits_policy_decision_event(tmp_path: Path) -> None:
    session = Session(name="policy-event-test", capability=CapabilityName.web_security)
    bus = EventBus()
    orchestrator = AnalystOrchestrator(
        bus=bus,
        registry=PluginRegistry.with_defaults(),
        policy=SafetyPolicy(),
        graph=KnowledgeGraphEngine(),
        recommendations=RecommendationEngine(),
        store=SQLiteStore(tmp_path / "mcaoe.sqlite3"),
    )

    task = orchestrator.plan_tool_run(session, "whatweb", "https://example.com")

    assert task.policy_profile == "web_security"
    assert task.policy_reason is not None
    assert any(event.type is EventType.policy_decision_recorded for event in bus.history)


def test_ingest_nmap_xml_persists_technologies_and_evidence(tmp_path: Path) -> None:
    session = Session(name="ingest-test", capability=CapabilityName.web_security)
    bus = EventBus()
    orchestrator = AnalystOrchestrator(
        bus=bus,
        registry=PluginRegistry.with_defaults(),
        policy=SafetyPolicy(),
        graph=KnowledgeGraphEngine(),
        recommendations=RecommendationEngine(),
        store=SQLiteStore(tmp_path / "mcaoe.sqlite3"),
    )

    counts = orchestrator.ingest_nmap_xml(session, SAMPLE_NMAP_XML)

    assert counts["hosts"] == 1
    assert counts["services"] == 1
    assert counts["technologies"] >= 1
    assert session.evidence
    assert session.technologies
    assert orchestrator.graph.summary()["nodes"] >= 3


SAMPLE_WHATWEB_JSON = """
[
    {
        "target": "https://example.com",
        "plugins": {
            "nginx": {"version": "1.24.0"},
            "TLS": {"string": "enabled"}
        }
    }
]
"""

SAMPLE_NIKTO_OUTPUT = """
+ Target IP: 192.0.2.10
+ Target Hostname: example.local
+ Server: nginx/1.24.0
+ /: X-Frame-Options header not present.
+ /admin/: Directory indexing found.
"""

SAMPLE_FFUF_JSON = """
{
    "results": [
        {
            "url": "https://example.com/admin/",
            "status": 403,
            "length": 1234,
            "words": 120,
            "lines": 32
        },
        {
            "url": "https://example.com/healthz",
            "status": 200,
            "length": 42,
            "words": 4,
            "lines": 1
        }
    ]
}
"""


def test_ingest_whatweb_output_persists_technologies_and_recommendations(tmp_path: Path) -> None:
    session = Session(name="whatweb-test", capability=CapabilityName.web_security)
    orchestrator = AnalystOrchestrator(
        bus=EventBus(),
        registry=PluginRegistry.with_defaults(),
        policy=SafetyPolicy(),
        graph=KnowledgeGraphEngine(),
        recommendations=RecommendationEngine(),
        store=SQLiteStore(tmp_path / "mcaoe.sqlite3"),
    )

    counts = orchestrator.ingest_whatweb_output(session, SAMPLE_WHATWEB_JSON)

    assert counts["technologies"] == 2
    assert session.technologies
    assert any(technology.name == "nginx" for technology in session.technologies)
    assert any(recommendation.title == "Validate TLS posture" for recommendation in session.recommendations)


def test_ingest_nikto_output_persists_findings_and_recommendations(tmp_path: Path) -> None:
    session = Session(name="nikto-test", capability=CapabilityName.web_security)
    orchestrator = AnalystOrchestrator(
        bus=EventBus(),
        registry=PluginRegistry.with_defaults(),
        policy=SafetyPolicy(),
        graph=KnowledgeGraphEngine(),
        recommendations=RecommendationEngine(),
        store=SQLiteStore(tmp_path / "mcaoe.sqlite3"),
    )

    counts = orchestrator.ingest_nikto_output(session, SAMPLE_NIKTO_OUTPUT)

    assert counts["findings"] >= 2
    assert session.findings
    assert any(finding.title == "Missing X-Frame-Options header" for finding in session.findings)
    assert any(finding.title == "Directory indexing enabled" for finding in session.findings)
    assert any(recommendation.title == "Review higher-severity findings" for recommendation in session.recommendations)


def test_ingest_ffuf_output_persists_findings_and_recommendations(tmp_path: Path) -> None:
    session = Session(name="ffuf-test", capability=CapabilityName.web_security)
    orchestrator = AnalystOrchestrator(
        bus=EventBus(),
        registry=PluginRegistry.with_defaults(),
        policy=SafetyPolicy(),
        graph=KnowledgeGraphEngine(),
        recommendations=RecommendationEngine(),
        store=SQLiteStore(tmp_path / "mcaoe.sqlite3"),
    )

    counts = orchestrator.ingest_ffuf_output(session, SAMPLE_FFUF_JSON)

    assert counts["results"] == 2
    assert session.findings
    assert any(finding.title == "Restricted content discovered" for finding in session.findings)
    assert any(finding.title == "Interesting content discovered" for finding in session.findings)
    assert any(recommendation.title == "Review discovered content" for recommendation in session.recommendations)


def test_execute_planned_task_records_execution_audit_metadata(tmp_path: Path) -> None:
    class FakeProvider:
        async def execute(self, task: ExecutionTask) -> ExecutionResult:
            return ExecutionResult(
                task_id=uuid4(),
                exit_code=0,
                stdout="ok",
                stderr="",
                metadata={"backend": "fake-backend"},
            )

    session = Session(name="exec-audit-test", capability=CapabilityName.web_security)
    orchestrator = AnalystOrchestrator(
        bus=EventBus(),
        registry=PluginRegistry.with_defaults(),
        policy=SafetyPolicy(),
        graph=KnowledgeGraphEngine(),
        recommendations=RecommendationEngine(),
        store=SQLiteStore(tmp_path / "mcaoe.sqlite3"),
        provider=FakeProvider(),  # type: ignore[arg-type]
    )

    result = asyncio.run(
        orchestrator.execute_planned_task(
            session,
            ExecutionTask(command="echo", arguments=["hello"], timeout_seconds=10),
            approved_by_user=True,
        )
    )

    assert result["exit_code"] == 0
    assert session.commands
    command = session.commands[-1]
    assert command.backend == "fake-backend"
    assert command.started_at is not None
    assert command.completed_at is not None
    assert command.duration_seconds is not None
    assert command.duration_seconds >= 0
