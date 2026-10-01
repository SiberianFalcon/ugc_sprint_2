"""Порт хранения рецензий."""

from typing import Protocol

from ugc.domain.content.film_id import FilmId
from ugc.domain.content.review import Review
from ugc.domain.content.review_id import ReviewId
from ugc.domain.content.user_id import UserId


class ReviewRepository(Protocol):
    """Хранит рецензии пользователей."""

    async def save(self, review: Review) -> None:
        """Сохраняет новую или изменённую рецензию."""
        ...

    async def get(self, review_id: ReviewId) -> Review | None:
        """Возвращает рецензию по идентификатору или None."""
        ...

    async def delete(self, review_id: ReviewId) -> None:
        """Удаляет рецензию по идентификатору."""
        ...

    async def list_by_film(
        self, film_id: FilmId, offset: int, limit: int
    ) -> list[Review]:
        """Возвращает страницу рецензий фильма."""
        ...

    async def count_by_film(self, film_id: FilmId) -> int:
        """Возвращает число рецензий фильма."""
        ...

    async def list_by_user(self, user_id: UserId) -> list[Review]:
        """Возвращает рецензии пользователя."""
        ...
