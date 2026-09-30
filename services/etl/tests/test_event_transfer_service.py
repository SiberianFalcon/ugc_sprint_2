"""Тесты прикладного сервиса переноса событий."""

import asyncio
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from etl.application.ports.dead_letter_store import DeadLetterStore
from etl.application.transfer.mapper import EventMessageMapper
from etl.application.transfer.services import EventTransferService


def _valid_message() -> bytes:
    return json.dumps(
        {
            "event_id": "event-1",
            "user_id": "user-1",
            "event_type": "page_view",
            "event_time": "2024-01-01T00:00:00+00:00",
            "payload": {"page_url": "/movie", "duration": 30},
        }
    ).encode("utf-8")


class FakeConsumer:
    """Отдаёт заранее заданные пакеты сообщений."""

    def __init__(self, batches: Sequence[Sequence[bytes]]) -> None:
        self._batches = list(batches)
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def poll_batch(
        self, max_size: int, timeout_seconds: float
    ) -> Sequence[bytes]:
        if self._batches:
            return self._batches.pop(0)
        await asyncio.sleep(0)
        return []

    async def stop(self) -> None:
        self.stopped = True


class FakeRepository:
    """Запоминает записанные пакеты; может падать заданное число раз."""

    def __init__(self, fail_times: int = 0, fail_start_times: int = 0) -> None:
        self.batches: list[list[Mapping[str, object]]] = []
        self._fail_times = fail_times
        self._fail_start_times = fail_start_times
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        if self._fail_start_times > 0:
            self._fail_start_times -= 1
            raise RuntimeError("storage unavailable")
        self.started = True

    async def save_batch(self, events: Sequence[Mapping[str, object]]) -> None:
        if self._fail_times > 0:
            self._fail_times -= 1
            raise RuntimeError("storage unavailable")
        self.batches.append(list(events))

    async def stop(self) -> None:
        self.stopped = True


class FakeOffsetStore:
    """Считает вызовы фиксации прогресса."""

    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeDeadLetterStore:
    """Запоминает непригодные сообщения."""

    def __init__(self) -> None:
        self.saved: list[tuple[bytes, str]] = []
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def save(self, raw: bytes, reason: str) -> None:
        self.saved.append((raw, reason))

    async def stop(self) -> None:
        self.stopped = True


class _FlakyDeadLetterStore:
    """Падает заданное число раз, затем сохраняет сообщения."""

    def __init__(self, fail_times: int) -> None:
        self._fail_times = fail_times
        self.saved: list[tuple[bytes, str]] = []

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def save(self, raw: bytes, reason: str) -> None:
        if self._fail_times > 0:
            self._fail_times -= 1
            raise RuntimeError("dlq down")
        self.saved.append((raw, reason))


class _FailingDeadLetterStore:
    """Всегда падает при сохранении."""

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def save(self, raw: bytes, reason: str) -> None:
        raise RuntimeError("dlq down")


class FakeClock:
    """Часы с фиксированным временем."""

    def now(self) -> datetime:
        return datetime(2024, 1, 1, tzinfo=UTC)


def _service(
    consumer: FakeConsumer,
    repository: FakeRepository,
    offset_store: FakeOffsetStore,
    dead_letter_store: DeadLetterStore,
) -> EventTransferService:
    return EventTransferService(
        consumer=consumer,
        repository=repository,
        offset_store=offset_store,
        dead_letter_store=dead_letter_store,
        mapper=EventMessageMapper(),
        clock=FakeClock(),
        max_batch_size=100,
        batch_timeout_seconds=0.01,
        retry_backoff_seconds=0.0,
    )


async def test_iteration_saves_batch_and_commits() -> None:
    """Валидный пакет записывается и прогресс фиксируется."""
    repository = FakeRepository()
    offsets = FakeOffsetStore()
    dead_letters = FakeDeadLetterStore()
    service = _service(
        FakeConsumer([[_valid_message()]]),
        repository,
        offsets,
        dead_letters,
    )

    await service._iteration()

    assert len(repository.batches) == 1
    assert repository.batches[0][0]["event_id"] == "event-1"
    assert offsets.commits == 1
    assert dead_letters.saved == []


