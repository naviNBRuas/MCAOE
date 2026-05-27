from __future__ import annotations

from dataclasses import dataclass, field

from mcaoe.core.events import Event


@dataclass(slots=True)
class EventJournal:
    events: list[Event] = field(default_factory=list)

    def append(self, event: Event) -> None:
        self.events.append(event)

    def as_dicts(self) -> list[dict[str, object]]:
        return [
            {
                "type": event.type.value,
                "payload": event.payload,
                "id": event.id,
                "created_at": event.created_at.isoformat(),
            }
            for event in self.events
        ]

    def filter_by_type(self, event_type: str) -> list[Event]:
        return [event for event in self.events if event.type.value == event_type]

    def timeline(self) -> list[str]:
        return [f"{event.created_at.isoformat()} | {event.type.value}: {event.payload}" for event in self.events]
