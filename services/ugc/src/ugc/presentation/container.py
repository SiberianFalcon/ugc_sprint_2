"""Контейнер зависимостей прикладного слоя."""

from __future__ import annotations

from dataclasses import dataclass

from ugc.application.content.services import (
    BookmarkApplicationService,
    LikeApplicationService,
    ReviewApplicationService,
)
from ugc.infrastructure.container import InfrastructureDependencyContainer


@dataclass(slots=True)
class ApplicationDependencyContainer:
    """Собирает прикладные сервисы из инфраструктурных зависимостей."""

    infrastructure: InfrastructureDependencyContainer
    like_service: LikeApplicationService
    bookmark_service: BookmarkApplicationService
    review_service: ReviewApplicationService

    @classmethod
    async def assemble(
        cls, infrastructure: InfrastructureDependencyContainer
    ) -> ApplicationDependencyContainer:
        """Собирает контейнер прикладных зависимостей."""
        clock = infrastructure.clock
        return cls(
            infrastructure=infrastructure,
            like_service=LikeApplicationService(
                infrastructure.like_repository, clock
            ),
            bookmark_service=BookmarkApplicationService(
                infrastructure.bookmark_repository, clock
            ),
            review_service=ReviewApplicationService(
                infrastructure.review_repository, clock
            ),
        )
