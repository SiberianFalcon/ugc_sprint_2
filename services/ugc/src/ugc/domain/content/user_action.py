"""Общая модель действия пользователя над фильмом."""

from __future__ import annotations

from ugc.domain.content.created_at import CreatedAt
from ugc.domain.content.film_id import FilmId
from ugc.domain.content.user_id import UserId


class UserAction:
    """Действие пользователя над фильмом с идентичностью пары."""

    def __init__(
        self,
        user_id: UserId,
        film_id: FilmId,
        created_at: CreatedAt,
    ) -> None:
        self._user_id = user_id
        self._film_id = film_id
        self._created_at = created_at

    @property
    def user_id(self) -> UserId:
        """Возвращает идентификатор пользователя."""
        return self._user_id

    @property
    def film_id(self) -> FilmId:
        """Возвращает идентификатор фильма."""
        return self._film_id

    @property
    def created_at(self) -> CreatedAt:
        """Возвращает момент создания действия."""
        return self._created_at

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UserAction):
            return NotImplemented
        return (
            type(self) is type(other)
            and self._user_id == other._user_id
            and self._film_id == other._film_id
        )

    def __hash__(self) -> int:
        return hash((type(self), self._user_id, self._film_id))
