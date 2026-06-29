from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from mcaoe.core.workflow import evaluate_stage_gate
from mcaoe.core.events import Event, EventBus, EventType
from mcaoe.execution.provider import ExecutionProvider, ExecutionTask
from mcaoe.graph.engine import KnowledgeGraphEngine
from mcaoe.database.store import SQLiteStore
from mcaoe.models.domain import CommandExecution, Evidence, Finding, Session, Technology, Unknown

from mcaoe.policy import SafetyPolicy
from mcaoe.plugins.registry import PluginRegistry
from mcaoe.recommendations.engine import RecommendationEngine


@dataclass(slots=True)
class AnalystOrchestrator:
    bus: EventBus
    registry: PluginRegistry
    policy: SafetyPolicy
    graph: KnowledgeGraphEngine
    recommendations: RecommendationEngine
    store: SQLiteStore
    provider: ExecutionProvider | None = None

    def plan_tool_run(self, session: Session, plugin_name: str, target: str) -> ExecutionTask:
        plugin = self.registry.get(plugin_name)
        build_task = getattr(plugin, "build_task", None)
        if build_task is None:
            raise TypeError(f"Plugin {plugin_name!r} does not provide build_task()")

        task = build_task(session, target)
        decision = self.policy.evaluate(task)
        task.policy_profile = decision.policy_profile
        task.policy_reason = decision.reason
        task.risk_level = decision.risk_level
        self._emit_event(
            Event(
                type=EventType.policy_decision_recorded,
                payload={
                    "plugin": plugin_name,
                    "command": task.command,
                    "risk_level": decision.risk_level,
                    "allowed": decision.allowed,
                    "requires_approval": decision.requires_approval,
                    "policy_profile": decision.policy_profile,
                    "reason": decision.reason,
                },
            )
        )
        if not decision.allowed:
            raise PermissionError(f"Task blocked by safety policy: {decision.reason}")
        return task

    def _emit_event(self, event: Event) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(self.bus.publish(event))
        else:
            loop.create_task(self.bus.publish(event))

    async def execute_planned_task(
        self,
        session: Session,
        task: ExecutionTask,
        approved_by_user: bool = False,
    ) -> dict[str, Any]:
        if self.provider is None:
            raise RuntimeError("No execution provider configured")
        decision = self.policy.evaluate(task)
        task.policy_profile = decision.policy_profile
        task.policy_reason = decision.reason
        task.risk_level = decision.risk_level
        if not decision.allowed:
            raise PermissionError(f"Task blocked by safety policy: {decision.reason}")
        if decision.requires_approval and not approved_by_user:
            raise PermissionError(f"Task requires explicit approval: {decision.reason}")

        started_at = datetime.now(timezone.utc)
        await self.bus.publish(Event(type=EventType.task_started, payload={"command": task.command, "arguments": task.arguments}))
        result = await self.provider.execute(task)
        completed_at = datetime.now(timezone.utc)
        
        stats = {}
        if task.plugin_name and task.plugin_name in self.registry.plugins:
            plugin = self.registry.plugins[task.plugin_name]
            if hasattr(plugin, "ingest_output"):
                stats = plugin.ingest_output(session, result.stdout or "", result.stderr or "", self)
                
        backend = result.metadata.get("backend") or self.provider.__class__.__name__
        session.commands.append(
            CommandExecution(
                command=task.command,
                arguments=list(task.arguments),
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
                approved_by_user=approved_by_user,
                timeout_seconds=task.timeout_seconds,
                backend=str(backend),
                risk_level=task.risk_level,
                policy_profile=task.policy_profile,
                policy_reason=task.policy_reason,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=(completed_at - started_at).total_seconds(),
            )
        )
        await self.bus.publish(Event(type=EventType.task_completed, payload={"command": task.command, "exit_code": result.exit_code}))
        self.store.save_session(session)
        return {"exit_code": result.exit_code, "stdout": result.stdout, "stderr": result.stderr, "stats": stats}

    async def advance_workflow(
        self,
        session: Session,
        stage_value: str,
        approved_by_user: bool = False,
        force: bool = False,
    ) -> None:
        from mcaoe.models.domain import WorkflowStage

        next_stage = WorkflowStage(stage_value)
        gate = evaluate_stage_gate(session, next_stage)
        if not gate.allowed:
            if not (force and approved_by_user):
                raise PermissionError(f"Workflow transition blocked: {gate.reason}")
            session.workflow.notes.append(f"Override applied for stage {stage_value}: {gate.reason}")

        session.workflow.stage = next_stage
        await self.bus.publish(
            Event(
                type=EventType.workflow_transitioned,
                payload={
                    "stage": stage_value,
                    "capability": session.workflow.capability.value,
                    "gate_allowed": gate.allowed,
                    "gate_reason": gate.reason,
                    "gate_coverage_score": gate.coverage_score,
                    "override": bool(force and approved_by_user and not gate.allowed),
                },
            )
        )
        self.store.save_session(session)

    async def record_target(self, session: Session, target: str) -> None:
        if target not in session.targets:
            session.targets.append(target)
        session.workflow.target = target
        await self.bus.publish(Event(type=EventType.target_added, payload={"target": target}))
        self.store.save_session(session)



    def add_finding(self, session: Session, title: str, description: str, severity: str = "informational") -> None:
        finding = Finding(title=title, description=description, severity=severity)
        session.findings.append(finding)
        self.graph.add_finding(finding)
        self._emit_event(Event(type=EventType.recommendation_created, payload={"finding": title, "severity": severity}))
        session.recommendations = self.recommendations.generate(session)
        self.store.save_session(session)

    def add_note(self, session: Session, note: str) -> None:
        session.workflow.notes.append(note)
        self.store.save_session(session)

    def attach_evidence(self, session: Session, source: str, summary: str, payload: dict[str, Any] | None = None) -> None:
        evidence = Evidence(source=source, summary=summary, payload=payload or {})
        session.evidence.append(evidence)
        self.graph.add_evidence(evidence)
        self._emit_event(Event(type=EventType.evidence_added, payload={"source": source, "summary": summary}))
        self.store.save_session(session)

    def add_unknown(self, session: Session, label: str, details: str | None = None, priority: int = 3) -> None:
        unknown = Unknown(label=label, details=details, priority=priority)
        session.unknowns.append(unknown)
        self.graph.add_unknown(unknown)
        self._emit_event(Event(type=EventType.unknown_detected, payload={"label": label, "priority": priority}))
        session.recommendations = self.recommendations.generate(session)
        self.store.save_session(session)

    def summarize(self, session: Session) -> dict[str, int]:
        return {
            "hosts": len(session.hosts),
            "services": len(session.services),
            "findings": len(session.findings),
            "recommendations": len(session.recommendations),
            "unknowns": len(session.unknowns),
        }
