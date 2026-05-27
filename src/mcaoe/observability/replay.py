from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from mcaoe.core.events import Event
from mcaoe.models.domain import Session


@dataclass(slots=True)
class ReplayEntry:
    timestamp: datetime
    event_type: str
    description: str


@dataclass(slots=True)
class SessionReplay:
    session_name: str
    entries: list[ReplayEntry]

    @classmethod
    def from_session(cls, session: Session, events: list[Event]) -> "SessionReplay":
        return cls(session_name=session.name, entries=[_event_to_entry(event) for event in events])

    def timeline(self) -> list[str]:
        return [f"{entry.timestamp.isoformat()} | {entry.event_type} | {entry.description}" for entry in self.entries]

    def summary(self) -> str:
        counts = self.event_counts()
        if not counts:
            return f"Replay for {self.session_name}: {len(self.entries)} events"
        top_counts = ", ".join(f"{event_type}={count}" for event_type, count in counts.most_common(4))
        return f"Replay for {self.session_name}: {len(self.entries)} events | {top_counts}"

    def event_counts(self) -> Counter[str]:
        return Counter(entry.event_type for entry in self.entries)


def _event_to_entry(event: Event) -> ReplayEntry:
    return ReplayEntry(
        timestamp=event.created_at,
        event_type=event.type.value,
        description=_describe_event(event),
    )


def _describe_event(event: Event) -> str:
    payload = event.payload
    if not payload:
        return "no payload"
    parts = [f"{key}={value}" for key, value in payload.items()]
    return ", ".join(parts)
