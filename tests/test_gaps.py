from mcaoe.analysis.gaps import analyze_session_gaps
from mcaoe.models.domain import CapabilityName, Session


def test_gap_analysis_reports_missing_target_and_evidence() -> None:
    session = Session(name="gap-analysis-test", capability=CapabilityName.web_security)

    gaps = analyze_session_gaps(session)

    assert gaps.coverage_score < 100
    assert any(item.label == "Target not set" for item in gaps.items)
    assert any(item.label == "No evidence captured" for item in gaps.items)
    assert "Coverage score" in gaps.summary()