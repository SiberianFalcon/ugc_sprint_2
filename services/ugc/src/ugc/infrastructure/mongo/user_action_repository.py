"""Адаптер MongoDB для хранения лайков и закладок."""

from motor.motor_asyncio import AsyncIOMotorCollection

from ugc.domain.content.film_id import FilmId
from ugc.domain.content.user_action import UserAction
from ugc.domain.content.user_id import UserId
from ugc.infrastructure.mongo.serialization import (
    action_key,
    action_to_document,
)


class MongoUserActionRepository:
    """Хранит действия пользователя (лайки или закладки) в MongoDB."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def add(self, action: UserAction) -> None:
        """Идемпотентно сохраняет действие пользователя."""
        document = action_to_document(action)
        await self._collection.update_one(
            {"_id": document["_id"]},
            {"$setOnInsert": document},
            upsert=True,
        )

    async def remove(self, user_id: UserId, film_id: FilmId) -> None:
        """Удаляет действие пользователя над фильмом."""
        await self._collection.delete_one(
            {"_id": action_key(user_id.value, film_id.value)}
        )

    async def exists(self, user_id: UserId, film_id: FilmId) -> bool:
        """Сообщает, отмечал ли пользователь фильм."""
        count = await self._collection.count_documents(
            {"_id": action_key(user_id.value, film_id.value)}, limit=1
        )
        return count > 0

    async def count_by_film(self, film_id: FilmId) -> int:
        """Возвращает число действий по фильму."""
        return await self._collection.count_documents(
            {"film_id": film_id.value}
        )

    async def list_film_ids_by_user(
        self, user_id: UserId, offset: int, limit: int
    ) -> list[FilmId]:
        """Возвращает страницу фильмов, отмеченных пользователем."""
        cursor = (
            self._collection.find({"user_id": user_id.value})
            .sort([("created_at", -1), ("_id", -1)])
            .skip(offset)
            .limit(limit)
        )
        documents = await cursor.to_list(length=limit)
        return [FilmId(str(document["film_id"])) for document in documents]

    async def count_by_user(self, user_id: UserId) -> int:
        """Возвращает число действий пользователя."""
        return await self._collection.count_documents(
            {"user_id": user_id.value}
        )
