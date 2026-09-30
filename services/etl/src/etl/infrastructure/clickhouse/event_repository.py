"""Адаптер записи событий в ClickHouse."""

import json
from collections.abc import Mapping, Sequence
from contextlib import suppress
from datetime import UTC, datetime

import clickhouse_connect
from clickhouse_connect.driver.asyncclient import AsyncClient

from etl.infrastructure.settings import ClickHouseSettings


_ADMIN_DATABASE = "default"

_COLUMNS = (
    "event_id",
    "user_id",
    "event_type",
    "event_time",
    "page_url",
    "element_id",
    "duration",
    "event_name",
    "extra",
)


class ClickHouseEventRepository:
    """Записывает пакет событий в ClickHouse."""

    def __init__(self, settings: ClickHouseSettings) -> None:
        self._settings = settings
        self._client: AsyncClient | None = None

    async def start(self) -> None:
        """Создаёт клиент, базу данных и таблицу событий."""
        if self._client is not None:
            return
        client = await clickhouse_connect.get_async_client(
            host=self._settings.host,
            port=self._settings.port,
            username=self._settings.username,
            password=self._settings.password,
            database=_ADMIN_DATABASE,
        )
        try:
            await client.command(
                f"CREATE DATABASE IF NOT EXISTS {self._settings.database}"
            )
            await client.command(self._create_table_query())
        except Exception:
            with suppress(Exception):
                await client.close()
            raise
        self._client = client

    async def save_batch(self, events: Sequence[Mapping[str, object]]) -> None:
        """Записывает пакет нормализованных событий."""
        client = self._require_client()
        if not events:
            return
        rows = [_to_row(event) for event in events]
        await client.insert(
            self._table,
            rows,
            column_names=list(_COLUMNS),
        )

    async def stop(self) -> None:
        """Закрывает клиент ClickHouse."""
        if self._client is None:
            return
        await self._client.close()
        self._client = None

    @property
    def _table(self) -> str:
        return f"{self._settings.database}.{self._settings.table}"

    def _create_table_query(self) -> str:
        return (
            f"CREATE TABLE IF NOT EXISTS {self._table} (\n"
            "    event_id String,\n"
            "    user_id String,\n"
            "    event_type LowCardinality(String),\n"
            "    event_time DateTime64(3, 'UTC'),\n"
            "    page_url Nullable(String),\n"
            "    element_id Nullable(String),\n"
            "    duration Nullable(UInt32),\n"
            "    event_name Nullable(String),\n"
            "    extra String\n"
            ")\n"
            "ENGINE = ReplacingMergeTree\n"
            "ORDER BY event_id"
        )

    def _require_client(self) -> AsyncClient:
        if self._client is None:
            raise RuntimeError("Клиент ClickHouse не запущен.")
        return self._client


def _to_row(event: Mapping[str, object]) -> list[object]:
    extra = event.get("extra", {})
    return [
        str(event["event_id"]),
        str(event["user_id"]),
        str(event["event_type"]),
        _to_datetime(event["event_time"]),
        _optional_str(event.get("page_url")),
        _optional_str(event.get("element_id")),
        _optional_int(event.get("duration")),
        _optional_str(event.get("event_name")),
        json.dumps(extra, ensure_ascii=False, default=str),
    ]


def _to_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value)
    else:
        raise ValueError("Некорректное значение времени события.")
    if parsed.tzinfo is None:
        return parsed
    return parsed.astimezone(UTC).replace(tzinfo=None)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Длительность должна быть целым числом.")
    return value
