"""Порт фиксации событий, непригодных к обработке."""

from typing import Protocol


class DeadLetterStore(Protocol):
    """Фиксирует события, непригодные к обработке."""

    async def start(self) -> None:
        """Инициализирует соединение с хранилищем непригодных событий."""
        ...

    async def save(self, raw: bytes, reason: str) -> None:
        """Сохраняет непригодное событие и причину отказа."""
        ...

    async def stop(self) -> None:
        """Закрывает соединение с хранилищем непригодных событий."""
        ...
