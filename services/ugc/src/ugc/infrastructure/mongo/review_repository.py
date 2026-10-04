"""Адаптер MongoDB для хранения рецензий."""

from motor.motor_asyncio import AsyncIOMotorCollection

from ugc.domain.content.film_id import FilmId
from ugc.domain.content.review import Review
from ugc.domain.content.review_id import ReviewId
from ugc.domain.content.user_id import UserId
from ugc.infrastructure.mongo.serialization import (
    review_from_document,
    review_to_document,
)


class MongoReviewRepository:
    """Хранит рецензии пользователей в MongoDB."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def create(self, review: Review) -> None:
        """Сохраняет новую рецензию."""
        await self._collection.insert_one(review_to_document(review))

    async def update(self, review: Review, expected_version: int) -> bool:
        """Обновляет рецензию, если её версия совпадает с ожидаемой."""
        document = review_to_document(review)
        document.pop("_id")
        result = await self._collection.update_one(
            {
                "_id": review.review_id.value,
                "version": expected_version,
            },
            {"$set": document},
        )
        return result.matched_count == 1

    async def get(self, review_id: ReviewId) -> Review | None:
        """Возвращает рецензию по идентификатору или None."""
        document = await self._collection.find_one({"_id": review_id.value})
        if document is None:
            return None
        return review_from_document(document)

    async def delete(self, review_id: ReviewId) -> None:
        """Удаляет рецензию по идентификатору."""
        await self._collection.delete_one({"_id": review_id.value})

    async def list_by_film(
        self, film_id: FilmId, offset: int, limit: int
    ) -> list[Review]:
        """Возвращает страницу рецензий фильма."""
        cursor = (
            self._collection.find({"film_id": film_id.value})
            .sort([("created_at", -1), ("_id", -1)])
            .skip(offset)
            .limit(limit)
        )
        documents = await cursor.to_list(length=limit)
        return [review_from_document(document) for document in documents]

    async def count_by_film(self, film_id: FilmId) -> int:
        """Возвращает число рецензий фильма."""
        return await self._collection.count_documents(
            {"film_id": film_id.value}
        )

    async def list_by_user(
        self, user_id: UserId, offset: int, limit: int
    ) -> list[Review]:
        """Возвращает страницу рецензий пользователя."""
        cursor = (
            self._collection.find({"user_id": user_id.value})
            .sort([("created_at", -1), ("_id", -1)])
            .skip(offset)
            .limit(limit)
        )
        documents = await cursor.to_list(length=limit)
        return [review_from_document(document) for document in documents]

    async def count_by_user(self, user_id: UserId) -> int:
        """Возвращает число рецензий пользователя."""
        return await self._collection.count_documents(
            {"user_id": user_id.value}
        )
