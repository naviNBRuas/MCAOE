from mcaoe.core.events import Event, EventBus, EventType
from mcaoe.observability import EventJournal


async def _noop(event: Event) -> None:
    return None


def test_event_bus_subscribe_all_records_everything() -> None:
    bus = EventBus()
    journal = EventJournal()
    bus.subscribe_all(journal.append)

    import asyncio

    asyncio.run(bus.publish(Event(type=EventType.target_added, payload={"target": "example.com"})))
    asyncio.run(bus.publish(Event(type=EventType.workflow_transitioned, payload={"stage": "analysis"})))

    assert len(journal.events) == 2
    assert journal.as_dicts()[0]["type"] == "target_added"
