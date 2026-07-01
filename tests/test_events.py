from mcaoe.core.events import DeadLetter, Event, EventBus, EventType, error_boundary
from mcaoe.observability import EventJournal


async def _noop(event: Event) -> None:
    return None


def _failing_handler(event: Event) -> None:
    msg = "simulated failure"
    raise RuntimeError(msg)


def test_event_bus_subscribe_all_records_everything() -> None:
    bus = EventBus()
    journal = EventJournal()
    bus.subscribe_all(journal.append)

    import asyncio

    asyncio.run(bus.publish(Event(type=EventType.target_added, payload={"target": "example.com"})))
    asyncio.run(bus.publish(Event(type=EventType.workflow_transitioned, payload={"stage": "analysis"})))

    assert len(journal.events) == 2
    assert journal.as_dicts()[0]["type"] == "target_added"


def test_dead_letter_queue_records_failed_handlers() -> None:
    bus = EventBus()
    bus.subscribe(EventType.task_started, _failing_handler)

    import asyncio

    asyncio.run(bus.publish(Event(type=EventType.task_started, payload={"task": "test"})))

    dql = bus.dead_letter_queue
    assert len(dql) == 1
    assert dql[0].event.type == EventType.task_started
    assert "simulated failure" in dql[0].error
    assert dql[0].handler_name == "_failing_handler"


def test_dead_letter_queue_empty_when_handlers_succeed() -> None:
    bus = EventBus()
    bus.subscribe(EventType.target_added, _noop)

    import asyncio

    asyncio.run(bus.publish(Event(type=EventType.target_added, payload={"target": "example.com"})))

    assert len(bus.dead_letter_queue) == 0


def test_drain_dead_letter_queue_clears_items() -> None:
    bus = EventBus()
    bus.subscribe(EventType.task_started, _failing_handler)

    import asyncio

    asyncio.run(bus.publish(Event(type=EventType.task_started, payload={"task": "test"})))

    drained = bus.drain_dead_letter_queue()
    assert len(drained) == 1
    assert len(bus.dead_letter_queue) == 0


def test_error_boundary_wraps_sync_handler() -> None:
    errors: list[Exception] = []

    async def on_error(event: Event, exc: Exception) -> None:
        errors.append(exc)

    safe = error_boundary(_failing_handler, on_error=on_error)

    import asyncio

    result = safe(Event(type=EventType.task_started, payload={"task": "test"}))
    if result is not None:
        asyncio.run(result)  # type: ignore[arg-type]

    assert len(errors) == 1
    assert "simulated failure" in str(errors[0])


def test_error_boundary_passes_through_successful_handler() -> None:
    results: list[str] = []

    def record(event: Event) -> None:
        results.append(str(event.type))

    safe = error_boundary(record)

    import asyncio

    result = safe(Event(type=EventType.target_added, payload={"target": "t"}))
    if result is not None:
        asyncio.run(result)  # type: ignore[arg-type]

    assert len(results) == 1
    assert results[0] == "EventType.target_added"


def test_dead_letter_dataclass_fields() -> None:
    event = Event(type=EventType.ai_analysis_generated, payload={"model": "test"})
    dl = DeadLetter(
        event=event,
        error="test error",
        traceback="Traceback...",
        handler_name="test_handler",
    )
    assert dl.event.type == EventType.ai_analysis_generated
    assert dl.error == "test error"
    assert dl.handler_name == "test_handler"
