from mcaoe.models.domain import CapabilityName, Finding, Session, Service, Technology
from mcaoe.recommendations.engine import RecommendationEngine


def test_recommendations_include_capability_profile_guidance() -> None:
    session = Session(name="profile-test", capability=CapabilityName.web_security)
    session.services.append(Service(host_id=session.id, name="http", port=80, version=None))

    recommendations = RecommendationEngine().generate(session)

    titles = [recommendation.title for recommendation in recommendations]
    assert any("Run version detection" in title for title in titles)
    assert any("toolkit" in title.lower() for title in titles)
    assert session.workflow.stage.value == "discovery"


def test_recommendations_include_technology_guidance() -> None:
    session = Session(name="tech-test", capability=CapabilityName.web_security)
    session.technologies.extend(
        [
            Technology(name="nginx"),
            Technology(name="TLS"),
        ]
    )

    recommendations = RecommendationEngine().generate(session)

    titles = [recommendation.title for recommendation in recommendations]
    assert any("TLS posture" in title for title in titles)
    assert any("web server fingerprinting" in title.lower() for title in titles)


def test_recommendations_include_discovery_guidance() -> None:
    session = Session(name="ffuf-guidance-test", capability=CapabilityName.web_security)
    session.findings.append(
        Finding(
            title="Interesting content discovered",
            description="/healthz returned 200",
            severity="informational",
        )
    )

    recommendations = RecommendationEngine().generate(session)

    titles = [recommendation.title for recommendation in recommendations]
    assert any("discovered content" in title.lower() for title in titles)


def test_recommendations_include_gap_guidance() -> None:
    session = Session(name="gap-test", capability=CapabilityName.web_security)

    recommendations = RecommendationEngine().generate(session)

    titles = [recommendation.title for recommendation in recommendations]
    assert any("target" in title.lower() for title in titles)
    assert any("discovery" in title.lower() for title in titles)
