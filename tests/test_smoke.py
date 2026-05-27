from mcaoe.core.events import EventBus
from mcaoe.core.workflow import WorkflowEngine
from mcaoe.models.domain import CapabilityName, Session
from mcaoe.recommendations.engine import RecommendationEngine
from mcaoe.workflows import build_mvp_capability_profiles


def test_scaffold_imports_and_generates_recommendations() -> None:
    session = Session(name="smoke", capability=CapabilityName.web_security)
    bus = EventBus()
    workflow = WorkflowEngine(bus=bus)
    recommendations = RecommendationEngine().generate(session)
    profiles = build_mvp_capability_profiles()

    assert workflow.state.stage.value == "discovery"
    assert recommendations
    assert profiles
