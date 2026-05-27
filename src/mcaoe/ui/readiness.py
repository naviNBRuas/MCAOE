from __future__ import annotations

from dataclasses import dataclass, field

from mcaoe.analysis.gaps import analyze_session_gaps
from mcaoe.core.workflow import STAGE_SEQUENCE, evaluate_stage_gate
from mcaoe.models.domain import Session, WorkflowStage


@dataclass(slots=True)
class StageChecklistItem:
    stage: WorkflowStage
    status: str
    allowed: bool = True
    coverage_score: int = 0
    reasons: list[str] = field(default_factory=list)


def build_stage_checklist(session: Session) -> list[StageChecklistItem]:
    items: list[StageChecklistItem] = []
    current_index = STAGE_SEQUENCE.index(session.workflow.stage)

    for index, stage in enumerate(STAGE_SEQUENCE):
        if index < current_index:
            items.append(StageChecklistItem(stage=stage, status="completed"))
            continue
        if stage is session.workflow.stage:
            items.append(StageChecklistItem(stage=stage, status="current"))
            continue

        gate = evaluate_stage_gate(session, stage)
        items.append(
            StageChecklistItem(
                stage=stage,
                status="ready" if gate.allowed else "blocked",
                allowed=gate.allowed,
                coverage_score=gate.coverage_score,
                reasons=list(gate.reasons),
            )
        )

    return items


def render_readiness_scorecard(session: Session, max_reasons_per_stage: int = 2) -> list[str]:
    gaps = analyze_session_gaps(session)
    reporting_gate = evaluate_stage_gate(session, WorkflowStage.reporting)
    lines: list[str] = [
        f"Readiness scorecard: coverage={gaps.coverage_score}/100 | open_gaps={gaps.open_count}",
        f"Reporting gate: {'PASS' if reporting_gate.allowed else 'BLOCKED'} | coverage={reporting_gate.coverage_score}/100",
    ]

    if reporting_gate.reasons:
        for reason in reporting_gate.reasons[:max_reasons_per_stage]:
            lines.append(f"  ! reporting: {reason}")

    lines.append("Stage checklist:")
    for item in build_stage_checklist(session):
        icon = {
            "completed": "✓",
            "current": "•",
            "ready": "→",
            "blocked": "✗",
        }.get(item.status, "?")
        lines.append(f"  {icon} {item.stage.value}: {item.status}")
        if item.status == "blocked" and item.reasons:
            for reason in item.reasons[:max_reasons_per_stage]:
                lines.append(f"    - {reason}")

    return lines