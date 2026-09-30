"""Контейнер зависимостей инфраструктурного слоя."""

from __future__ import annotations

from dataclasses import dataclass

from etl.infrastructure.clickhouse.event_repository import (
    ClickHouseEventRepository,
)
from etl.infrastructure.clock import SystemClock
from etl.infrastructure.kafka.dead_letter_store import KafkaDeadLetterStore
from etl.infrastructure.kafka.event_consumer import KafkaEventConsumer
from etl.infrastructure.monitoring.memory import MemoryMonitor
from etl.infrastructure.settings import AppSettings


@dataclass(slots=True)
class InfrastructureDependencyContainer:
    """Собирает реализации портов инфраструктурного слоя."""

    settings: AppSettings
    clock: SystemClock
    event_consumer: KafkaEventConsumer
    event_repository: ClickHouseEventRepository
    dead_letter_store: KafkaDeadLetterStore
    memory_monitor: MemoryMonitor

    @classmethod
    async def assemble(
        cls, settings: AppSettings
    ) -> InfrastructureDependencyContainer:
        """Собирает контейнер инфраструктурных зависимостей."""
        kafka = settings.infrastructure.kafka
        return cls(
            settings=settings,
            clock=SystemClock(),
            event_consumer=KafkaEventConsumer(kafka),
            event_repository=ClickHouseEventRepository(
                settings.infrastructure.clickhouse
            ),
            dead_letter_store=KafkaDeadLetterStore(kafka),
            memory_monitor=MemoryMonitor(
                threshold_mb=settings.monitoring.memory_threshold_mb,
                interval_seconds=settings.monitoring.interval_seconds,
            ),
        )
