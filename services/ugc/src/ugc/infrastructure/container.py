"""Контейнер зависимостей инфраструктурного слоя."""

from __future__ import annotations

from dataclasses import dataclass

from ugc.infrastructure.clock import SystemClock
from ugc.infrastructure.mongo.client import MongoConnection
from ugc.infrastructure.mongo.review_repository import (
    MongoReviewRepository,
)
from ugc.infrastructure.mongo.user_action_repository import (
    MongoUserActionRepository,
)
from ugc.infrastructure.settings import AppSettings


@dataclass(slots=True)
class InfrastructureDependencyContainer:
    """Собирает реализации портов инфраструктурного слоя."""

    settings: AppSettings
    clock: SystemClock
    connection: MongoConnection
    like_repository: MongoUserActionRepository
    bookmark_repository: MongoUserActionRepository
    review_repository: MongoReviewRepository

    @classmethod
    async def assemble(
        cls, settings: AppSettings
    ) -> InfrastructureDependencyContainer:
        """Собирает контейнер инфраструктурных зависимостей."""
        connection = MongoConnection(settings.mongo)
        await connection.start()
        return cls(
            settings=settings,
            clock=SystemClock(),
            connection=connection,
            like_repository=MongoUserActionRepository(
                connection.collection(settings.mongo.like_collection)
            ),
            bookmark_repository=MongoUserActionRepository(
                connection.collection(settings.mongo.bookmark_collection)
            ),
            review_repository=MongoReviewRepository(
                connection.collection(settings.mongo.review_collection)
            ),
        )
