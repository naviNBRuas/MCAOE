from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from mcaoe.execution.orchestrator import AnalystOrchestrator

from mcaoe.execution.provider import ExecutionTask
from mcaoe.models.domain import Session


@dataclass(slots=True)
class PluginMetadata:
    name: str
    description: str
    capability_tags: list[str]
    risk_level: str = "medium"


class Plugin(Protocol):
    metadata: PluginMetadata

    def build_task(self, session: Session, target: str) -> ExecutionTask: ...
    
    def ingest_output(self, session: Session, stdout: str, stderr: str, orchestrator: "AnalystOrchestrator") -> dict[str, int]: ...
