"""Общие тестовые двойники репозиториев для сервиса ugc.

Поведение приближено к MongoDB-адаптерам: данные хранятся в виде документов,
а чтение возвращает независимые объекты, собранные из документа.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from ugc.domain.content.film_id import FilmId
from ugc.domain.content.review import Review
from ugc.domain.content.review_id import ReviewId
from ugc.domain.content.user_action import UserAction
from ugc.domain.content.user_id import UserId
from ugc.infrastructure.mongo.serialization import (
    action_key,
    action_to_document,
    review_from_document,
    review_to_document,
)


class FakeClock:
    """Часы с управляемым временем."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 1, 1, tzinfo=UTC)

    def now(self) -> datetime:
        """Возвращает текущее время."""
        return self._now

    def advance(self, seconds: float) -> None:
        """Сдвигает время вперёд."""
        self._now = self._now + timedelta(seconds=seconds)


def _created_at(document: dict[str, object]) -> datetime:
    return cast(datetime, document["created_at"])


class FakeUserActionRepository:
    """Хранилище действий в памяти."""

    def __init__(self) -> None:
        self.documents: dict[str, dict[str, object]] = {}

    async def add(self, action: UserAction) -> None:
        document = action_to_document(action)
        self.documents[str(document["_id"])] = document

    async def remove(self, user_id: UserId, film_id: FilmId) -> None:
        self.documents.pop(action_key(user_id.value, film_id.value), None)

    async def exists(self, user_id: UserId, film_id: FilmId) -> bool:
        return action_key(user_id.value, film_id.value) in self.documents

    async def count_by_film(self, film_id: FilmId) -> int:
        return sum(
            1
            for document in self.documents.values()
            if document["film_id"] == film_id.value
        )

    async def list_film_ids_by_user(self, user_id: UserId) -> list[FilmId]:
        matching = [
            document
            for document in self.documents.values()
            if document["user_id"] == user_id.value
        ]
        ordered = sorted(matching, key=_created_at, reverse=True)
        return [FilmId(str(document["film_id"])) for document in ordered]


class FakeReviewRepository:
    """Хранилище рецензий в памяти, возвращающее независимые копии."""

    def __init__(self) -> None:
        self.documents: dict[str, dict[str, object]] = {}

    async def save(self, review: Review) -> None:
        self.documents[review.review_id.value] = review_to_document(review)

    async def get(self, review_id: ReviewId) -> Review | None:
        document = self.documents.get(review_id.value)
        if document is None:
            return None
        return review_from_document(document)

    async def delete(self, review_id: ReviewId) -> None:
        self.documents.pop(review_id.value, None)

    async def list_by_film(
        self, film_id: FilmId, offset: int, limit: int
    ) -> list[Review]:
        matching = [
            document
            for document in self.documents.values()
            if document["film_id"] == film_id.value
        ]
        ordered = sorted(matching, key=_created_at, reverse=True)
        page = ordered[offset : offset + limit]
        return [review_from_document(document) for document in page]

    async def count_by_film(self, film_id: FilmId) -> int:
        return sum(
            1
            for document in self.documents.values()
            if document["film_id"] == film_id.value
        )

    async def list_by_user(self, user_id: UserId) -> list[Review]:
        matching = [
            document
            for document in self.documents.values()
            if document["user_id"] == user_id.value
        ]
        ordered = sorted(matching, key=_created_at, reverse=True)
        return [review_from_document(document) for document in ordered]
