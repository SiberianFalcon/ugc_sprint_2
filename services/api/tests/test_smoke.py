"""Дымовой тест инфраструктурных зависимостей API-сервиса."""

from api.infrastructure.clock import SystemClock


def test_clock_returns_time_with_timezone() -> None:
    """Проверяет, что часы возвращают время с часовым поясом."""
    moment = SystemClock().now()
    assert moment.tzinfo is not None
