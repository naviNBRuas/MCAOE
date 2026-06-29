from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from mcaoe.execution.orchestrator import AnalystOrchestrator

from mcaoe.execution.provider import ExecutionTask
from mcaoe.models.domain import Session
from mcaoe.plugins.base import PluginMetadata


ArgumentFactory = Callable[[Session, str], list[str]]
IngestCallback = Callable[[Session, str, str, "AnalystOrchestrator"], dict[str, int]]


@dataclass(slots=True)
class StaticCommandPlugin:
    metadata: PluginMetadata
    command: str
    argument_factory: ArgumentFactory
    timeout_seconds: int = 600
    requires_approval: bool = True
    ingest_callback: IngestCallback | None = None

    def build_task(self, session: Session, target: str) -> ExecutionTask:
        return ExecutionTask(
            command=self.command,
            arguments=self.argument_factory(session, target),
            timeout_seconds=self.timeout_seconds,
            requires_approval=self.requires_approval,
            profile=session.capability.value,
            plugin_name=self.metadata.name,
            risk_level=self.metadata.risk_level,
        )

    def ingest_output(self, session: Session, stdout: str, stderr: str, orchestrator: "AnalystOrchestrator") -> dict[str, int]:
        if self.ingest_callback:
            return self.ingest_callback(session, stdout, stderr, orchestrator)
        return {}
