"""Порт хранения действий пользователя над фильмом."""

from typing import Protocol

from ugc.domain.content.film_id import FilmId
from ugc.domain.content.user_action import UserAction
from ugc.domain.content.user_id import UserId


class UserActionRepository(Protocol):
    """Хранит лайки или закладки пользователей."""

    async def add(self, action: UserAction) -> None:
        """Идемпотентно сохраняет действие пользователя."""
        ...

    async def remove(self, user_id: UserId, film_id: FilmId) -> None:
        """Удаляет действие пользователя над фильмом."""
        ...

    async def exists(self, user_id: UserId, film_id: FilmId) -> bool:
        """Сообщает, отмечал ли пользователь фильм."""
        ...

    async def count_by_film(self, film_id: FilmId) -> int:
        """Возвращает число действий по фильму."""
        ...

    async def list_film_ids_by_user(self, user_id: UserId) -> list[FilmId]:
        """Возвращает фильмы, отмеченные пользователем."""
        ...
