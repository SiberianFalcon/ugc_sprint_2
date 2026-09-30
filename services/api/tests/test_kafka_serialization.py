"""Тесты сериализации события в сообщение очереди."""

import json
from datetime import UTC, datetime

from api.domain.event.element_id import ElementId
from api.domain.event.event import Event
from api.domain.event.event_id import EventId
from api.domain.event.event_time import EventTime
from api.domain.event.event_type import EventType
from api.domain.event.page_url import PageUrl
from api.domain.event.payload import Payload
from api.domain.event.user_id import UserId
from api.infrastructure.kafka.serialization import serialize_event


def test_serialize_event_contains_all_fields() -> None:
    """Сообщение содержит все поля события."""
    event = Event(
        event_id=EventId("event-1"),
        user_id=UserId("user-1"),
        event_type=EventType.CLICK,
        event_time=EventTime(datetime(2024, 1, 1, tzinfo=UTC)),
        payload=Payload.for_click(
            PageUrl("https://example.com/movie"),
            ElementId("play"),
        ),
    )
    message = json.loads(serialize_event(event).decode("utf-8"))
    assert message["event_id"] == "event-1"
    assert message["user_id"] == "user-1"
    assert message["event_type"] == "click"
    assert message["event_time"] == "2024-01-01T00:00:00+00:00"
    assert message["payload"]["element_id"] == "play"
