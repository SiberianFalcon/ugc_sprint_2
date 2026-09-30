"""Контейнер зависимостей инфраструктурного слоя."""

from __future__ import annotations

from dataclasses import dataclass

from api.infrastructure.clock import SystemClock
from api.infrastructure.kafka.event_producer import KafkaEventProducer
from api.infrastructure.security.token_verifier import JwtTokenVerifier
from api.infrastructure.settings import AppSettings


@dataclass(slots=True)
class InfrastructureDependencyContainer:
    """Собирает реализации портов инфраструктурного слоя."""

    settings: AppSettings
    clock: SystemClock
    event_producer: KafkaEventProducer
    token_verifier: JwtTokenVerifier

    @classmethod
    async def assemble(
        cls, settings: AppSettings
    ) -> InfrastructureDependencyContainer:
        """Собирает контейнер инфраструктурных зависимостей."""
        return cls(
            settings=settings,
            clock=SystemClock(),
            event_producer=KafkaEventProducer(settings.infrastructure.kafka),
            token_verifier=JwtTokenVerifier(settings.auth),
        )
