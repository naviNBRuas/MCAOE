from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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
