"""Сериализация события в сообщение очереди."""

import json

from api.domain.event.event import Event


def serialize_event(event: Event) -> bytes:
    """Сериализует событие в JSON-сообщение для очереди."""
    message = {
        "event_id": str(event.event_id),
        "user_id": str(event.user_id),
        "event_type": str(event.event_type),
        "event_time": event.event_time.value.isoformat(),
        "payload": dict(event.payload.data),
    }
    return json.dumps(message, ensure_ascii=False, default=str).encode("utf-8")
