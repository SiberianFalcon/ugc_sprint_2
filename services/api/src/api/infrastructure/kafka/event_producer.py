"""Адаптер публикации событий в Kafka."""

import asyncio
from contextlib import suppress

from aiokafka import AIOKafkaProducer

from api.domain.event.event import Event
from api.infrastructure.kafka.serialization import serialize_event
from api.infrastructure.settings import KafkaSettings


_CHECK_TIMEOUT_SECONDS = 2.0


class KafkaEventProducer:
    """Публикует события в Kafka в идемпотентном режиме."""

    def __init__(self, settings: KafkaSettings) -> None:
        self._settings = settings
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Создаёт и запускает продюсер Kafka."""
        if self._producer is not None:
            return
        producer = AIOKafkaProducer(
            bootstrap_servers=self._settings.bootstrap_servers,
            client_id=self._settings.client_id,
            enable_idempotence=True,
            acks="all",
        )
        try:
            await producer.start()
        except Exception:
            with suppress(Exception):
                await producer.stop()
            raise
        self._producer = producer

    async def publish(self, event: Event, key: str) -> None:
        """Публикует событие в топик Kafka."""
        if self._producer is None:
            raise RuntimeError("Продюсер Kafka не запущен.")
        await self._producer.send_and_wait(
            self._settings.topic,
            key=key.encode("utf-8"),
            value=serialize_event(event),
        )

    async def check(self) -> bool:
        """Проверяет доступность брокера Kafka с ограничением ожидания."""
        if self._producer is None:
            return False
        try:
            await asyncio.wait_for(
                self._producer.partitions_for(self._settings.topic),
                timeout=_CHECK_TIMEOUT_SECONDS,
            )
        except Exception:
            return False
        return True

    async def stop(self) -> None:
        """Останавливает продюсер Kafka."""
        if self._producer is None:
            return
        await self._producer.stop()
        self._producer = None
