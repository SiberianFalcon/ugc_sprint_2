"""Порт записи событий в аналитическое хранилище."""

from collections.abc import Mapping, Sequence
from typing import Protocol


class EventRepository(Protocol):
    """Записывает пакет событий в аналитическое хранилище."""

    async def start(self) -> None:
        """Инициализирует соединение с аналитическим хранилищем."""
        ...

    async def save_batch(self, events: Sequence[Mapping[str, object]]) -> None:
        """Записывает пакет нормализованных событий."""
        ...

    async def stop(self) -> None:
        """Закрывает соединение с аналитическим хранилищем."""
        ...
