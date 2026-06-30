from mcaoe.profiles.catalog import build_profiles
from mcaoe.models.domain import CapabilityName, WorkflowStage


def test_build_profiles_returns_all_capabilities() -> None:
    profiles = build_profiles()
    names = {profile.name for profile in profiles}
    assert CapabilityName.web_security in names
    assert CapabilityName.infrastructure in names
    assert CapabilityName.active_directory in names
    assert CapabilityName.cloud in names
    assert CapabilityName.dfir in names
    assert CapabilityName.threat_hunting in names
    assert CapabilityName.malware_analysis in names
    assert CapabilityName.osint in names
    assert CapabilityName.ctf in names


def test_build_profiles_web_security_has_recommended_plugins() -> None:
    profiles = {profile.name: profile for profile in build_profiles()}
    web = profiles[CapabilityName.web_security]
    assert "nmap" in web.recommended_plugins
    assert "whatweb" in web.recommended_plugins
    assert "nikto" in web.recommended_plugins
    assert "ffuf" in web.recommended_plugins
    assert "gobuster" in web.recommended_plugins
    assert web.default_workflow_stage == WorkflowStage.discovery


def test_build_profiles_osint_has_low_risk_plugins() -> None:
    profiles = {profile.name: profile for profile in build_profiles()}
    osint = profiles[CapabilityName.osint]
    assert "subfinder" in osint.recommended_plugins
    assert "amass" in osint.recommended_plugins
    assert osint.default_workflow_stage == WorkflowStage.discovery


def test_build_profiles_dfir_starts_at_analysis() -> None:
    profiles = {profile.name: profile for profile in build_profiles()}
    dfir = profiles[CapabilityName.dfir]
    assert dfir.default_workflow_stage == WorkflowStage.analysis
