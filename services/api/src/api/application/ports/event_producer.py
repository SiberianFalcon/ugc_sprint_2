"""Порт публикации событий в очередь сообщений."""

from typing import Protocol

from api.domain.event.event import Event


class EventProducer(Protocol):
    """Публикует события в очередь сообщений."""

    async def start(self) -> None:
        """Инициализирует соединение с очередью."""
        ...

    async def publish(self, event: Event, key: str) -> None:
        """Публикует событие с указанным ключом."""
        ...

    async def stop(self) -> None:
        """Закрывает соединение с очередью."""
        ...
