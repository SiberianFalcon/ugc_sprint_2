"""Порт чтения событий из очереди сообщений."""

from collections.abc import Sequence
from typing import Protocol


class EventConsumer(Protocol):
    """Читает события из очереди сообщений."""

    async def start(self) -> None:
        """Инициализирует соединение с очередью."""
        ...

    async def poll_batch(
        self, max_size: int, timeout_seconds: float
    ) -> Sequence[bytes]:
        """Возвращает пакет прочитанных сообщений."""
        ...

    async def stop(self) -> None:
        """Закрывает соединение с очередью."""
        ...
