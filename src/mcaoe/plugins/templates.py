from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from mcaoe.execution.provider import ExecutionTask
from mcaoe.models.domain import Session
from mcaoe.plugins.base import PluginMetadata


ArgumentFactory = Callable[[Session, str], list[str]]


@dataclass(slots=True)
class StaticCommandPlugin:
    metadata: PluginMetadata
    command: str
    argument_factory: ArgumentFactory
    timeout_seconds: int = 600
    requires_approval: bool = True

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
