"""Сборка зависимостей ETL-сервиса."""

from __future__ import annotations

from dataclasses import dataclass

from etl.application.transfer.mapper import EventMessageMapper
from etl.application.transfer.services import EventTransferService
from etl.infrastructure.container import InfrastructureDependencyContainer


@dataclass(slots=True)
class ApplicationDependencyContainer:
    """Собирает прикладной сервис из инфраструктурных зависимостей."""

    infrastructure: InfrastructureDependencyContainer
    transfer_service: EventTransferService

    @classmethod
    async def assemble(
        cls, infrastructure: InfrastructureDependencyContainer
    ) -> ApplicationDependencyContainer:
        """Собирает контейнер прикладных зависимостей."""
        settings = infrastructure.settings
        transfer_service = EventTransferService(
            consumer=infrastructure.event_consumer,
            repository=infrastructure.event_repository,
            offset_store=infrastructure.event_consumer,
            dead_letter_store=infrastructure.dead_letter_store,
            mapper=EventMessageMapper(),
            clock=infrastructure.clock,
            max_batch_size=settings.batch.max_size,
            batch_timeout_seconds=settings.batch.timeout_seconds,
            retry_backoff_seconds=settings.retry.backoff_seconds,
        )
        return cls(
            infrastructure=infrastructure,
            transfer_service=transfer_service,
        )
