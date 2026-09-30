"""Value Object типа события."""

from __future__ import annotations

from enum import StrEnum

from api.domain.event.exceptions import InvalidEventTypeError


class EventType(StrEnum):
    """Тип пользовательского события."""

    CLICK = "click"
    PAGE_VIEW = "page_view"
    CUSTOM = "custom"

    @classmethod
    def from_value(cls, value: str) -> EventType:
        """Преобразует строковое значение в тип события."""
        try:
            return cls(value)
        except ValueError as error:
            raise InvalidEventTypeError(
                f"Недопустимый тип события: {value}."
            ) from error
