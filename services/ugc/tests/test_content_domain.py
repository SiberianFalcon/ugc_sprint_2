"""Тесты доменной модели пользовательского контента."""

from datetime import UTC, datetime

import pytest

from ugc.domain.content.bookmark import Bookmark
from ugc.domain.content.created_at import CreatedAt
from ugc.domain.content.exceptions import (
    InvalidCreatedAtError,
    InvalidFilmIdError,
    InvalidRatingError,
    InvalidReviewTextError,
    InvalidUserIdError,
)
from ugc.domain.content.film_id import FilmId
from ugc.domain.content.like import Like
from ugc.domain.content.rating import Rating
from ugc.domain.content.review import Review
from ugc.domain.content.review_id import ReviewId
from ugc.domain.content.review_text import ReviewText
from ugc.domain.content.user_id import UserId


def _now() -> CreatedAt:
    return CreatedAt(datetime(2026, 1, 1, tzinfo=UTC))


def test_user_id_rejects_empty_value() -> None:
    """Пустой идентификатор пользователя отклоняется."""
    with pytest.raises(InvalidUserIdError):
        UserId("   ")


def test_user_id_normalizes_value() -> None:
    """Идентификатор пользователя обрезается по краям."""
    assert UserId(" user-1 ").value == "user-1"


def test_film_id_rejects_empty_value() -> None:
    """Пустой идентификатор фильма отклоняется."""
    with pytest.raises(InvalidFilmIdError):
        FilmId("")


def test_created_at_requires_timezone() -> None:
    """Время без часового пояса отклоняется."""
    with pytest.raises(InvalidCreatedAtError):
        CreatedAt(datetime(2026, 1, 1))


def test_review_id_generates_unique_values() -> None:
    """Сгенерированные идентификаторы рецензий различаются."""
    assert ReviewId.new() != ReviewId.new()


def test_review_text_rejects_empty_value() -> None:
    """Пустой текст рецензии отклоняется."""
    with pytest.raises(InvalidReviewTextError):
        ReviewText("   ")


def test_review_text_rejects_too_long_value() -> None:
    """Слишком длинный текст рецензии отклоняется."""
    with pytest.raises(InvalidReviewTextError):
        ReviewText("x" * (ReviewText.MAX_LENGTH + 1))


def test_rating_accepts_boundaries() -> None:
    """Граничные оценки допустимы."""
    assert Rating(Rating.MIN_VALUE).value == 1
    assert Rating(Rating.MAX_VALUE).value == 10


@pytest.mark.parametrize("value", [0, 11, -5])
def test_rating_rejects_out_of_range(value: int) -> None:
    """Оценки вне диапазона отклоняются."""
    with pytest.raises(InvalidRatingError):
        Rating(value)


def test_like_and_bookmark_are_not_equal() -> None:
    """Лайк и закладка с одинаковыми данными различаются."""
    user_id = UserId("user-1")
    film_id = FilmId("film-1")
    like = Like(user_id, film_id, _now())
    bookmark = Bookmark(user_id, film_id, _now())
    assert like != bookmark


def test_review_create_assigns_identifier_and_timestamps() -> None:
    """Создание рецензии проставляет идентификатор и время."""
    review = Review.create(
        user_id=UserId("user-1"),
        film_id=FilmId("film-1"),
        rating=Rating(8),
        text=ReviewText("Отличный фильм"),
        created_at=_now(),
    )
    assert review.review_id.value
    assert review.created_at == review.updated_at
    assert review.is_authored_by(UserId("user-1"))


def test_review_edit_updates_rating_text_and_time() -> None:
    """Изменение рецензии обновляет оценку, текст и время."""
    review = Review.create(
        user_id=UserId("user-1"),
        film_id=FilmId("film-1"),
        rating=Rating(5),
        text=ReviewText("Средне"),
        created_at=_now(),
    )
    updated_at = CreatedAt(datetime(2026, 2, 1, tzinfo=UTC))
    review.edit(Rating(9), ReviewText("Пересмотрел — шедевр"), updated_at)
    assert review.rating == Rating(9)
    assert str(review.text) == "Пересмотрел — шедевр"
    assert review.updated_at == updated_at
