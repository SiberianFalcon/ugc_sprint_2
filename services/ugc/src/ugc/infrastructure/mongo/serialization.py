"""Преобразование доменных объектов в документы MongoDB и обратно."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from ugc.domain.content.created_at import CreatedAt
from ugc.domain.content.film_id import FilmId
from ugc.domain.content.rating import Rating
from ugc.domain.content.review import Review
from ugc.domain.content.review_id import ReviewId
from ugc.domain.content.review_text import ReviewText
from ugc.domain.content.user_action import UserAction
from ugc.domain.content.user_id import UserId


def action_key(user_id: str, film_id: str) -> str:
    """Формирует ключ действия пользователя над фильмом."""
    return f"{user_id}:{film_id}"


def action_to_document(action: UserAction) -> dict[str, object]:
    """Преобразует действие в документ MongoDB."""
    return {
        "_id": action_key(action.user_id.value, action.film_id.value),
        "user_id": action.user_id.value,
        "film_id": action.film_id.value,
        "created_at": action.created_at.value,
    }


def review_to_document(review: Review) -> dict[str, object]:
    """Преобразует рецензию в документ MongoDB."""
    return {
        "_id": review.review_id.value,
        "user_id": review.user_id.value,
        "film_id": review.film_id.value,
        "rating": review.rating.value,
        "text": review.text.value,
        "created_at": review.created_at.value,
        "updated_at": review.updated_at.value,
        "version": review.version,
    }


def review_from_document(document: dict[str, object]) -> Review:
    """Восстанавливает рецензию из документа MongoDB."""
    return Review(
        review_id=ReviewId(str(document["_id"])),
        user_id=UserId(str(document["user_id"])),
        film_id=FilmId(str(document["film_id"])),
        rating=Rating(cast(int, document["rating"])),
        text=ReviewText(str(document["text"])),
        created_at=CreatedAt(cast(datetime, document["created_at"])),
        updated_at=CreatedAt(cast(datetime, document["updated_at"])),
        version=cast(int, document.get("version", 0)),
    )
