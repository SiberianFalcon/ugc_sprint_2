"""Value Object идентификатора пользователя."""

from __future__ import annotations

from typing import ClassVar

from ugc.domain.content.exceptions import InvalidUserIdError


class UserId:
    """Идентификатор пользователя, которому принадлежит контент."""

    ANONYMOUS_VALUE: ClassVar[str] = "anonymous"

    def __init__(self, value: str) -> None:
        normalized = value.strip()
        if not normalized:
            raise InvalidUserIdError(
                "Идентификатор пользователя не может быть пустым."
            )
        self._value = normalized

    @classmethod
    def anonymous(cls) -> UserId:
        """Создаёт идентификатор анонимного пользователя."""
        return cls(cls.ANONYMOUS_VALUE)

    @property
    def value(self) -> str:
        """Возвращает идентификатор пользователя."""
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UserId):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __str__(self) -> str:
        return self._value
