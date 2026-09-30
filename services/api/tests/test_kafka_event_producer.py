"""Тесты продюсера Kafka (проверка доступности)."""

from typing import ClassVar

import pytest

from api.infrastructure.kafka import event_producer as producer_module
from api.infrastructure.kafka.event_producer import KafkaEventProducer
from api.infrastructure.settings import KafkaSettings


class _FakeAIOKafkaProducer:
    """Подменяет AIOKafkaProducer, не требуя брокера."""

    instances: ClassVar[list["_FakeAIOKafkaProducer"]] = []
    fail_start_times: ClassVar[int] = 0

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.partitions: set[int] = set()
        self.partitions_error: Exception | None = None
        self.started = False
        self.stopped = False
        _FakeAIOKafkaProducer.instances.append(self)

    async def start(self) -> None:
        if _FakeAIOKafkaProducer.fail_start_times > 0:
            _FakeAIOKafkaProducer.fail_start_times -= 1
            raise RuntimeError("broker down")
        self.started = True

    async def partitions_for(self, topic: str) -> set[int]:
        if self.partitions_error is not None:
            raise self.partitions_error
        return self.partitions

    async def stop(self) -> None:
        self.stopped = True


def _install_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeAIOKafkaProducer.instances.clear()
    _FakeAIOKafkaProducer.fail_start_times = 0
    monkeypatch.setattr(
        producer_module, "AIOKafkaProducer", _FakeAIOKafkaProducer
    )


async def test_check_false_before_start() -> None:
    """До запуска продюсера проверка недоступна."""
    producer = KafkaEventProducer(KafkaSettings())
    assert await producer.check() is False


async def test_check_true_when_metadata_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """При доступном брокере проверка успешна."""
    _install_fake(monkeypatch)
    producer = KafkaEventProducer(KafkaSettings())
    await producer.start()
    assert await producer.check() is True


async def test_check_false_when_metadata_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """При ошибке получения метаданных проверка неуспешна."""
    _install_fake(monkeypatch)
    producer = KafkaEventProducer(KafkaSettings())
    await producer.start()
    fake = _FakeAIOKafkaProducer.instances[-1]
    fake.partitions_error = RuntimeError("broker down")
    assert await producer.check() is False


async def test_start_can_be_retried_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """После сбоя запуска повторный start() действительно перезапускает."""
    _install_fake(monkeypatch)
    _FakeAIOKafkaProducer.fail_start_times = 1
    producer = KafkaEventProducer(KafkaSettings())

    with pytest.raises(RuntimeError):
        await producer.start()

    await producer.start()

    assert await producer.check() is True
    assert len(_FakeAIOKafkaProducer.instances) == 2
