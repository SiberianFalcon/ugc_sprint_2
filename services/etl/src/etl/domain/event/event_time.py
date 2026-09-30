"""Value Object времени события."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from etl.domain.event.exceptions import InvalidEventTimeError


@dataclass(frozen=True, slots=True)
class EventTime:
    """Момент возникновения события."""

    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is None:
            raise InvalidEventTimeError(
                "Время события должно содержать часовой пояс."
            )

    @classmethod
    def parse(cls, value: str) -> EventTime:
        """Разбирает время события из строки в формате ISO 8601."""
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as error:
            raise InvalidEventTimeError(
                "Время события имеет некорректный формат."
            ) from error
        return cls(parsed)

    def __str__(self) -> str:
        return self.value.isoformat()
