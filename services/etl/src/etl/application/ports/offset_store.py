"""Порт фиксации прогресса чтения очереди."""

from typing import Protocol


class OffsetStore(Protocol):
    """Фиксирует прогресс чтения очереди сообщений."""

    async def commit(self) -> None:
        """Фиксирует текущий прогресс чтения."""
        ...
