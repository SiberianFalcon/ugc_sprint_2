"""Тесты доменной модели события API-сервиса."""

from datetime import UTC, datetime

import pytest

from api.domain.event.element_id import ElementId
from api.domain.event.event import Event
from api.domain.event.event_id import EventId
from api.domain.event.event_name import EventName
from api.domain.event.event_time import EventTime
from api.domain.event.event_type import EventType
from api.domain.event.exceptions import (
    InvalidEventError,
    InvalidEventIdError,
    InvalidEventTimeError,
    InvalidPageUrlError,
    InvalidPayloadError,
)
from api.domain.event.page_url import PageUrl
from api.domain.event.payload import Payload
from api.domain.event.user_id import UserId


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
    assert EventType.from_value("click") is EventType.CLICK


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


def test_page_view_rejects_out_of_range_duration() -> None:
    """Длительность вне диапазона UInt32 отклоняется."""
    for duration in (-1, 4294967296):
        with pytest.raises(InvalidPayloadError):
            Payload.for_page_view(PageUrl("/movie"), duration=duration)


def _click_event() -> Event:
    return Event(
        event_id=EventId.new(),
        user_id=UserId("user-1"),
        event_type=EventType.CLICK,
        event_time=_now(),
        payload=Payload.for_click(
            PageUrl("https://example.com/movie"),
            ElementId("play-button"),
        ),
    )


def test_click_event_accepts_matching_payload() -> None:
    """Событие клика создаётся с корректным payload."""
    assert _click_event().is_type(EventType.CLICK)


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
