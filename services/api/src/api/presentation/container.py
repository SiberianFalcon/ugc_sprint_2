"""Контейнеры зависимостей прикладного и презентационного слоёв."""

from __future__ import annotations

from dataclasses import dataclass

from api.application.events.services import EventApplicationService
from api.infrastructure.container import InfrastructureDependencyContainer


@dataclass(slots=True)
class ApplicationDependencyContainer:
    """Собирает прикладные сервисы из инфраструктурных зависимостей."""

    infrastructure: InfrastructureDependencyContainer
    event_service: EventApplicationService

    @classmethod
    async def assemble(
        cls, infrastructure: InfrastructureDependencyContainer
    ) -> ApplicationDependencyContainer:
        """Собирает контейнер прикладных зависимостей."""
        event_service = EventApplicationService(
            producer=infrastructure.event_producer,
            clock=infrastructure.clock,
        )
        return cls(
            infrastructure=infrastructure,
            event_service=event_service,
        )
