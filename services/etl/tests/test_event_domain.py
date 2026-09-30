"""Тесты доменной модели события ETL-сервиса."""

from datetime import UTC, datetime

import pytest

from etl.domain.event.event import Event
from etl.domain.event.event_id import EventId
from etl.domain.event.event_name import EventName
from etl.domain.event.event_time import EventTime
from etl.domain.event.event_type import EventType
from etl.domain.event.exceptions import (
    InvalidEventError,
    InvalidEventIdError,
    InvalidEventTimeError,
    InvalidPageUrlError,
    InvalidPayloadError,
)
from etl.domain.event.page_url import PageUrl
from etl.domain.event.payload import Payload
from etl.domain.event.user_id import UserId


def _now() -> EventTime:
    return EventTime(datetime.now(UTC))


def test_event_id_rejects_empty_value() -> None:
    """Идентификатор события не может быть пустым."""
    with pytest.raises(InvalidEventIdError):
        EventId("   ")


def test_event_id_new_generates_unique_values() -> None:
    """Каждый новый идентификатор уникален."""
    assert EventId.new() != EventId.new()


def test_user_id_anonymous() -> None:
    """Зарезервированное значение обозначает анонимного пользователя."""
    assert UserId.anonymous().is_anonymous


def test_event_type_from_known_value() -> None:
    """Строковое значение преобразуется в тип события."""
    assert EventType.from_value("page_view") is EventType.PAGE_VIEW


def test_event_time_requires_timezone() -> None:
    """Время без часового пояса отклоняется."""
    with pytest.raises(InvalidEventTimeError):
        EventTime(datetime(2024, 1, 1))


def test_page_url_rejects_invalid_value() -> None:
    """Некорректный адрес страницы отклоняется."""
    with pytest.raises(InvalidPageUrlError):
        PageUrl("not-a-url")


def test_page_url_handles_malformed_value() -> None:
    """URL, ломающий urlparse, даёт доменную ошибку, а не ValueError."""
    with pytest.raises(InvalidPageUrlError):
        PageUrl("http://[")


def test_event_rejects_payload_of_another_type() -> None:
    """Payload, не соответствующий типу, отклоняется."""
    with pytest.raises(InvalidEventError):
        Event(
            event_id=EventId.new(),
            user_id=UserId("user-1"),
            event_type=EventType.CLICK,
            event_time=_now(),
            payload=Payload.for_custom(EventName("purchase")),
        )


def test_normalize_returns_flat_record() -> None:
    """Нормализация возвращает плоскую запись с ключами события."""
    event = Event(
        event_id=EventId.new(),
        user_id=UserId("user-1"),
        event_type=EventType.PAGE_VIEW,
        event_time=_now(),
        payload=Payload.for_page_view(
            PageUrl("https://example.com/movie"),
            duration=120,
        ),
    )
    record = event.normalize()
    assert record["user_id"] == "user-1"
    assert record["event_type"] == "page_view"
    assert record["page_url"] == "https://example.com/movie"
    assert record["duration"] == 120
    assert record["extra"] == {}


def test_normalize_does_not_override_base_fields() -> None:
    """Данные payload не заменяют базовые поля события."""
    event = Event(
        event_id=EventId("event-1"),
        user_id=UserId("user-1"),
        event_type=EventType.CUSTOM,
        event_time=EventTime(datetime(2024, 1, 1, tzinfo=UTC)),
        payload=Payload(
            {
                "event_name": "buy",
                "event_id": "hacked",
                "user_id": "hacked",
                "event_time": "2000-01-01T00:00:00+00:00",
            }
        ),
    )
    record = event.normalize()
    assert record["event_id"] == "event-1"
    assert record["user_id"] == "user-1"
    assert record["event_time"] == "2024-01-01T00:00:00+00:00"
    assert record["extra"] == {
        "event_id": "hacked",
        "user_id": "hacked",
        "event_time": "2000-01-01T00:00:00+00:00",
    }


def test_normalize_stores_custom_fields_separately() -> None:
    """Дополнительные поля custom не попадают в типизированные колонки."""
    event = Event(
        event_id=EventId("event-1"),
        user_id=UserId("user-1"),
        event_type=EventType.CUSTOM,
        event_time=_now(),
        payload=Payload(
            {"event_name": "buy", "duration": "text", "product_id": "p1"}
        ),
    )
    record = event.normalize()
    assert record["event_name"] == "buy"
    assert "duration" not in record
    assert record["extra"] == {"duration": "text", "product_id": "p1"}


def test_page_view_rejects_out_of_range_duration() -> None:
    """Длительность вне диапазона UInt32 отклоняется."""
    for duration in (-1, 4294967296):
        with pytest.raises(InvalidPayloadError):
            Event(
                event_id=EventId("event-1"),
                user_id=UserId("user-1"),
                event_type=EventType.PAGE_VIEW,
                event_time=_now(),
                payload=Payload({"page_url": "/movie", "duration": duration}),
            )
