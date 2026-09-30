"""Value Object идентификатора пользователя."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from etl.domain.event.exceptions import InvalidUserIdError


@dataclass(frozen=True, slots=True)
class UserId:
    """Идентификатор пользователя, которому принадлежит событие."""

    ANONYMOUS_VALUE: ClassVar[str] = "anonymous"

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise InvalidUserIdError(
                "Идентификатор пользователя не может быть пустым."
            )

    @classmethod
    def anonymous(cls) -> UserId:
        """Создаёт идентификатор анонимного пользователя."""
        return cls(cls.ANONYMOUS_VALUE)

    @property
    def is_anonymous(self) -> bool:
        """Сообщает, является ли пользователь анонимным."""
        return self.value == self.ANONYMOUS_VALUE

    def __str__(self) -> str:
        return self.value
