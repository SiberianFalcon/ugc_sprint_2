"""Прикладной сервис переноса событий из очереди в хранилище."""

import asyncio
import logging
from collections.abc import Mapping, Sequence

from etl.application.errors import ApplicationError
from etl.application.ports.clock import Clock
from etl.application.ports.dead_letter_store import DeadLetterStore
from etl.application.ports.event_consumer import EventConsumer
from etl.application.ports.event_repository import EventRepository
from etl.application.ports.offset_store import OffsetStore
from etl.application.transfer.mapper import EventMessageMapper
from etl.domain.exceptions import DomainError


logger = logging.getLogger(__name__)


class EventTransferService:
    """Непрерывно переносит события из очереди в хранилище."""

    def __init__(
        self,
        consumer: EventConsumer,
        repository: EventRepository,
        offset_store: OffsetStore,
        dead_letter_store: DeadLetterStore,
        mapper: EventMessageMapper,
        clock: Clock,
        max_batch_size: int,
        batch_timeout_seconds: float,
        retry_backoff_seconds: float,
    ) -> None:
        self._consumer = consumer
        self._repository = repository
        self._offset_store = offset_store
        self._dead_letter_store = dead_letter_store
        self._mapper = mapper
        self._clock = clock
        self._max_batch_size = max_batch_size
        self._batch_timeout_seconds = batch_timeout_seconds
        self._retry_backoff_seconds = retry_backoff_seconds
        self._stopped = asyncio.Event()

    async def run(self) -> None:
        """Запускает цикл непрерывного переноса событий."""
        if not await self._start_dependencies():
            await self._stop_dependencies()
            return
        try:
            while not self._stopped.is_set():
                await self._iteration()
        finally:
            self._stopped.set()
            await self._stop_dependencies()

    async def _start_dependencies(self) -> bool:
        while not self._stopped.is_set():
            try:
                await self._consumer.start()
                await self._dead_letter_store.start()
                await self._repository.start()
            except Exception as error:
                logger.warning(
                    "Не удалось запустить зависимости (%s), "
                    "повтор через %.1f с: %s",
                    self._clock.now().isoformat(),
                    self._retry_backoff_seconds,
                    error,
                )
                await asyncio.sleep(self._retry_backoff_seconds)
                continue
            return True
        return False

    async def _stop_dependencies(self) -> None:
        await self._repository.stop()
        await self._dead_letter_store.stop()
        await self._consumer.stop()

    async def stop(self) -> None:
        """Останавливает цикл переноса событий."""
        self._stopped.set()

    async def _iteration(self) -> None:
        try:
            messages = await self._consumer.poll_batch(
                self._max_batch_size, self._batch_timeout_seconds
            )
        except Exception as error:
            logger.warning("Не удалось прочитать события: %s", error)
            return
        if not messages:
            return
        records, persisted = await self._to_records(messages)
        if not persisted:
            return
        if records and not await self._save(records):
            return
        await self._commit()

    async def _to_records(
        self, messages: Sequence[bytes]
    ) -> tuple[list[Mapping[str, object]], bool]:
        records: list[Mapping[str, object]] = []
        for raw in messages:
            try:
                event = self._mapper.to_event(raw)
            except (ApplicationError, DomainError) as error:
                if not await self._save_dead_letter(raw, str(error)):
                    return records, False
                continue
            records.append(event.normalize())
        return records, True

    async def _save(self, records: Sequence[Mapping[str, object]]) -> bool:
        while not self._stopped.is_set():
            try:
                await self._repository.save_batch(records)
            except Exception as error:
                logger.warning(
                    "Хранилище недоступно (%s), повтор через %.1f с: %s",
                    self._clock.now().isoformat(),
                    self._retry_backoff_seconds,
                    error,
                )
                await asyncio.sleep(self._retry_backoff_seconds)
                continue
            return True
        return False

    async def _commit(self) -> None:
        try:
            await self._offset_store.commit()
        except Exception as error:
            logger.warning("Не удалось зафиксировать прогресс: %s", error)

    async def _save_dead_letter(self, raw: bytes, reason: str) -> bool:
        while not self._stopped.is_set():
            try:
                await self._dead_letter_store.save(raw, reason)
            except Exception as error:
                logger.warning(
                    "Не удалось записать событие в DLQ (%s), "
                    "повтор через %.1f с: %s",
                    self._clock.now().isoformat(),
                    self._retry_backoff_seconds,
                    error,
                )
                await asyncio.sleep(self._retry_backoff_seconds)
                continue
            return True
        return False
