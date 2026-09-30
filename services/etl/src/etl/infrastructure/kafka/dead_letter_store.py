"""Адаптер записи непригодных событий в Kafka."""

import json
from contextlib import suppress

from aiokafka import AIOKafkaProducer

from etl.infrastructure.settings import KafkaSettings


class KafkaDeadLetterStore:
    """Публикует непригодные события в отдельный топик Kafka."""

    def __init__(self, settings: KafkaSettings) -> None:
        self._settings = settings
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Создаёт и запускает продюсер DLQ."""
        if self._producer is not None:
            return
        producer = AIOKafkaProducer(
            bootstrap_servers=self._settings.bootstrap_servers,
            client_id=f"{self._settings.client_id}-dlq",
        )
        try:
            await producer.start()
        except Exception:
            with suppress(Exception):
                await producer.stop()
            raise
        self._producer = producer

    async def save(self, raw: bytes, reason: str) -> None:
        """Публикует непригодное событие с причиной отказа."""
        producer = self._require_producer()
        message = json.dumps(
            {"reason": reason, "raw": raw.decode("utf-8", "replace")},
            ensure_ascii=False,
        ).encode("utf-8")
        await producer.send_and_wait(self._settings.dlq_topic, value=message)

    async def stop(self) -> None:
        """Останавливает продюсер DLQ."""
        if self._producer is None:
            return
        await self._producer.stop()
        self._producer = None

    def _require_producer(self) -> AIOKafkaProducer:
        if self._producer is None:
            raise RuntimeError("Продюсер DLQ не запущен.")
        return self._producer
