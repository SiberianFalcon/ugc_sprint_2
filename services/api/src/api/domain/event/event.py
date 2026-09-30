"""Агрегат события."""

from api.domain.event.event_id import EventId
from api.domain.event.event_time import EventTime
from api.domain.event.event_type import EventType
from api.domain.event.exceptions import InvalidEventError
from api.domain.event.payload import Payload
from api.domain.event.user_id import UserId


class Event:
    """Зафиксированное действие пользователя — корень Event Aggregate."""

    def __init__(
        self,
        event_id: EventId,
        user_id: UserId,
        event_type: EventType,
        event_time: EventTime,
        payload: Payload,
    ) -> None:
        if not payload.matches(event_type):
            raise InvalidEventError(
                "Состав данных не соответствует типу события."
            )
        self._id = event_id
        self._user_id = user_id
        self._event_type = event_type
        self._event_time = event_time
        self._payload = payload

    @property
    def event_id(self) -> EventId:
        """Возвращает идентификатор события."""
        return self._id

    @property
    def user_id(self) -> UserId:
        """Возвращает идентификатор пользователя."""
        return self._user_id

    @property
    def event_type(self) -> EventType:
        """Возвращает тип события."""
        return self._event_type

    @property
    def event_time(self) -> EventTime:
        """Возвращает время события."""
        return self._event_time

    @property
    def payload(self) -> Payload:
        """Возвращает данные события."""
        return self._payload

    def is_type(self, event_type: EventType) -> bool:
        """Сообщает, относится ли событие к указанному типу."""
        return self._event_type is event_type
