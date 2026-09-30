"""Value Object данных события."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from api.domain.event.element_id import ElementId
from api.domain.event.event_name import EventName
from api.domain.event.event_type import EventType
from api.domain.event.exceptions import InvalidPayloadError
from api.domain.event.page_url import PageUrl


_REQUIRED_KEYS: dict[EventType, tuple[str, ...]] = {
    EventType.CLICK: ("page_url", "element_id"),
    EventType.PAGE_VIEW: ("page_url",),
    EventType.CUSTOM: ("event_name",),
}

_MAX_DURATION_SECONDS = 4294967295


@dataclass(frozen=True, slots=True)
class Payload:
    """Данные события, состав которых зависит от его типа."""

    data: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.data:
            raise InvalidPayloadError("Данные события не могут быть пустыми.")
        object.__setattr__(self, "data", MappingProxyType(dict(self.data)))

    @classmethod
    def for_click(cls, page_url: PageUrl, element_id: ElementId) -> Payload:
        """Создаёт данные события клика."""
        return cls({"page_url": str(page_url), "element_id": str(element_id)})

    @classmethod
    def for_page_view(
        cls, page_url: PageUrl, duration: int | None = None
    ) -> Payload:
        """Создаёт данные события просмотра страницы."""
        data: dict[str, object] = {"page_url": str(page_url)}
        if duration is not None:
            _check_duration(duration)
            data["duration"] = duration
        return cls(data)

    @classmethod
    def for_custom(
        cls,
        event_name: EventName,
        extra: Mapping[str, object] | None = None,
    ) -> Payload:
        """Создаёт данные кастомного события."""
        data: dict[str, object] = {"event_name": str(event_name)}
        if extra:
            data.update(extra)
        return cls(data)

    def matches(self, event_type: EventType) -> bool:
        """Проверяет, соответствует ли состав данных типу события."""
        required = _REQUIRED_KEYS.get(event_type, ())
        return all(key in self.data for key in required)

    def as_json(self) -> str:
        """Сериализует данные для передачи в очередь сообщений."""
        return json.dumps(
            dict(self.data),
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )


def _check_duration(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidPayloadError(
            "Длительность просмотра должна быть целым числом."
        )
    if not 0 <= value <= _MAX_DURATION_SECONDS:
        raise InvalidPayloadError(
            "Длительность просмотра должна быть в диапазоне от 0 до "
            f"{_MAX_DURATION_SECONDS}."
        )
