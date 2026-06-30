import json
import logging

from mcaoe.logging import configure_logging, JsonFormatter


def test_configure_logging_sets_level() -> None:
    configure_logging("ERROR")
    root = logging.getLogger()
    assert root.level == logging.ERROR
    configure_logging("INFO")


def test_json_formatter_produces_valid_json() -> None:
    logger = logging.getLogger("test_json")
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    import io

    buf = io.StringIO()
    handler.stream = buf
    logger.info("test message")
    output = buf.getvalue()
    record = json.loads(output)

    assert record["level"] == "INFO"
    assert record["message"] == "test message"
    assert record["logger"] == "test_json"
    assert "timestamp" in record


def test_json_formatter_includes_exception() -> None:
    logger = logging.getLogger("test_exc")
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    import io

    buf = io.StringIO()
    handler.stream = buf
    try:
        raise ValueError("test error")
    except ValueError:
        logger.exception("error occurred")
    output = buf.getvalue()
    record = json.loads(output)

    assert record["level"] == "ERROR"
    assert "exception" in record
    assert "ValueError" in record["exception"]
