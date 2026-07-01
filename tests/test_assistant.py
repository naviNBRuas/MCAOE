from unittest.mock import MagicMock, patch

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


def test_assistant_llm_disabled_by_default() -> None:
    assistant = AnalystAssistant()
    assert assistant.llm_enabled is False
    assert assistant.llm_provider is None


def test_assistant_enable_llm_sets_provider() -> None:
    assistant = AnalystAssistant()
    assistant.enable_llm("gemini")
    assert assistant.llm_enabled is True
    assert assistant.llm_provider is not None
    assert assistant.llm_provider.name() == "gemini"


def test_assistant_llm_summarize_included_when_enabled() -> None:
    mock_provider = MagicMock()
    mock_provider.name.return_value = "gemini"
    mock_provider.generate.return_value = "AI-generated session summary."

    assistant = AnalystAssistant(llm_provider=mock_provider, llm_enabled=True)
    session = Session(name="llm-test", capability=CapabilityName.web_security)

    summary = assistant.summarize(session)
    assert "AI-generated session summary." in summary
    assert "LLM back-end: gemini" in summary


def test_assistant_llm_failure_falls_back_to_rule_based() -> None:
    mock_provider = MagicMock()
    mock_provider.name.return_value = "gemini"
    mock_provider.generate.side_effect = RuntimeError("API error")

    assistant = AnalystAssistant(llm_provider=mock_provider, llm_enabled=True)
    session = Session(name="fallback-test", capability=CapabilityName.web_security)

    summary = assistant.summarize(session)
    assert "Session: fallback-test" in summary
    assert "Capability profile: web_security" in summary


def test_assistant_enable_llm_with_invalid_provider_sets_flag() -> None:
    with patch("mcaoe.ai.assistant.create_provider", side_effect=RuntimeError("no key")):
        assistant = AnalystAssistant()
        assistant.enable_llm("gemini")
        assert assistant.llm_enabled is False


def test_assistant_next_steps_returns_limited_recommendations() -> None:
    session = Session(name="steps-test", capability=CapabilityName.web_security)
    session.recommendations.append(
        Recommendation(title="Step A", rationale="First step", confidence=0.9, priority=1)
    )
    session.recommendations.append(
        Recommendation(title="Step B", rationale="Second step", confidence=0.8, priority=2)
    )

    assistant = AnalystAssistant()
    steps = assistant.next_steps(session, limit=1)
    assert len(steps) == 1
    assert "Step A" in steps[0]


def test_assistant_contextual_hint_format() -> None:
    rec = Recommendation(title="Test", rationale="Because.", confidence=0.75, priority=2)
    assistant = AnalystAssistant()
    hint = assistant.contextual_hint(rec)
    assert "Test" in hint
    assert "75%" in hint
    assert "priority 2" in hint


def test_assistant_summary_includes_coverage() -> None:
    session = Session(name="cov-test", capability=CapabilityName.web_security)
    assistant = AnalystAssistant()
    summary = assistant.summarize(session)
    assert "Coverage score:" in summary
