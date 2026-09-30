"""Реализация порта Clock на основе системных часов."""

from datetime import UTC, datetime

from etl.application.ports.clock import Clock


class SystemClock(Clock):
    """Возвращает текущее время из системных часов."""

    def now(self) -> datetime:
        """Возвращает текущее время в UTC."""
        return datetime.now(UTC)
