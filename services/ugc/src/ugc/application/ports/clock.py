"""Порт доступа к текущему времени."""

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Предоставляет текущее время приложению."""

    def now(self) -> datetime:
        """Возвращает текущее время."""
        ...
