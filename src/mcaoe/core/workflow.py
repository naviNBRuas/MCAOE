from __future__ import annotations

from dataclasses import dataclass, field

from mcaoe.analysis.gaps import analyze_session_gaps
from mcaoe.core.events import Event, EventBus, EventType
from mcaoe.models.domain import Session, WorkflowStage, WorkflowState


STAGE_SEQUENCE: tuple[WorkflowStage, ...] = (
    WorkflowStage.discovery,
    WorkflowStage.enumeration,
    WorkflowStage.fingerprinting,
    WorkflowStage.validation,
    WorkflowStage.correlation,
    WorkflowStage.analysis,
    WorkflowStage.reporting,
)


@dataclass(slots=True)
class WorkflowGateResult:
    allowed: bool
    next_stage: WorkflowStage
    reasons: list[str] = field(default_factory=list)
    coverage_score: int = 0

    @property
    def reason(self) -> str:
        if not self.reasons:
            return "Workflow gate passed"
        return "; ".join(self.reasons)


def evaluate_stage_gate(session: Session, next_stage: WorkflowStage) -> WorkflowGateResult:
    coverage = analyze_session_gaps(session)
    reasons: list[str] = []

    current_idx = STAGE_SEQUENCE.index(session.workflow.stage)
    next_idx = STAGE_SEQUENCE.index(next_stage)
    if next_idx < current_idx:
        reasons.append(f"Backward transition from {session.workflow.stage.value} to {next_stage.value} is blocked")

    if next_stage is WorkflowStage.enumeration:
        if not session.workflow.target:
            reasons.append("Set a target before entering enumeration")

    elif next_stage is WorkflowStage.fingerprinting:
        if not session.hosts and not session.services:
            reasons.append("Discover at least one host or service before fingerprinting")

    elif next_stage is WorkflowStage.validation:
        if not session.technologies:
            reasons.append("Capture technologies before validation")
        if not session.evidence:
            reasons.append("Collect evidence before validation")

    elif next_stage is WorkflowStage.correlation:
        if not session.evidence:
            reasons.append("Collect evidence before correlation")
        if not (session.findings or session.unknowns or session.technologies):
            reasons.append("Need findings, unknowns, or technologies before correlation")

    elif next_stage is WorkflowStage.analysis:
        if not session.evidence:
            reasons.append("Collect evidence before analysis")
        if not (session.findings or session.unknowns):
            reasons.append("Need findings or unknowns before analysis")

    elif next_stage is WorkflowStage.reporting:
        if not session.evidence:
            reasons.append("Collect evidence before reporting")
        if not session.commands:
            reasons.append("Execute and record at least one command before reporting")
        if not (session.findings or session.unknowns or session.technologies):
            reasons.append("Need findings, unknowns, or technologies before reporting")
        if coverage.coverage_score < 80:
            reasons.append(f"Coverage score {coverage.coverage_score}/100 is below reporting threshold (80)")

    return WorkflowGateResult(
        allowed=not reasons,
        next_stage=next_stage,
        reasons=reasons,
        coverage_score=coverage.coverage_score,
    )


@dataclass(slots=True)
class WorkflowEngine:
    bus: EventBus
    state: WorkflowState = field(default_factory=WorkflowState)

    async def advance(self, next_stage: WorkflowStage) -> WorkflowState:
        self.state.stage = next_stage
        await self.bus.publish(
            Event(
                type=EventType.workflow_transitioned,
                payload={"stage": next_stage.value, "target": self.state.target},
            )
        )
        return self.state
