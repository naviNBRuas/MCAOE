from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from mcaoe.execution.provider import ExecutionTask
from mcaoe.models.domain import Session
from mcaoe.plugins.base import PluginMetadata


@dataclass(slots=True)
class NmapPlugin:
    metadata: PluginMetadata = field(
        default_factory=lambda: PluginMetadata(
            name="nmap",
            description="Structured network discovery and service fingerprinting.",
            capability_tags=["infrastructure", "web_security", "enumeration"],
            risk_level="medium",
        )
    )

    def build_task(self, session: Session, target: str) -> ExecutionTask:
        return ExecutionTask(
            command="nmap",
            arguments=["-sV", "-oX", "-", target],
            timeout_seconds=600,
            requires_approval=True,
            profile=session.capability.value,
            plugin_name=self.metadata.name,
            risk_level=self.metadata.risk_level,
        )
