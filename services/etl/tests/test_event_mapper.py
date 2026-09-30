"""Тесты преобразования сообщений очереди в события."""

import json

import pytest

from etl.application.errors import InvalidEventMessageError
from etl.application.transfer.mapper import EventMessageMapper
from etl.domain.event.event_type import EventType
from etl.domain.event.exceptions import (
    InvalidEventTypeError,
    InvalidPayloadError,
)


def _message(**overrides: object) -> bytes:
    payload: dict[str, object] = {
        "event_id": "event-1",
        "user_id": "user-1",
        "event_type": "page_view",
        "event_time": "2024-01-01T00:00:00+00:00",
        "payload": {"page_url": "/movie", "duration": 30},
    }
    payload.update(overrides)
    return json.dumps(payload).encode("utf-8")


def test_maps_valid_message_to_event() -> None:
    """Корректное сообщение преобразуется в событие."""
    event = EventMessageMapper().to_event(_message())
    assert event.is_type(EventType.PAGE_VIEW)
    assert str(event.event_id) == "event-1"
    assert str(event.user_id) == "user-1"


def test_rejects_non_json_message() -> None:
    """Не-JSON сообщение отклоняется."""
    with pytest.raises(InvalidEventMessageError):
        EventMessageMapper().to_event(b"not a json")


def test_rejects_message_without_required_field() -> None:
    """Сообщение без обязательного поля отклоняется."""
    raw = json.dumps({"user_id": "user-1"}).encode("utf-8")
    with pytest.raises(InvalidEventMessageError):
        EventMessageMapper().to_event(raw)


def test_propagates_domain_error_on_unknown_type() -> None:
    """Неизвестный тип события даёт доменную ошибку."""
    with pytest.raises(InvalidEventTypeError):
        EventMessageMapper().to_event(_message(event_type="nope"))


def test_propagates_domain_error_on_payload_mismatch() -> None:
    """Payload, не соответствующий типу, даёт доменную ошибку."""
    with pytest.raises(InvalidPayloadError):
        EventMessageMapper().to_event(_message(event_type="click", payload={}))
