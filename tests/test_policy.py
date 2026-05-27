from mcaoe.execution.provider import ExecutionTask
from mcaoe.policy import SafetyPolicy


def test_policy_blocks_dangerous_pattern() -> None:
    policy = SafetyPolicy()
    task = ExecutionTask(command="sqlmap", arguments=["-u", "https://example.com"], profile="web_security", risk_level="high")

    decision = policy.evaluate(task)

    assert decision.allowed is False
    assert "Blocked by safety pattern" in decision.reason


def test_policy_blocks_high_risk_for_dfir_profile() -> None:
    policy = SafetyPolicy()
    task = ExecutionTask(command="nmap", arguments=["-sV", "example.com"], profile="dfir", risk_level="high")

    decision = policy.evaluate(task)

    assert decision.allowed is False
    assert "not allowed" in decision.reason
    assert decision.policy_profile == "dfir"


def test_policy_allows_medium_risk_for_web_security_with_approval() -> None:
    policy = SafetyPolicy()
    task = ExecutionTask(command="whatweb", arguments=["https://example.com"], profile="web_security", risk_level="medium")

    decision = policy.evaluate(task)

    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.policy_profile == "web_security"


def test_safety_policy_blocks_dash_a_pattern() -> None:
    policy = SafetyPolicy()
    blocked = ExecutionTask(command="nmap", arguments=["-A", "127.0.0.1"], profile="infrastructure", risk_level="medium")

    assert not policy.is_allowed(blocked)
    assert policy.requires_approval(blocked)
