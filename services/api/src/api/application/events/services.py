"""Прикладной сервис приёма пользовательских событий."""

from collections.abc import Mapping

from api.application.dto.collect_event import CollectEventCommand
from api.application.ports.clock import Clock
from api.application.ports.event_producer import EventProducer
from api.domain.event.element_id import ElementId
from api.domain.event.event import Event
from api.domain.event.event_id import EventId
from api.domain.event.event_name import EventName
from api.domain.event.event_time import EventTime
from api.domain.event.event_type import EventType
from api.domain.event.exceptions import InvalidPayloadError
from api.domain.event.page_url import PageUrl
from api.domain.event.payload import Payload
from api.domain.event.user_id import UserId


class EventApplicationService:
    """Принимает события и публикует их в очередь."""

    def __init__(self, producer: EventProducer, clock: Clock) -> None:
        self._producer = producer
        self._clock = clock

    async def collect_event(self, command: CollectEventCommand) -> Event:
        """Принимает событие и публикует его в очередь."""
        event = self._build_event(command)
        await self._producer.publish(event, key=str(event.event_id))
        return event

    def _build_event(self, command: CollectEventCommand) -> Event:
        event_type = EventType.from_value(command.event_type)
        event_time = (
            EventTime.parse(command.event_time)
            if command.event_time
            else EventTime(self._clock.now())
        )
        event_id = (
            EventId(command.event_id) if command.event_id else EventId.new()
        )
        return Event(
            event_id=event_id,
            user_id=UserId(command.user_id),
            event_type=event_type,
            event_time=event_time,
            payload=self._build_payload(event_type, command.payload),
        )

    def _build_payload(
        self,
        event_type: EventType,
        payload: Mapping[str, object],
    ) -> Payload:
        if event_type is EventType.CLICK:
            return Payload.for_click(
                PageUrl(_require_str(payload, "page_url")),
                ElementId(_require_str(payload, "element_id")),
            )
        if event_type is EventType.PAGE_VIEW:
            return Payload.for_page_view(
                PageUrl(_require_str(payload, "page_url")),
                duration=_optional_int(payload, "duration"),
            )
        return Payload.for_custom(
            EventName(_require_str(payload, "event_name")),
            extra={
                key: value
                for key, value in payload.items()
                if key != "event_name"
            },
        )


def _require_str(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise InvalidPayloadError(
            f"Поле {key} обязательно и должно быть непустой строкой."
        )
    return value


def _optional_int(payload: Mapping[str, object], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidPayloadError(f"Поле {key} должно быть целым числом.")
    return value