async def test_iteration_sends_bad_message_to_dead_letter() -> None:
    """Непригодное сообщение уходит в DLQ, остальные записываются."""
    repository = FakeRepository()
    offsets = FakeOffsetStore()
    dead_letters = FakeDeadLetterStore()
    service = _service(
        FakeConsumer([[b"not a json", _valid_message()]]),
        repository,
        offsets,
        dead_letters,
    )

    await service._iteration()

    assert len(dead_letters.saved) == 1
    assert len(repository.batches) == 1
    assert len(repository.batches[0]) == 1
    assert offsets.commits == 1


async def test_iteration_retries_save_after_failure() -> None:
    """При сбое хранилища запись повторяется до успеха."""
    repository = FakeRepository(fail_times=1)
    offsets = FakeOffsetStore()
    service = _service(
        FakeConsumer([[_valid_message()]]),
        repository,
        offsets,
        FakeDeadLetterStore(),
    )

    await service._iteration()

    assert len(repository.batches) == 1
    assert offsets.commits == 1


async def test_iteration_skips_empty_batch() -> None:
    """Пустой пакет не приводит к записи и фиксации."""
    repository = FakeRepository()
    offsets = FakeOffsetStore()
    service = _service(
        FakeConsumer([[]]),
        repository,
        offsets,
        FakeDeadLetterStore(),
    )

    await service._iteration()

    assert repository.batches == []
    assert offsets.commits == 0


async def test_run_starts_and_stops_consumer() -> None:
    """Цикл запускает и останавливает консьюмер."""
    consumer = FakeConsumer([[]])
    repository = FakeRepository()
    dead_letters = FakeDeadLetterStore()
    service = _service(
        consumer,
        repository,
        FakeOffsetStore(),
        dead_letters,
    )

    task = asyncio.create_task(service.run())
    await asyncio.sleep(0.01)
    await service.stop()
    await asyncio.wait_for(task, timeout=1)

    assert consumer.started
    assert consumer.stopped
    assert repository.started
    assert repository.stopped
    assert dead_letters.started
    assert dead_letters.stopped


async def test_run_retries_dependency_start() -> None:
    """Сбой запуска зависимости приводит к повтору, а не к падению."""
    consumer = FakeConsumer([[_valid_message()]])
    repository = FakeRepository(fail_start_times=1)
    offsets = FakeOffsetStore()
    service = _service(
        consumer,
        repository,
        offsets,
        FakeDeadLetterStore(),
    )

    task = asyncio.create_task(service.run())
    for _ in range(200):
        if offsets.commits >= 1:
            break
        await asyncio.sleep(0.01)
    await service.stop()
    await asyncio.wait_for(task, timeout=2)

    assert repository.started
    assert len(repository.batches) == 1


async def test_dead_letter_retries_until_success() -> None:
    """Сбой отправки в DLQ повторяется до успеха."""
    dlq = _FlakyDeadLetterStore(fail_times=1)
    service = _service(
        FakeConsumer([[]]),
        FakeRepository(),
        FakeOffsetStore(),
        dlq,
    )

    ok = await service._save_dead_letter(b"bad", "reason")

    assert ok is True
    assert len(dlq.saved) == 1


async def test_dead_letter_returns_false_when_stopped() -> None:
    """При постоянном сбое DLQ запись не подтверждается после остановки."""
    service = _service(
        FakeConsumer([[]]),
        FakeRepository(),
        FakeOffsetStore(),
        _FailingDeadLetterStore(),
    )

    task = asyncio.create_task(service._save_dead_letter(b"bad", "reason"))
    await asyncio.sleep(0.02)
    await service.stop()
    ok = await asyncio.wait_for(task, timeout=1)

    assert ok is False


async def test_iteration_commits_after_dlq_recovers() -> None:
    """Прогресс фиксируется только после успешной записи в DLQ."""
    repository = FakeRepository()
    offsets = FakeOffsetStore()
    dlq = _FlakyDeadLetterStore(fail_times=1)
    service = _service(
        FakeConsumer([[b"not a json", _valid_message()]]),
        repository,
        offsets,
        dlq,
    )

    await service._iteration()

    assert offsets.commits == 1
    assert len(repository.batches) == 1
