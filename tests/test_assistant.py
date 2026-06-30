from mcaoe.ai.assistant import AnalystAssistant
from mcaoe.models.domain import CapabilityName, Finding, Recommendation, Session, Technology, Unknown


def test_assistant_session_card_and_highlights() -> None:
    session = Session(name="summary-test", capability=CapabilityName.web_security)
    session.workflow.target = "https://example.com"
    session.targets.append("https://example.com")
    session.technologies.append(Technology(name="nginx", confidence=0.9))
    session.findings.append(Finding(title="Restricted content discovered", description="/admin/", severity="low"))
    session.unknowns.append(Unknown(label="TLS configuration", details="Not yet validated", priority=2))
    session.recommendations.append(
        Recommendation(
            title="Review discovered content",
            rationale="Fuzzing exposed restricted content.",
            confidence=0.84,
            priority=2,
            workflow_relevance="enumeration",
        )
    )

    assistant = AnalystAssistant()
    card: dict[str, object] = assistant.session_card(session)

    assert str(card["session"]) == "summary-test"
    assert str(card["target"]) == "https://example.com"
    assert isinstance(card["counts"], dict)
    assert card["counts"].get("targets") == 1
    assert isinstance(card["coverage_score"], int) and card["coverage_score"] < 100
    assert card["counts"]["technologies"] == 1
    assert card["top_recommendations"]
    assert any("Key findings" in highlight for highlight in assistant.highlights(session))
    assert any("Open coverage gaps" in highlight for highlight in assistant.highlights(session))
    assert "Target: https://example.com" in assistant.summarize(session)
    assert "Coverage score:" in assistant.summarize(session)
    assert "Highlights:" in assistant.summarize(session)