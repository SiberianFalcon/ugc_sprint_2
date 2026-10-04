"""Прикладные сервисы работы с пользовательским контентом."""

from __future__ import annotations

from ugc.application.errors import (
    ReviewAccessDeniedError,
    ReviewConflictError,
    ReviewNotFoundError,
)
from ugc.application.ports.clock import Clock
from ugc.application.ports.review_repository import ReviewRepository
from ugc.application.ports.user_action_repository import (
    UserActionRepository,
)
from ugc.domain.content.bookmark import Bookmark
from ugc.domain.content.created_at import CreatedAt
from ugc.domain.content.film_id import FilmId
from ugc.domain.content.like import Like
from ugc.domain.content.rating import Rating
from ugc.domain.content.review import Review
from ugc.domain.content.review_id import ReviewId
from ugc.domain.content.review_text import ReviewText
from ugc.domain.content.user_id import UserId


class UserActionApplicationService:
    """Общая логика работы с лайками и закладками."""

    def __init__(self, repository: UserActionRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def remove(self, user_id: str, film_id: str) -> None:
        """Снимает действие пользователя над фильмом."""
        await self._repository.remove(UserId(user_id), FilmId(film_id))

    async def is_present(self, user_id: str, film_id: str) -> bool:
        """Сообщает, отмечал ли пользователь фильм."""
        return await self._repository.exists(UserId(user_id), FilmId(film_id))

    async def count(self, film_id: str) -> int:
        """Возвращает число действий по фильму."""
        return await self._repository.count_by_film(FilmId(film_id))

    async def list_film_ids(self, user_id: str) -> list[FilmId]:
        """Возвращает фильмы, отмеченные пользователем."""
        return await self._repository.list_film_ids_by_user(UserId(user_id))


class LikeApplicationService(UserActionApplicationService):
    """Ставит и снимает лайки фильмов."""

    async def add(self, user_id: str, film_id: str) -> Like:
        """Ставит лайк фильму, повторный вызов идемпотентен."""
        like = Like(
            user_id=UserId(user_id),
            film_id=FilmId(film_id),
            created_at=CreatedAt(self._clock.now()),
        )
        await self._repository.add(like)
        return like


class BookmarkApplicationService(UserActionApplicationService):
    """Добавляет и удаляет закладки фильмов."""

    async def add(self, user_id: str, film_id: str) -> Bookmark:
        """Добавляет фильм в закладки, повторный вызов идемпотентен."""
        bookmark = Bookmark(
            user_id=UserId(user_id),
            film_id=FilmId(film_id),
            created_at=CreatedAt(self._clock.now()),
        )
        await self._repository.add(bookmark)
        return bookmark


class ReviewApplicationService:
    """Создаёт, изменяет и читает рецензии пользователей."""

    def __init__(self, repository: ReviewRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    async def create(
        self, user_id: str, film_id: str, rating: int, text: str
    ) -> Review:
        """Создаёт рецензию пользователя на фильм."""
        review = Review.create(
            user_id=UserId(user_id),
            film_id=FilmId(film_id),
            rating=Rating(rating),
            text=ReviewText(text),
            created_at=CreatedAt(self._clock.now()),
        )
        await self._repository.create(review)
        return review

    async def update(
        self,
        review_id: str,
        user_id: str,
        rating: int,
        text: str,
    ) -> Review:
        """Изменяет рецензию, если пользователь является её автором."""
        review = await self._get_or_raise(review_id)
        if not review.is_authored_by(UserId(user_id)):
            raise ReviewAccessDeniedError(
                "Изменять рецензию может только её автор."
            )
        expected_version = review.version
        review.edit(
            Rating(rating),
            ReviewText(text),
            CreatedAt(self._clock.now()),
        )
        updated = await self._repository.update(review, expected_version)
        if not updated:
            raise ReviewConflictError(
                "Рецензия изменена другим запросом, повторите попытку."
            )
        return review

    async def delete(self, review_id: str, user_id: str) -> None:
        """Удаляет рецензию, если пользователь является её автором."""
        review = await self._get_or_raise(review_id)
        if not review.is_authored_by(UserId(user_id)):
            raise ReviewAccessDeniedError(
                "Удалять рецензию может только её автор."
            )
        await self._repository.delete(review.review_id)

    async def get(self, review_id: str) -> Review:
        """Возвращает рецензию по идентификатору."""
        return await self._get_or_raise(review_id)

    async def list_by_film(
        self, film_id: str, offset: int, limit: int
    ) -> list[Review]:
        """Возвращает страницу рецензий фильма."""
        return await self._repository.list_by_film(
            FilmId(film_id), offset, limit
        )

    async def count_by_film(self, film_id: str) -> int:
        """Возвращает число рецензий фильма."""
        return await self._repository.count_by_film(FilmId(film_id))

    async def list_by_user(self, user_id: str) -> list[Review]:
        """Возвращает рецензии пользователя."""
        return await self._repository.list_by_user(UserId(user_id))

    async def _get_or_raise(self, review_id: str) -> Review:
        review = await self._repository.get(ReviewId(review_id))
        if review is None:
            raise ReviewNotFoundError(f"Рецензия {review_id} не найдена.")
        return review
