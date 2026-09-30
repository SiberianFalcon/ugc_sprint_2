"""Адаптер чтения событий из Kafka."""

from collections.abc import Sequence
from contextlib import suppress

from aiokafka import AIOKafkaConsumer
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError

from etl.infrastructure.settings import KafkaSettings


class KafkaEventConsumer:
    """Читает события из Kafka и фиксирует прогресс чтения."""

    def __init__(self, settings: KafkaSettings) -> None:
        self._settings = settings
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self) -> None:
        """Создаёт топик при необходимости и запускает консьюмер Kafka."""
        if self._consumer is not None:
            return
        await self._ensure_topic()
        consumer = AIOKafkaConsumer(
            self._settings.topic,
            bootstrap_servers=self._settings.bootstrap_servers,
            group_id=self._settings.group_id,
            client_id=self._settings.client_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        try:
            await consumer.start()
        except Exception:
            with suppress(Exception):
                await consumer.stop()
            raise
        self._consumer = consumer

    async def poll_batch(
        self, max_size: int, timeout_seconds: float
    ) -> Sequence[bytes]:
        """Возвращает пакет прочитанных сообщений."""
        consumer = self._require_consumer()
        batches = await consumer.getmany(
            timeout_ms=int(timeout_seconds * 1000),
            max_records=max_size,
        )
        messages: list[bytes] = []
        for records in batches.values():
            for record in records:
                if isinstance(record.value, bytes):
                    messages.append(record.value)
        return messages

    async def commit(self) -> None:
        """Фиксирует прогресс чтения очереди."""
        consumer = self._require_consumer()
        await consumer.commit()

    async def stop(self) -> None:
        """Останавливает консьюмер Kafka."""
        if self._consumer is None:
            return
        await self._consumer.stop()
        self._consumer = None

    def _require_consumer(self) -> AIOKafkaConsumer:
        if self._consumer is None:
            raise RuntimeError("Консьюмер Kafka не запущен.")
        return self._consumer

    async def _ensure_topic(self) -> None:
        admin = AIOKafkaAdminClient(
            bootstrap_servers=self._settings.bootstrap_servers,
            client_id=f"{self._settings.client_id}-admin",
        )
        await admin.start()
        try:
            await admin.create_topics(
                [
                    NewTopic(
                        name=self._settings.topic,
                        num_partitions=1,
                        replication_factor=1,
                    )
                ]
            )
        except TopicAlreadyExistsError:
            return
        finally:
            await admin.close()
