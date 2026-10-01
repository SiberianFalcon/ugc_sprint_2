"""Подключение к MongoDB и инициализация индексов."""

from __future__ import annotations

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from ugc.infrastructure.settings import MongoSettings


class MongoConnection:
    """Обёртка над асинхронным клиентом MongoDB."""

    def __init__(self, settings: MongoSettings) -> None:
        self._settings = settings
        self._client: AsyncIOMotorClient | None = None
        self._database: AsyncIOMotorDatabase | None = None

    async def start(self) -> None:
        """Устанавливает соединение и создаёт индексы."""
        client: AsyncIOMotorClient = AsyncIOMotorClient(
            self._settings.uri, tz_aware=True
        )
        await client.admin.command("ping")
        self._client = client
        self._database = client[self._settings.database]
        await self._ensure_indexes()

    async def stop(self) -> None:
        """Закрывает соединение с MongoDB."""
        if self._client is not None:
            self._client.close()
        self._client = None
        self._database = None

    async def check(self) -> bool:
        """Проверяет доступность MongoDB."""
        if self._client is None:
            return False
        try:
            await self._client.admin.command("ping")
        except Exception:
            return False
        return True

    def collection(self, name: str) -> AsyncIOMotorCollection:
        """Возвращает коллекцию по имени."""
        if self._database is None:
            raise RuntimeError("Соединение с MongoDB не установлено.")
        return self._database[name]

    async def _ensure_indexes(self) -> None:
        actions = (
            self.collection(self._settings.like_collection),
            self.collection(self._settings.bookmark_collection),
        )
        for collection in actions:
            await collection.create_index("film_id")
            await collection.create_index("user_id")
        reviews = self.collection(self._settings.review_collection)
        await reviews.create_index([("film_id", 1), ("created_at", -1)])
        await reviews.create_index([("user_id", 1), ("created_at", -1)])
