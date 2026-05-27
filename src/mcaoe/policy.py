from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from mcaoe.execution.provider import ExecutionTask


DANGEROUS_PATTERNS = (
    "--script",
    "-A",
    "--traceroute",
    "--data",
    "--post-data",
    "sqlmap",
    "hydra",
    "medusa",
    "john",
    "hashcat",
)

RISK_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


@dataclass(slots=True)
class PolicyProfile:
    name: str
    allowed_risk_levels: set[str] = field(default_factory=lambda: {"low", "medium"})
    require_approval_at_or_above: str = "low"


@dataclass(slots=True)
class PolicyDecision:
    allowed: bool
    requires_approval: bool
    risk_level: str
    policy_profile: str
    reason: str


DEFAULT_POLICY_PROFILES: dict[str, PolicyProfile] = {
    "web_security": PolicyProfile(name="web_security", allowed_risk_levels={"low", "medium"}, require_approval_at_or_above="low"),
    "infrastructure": PolicyProfile(name="infrastructure", allowed_risk_levels={"low", "medium"}, require_approval_at_or_above="low"),
    "active_directory": PolicyProfile(name="active_directory", allowed_risk_levels={"low", "medium"}, require_approval_at_or_above="low"),
    "cloud": PolicyProfile(name="cloud", allowed_risk_levels={"low", "medium"}, require_approval_at_or_above="low"),
    "osint": PolicyProfile(name="osint", allowed_risk_levels={"low", "medium"}, require_approval_at_or_above="medium"),
    "ctf": PolicyProfile(name="ctf", allowed_risk_levels={"low", "medium", "high"}, require_approval_at_or_above="low"),
    "dfir": PolicyProfile(name="dfir", allowed_risk_levels={"low"}, require_approval_at_or_above="low"),
    "threat_hunting": PolicyProfile(name="threat_hunting", allowed_risk_levels={"low"}, require_approval_at_or_above="low"),
    "malware_analysis": PolicyProfile(name="malware_analysis", allowed_risk_levels={"low", "medium"}, require_approval_at_or_above="low"),
}


@dataclass(slots=True)
class SafetyPolicy:
    require_explicit_approval: bool = True
    profiles: dict[str, PolicyProfile] = field(default_factory=lambda: dict(DEFAULT_POLICY_PROFILES))

    def evaluate(self, task: ExecutionTask) -> PolicyDecision:
        command_text = " ".join([task.command, *task.arguments]).lower()
        risk_level = _normalize_risk_level(task.risk_level)
        profile_name = task.profile or "web_security"
        profile = self.profiles.get(profile_name) or PolicyProfile(name=profile_name)

        dangerous = next((pattern for pattern in DANGEROUS_PATTERNS if pattern in command_text), None)
        if dangerous is not None:
            return PolicyDecision(
                allowed=False,
                requires_approval=True,
                risk_level=risk_level,
                policy_profile=profile.name,
                reason=f"Blocked by safety pattern: {dangerous}",
            )

        if risk_level not in profile.allowed_risk_levels:
            allowed_levels = ", ".join(sorted(profile.allowed_risk_levels))
            return PolicyDecision(
                allowed=False,
                requires_approval=True,
                risk_level=risk_level,
                policy_profile=profile.name,
                reason=f"Risk level {risk_level} is not allowed for profile {profile.name}. Allowed: {allowed_levels}",
            )

        approval_threshold = _normalize_risk_level(profile.require_approval_at_or_above)
        risk_requires_approval = RISK_ORDER[risk_level] >= RISK_ORDER[approval_threshold]
        requires_approval = self.require_explicit_approval or task.requires_approval or risk_requires_approval
        reason = (
            f"Allowed under profile {profile.name} with risk={risk_level}; "
            f"approval={'required' if requires_approval else 'not required'}"
        )
        return PolicyDecision(
            allowed=True,
            requires_approval=requires_approval,
            risk_level=risk_level,
            policy_profile=profile.name,
            reason=reason,
        )

    def is_allowed(self, task: ExecutionTask) -> bool:
        return self.evaluate(task).allowed

    def requires_approval(self, task: ExecutionTask) -> bool:
        return self.evaluate(task).requires_approval


def _normalize_risk_level(value: str | None) -> str:
    if not value:
        return "medium"
    lowered = value.lower().strip()
    if lowered in RISK_ORDER:
        return lowered
    return "medium"
