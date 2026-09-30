"""Тесты адаптера записи событий в ClickHouse."""

import json
from datetime import datetime
from typing import ClassVar

import pytest

from etl.infrastructure.clickhouse import event_repository as repository_module
from etl.infrastructure.clickhouse.event_repository import (
    ClickHouseEventRepository,
)
from etl.infrastructure.settings import ClickHouseSettings


class _FakeClient:
    fail_command_times: ClassVar[int] = 0

    def __init__(self, **kwargs: object) -> None:
        self.connect_kwargs = kwargs
        self.commands: list[str] = []
        self.inserts: list[tuple[str, list[list[object]], list[str]]] = []
        self.closed = False

    async def command(self, query: str) -> None:
        if _FakeClient.fail_command_times > 0:
            _FakeClient.fail_command_times -= 1
            raise RuntimeError("schema failed")
        self.commands.append(query)

    async def insert(
        self,
        table: str,
        data: list[list[object]],
        column_names: list[str],
    ) -> None:
        self.inserts.append((table, data, column_names))

    async def close(self) -> None:
        self.closed = True


class _FakeFactory:
    instances: ClassVar[list[_FakeClient]] = []

    @classmethod
    async def create(cls, **kwargs: object) -> _FakeClient:
        client = _FakeClient(**kwargs)
        cls.instances.append(client)
        return client


def _install_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeFactory.instances.clear()
    _FakeClient.fail_command_times = 0
    monkeypatch.setattr(
        repository_module.clickhouse_connect,
        "get_async_client",
        _FakeFactory.create,
    )


def _record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "event_id": "event-1",
        "user_id": "user-1",
        "event_type": "click",
        "event_time": "2024-01-01T00:00:00+00:00",
        "page_url": "/movie",
        "element_id": "play",
        "extra": {},
    }
    record.update(overrides)
    return record


async def test_start_creates_database_and_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Старт создаёт базу данных и таблицу событий."""
    _install_fake(monkeypatch)
    repository = ClickHouseEventRepository(ClickHouseSettings())

    await repository.start()

    client = _FakeFactory.instances[-1]
    assert client.connect_kwargs["database"] == "default"
    assert any(
        "CREATE DATABASE IF NOT EXISTS ugc" in query
        for query in client.commands
    )
    table_ddl = client.commands[-1]
    assert "CREATE TABLE IF NOT EXISTS ugc.events" in table_ddl
    assert "ReplacingMergeTree" in table_ddl
    assert "ORDER BY event_id" in table_ddl


async def test_save_batch_maps_record_to_columns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Запись раскладывается по колонкам, лишние поля уходят в extra."""
    _install_fake(monkeypatch)
    repository = ClickHouseEventRepository(ClickHouseSettings())
    await repository.start()
    client = _FakeFactory.instances[-1]

    await repository.save_batch([_record(extra={"extra_field": "x"})])

    table, data, columns = client.inserts[0]
    assert table == "ugc.events"
    assert columns[0] == "event_id"
    assert len(columns) == 9
    row = data[0]
    assert row[0] == "event-1"
    assert row[1] == "user-1"
    assert row[2] == "click"
    assert row[3] == datetime(2024, 1, 1)
    assert row[4] == "/movie"
    assert row[5] == "play"
    assert row[6] is None
    assert row[7] is None
    extra = row[8]
    assert isinstance(extra, str)
    assert json.loads(extra) == {"extra_field": "x"}


async def test_save_batch_handles_page_view_and_custom(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Просмотр сохраняет duration, кастомное событие — имя и extra."""
    _install_fake(monkeypatch)
    repository = ClickHouseEventRepository(ClickHouseSettings())
    await repository.start()
    client = _FakeFactory.instances[-1]

    await repository.save_batch(
        [
            _record(
                event_id="e1",
                event_type="page_view",
                element_id=None,
                duration=30,
            ),
            _record(
                event_id="e2",
                event_type="custom",
                page_url=None,
                element_id=None,
                event_name="buy",
                extra={"product_id": "p1"},
            ),
        ]
    )

    _, data, _ = client.inserts[0]
    assert data[0][6] == 30
    assert data[1][7] == "buy"
    extra = data[1][8]
    assert isinstance(extra, str)
    assert json.loads(extra) == {"product_id": "p1"}


async def test_save_batch_skips_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Пустой пакет не приводит к вставке."""
    _install_fake(monkeypatch)
    repository = ClickHouseEventRepository(ClickHouseSettings())
    await repository.start()
    client = _FakeFactory.instances[-1]

    await repository.save_batch([])

    assert client.inserts == []


async def test_stop_closes_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Остановка закрывает клиент ClickHouse."""
    _install_fake(monkeypatch)
    repository = ClickHouseEventRepository(ClickHouseSettings())
    await repository.start()
    client = _FakeFactory.instances[-1]

    await repository.stop()

    assert client.closed


async def test_save_before_start_raises() -> None:
    """Запись до запуска клиента запрещена."""
    repository = ClickHouseEventRepository(ClickHouseSettings())
    with pytest.raises(RuntimeError):
        await repository.save_batch([_record()])


async def test_start_can_be_retried_after_schema_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """После сбоя создания схемы повторный start() пересоздаёт клиент."""
    _install_fake(monkeypatch)
    _FakeClient.fail_command_times = 1
    repository = ClickHouseEventRepository(ClickHouseSettings())

    with pytest.raises(RuntimeError):
        await repository.start()

    await repository.start()

    assert _FakeFactory.instances[-1].commands
    assert len(_FakeFactory.instances) == 2
