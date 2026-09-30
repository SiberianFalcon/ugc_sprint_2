"""Value Object идентификатора события."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from api.domain.event.exceptions import InvalidEventIdError


@dataclass(frozen=True, slots=True)
class EventId:
    """Уникальный идентификатор события."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise InvalidEventIdError(
                "Идентификатор события не может быть пустым."
            )

    @classmethod
    def new(cls) -> EventId:
        """Создаёт новый случайный идентификатор события."""
        return cls(uuid.uuid4().hex)

    def __str__(self) -> str:
        return self.value
