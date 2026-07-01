from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from traceback import format_exc
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


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
    handler_failed = "handler_failed"


@dataclass(slots=True)
class Event:
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: str(uuid4()))


EventHandler = Callable[[Event], Awaitable[None] | None]

ErrorHandler = Callable[[Event, Exception], Awaitable[None] | None]


@dataclass(slots=True)
class DeadLetter:
    event: Event
    error: str
    traceback: str
    handler_name: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def error_boundary(handler: EventHandler, on_error: ErrorHandler | None = None) -> EventHandler:
    """Wrap an event handler so that exceptions are logged and sent to an error handler."""

    @functools.wraps(handler)
    async def safe_handler(event: Event) -> None:
        try:
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:
            name = getattr(handler, "__name__", str(handler))
            logger.exception("Handler %s failed processing event %s", name, event.type)
            if on_error is not None:
                try:
                    result = on_error(event, exc)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    logger.exception("Error handler itself failed for event %s", event.type)

    return safe_handler


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[EventHandler]] = {event: [] for event in EventType}
        self._history: list[Event] = []
        self._dead_letter_queue: list[DeadLetter] = []
        self._on_handler_error: ErrorHandler | None = self._default_error_handler

    @property
    def history(self) -> list[Event]:
        return list(self._history)

    @property
    def dead_letter_queue(self) -> list[DeadLetter]:
        return list(self._dead_letter_queue)

    async def _default_error_handler(self, event: Event, exc: Exception) -> None:
        self._dead_letter_queue.append(
            DeadLetter(
                event=event,
                error=str(exc),
                traceback=format_exc(),
                handler_name="unknown",
            )
        )
        logger.warning("Event %s moved to dead-letter queue: %s", event.type, exc)

    def set_on_handler_error(self, handler: ErrorHandler) -> None:
        self._on_handler_error = handler

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        safe = error_boundary(handler, on_error=self._on_handler_error)
        self._subscribers[event_type].append(safe)

    def subscribe_all(self, handler: EventHandler) -> None:
        safe = error_boundary(handler, on_error=self._on_handler_error)
        for event_type in EventType:
            self._subscribers[event_type].append(safe)

    def subscribe_raw(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe without wrapping in an error boundary. Use for direct control."""
        self._subscribers[event_type].append(handler)

    def subscribe_all_raw(self, handler: EventHandler) -> None:
        for event_type in EventType:
            self.subscribe_raw(event_type, handler)

    async def publish(self, event: Event) -> None:
        self._history.append(event)
        handlers = list(self._subscribers.get(event.type, []))
        for handler in handlers:
            result = handler(event)
            if asyncio.iscoroutine(result):
                await result

    def drain_dead_letter_queue(self) -> list[DeadLetter]:
        items = list(self._dead_letter_queue)
        self._dead_letter_queue.clear()
        return items
