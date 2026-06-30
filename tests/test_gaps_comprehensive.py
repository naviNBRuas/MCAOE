from mcaoe.analysis.gaps import analyze_session_gaps
from mcaoe.models.domain import CapabilityName, Session, Host, Service, Technology, Evidence, Unknown


def test_gap_analysis_full_coverage() -> None:
    session = Session(name="full-coverage", capability=CapabilityName.web_security)
    session.workflow.target = "https://example.com"
    session.hosts.append(Host(address="192.0.2.1"))
    session.services.append(Service(host_id=session.id, name="http", port=80, version="1.1"))
    session.technologies.append(Technology(name="nginx", confidence=0.9))
    session.technologies.append(Technology(name="TLS", confidence=0.8))
    session.evidence.append(Evidence(source="manual", summary="baseline"))

    gaps = analyze_session_gaps(session)

    assert gaps.coverage_score == 100
    assert len(gaps.items) == 0


def test_gap_analysis_missing_target() -> None:
    session = Session(name="no-target", capability=CapabilityName.web_security)
    gaps = analyze_session_gaps(session)
    assert any(item.label == "Target not set" for item in gaps.items)
    assert gaps.coverage_score <= 80


def test_gap_analysis_missing_versions() -> None:
    session = Session(name="no-versions", capability=CapabilityName.web_security)
    session.workflow.target = "https://example.com"
    session.hosts.append(Host(address="192.0.2.1"))
    session.services.append(Service(host_id=session.id, name="http", port=80, version=None))
    session.evidence.append(Evidence(source="manual", summary="baseline"))
    session.technologies.append(Technology(name="nginx", confidence=0.9))

    gaps = analyze_session_gaps(session)

    assert any(item.label == "Service versions missing" for item in gaps.items)


def test_gap_analysis_unverified_tls() -> None:
    session = Session(name="tls-gap", capability=CapabilityName.web_security)
    session.workflow.target = "https://example.com"
    session.hosts.append(Host(address="192.0.2.1"))
    session.services.append(Service(host_id=session.id, name="https", port=443, version="1.1"))
    session.evidence.append(Evidence(source="manual", summary="baseline"))

    gaps = analyze_session_gaps(session)

    assert any(item.label == "TLS posture unverified" for item in gaps.items)


def test_gap_analysis_open_unknowns() -> None:
    session = Session(name="unknowns", capability=CapabilityName.web_security)
    session.workflow.target = "https://example.com"
    session.hosts.append(Host(address="192.0.2.1"))
    session.evidence.append(Evidence(source="manual", summary="baseline"))
    session.technologies.append(Technology(name="nginx", confidence=0.9))
    session.unknowns.append(Unknown(label="Suspicious header", priority=2))

    gaps = analyze_session_gaps(session)

    assert any(item.label == "Open unknowns remain" for item in gaps.items)
    assert gaps.coverage_score < 100


def test_gap_analysis_no_evidence() -> None:
    session = Session(name="no-evidence", capability=CapabilityName.web_security)
    session.workflow.target = "https://example.com"
    session.hosts.append(Host(address="192.0.2.1"))

    gaps = analyze_session_gaps(session)

    assert any(item.label == "No evidence captured" for item in gaps.items)


def test_gap_summary_has_no_gaps_message() -> None:
    session = Session(name="summary", capability=CapabilityName.web_security)
    gaps = analyze_session_gaps(session)
    summary = gaps.summary()
    assert "Coverage score" in summary
    assert gaps.items
