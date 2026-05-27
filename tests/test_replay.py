from mcaoe.core.events import Event, EventType
from mcaoe.models.domain import CapabilityName, Session
from mcaoe.observability import EventJournal, SessionReplay


def test_session_replay_uses_event_timestamps() -> None:
    session = Session(name="replay-test", capability=CapabilityName.web_security)
    journal = EventJournal()
    event = Event(type=EventType.target_added, payload={"target": "example.com"})
    journal.append(event)

    replay = SessionReplay.from_session(session, journal.events)

    assert replay.entries[0].timestamp == event.created_at
    assert replay.timeline()[0].startswith(event.created_at.isoformat())
    assert "target=example.com" in replay.timeline()[0]
