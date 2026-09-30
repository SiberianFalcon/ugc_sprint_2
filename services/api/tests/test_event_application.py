"""Тесты прикладного сервиса приёма событий API."""

from datetime import UTC, datetime

import pytest

from api.application.dto.collect_event import CollectEventCommand
from api.application.events.services import EventApplicationService
from api.domain.event.event import Event
from api.domain.event.event_type import EventType
from api.domain.event.exceptions import (
    InvalidEventTypeError,
    InvalidPayloadError,
)


class FakeClock:
    """Часы с фиксированным временем."""

    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class FakeProducer:
    """Продюсер, запоминающий опубликованные события."""

    def __init__(self) -> None:
        self.published: list[tuple[Event, str]] = []

    async def start(self) -> None: ...

    async def publish(self, event: Event, key: str) -> None:
        self.published.append((event, key))

    async def stop(self) -> None: ...


def _service(producer: FakeProducer) -> EventApplicationService:
    return EventApplicationService(
        producer=producer,
        clock=FakeClock(datetime(2024, 1, 1, tzinfo=UTC)),
    )


async def test_collect_event_publishes_with_event_id_key() -> None:
    """Событие публикуется, ключ сообщения равен идентификатору события."""
    producer = FakeProducer()
    event = await _service(producer).collect_event(
        CollectEventCommand(
            user_id="user-1",
            event_type="click",
            payload={
                "page_url": "https://example.com/movie",
                "element_id": "play",
            },
        )
    )
    assert event.is_type(EventType.CLICK)
    assert producer.published[0][1] == str(event.event_id)


async def test_collect_event_uses_client_supplied_id() -> None:
    """Клиентский идентификатор события сохраняется."""
    producer = FakeProducer()
    event = await _service(producer).collect_event(
        CollectEventCommand(
            user_id="user-1",
            event_type="page_view",
            event_id="event-42",
            payload={"page_url": "/movie"},
        )
    )
    assert str(event.event_id) == "event-42"


async def test_collect_event_uses_clock_when_time_absent() -> None:
    """При отсутствии времени используется время часов."""
    producer = FakeProducer()
    event = await _service(producer).collect_event(
        CollectEventCommand(
            user_id="user-1",
            event_type="page_view",
            payload={"page_url": "/movie"},
        )
    )
    assert event.event_time.value == datetime(2024, 1, 1, tzinfo=UTC)


async def test_collect_event_rejects_unknown_type() -> None:
    """Неизвестный тип события отклоняется."""
    with pytest.raises(InvalidEventTypeError):
        await _service(FakeProducer()).collect_event(
            CollectEventCommand(user_id="user-1", event_type="unknown")
        )


async def test_collect_event_requires_page_url_for_click() -> None:
    """Для клика обязателен адрес страницы."""
    with pytest.raises(InvalidPayloadError):
        await _service(FakeProducer()).collect_event(
            CollectEventCommand(
                user_id="user-1",
                event_type="click",
                payload={"element_id": "play"},
            )
        )


async def test_collect_event_rejects_out_of_range_duration() -> None:
    """Длительность вне диапазона колонки отклоняется."""
    with pytest.raises(InvalidPayloadError):
        await _service(FakeProducer()).collect_event(
            CollectEventCommand(
                user_id="user-1",
                event_type="page_view",
                payload={"page_url": "/movie", "duration": 4294967296},
            )
        )
