"""Агрегат рецензии пользователя."""

from __future__ import annotations

from ugc.domain.content.created_at import CreatedAt
from ugc.domain.content.film_id import FilmId
from ugc.domain.content.rating import Rating
from ugc.domain.content.review_id import ReviewId
from ugc.domain.content.review_text import ReviewText
from ugc.domain.content.user_id import UserId


class Review:
    """Рецензия пользователя на фильм — корень агрегата."""

    def __init__(
        self,
        review_id: ReviewId,
        user_id: UserId,
        film_id: FilmId,
        rating: Rating,
        text: ReviewText,
        created_at: CreatedAt,
        updated_at: CreatedAt,
        version: int = 0,
    ) -> None:
        self._id = review_id
        self._user_id = user_id
        self._film_id = film_id
        self._rating = rating
        self._text = text
        self._created_at = created_at
        self._updated_at = updated_at
        self._version = version

    @classmethod
    def create(
        cls,
        user_id: UserId,
        film_id: FilmId,
        rating: Rating,
        text: ReviewText,
        created_at: CreatedAt,
    ) -> Review:
        """Создаёт новую рецензию с присвоением идентификатора."""
        return cls(
            review_id=ReviewId.new(),
            user_id=user_id,
            film_id=film_id,
            rating=rating,
            text=text,
            created_at=created_at,
            updated_at=created_at,
        )

    def edit(
        self, rating: Rating, text: ReviewText, updated_at: CreatedAt
    ) -> None:
        """Изменяет оценку и текст рецензии, увеличивая версию."""
        self._rating = rating
        self._text = text
        self._updated_at = updated_at
        self._version += 1

    def is_authored_by(self, user_id: UserId) -> bool:
        """Сообщает, принадлежит ли рецензия пользователю."""
        return self._user_id == user_id

    @property
    def review_id(self) -> ReviewId:
        """Возвращает идентификатор рецензии."""
        return self._id

    @property
    def user_id(self) -> UserId:
        """Возвращает идентификатор автора."""
        return self._user_id

    @property
    def film_id(self) -> FilmId:
        """Возвращает идентификатор фильма."""
        return self._film_id

    @property
    def rating(self) -> Rating:
        """Возвращает оценку рецензии."""
        return self._rating

    @property
    def text(self) -> ReviewText:
        """Возвращает текст рецензии."""
        return self._text

    @property
    def created_at(self) -> CreatedAt:
        """Возвращает момент создания рецензии."""
        return self._created_at

    @property
    def updated_at(self) -> CreatedAt:
        """Возвращает момент последнего изменения рецензии."""
        return self._updated_at

    @property
    def version(self) -> int:
        """Возвращает версию записи для оптимистичной блокировки."""
        return self._version
