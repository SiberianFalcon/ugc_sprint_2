"""Преобразование сообщений очереди в доменные события."""

from __future__ import annotations

import json
from collections.abc import Mapping

from etl.application.errors import InvalidEventMessageError
from etl.domain.event.event import Event
from etl.domain.event.event_id import EventId
from etl.domain.event.event_time import EventTime
from etl.domain.event.event_type import EventType
from etl.domain.event.payload import Payload
from etl.domain.event.user_id import UserId


class EventMessageMapper:
    """Преобразует JSON-сообщение очереди в доменное событие."""

    def to_event(self, raw: bytes) -> Event:
        """Разбирает сообщение очереди в событие."""
        message = self._parse(raw)
        return Event(
            event_id=EventId(_field_str(message, "event_id")),
            user_id=UserId(_field_str(message, "user_id")),
            event_type=EventType.from_value(_field_str(message, "event_type")),
            event_time=EventTime.parse(_field_str(message, "event_time")),
            payload=Payload(_field_mapping(message, "payload")),
        )

    @staticmethod
    def _parse(raw: bytes) -> Mapping[str, object]:
        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise InvalidEventMessageError(
                "Сообщение не является корректным UTF-8."
            ) from error
        try:
            parsed = json.loads(decoded)
        except json.JSONDecodeError as error:
            raise InvalidEventMessageError(
                "Сообщение не является корректным JSON."
            ) from error
        if not isinstance(parsed, Mapping):
            raise InvalidEventMessageError(
                "Сообщение должно быть JSON-объектом."
            )
        return parsed


def _field_str(message: Mapping[str, object], key: str) -> str:
    value = message.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InvalidEventMessageError(
            f"Поле {key} обязательно и должно быть непустой строкой."
        )
    return value


def _field_mapping(
    message: Mapping[str, object], key: str
) -> Mapping[str, object]:
    value = message.get(key)
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise InvalidEventMessageError(f"Поле {key} должно быть объектом.")
    return value
