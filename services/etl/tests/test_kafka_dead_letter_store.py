"""Тесты адаптера записи непригодных событий в Kafka."""

import json
from typing import ClassVar

import pytest

from etl.infrastructure.kafka import dead_letter_store as dlq_module
from etl.infrastructure.kafka.dead_letter_store import KafkaDeadLetterStore
from etl.infrastructure.settings import KafkaSettings


class _FakeAIOKafkaProducer:
    """Подменяет AIOKafkaProducer, не требуя брокера."""

    instances: ClassVar[list["_FakeAIOKafkaProducer"]] = []
    fail_start_times: ClassVar[int] = 0

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.sent: list[tuple[str, bytes]] = []
        self.started = False
        self.stopped = False
        _FakeAIOKafkaProducer.instances.append(self)

    async def start(self) -> None:
        if _FakeAIOKafkaProducer.fail_start_times > 0:
            _FakeAIOKafkaProducer.fail_start_times -= 1
            raise RuntimeError("broker down")
        self.started = True

    async def send_and_wait(self, topic: str, value: bytes) -> None:
        self.sent.append((topic, value))

    async def stop(self) -> None:
        self.stopped = True


def _install_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeAIOKafkaProducer.instances.clear()
    _FakeAIOKafkaProducer.fail_start_times = 0
    monkeypatch.setattr(
        dlq_module,
        "AIOKafkaProducer",
        _FakeAIOKafkaProducer,
    )


async def test_save_publishes_message_with_reason(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Непригодное сообщение публикуется в DLQ-топик с причиной."""
    _install_fake(monkeypatch)
    settings = KafkaSettings()
    store = KafkaDeadLetterStore(settings)
    await store.start()
    fake = _FakeAIOKafkaProducer.instances[-1]

    await store.save(b'{"bad": true}', "bad payload")
    await store.stop()

    topic, value = fake.sent[0]
    assert topic == settings.dlq_topic
    payload = json.loads(value)
    assert payload["reason"] == "bad payload"
    assert payload["raw"] == '{"bad": true}'
    assert fake.stopped


async def test_save_before_start_raises() -> None:
    """Публикация до запуска продюсера запрещена."""
    store = KafkaDeadLetterStore(KafkaSettings())
    with pytest.raises(RuntimeError):
        await store.save(b"x", "reason")


async def test_start_can_be_retried_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """После сбоя запуска повторный start() пересоздаёт продюсер."""
    _install_fake(monkeypatch)
    _FakeAIOKafkaProducer.fail_start_times = 1
    store = KafkaDeadLetterStore(KafkaSettings())

    with pytest.raises(RuntimeError):
        await store.start()

    await store.start()

    assert _FakeAIOKafkaProducer.instances[-1].started
    assert len(_FakeAIOKafkaProducer.instances) == 2
