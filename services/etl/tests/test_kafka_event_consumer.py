"""Тесты адаптера чтения событий из Kafka."""

from typing import ClassVar

import pytest
from aiokafka.admin import NewTopic

from etl.infrastructure.kafka import event_consumer as event_consumer_module
from etl.infrastructure.kafka.event_consumer import KafkaEventConsumer
from etl.infrastructure.settings import KafkaSettings


class _FakeRecord:
    def __init__(self, value: object) -> None:
        self.value = value


class _FakeAdminClient:
    """Подменяет AIOKafkaAdminClient, не требуя брокера."""

    instances: ClassVar[list["_FakeAdminClient"]] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.created: list[NewTopic] = []
        self.closed = False
        _FakeAdminClient.instances.append(self)

    async def start(self) -> None:
        return None

    async def create_topics(self, topics: list[NewTopic]) -> None:
        self.created.extend(topics)

    async def close(self) -> None:
        self.closed = True


class _FakeAIOKafkaConsumer:
    """Подменяет AIOKafkaConsumer, не требуя брокера."""

    instances: ClassVar[list["_FakeAIOKafkaConsumer"]] = []
    fail_start_times: ClassVar[int] = 0

    def __init__(self, *topics: str, **kwargs: object) -> None:
        self.topics = topics
        self.kwargs = kwargs
        self.batches: dict[str, list[_FakeRecord]] = {}
        self.started = False
        self.stopped = False
        self.commits = 0
        self.getmany_calls: list[dict[str, int]] = []
        _FakeAIOKafkaConsumer.instances.append(self)

    async def start(self) -> None:
        if _FakeAIOKafkaConsumer.fail_start_times > 0:
            _FakeAIOKafkaConsumer.fail_start_times -= 1
            raise RuntimeError("broker down")
        self.started = True

    async def getmany(self, **kwargs: int) -> dict[str, list[_FakeRecord]]:
        self.getmany_calls.append(kwargs)
        return self.batches

    async def commit(self) -> None:
        self.commits += 1

    async def stop(self) -> None:
        self.stopped = True


def _install_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeAIOKafkaConsumer.instances.clear()
    _FakeAIOKafkaConsumer.fail_start_times = 0
    _FakeAdminClient.instances.clear()
    monkeypatch.setattr(
        event_consumer_module,
        "AIOKafkaConsumer",
        _FakeAIOKafkaConsumer,
    )
    monkeypatch.setattr(
        event_consumer_module,
        "AIOKafkaAdminClient",
        _FakeAdminClient,
    )


async def test_start_creates_consumer_with_expected_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Консьюмер создаётся с ручной фиксацией и чтением с начала."""
    _install_fake(monkeypatch)
    settings = KafkaSettings()
    consumer = KafkaEventConsumer(settings)

    await consumer.start()

    fake = _FakeAIOKafkaConsumer.instances[-1]
    assert fake.started
    assert fake.topics == (settings.topic,)
    assert fake.kwargs["group_id"] == settings.group_id
    assert fake.kwargs["enable_auto_commit"] is False
    assert fake.kwargs["auto_offset_reset"] == "earliest"


async def test_start_creates_topic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Перед запуском консьюмера создаётся топик событий."""
    _install_fake(monkeypatch)
    settings = KafkaSettings()

    await KafkaEventConsumer(settings).start()

    admin = _FakeAdminClient.instances[-1]
    assert [topic.name for topic in admin.created] == [settings.topic]
    assert admin.closed


async def test_poll_batch_returns_message_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Пакет разворачивается в плоский список значений."""
    _install_fake(monkeypatch)
    consumer = KafkaEventConsumer(KafkaSettings())
    await consumer.start()
    fake = _FakeAIOKafkaConsumer.instances[-1]
    fake.batches = {
        "tp-1": [_FakeRecord(b"a"), _FakeRecord(b"b")],
        "tp-2": [_FakeRecord(None)],
    }

    messages = await consumer.poll_batch(10, 2.0)

    assert list(messages) == [b"a", b"b"]
    assert fake.getmany_calls[-1] == {"timeout_ms": 2000, "max_records": 10}


async def test_commit_and_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Фиксация прогресса и остановка делегируются консьюмеру."""
    _install_fake(monkeypatch)
    consumer = KafkaEventConsumer(KafkaSettings())
    await consumer.start()
    fake = _FakeAIOKafkaConsumer.instances[-1]

    await consumer.commit()
    await consumer.stop()

    assert fake.commits == 1
    assert fake.stopped


async def test_poll_before_start_raises() -> None:
    """Обращение к незапущенному консьюмеру запрещено."""
    consumer = KafkaEventConsumer(KafkaSettings())
    with pytest.raises(RuntimeError):
        await consumer.poll_batch(1, 0.1)


async def test_start_can_be_retried_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """После сбоя запуска повторный start() пересоздаёт консьюмер."""
    _install_fake(monkeypatch)
    _FakeAIOKafkaConsumer.fail_start_times = 1
    consumer = KafkaEventConsumer(KafkaSettings())

    with pytest.raises(RuntimeError):
        await consumer.start()

    await consumer.start()

    assert _FakeAIOKafkaConsumer.instances[-1].started
    assert len(_FakeAIOKafkaConsumer.instances) == 2
