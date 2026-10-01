"""Системные часы."""

from datetime import UTC, datetime


class SystemClock:
    """Возвращает текущее время в UTC."""

    def now(self) -> datetime:
        """Возвращает текущий момент времени с часовым поясом."""
        return datetime.now(UTC)
