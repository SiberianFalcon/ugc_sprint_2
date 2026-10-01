"""Тесты сериализации объектов в документы MongoDB и обратно."""

from datetime import UTC, datetime

from ugc.domain.content.created_at import CreatedAt
from ugc.domain.content.film_id import FilmId
from ugc.domain.content.like import Like
from ugc.domain.content.rating import Rating
from ugc.domain.content.review import Review
from ugc.domain.content.review_text import ReviewText
from ugc.domain.content.user_id import UserId
from ugc.infrastructure.mongo.serialization import (
    action_key,
    action_to_document,
    review_from_document,
    review_to_document,
)


def _created_at() -> CreatedAt:
    return CreatedAt(datetime(2026, 1, 1, tzinfo=UTC))


def test_action_key_joins_user_and_film() -> None:
    """Ключ действия объединяет идентификаторы пользователя и фильма."""
    assert action_key("user-1", "film-2") == "user-1:film-2"


def test_action_to_document_contains_all_fields() -> None:
    """Документ действия содержит ключ и поля."""
    like = Like(
        user_id=UserId("user-1"),
        film_id=FilmId("film-1"),
        created_at=_created_at(),
    )
    document = action_to_document(like)
    assert document["_id"] == "user-1:film-1"
    assert document["user_id"] == "user-1"
    assert document["film_id"] == "film-1"


def test_review_roundtrip_preserves_fields() -> None:
    """Рецензия переживает преобразование в документ и обратно."""
    review = Review.create(
        user_id=UserId("user-1"),
        film_id=FilmId("film-1"),
        rating=Rating(8),
        text=ReviewText("Отличный фильм"),
        created_at=_created_at(),
    )
    restored = review_from_document(review_to_document(review))
    assert restored.review_id == review.review_id
    assert restored.user_id == review.user_id
    assert restored.film_id == review.film_id
    assert restored.rating == review.rating
    assert restored.text == review.text
    assert restored.created_at == review.created_at
    assert restored.updated_at == review.updated_at
