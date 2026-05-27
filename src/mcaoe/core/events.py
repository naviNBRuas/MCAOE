from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class EventType(str, Enum):
    target_added = "target_added"
    task_started = "task_started"
    task_completed = "task_completed"
    port_discovered = "port_discovered"
    service_identified = "service_identified"
    technology_detected = "technology_detected"
    unknown_detected = "unknown_detected"
    recommendation_created = "recommendation_created"
    ai_analysis_generated = "ai_analysis_generated"
    evidence_added = "evidence_added"
    workflow_transitioned = "workflow_transitioned"
    policy_decision_recorded = "policy_decision_recorded"


@dataclass(slots=True)
class Event:
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: str(uuid4()))


EventHandler = Callable[[Event], Awaitable[None] | None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[EventHandler]] = {event: [] for event in EventType}
        self._history: list[Event] = []

    @property
    def history(self) -> list[Event]:
        return list(self._history)

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        for event_type in EventType:
            self.subscribe(event_type, handler)

    async def publish(self, event: Event) -> None:
        self._history.append(event)
        handlers = list(self._subscribers.get(event.type, []))
        for handler in handlers:
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result
